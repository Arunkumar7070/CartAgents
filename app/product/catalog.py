import json
import os
from pathlib import Path

_DEFAULT_CATALOG_PATH = Path(__file__).resolve().parents[2] / "data" / "products.json"


def catalog_path() -> Path:
    override = os.environ.get("PRODUCTS_CATALOG_PATH")
    return Path(override) if override else _DEFAULT_CATALOG_PATH


def load_catalog() -> list[dict]:
    with catalog_path().open(encoding="utf-8") as f:
        raw_products = json.load(f)
    return [
        {
            "id": p["id"],
            "name": p["name"],
            "category": p["category"],
            "brand": p["brand"],
            "price_cents": round(p["price"] * 100),
            "stock": p["stock"],
            "specs": p["specs"],
            "description": p["description"],
        }
        for p in raw_products
    ]
