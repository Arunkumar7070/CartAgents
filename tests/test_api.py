import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from langchain_google_genai.chat_models import GoogleAPIError

from app.llm.types import OrderItem
from tests.conftest import decision

pytestmark = pytest.mark.anyio

SESSION_HEADER = "X-Session-Id"


def _block(body: dict, block_type: str) -> dict:
    return next(b for b in body["blocks"] if b["type"] == block_type)


def _block_types(body: dict) -> list[str]:
    return [b["type"] for b in body["blocks"]]


async def _chat(client: AsyncClient, message: str, session_id: str | None = None, token: str | None = None):
    headers = {SESSION_HEADER: session_id} if session_id else {}
    return await client.post("/chat", json={"message": message, "confirm_token": token}, headers=headers)


async def _draft_order(client: AsyncClient, route, quantity: int = 2) -> dict:
    with route(decision("order", items=[OrderItem(product_id="probook-15", quantity=quantity)])):
        response = await _chat(client, f"I want {quantity} ProBooks")
    assert response.status_code == 200
    return response.json()


async def test_qa_returns_answer_cards_and_citations(client: AsyncClient, route, qa_answer) -> None:
    with route(decision("qa")), qa_answer("The ProBook 15 is $1,299.99 and great for travel."):
        response = await _chat(client, "Tell me about the ProBook")
    body = response.json()
    assert response.status_code == 200
    assert body["skill"] == "qa"
    assert _block(body, "text")["markdown"].startswith("The ProBook 15")
    assert _block(body, "product_cards")["products"]
    assert _block(body, "citations")["items"][0]["source"] == "catalog"
    assert len(body["session_id"]) == 43


async def test_answer_with_invented_price_is_replaced_by_catalog_listing(
    client: AsyncClient, route, qa_answer
) -> None:
    with route(decision("qa")), qa_answer("Great news, the ProBook is only $1.00 today!"):
        body = (await _chat(client, "ProBook price?")).json()
    assert "$1.00" not in _block(body, "text")["markdown"]
    assert "Here is what I found in the catalog" in _block(body, "text")["markdown"]


async def test_cards_show_only_products_the_answer_mentions(client: AsyncClient, route, qa_answer) -> None:
    with route(decision("qa", category="laptops")), qa_answer("The UltraBook 13 Air is the lightest pick."):
        body = (await _chat(client, "light laptop")).json()
    assert [p["id"] for p in _block(body, "product_cards")["products"]] == ["ultrabook-13"]


async def test_price_filter_is_applied_and_reported(client: AsyncClient, route, qa_answer) -> None:
    with route(decision("qa", category="audio", max_price=150)), qa_answer("Here are some options."):
        body = (await _chat(client, "headphones under $150")).json()
    assert all(p["price_cents"] <= 15000 for p in _block(body, "product_cards")["products"])
    assert {"field": "max_price_cents", "value": 15000} in _block(body, "filters")["applied"]


async def test_second_turn_router_sees_first_turn_history(client: AsyncClient, route, qa_answer) -> None:
    with route(decision("qa")), qa_answer("We have three laptops."):
        first = (await _chat(client, "show me laptops")).json()
    with route(decision("qa")) as router, qa_answer("The UltraBook is cheaper."):
        await _chat(client, "the cheaper one?", session_id=first["session_id"])
    history = router.await_args.args[1]
    assert history == [
        {"role": "user", "content": "show me laptops"},
        {"role": "assistant", "content": "We have three laptops."},
    ]


async def test_off_topic_message_is_refused(client: AsyncClient, route) -> None:
    with route(decision("qa", on_topic=False)):
        body = (await _chat(client, "write me a python script")).json()
    assert _block_types(body) == ["text"]
    assert "only help with shopping" in _block(body, "text")["markdown"]


async def test_order_total_is_computed_from_catalog(client: AsyncClient, route) -> None:
    body = await _draft_order(client, route, quantity=2)
    cart = _block(body, "cart")
    assert cart["subtotal_cents"] == 259998
    assert cart["total_cents"] == 259998 + 20800
    assert body["pending_confirmation"] is True
    assert body["confirm_token"]


