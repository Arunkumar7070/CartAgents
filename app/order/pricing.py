import hashlib
import json
from typing import TypedDict

FREE_SHIPPING_THRESHOLD_CENTS = 5000
FLAT_SHIPPING_CENTS = 599
TAX_RATE = 0.08


class CartLine(TypedDict):
    product_id: str
    name: str
    category: str
    quantity: int
    unit_price_cents: int
    line_total_cents: int


class Cart(TypedDict):
    lines: list[CartLine]
    subtotal_cents: int
    shipping_cents: int
    tax_cents: int
    total_cents: int
    cart_hash: str


def build_cart(selections: list[tuple[dict, int]]) -> Cart:
    lines: list[CartLine] = [
        {
            "product_id": product["id"],
            "name": product["name"],
            "category": product["category"],
            "quantity": quantity,
            "unit_price_cents": product["price_cents"],
            "line_total_cents": product["price_cents"] * quantity,
        }
        for product, quantity in selections
    ]
    subtotal = sum(line["line_total_cents"] for line in lines)
    shipping = 0 if subtotal >= FREE_SHIPPING_THRESHOLD_CENTS else FLAT_SHIPPING_CENTS
    tax = round(subtotal * TAX_RATE)
    total = subtotal + shipping + tax
    return {
        "lines": lines,
        "subtotal_cents": subtotal,
        "shipping_cents": shipping,
        "tax_cents": tax,
        "total_cents": total,
        "cart_hash": _cart_hash(lines, total),
    }


def _cart_hash(lines: list[CartLine], total_cents: int) -> str:
    canonical = json.dumps(
        {
            "lines": [[line["product_id"], line["quantity"], line["unit_price_cents"]] for line in lines],
            "total_cents": total_cents,
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def stock_shortfalls(selections: list[tuple[dict, int]]) -> list[str]:
    return [
        f"{product['name']} (only {product['stock']} in stock)"
        for product, quantity in selections
        if quantity > product["stock"]
    ]


def format_cents(cents: int) -> str:
    return f"${cents / 100:,.2f}"
