import re

from app.llm.types import RouteDecision

MAX_QUANTITY = 10
MAX_COMPARED = 4
MAX_PRICE_CENTS = 10_000_000
ORDER_ID_PATTERN = re.compile(r"^ORD-\d{1,9}$")


def _price_cents(dollars: float | None) -> int | None:
    if dollars is None or dollars < 0:
        return None
    return min(round(dollars * 100), MAX_PRICE_CENTS)


def _known(value: str | None, allowed: set[str]) -> str | None:
    if value is None:
        return None
    matches = [candidate for candidate in allowed if candidate.lower() == value.strip().lower()]
    return matches[0] if matches else None


def sanitize_decision(decision: RouteDecision, catalog: list[dict]) -> dict:
    known_ids = {p["id"] for p in catalog}
    quantities: dict[str, int] = {}
    for item in decision.items:
        if item.product_id in known_ids:
            quantities[item.product_id] = min(max(item.quantity, 1), MAX_QUANTITY)
    order_id = (decision.order_id or "").strip().upper()
    return {
        "on_topic": decision.on_topic,
        "skill": decision.skill,
        "filters": {
            "category": _known(decision.category, {p["category"] for p in catalog}),
            "brand": _known(decision.brand, {p["brand"] for p in catalog}),
            "min_price_cents": _price_cents(decision.min_price),
            "max_price_cents": _price_cents(decision.max_price),
        },
        "items": [{"product_id": pid, "quantity": qty} for pid, qty in quantities.items()],
        "product_ids": list(dict.fromkeys(pid for pid in decision.product_ids if pid in known_ids))[
            :MAX_COMPARED
        ],
        "order_id": order_id if ORDER_ID_PATTERN.fullmatch(order_id) else None,
        "return_action": decision.return_action or "return",
    }
