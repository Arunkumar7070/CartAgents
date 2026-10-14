from typing import Annotated, Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    confirm_token: str | None = Field(default=None, max_length=64)


class ProductCard(BaseModel):
    id: str
    name: str
    brand: str
    category: str
    price_cents: int
    stock: int
    specs: str
    description: str


class TextBlock(BaseModel):
    type: Literal["text"] = "text"
    markdown: str


class ProductCardsBlock(BaseModel):
    type: Literal["product_cards"] = "product_cards"
    products: list[ProductCard]


class ComparisonRow(BaseModel):
    attribute: str
    values: list[str]
    differs: bool


class ComparisonBlock(BaseModel):
    type: Literal["comparison"] = "comparison"
    products: list[ProductCard]
    rows: list[ComparisonRow]


class AppliedFilter(BaseModel):
    field: str
    value: str | int


class FiltersBlock(BaseModel):
    type: Literal["filters"] = "filters"
    applied: list[AppliedFilter]


class CartLine(BaseModel):
    product_id: str
    name: str
    category: str
    quantity: int
    unit_price_cents: int
    line_total_cents: int


class CartBlock(BaseModel):
    type: Literal["cart"] = "cart"
    lines: list[CartLine]
    subtotal_cents: int
    shipping_cents: int
    tax_cents: int
    total_cents: int
    cart_hash: str


class ConfirmationBlock(BaseModel):
    type: Literal["confirmation"] = "confirmation"
    action: Literal["order", "cancel", "return"]
    prompt: str


class OrderLine(BaseModel):
    product_id: str
    name: str
    category: str
    quantity: int
    unit_price_cents: int


class OrderBlock(BaseModel):
    type: Literal["order"] = "order"
    order_id: str
    status: str
    eta: str | None
    lines: list[OrderLine]
    total_cents: int
    cart_hash: str
    created_at: str


class Citation(BaseModel):
    source: Literal["catalog", "policy"]
    ref: str
    quote: str


class CitationsBlock(BaseModel):
    type: Literal["citations"] = "citations"
    items: list[Citation]


Block = Annotated[
    TextBlock
    | ProductCardsBlock
    | ComparisonBlock
    | FiltersBlock
    | CartBlock
    | ConfirmationBlock
    | OrderBlock
    | CitationsBlock,
    Field(discriminator="type"),
]


class ChatResponse(BaseModel):
    session_id: str
    skill: str | None
    blocks: list[Block]
    pending_confirmation: bool
    confirm_token: str | None


class HealthResponse(BaseModel):
    status: Literal["ok", "unavailable"]
