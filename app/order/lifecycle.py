from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

# The demo runs on an accelerated clock so a visitor can watch an order move through every stage.
SHIPS_AFTER = timedelta(minutes=2)
DELIVERED_AFTER = timedelta(minutes=10)

Stage = Literal["processing", "shipped", "delivered"]


@dataclass(frozen=True)
class Fulfilment:
    stage: Stage
    delivered_at: datetime
    eta: str


def fulfilment_status(created_at: datetime, now: datetime) -> Fulfilment:
    delivered_at = created_at + DELIVERED_AFTER
    age = now - created_at
    if age < SHIPS_AFTER:
        return Fulfilment("processing", delivered_at, "Ships within 2 minutes")
    if age < DELIVERED_AFTER:
        minutes_left = max(1, round((delivered_at - now).total_seconds() / 60))
        return Fulfilment("shipped", delivered_at, f"Arrives in about {minutes_left} min")
    return Fulfilment("delivered", delivered_at, f"Delivered {delivered_at:%b %d, %H:%M} UTC")