async def test_confirm_with_token_places_order(client: AsyncClient, route) -> None:
    draft = await _draft_order(client, route)
    body = (await _chat(client, "yes please", draft["session_id"], draft["confirm_token"])).json()
    order = _block(body, "order")
    assert order["order_id"] == "ORD-1000"
    assert order["status"] == "processing"
    assert body["pending_confirmation"] is False
    product = (await client.get("/products/probook-15")).json()
    assert product["stock"] == 3


async def test_yes_without_confirm_token_does_not_place_order(client: AsyncClient, route, qa_answer) -> None:
    draft = await _draft_order(client, route)
    with route(decision("qa")), qa_answer("Happy to help."):
        await _chat(client, "yes", draft["session_id"])
    orders = await client.get("/orders", headers={SESSION_HEADER: draft["session_id"]})
    assert orders.json() == []


async def test_another_session_cannot_confirm_a_pending_order(client: AsyncClient, route, qa_answer) -> None:
    draft = await _draft_order(client, route)
    with route(decision("qa")), qa_answer("Hello."):
        intruder = (await _chat(client, "hi")).json()
    with route(decision("qa")), qa_answer("Hello again."):
        await _chat(client, "yes", intruder["session_id"], draft["confirm_token"])
    for session_id in (draft["session_id"], intruder["session_id"]):
        assert (await client.get("/orders", headers={SESSION_HEADER: session_id})).json() == []


async def test_unclear_reply_reprompts_and_keeps_order_pending(client: AsyncClient, route) -> None:
    draft = await _draft_order(client, route)
    body = (await _chat(client, "hmm, not sure", draft["session_id"], draft["confirm_token"])).json()
    assert body["pending_confirmation"] is True
    assert "yes or no" in _block(body, "text")["markdown"]
    confirmed = (await _chat(client, "ok", draft["session_id"], body["confirm_token"])).json()
    assert _block(confirmed, "order")["order_id"] == "ORD-1000"


async def test_no_cancels_pending_order(client: AsyncClient, route) -> None:
    draft = await _draft_order(client, route)
    body = (await _chat(client, "no", draft["session_id"], draft["confirm_token"])).json()
    assert body["pending_confirmation"] is False
    assert "nothing was changed" in _block(body, "text")["markdown"]


async def test_order_exceeding_stock_is_refused_before_confirmation(client: AsyncClient, route) -> None:
    body = await _draft_order(client, route, quantity=9)
    assert body["pending_confirmation"] is False
    assert "only 5 in stock" in _block(body, "text")["markdown"]


async def test_track_lists_placed_orders(client: AsyncClient, route) -> None:
    draft = await _draft_order(client, route)
    await _chat(client, "yes", draft["session_id"], draft["confirm_token"])
    with route(decision("track")):
        body = (await _chat(client, "where is my order?", draft["session_id"])).json()
    assert _block(body, "order")["order_id"] == "ORD-1000"


async def test_cancel_processing_order_after_confirmation(client: AsyncClient, route) -> None:
    draft = await _draft_order(client, route)
    session_id = draft["session_id"]
    await _chat(client, "yes", session_id, draft["confirm_token"])
    with route(decision("returns", return_action="cancel")):
        proposal = (await _chat(client, "cancel my order", session_id)).json()
    assert proposal["pending_confirmation"] is True
    assert _block(proposal, "citations")["items"][0]["ref"] == "§1"
    done = (await _chat(client, "yes", session_id, proposal["confirm_token"])).json()
    assert _block(done, "order")["status"] == "cancelled"


async def test_return_of_undelivered_order_is_refused_with_policy_citation(
    client: AsyncClient, route
) -> None:
    draft = await _draft_order(client, route)
    session_id = draft["session_id"]
    await _chat(client, "yes", session_id, draft["confirm_token"])
    with route(decision("returns", return_action="return")):
        body = (await _chat(client, "return it", session_id)).json()
    assert body["pending_confirmation"] is False
    assert "not been delivered" in _block(body, "text")["markdown"]


