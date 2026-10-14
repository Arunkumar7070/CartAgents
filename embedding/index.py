import asyncio
import sys

import psycopg
from dotenv import load_dotenv
from langchain_core.embeddings import Embeddings

from app.config.settings import Settings
from app.llm.gemini import build_embeddings
from app.product.catalog import load_catalog
from app.product.repository import embedding_literal

_UPSERT_PRODUCT_SQL = """
INSERT INTO products (id, name, category, brand, price_cents, stock, specs, description)
VALUES (%(id)s, %(name)s, %(category)s, %(brand)s, %(price_cents)s, %(stock)s, %(specs)s, %(description)s)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name, category = EXCLUDED.category, brand = EXCLUDED.brand,
    price_cents = EXCLUDED.price_cents, stock = EXCLUDED.stock,
    specs = EXCLUDED.specs, description = EXCLUDED.description
"""

_UPSERT_EMBEDDING_SQL = """
INSERT INTO product_embeddings (product_id, embedding_model, embedding)
VALUES (%s, %s, %s::vector)
ON CONFLICT (product_id, embedding_model) DO UPDATE SET embedding = EXCLUDED.embedding
"""


def product_to_text(product: dict) -> str:
    fields = ("name", "category", "brand", "specs", "description")
    return " | ".join(str(product[field]) for field in fields)


async def build_index(database_url: str, embeddings: Embeddings, embedding_model: str) -> int:
    products = load_catalog()
    vectors = await embeddings.aembed_documents([product_to_text(p) for p in products])
    async with await psycopg.AsyncConnection.connect(database_url) as conn, conn.transaction():
        async with conn.cursor() as cur:
            await cur.executemany(_UPSERT_PRODUCT_SQL, products)
            await cur.executemany(
                _UPSERT_EMBEDDING_SQL,
                [
                    (p["id"], embedding_model, embedding_literal(v))
                    for p, v in zip(products, vectors, strict=True)
                ],
            )
    return len(products)


if __name__ == "__main__":
    load_dotenv()
    settings = Settings.from_env()
    count = asyncio.run(
        build_index(
            settings.database_url,
            build_embeddings(settings.google_api_key, settings.embedding_model),
            settings.embedding_model,
        )
    )
    print(f"Indexed {count} products with {settings.embedding_model}.", file=sys.stderr)
