from typing import Literal

from pydantic import BaseModel, Field

Skill = Literal["qa", "order", "track", "returns", "compare"]


class OrderItem(BaseModel):
    product_id: str = Field(description="Exact catalog id of the product")
    quantity: int = Field(description="How many units the user wants; 1 if unspecified")


class RouteDecision(BaseModel):
    on_topic: bool = Field(description="False only for clearly blocked content")
    skill: Skill
    category: str | None = Field(default=None, description="Catalog category the user restricted to")
    brand: str | None = Field(default=None, description="Catalog brand the user restricted to")
    min_price: float | None = Field(default=None, description="Lower price bound in dollars")
    max_price: float | None = Field(default=None, description="Upper price bound in dollars")
    items: list[OrderItem] = Field(default_factory=list, description="Products to buy, for skill=order")
    product_ids: list[str] = Field(default_factory=list, description="Products to compare, for skill=compare")
    order_id: str | None = Field(default=None, description="Order id like ORD-1000 if the user named one")
    return_action: Literal["cancel", "return"] | None = Field(
        default=None, description="For skill=returns: cancel before shipping, or return/refund/exchange"
    )