async def test_compare_returns_side_by_side_rows(client: AsyncClient, route) -> None:
    with route(decision("compare", product_ids=["probook-15", "ultrabook-13"])):
        body = (await _chat(client, "compare ProBook and UltraBook")).json()
    comparison = _block(body, "comparison")
    assert [p["id"] for p in comparison["products"]] == ["probook-15", "ultrabook-13"]
    assert next(r for r in comparison["rows"] if r["attribute"] == "Price")["differs"] is True


async def test_unissued_session_id_is_rejected(client: AsyncClient) -> None:
    response = await _chat(client, "hello", session_id="a" * 43)
    assert response.status_code == 404


async def test_orders_endpoint_requires_a_session(client: AsyncClient) -> None:
    assert (await client.get("/orders")).status_code == 401


async def test_empty_message_rejected(client: AsyncClient) -> None:
    assert (await client.post("/chat", json={"message": ""})).status_code == 422


async def test_daily_budget_exhaustion_returns_429_with_retry_after(client_factory, route, qa_answer) -> None:
    async with client_factory(daily_llm_call_cap=1) as client:
        with route(decision("qa")), qa_answer("unused"):
            response = await _chat(client, "laptops?")
    assert response.status_code == 429
    assert int(response.headers["Retry-After"]) > 0
    assert "resets at 00:00 UTC" in response.json()["detail"]


async def test_cors_allows_only_listed_origins(client: AsyncClient) -> None:
    allowed = await client.get("/health", headers={"Origin": "http://localhost:5173"})
    denied = await client.get("/health", headers={"Origin": "https://evil.example"})
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "access-control-allow-origin" not in denied.headers


async def test_health_is_ok_when_index_exists(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_health_unavailable_when_index_built_with_another_model(client_factory) -> None:
    async with client_factory(embedding_model="some-other-model") as client:
        response = await client.get("/health")
    assert response.status_code == 503


async def test_stream_emits_session_steps_deltas_and_done(client: AsyncClient, route, qa_answer) -> None:
    with route(decision("qa")), qa_answer("Streaming answer."):
        response = await client.post("/chat/stream", json={"message": "laptops?"})
    events = [
        (
            chunk.split("\n")[0].removeprefix("event: "),
            json.loads(chunk.split("\n")[1].removeprefix("data: ")),
        )
        for chunk in response.text.strip().split("\n\n")
    ]
    names = [name for name, _ in events]
    assert names[0] == "session"
    assert names[-1] == "done"
    assert ("step", {"node": "search_products", "status": "start"}) in events
    assert events[-1][1]["skill"] == "qa"
    assert response.headers[SESSION_HEADER] == events[0][1]["session_id"]


async def test_products_endpoint_filters_by_category(client: AsyncClient) -> None:
    products = (await client.get("/products", params={"category": "laptops"})).json()
    assert products
    assert {p["category"] for p in products} == {"laptops"}


async def test_evals_endpoint_serves_published_results(client: AsyncClient, tmp_path, monkeypatch) -> None:
    results = tmp_path / "results.json"
    results.write_text(json.dumps({"routing": {"accuracy": 0.95}}))
    monkeypatch.setattr("app.main.EVAL_RESULTS_PATH", results)
    assert (await client.get("/evals")).json() == {"routing": {"accuracy": 0.95}}
    monkeypatch.setattr("app.main.EVAL_RESULTS_PATH", tmp_path / "missing.json")
    assert (await client.get("/evals")).status_code == 404


def _gemini_overloaded() -> AsyncMock:
    error = GoogleAPIError(503, {"error": {"code": 503, "message": "high demand", "status": "UNAVAILABLE"}})
    return patch("app.llm.skill_router.SkillRouter.decide", AsyncMock(side_effect=error))


async def test_gemini_overload_returns_503_with_retry_after(client: AsyncClient) -> None:
    with _gemini_overloaded():
        response = await _chat(client, "laptops?")
    assert response.status_code == 503
    assert response.headers["Retry-After"] == "15"
    assert "busy" in response.json()["detail"]


async def test_gemini_overload_during_stream_emits_upstream_busy_event(client: AsyncClient) -> None:
    with _gemini_overloaded():
        response = await client.post("/chat/stream", json={"message": "laptops?"})
    last_event = response.text.strip().split("\n\n")[-1]
    assert last_event.startswith("event: error")
    assert '"code": "upstream_busy"' in last_event
