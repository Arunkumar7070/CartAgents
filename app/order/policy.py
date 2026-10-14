from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

from app.order.lifecycle import fulfilment_status

POLICY_CLAUSES: dict[str, str] = {
    "§1": "Orders can be cancelled free of charge until they ship. Shipped orders must be returned instead.",
    "§2": "Most items can be returned within 30 days of delivery in their original condition.",
    "§3": "Laptops, phones and tablets have a shorter 15-day return window.",
    "§4": (
        "Refunds go back to the original payment method within 5-7 business days of the return arriving. "
        "Shipping fees are refunded only for defective items."
    ),
    "§5": "Shipping is free on orders of $50.00 or more; otherwise a flat $5.99 applies. Sales tax is 8%.",
}

SHORT_WINDOW_CATEGORIES = frozenset({"laptops", "phones", "tablets"})
STANDARD_RETURN_WINDOW = timedelta(days=30)
SHORT_RETURN_WINDOW = timedelta(days=15)

ReturnAction = Literal["cancel", "return"]


@dataclass(frozen=True)
class Eligibility:
    allowed: bool
    clause: str
    reason: str


def check_eligibility(order: dict, action: ReturnAction, now: datetime) -> Eligibility:
    if order["status"] != "placed":
        return Eligibility(
            False, "§1", f"Order {order['id']} is already {order['status'].replace('_', ' ')}."
        )

    fulfilment = fulfilment_status(order["created_at"], now)
    if action == "cancel":
        if fulfilment.stage == "processing":
            return Eligibility(
                True, "§1", f"Order {order['id']} has not shipped yet, so it can be cancelled."
            )
        return Eligibility(
            False,
            "§1",
            f"Order {order['id']} has already shipped, so it can only be returned after delivery.",
        )

    if fulfilment.stage != "delivered":
        return Eligibility(
            False,
            "§1",
            f"Order {order['id']} has not been delivered yet. You can cancel it while it is processing.",
        )
    has_short_window_item = any(line["category"] in SHORT_WINDOW_CATEGORIES for line in order["lines"])
    window, clause = (SHORT_RETURN_WINDOW, "§3") if has_short_window_item else (STANDARD_RETURN_WINDOW, "§2")
    if now - fulfilment.delivered_at > window:
        return Eligibility(
            False, clause, f"Order {order['id']} is outside its {window.days}-day return window."
        )
    return Eligibility(True, clause, f"Order {order['id']} is within its {window.days}-day return window.")
