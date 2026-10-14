from datetime import datetime

from app.models import (
    CartBlock,
    Citation,
    CitationsBlock,
    ComparisonBlock,
    ComparisonRow,
    ConfirmationBlock,
    FiltersBlock,
    OrderBlock,
    ProductCard,
    ProductCardsBlock,
    TextBlock,
)
from app.order.lifecycle import fulfilment_status
from app.order.policy import POLICY_CLAUSES
from app.order.pricing import Cart, format_cents

_COMPARED_ATTRIBUTES = (
    ("Price", lambda p: format_cents(p["price_cents"])),
    ("Brand", lambda p: p["brand"]),
    ("Category", lambda p: p["category"]),
    ("In stock", lambda p: str(p["stock"])),
    ("Specs", lambda p: p["specs"]),
)


def text(markdown: str) -> dict:
    return TextBlock(markdown=markdown).model_dump()


def product_cards(products: list[dict]) -> dict:
    return ProductCardsBlock(products=[ProductCard(**p) for p in products]).model_dump()


def comparison(products: list[dict]) -> dict:
    rows = []
    for attribute, value_of in _COMPARED_ATTRIBUTES:
        values = [value_of(p) for p in products]
        rows.append(ComparisonRow(attribute=attribute, values=values, differs=len(set(values)) > 1))
    return ComparisonBlock(products=[ProductCard(**p) for p in products], rows=rows).model_dump()


def filters(applied: list[dict]) -> dict:
    return FiltersBlock(applied=applied).model_dump()


def cart(cart_data: Cart) -> dict:
    return CartBlock(**cart_data).model_dump()


def confirmation(action: str, prompt: str) -> dict:
    return ConfirmationBlock(action=action, prompt=prompt).model_dump()


def order(order_row: dict, now: datetime) -> dict:
    if order_row["status"] == "placed":
        fulfilment = fulfilment_status(order_row["created_at"], now)
        status, eta = fulfilment.stage, fulfilment.eta
    else:
        status, eta = order_row["status"], None
    return OrderBlock(
        order_id=order_row["id"],
        status=status,
        eta=eta,
        lines=order_row["lines"],
        total_cents=order_row["total_cents"],
        cart_hash=order_row["cart_hash"],
        created_at=order_row["created_at"].isoformat(),
    ).model_dump()


def citations(products: list[dict], clauses: list[str]) -> dict:
    items = [
        Citation(source="catalog", ref=p["id"], quote=f"{p['name']} — {format_cents(p['price_cents'])}")
        for p in products
    ] + [Citation(source="policy", ref=clause, quote=POLICY_CLAUSES[clause]) for clause in clauses]
    return CitationsBlock(items=items).model_dump()
