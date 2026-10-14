import pytest
from psycopg_pool import AsyncConnectionPool

from app.order.pricing import build_cart
from app.order.repository import OrderRepository, OutOfStockError
from app.product.repository import ProductRepository, SearchFilters
from app.session import BudgetExceededError, LlmBudget, SessionStore
from tests.conftest import EMBEDDING_MODEL, BagOfWordsEmbeddings

pytestmark = pytest.mark.anyio


@pytest.fixture
def products(pool: AsyncConnectionPool, fake_embeddings: BagOfWordsEmbeddings) -> ProductRepository:
    return ProductRepository(pool, fake_embeddings, EMBEDDING_MODEL, top_k=5)


async def _cart_for(products: ProductRepository, product_id: str, quantity: int):
    found = await products.get_many([product_id])
    return build_cart([(found[product_id], quantity)])


async def test_hybrid_search_applies_max_price_filter(products: ProductRepository) -> None:
    results = await products.search("laptop for work", SearchFilters(max_price_cents=100000))
    assert results
    assert all(p["price_cents"] <= 100000 for p in results)


async def test_hybrid_search_applies_category_filter(products: ProductRepository) -> None:
    results = await products.search("something good", SearchFilters(category="audio"))
    assert results
    assert {p["category"] for p in results} == {"audio"}


async def test_keyword_match_ranks_named_product_first(products: ProductRepository) -> None:
    results = await products.search("ProBook", SearchFilters())
    assert results[0]["id"] == "probook-15"


async def test_placing_order_decrements_stock(pool: AsyncConnectionPool, products: ProductRepository) -> None:
    session_id = await SessionStore(pool).create()
    order = await OrderRepository(pool).place(session_id, await _cart_for(products, "probook-15", 2))
    assert order["lines"][0]["quantity"] == 2
    assert (await products.get_many(["probook-15"]))["probook-15"]["stock"] == 3


async def test_cancelling_restocks_once(pool: AsyncConnectionPool, products: ProductRepository) -> None:
    session_id = await SessionStore(pool).create()
    orders = OrderRepository(pool)
    order = await orders.place(session_id, await _cart_for(products, "probook-15", 2))
    await orders.cancel(session_id, order["id"])
    cancelled_again = await orders.cancel(session_id, order["id"])
    assert cancelled_again["status"] == "cancelled"
    assert (await products.get_many(["probook-15"]))["probook-15"]["stock"] == 5


async def test_order_rejected_when_stock_runs_out_and_nothing_is_reserved(
    pool: AsyncConnectionPool, products: ProductRepository
) -> None:
    session_id = await SessionStore(pool).create()
    with pytest.raises(OutOfStockError):
        await OrderRepository(pool).place(session_id, await _cart_for(products, "probook-15", 6))
    assert (await products.get_many(["probook-15"]))["probook-15"]["stock"] == 5
    assert await OrderRepository(pool).find_by_session(session_id) == []


async def test_order_ids_unique_across_repository_restart(
    pool: AsyncConnectionPool, products: ProductRepository
) -> None:
    session_id = await SessionStore(pool).create()
    cart = await _cart_for(products, "probook-15", 1)
    first = await OrderRepository(pool).place(session_id, cart)
    second = await OrderRepository(pool).place(session_id, cart)
    assert first["id"] == "ORD-1000"
    assert second["id"] == "ORD-1001"


async def test_orders_are_scoped_to_their_session(
    pool: AsyncConnectionPool, products: ProductRepository
) -> None:
    sessions = SessionStore(pool)
    owner, stranger = await sessions.create(), await sessions.create()
    order = await OrderRepository(pool).place(owner, await _cart_for(products, "probook-15", 1))
    assert await OrderRepository(pool).get(stranger, order["id"]) is None


async def test_session_budget_stops_at_cap(pool: AsyncConnectionPool) -> None:
    session_id = await SessionStore(pool).create()
    budget = LlmBudget(pool, daily_cap=100, session_cap=2)
    await budget.spend(session_id)
    await budget.spend(session_id)
    with pytest.raises(BudgetExceededError) as error:
        await budget.spend(session_id)
    assert error.value.scope == "session"


async def test_daily_budget_is_shared_across_sessions(pool: AsyncConnectionPool) -> None:
    sessions = SessionStore(pool)
    budget = LlmBudget(pool, daily_cap=1, session_cap=100)
    await budget.spend(await sessions.create())
    with pytest.raises(BudgetExceededError) as error:
        await budget.spend(await sessions.create())
    assert error.value.scope == "daily"


async def test_unissued_session_id_does_not_exist(pool: AsyncConnectionPool) -> None:
    sessions = SessionStore(pool)
    assert not await sessions.exists("a" * 43)
    assert not await sessions.exists("test")
    assert await sessions.exists(await sessions.create())
