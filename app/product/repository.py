import re
from dataclasses import dataclass

from langchain_core.embeddings import Embeddings
from psycopg_pool import AsyncConnectionPool

from app.logger import setup_logger

logger = setup_logger("retrieval")

RRF_K = 60
CANDIDATES_PER_RANKER = 20

_PRODUCT_COLUMNS = "p.id, p.name, p.category, p.brand, p.price_cents, p.stock, p.specs, p.description"

_FILTER_CLAUSE = """
    (%(category)s::text IS NULL OR p.category = %(category)s)
    AND (%(brand)s::text IS NULL OR p.brand = %(brand)s)
    AND (%(min_price_cents)s::int IS NULL OR p.price_cents >= %(min_price_cents)s)
    AND (%(max_price_cents)s::int IS NULL OR p.price_cents <= %(max_price_cents)s)
"""

_HYBRID_SEARCH_SQL = f"""
WITH semantic AS (
    SELECT p.id, row_number() OVER (ORDER BY e.embedding <=> %(embedding)s::vector) AS rank
    FROM products p
    JOIN product_embeddings e ON e.product_id = p.id AND e.embedding_model = %(embedding_model)s
    WHERE {_FILTER_CLAUSE}
    ORDER BY e.embedding <=> %(embedding)s::vector
    LIMIT {CANDIDATES_PER_RANKER}
),
keyword AS (
    SELECT p.id, row_number() OVER (ORDER BY ts_rank_cd(p.search_tsv, q) DESC) AS rank
    FROM products p, to_tsquery('english', %(keywords)s) q
    WHERE %(keywords)s <> '' AND p.search_tsv @@ q AND {_FILTER_CLAUSE}
    LIMIT {CANDIDATES_PER_RANKER}
)
SELECT {_PRODUCT_COLUMNS},
       coalesce(1.0 / ({RRF_K} + s.rank), 0) + coalesce(1.0 / ({RRF_K} + k.rank), 0) AS score
FROM products p
LEFT JOIN semantic s ON s.id = p.id
LEFT JOIN keyword k ON k.id = p.id
WHERE s.id IS NOT NULL OR k.id IS NOT NULL
ORDER BY score DESC, p.id
LIMIT %(top_k)s
"""


@dataclass(frozen=True)
class SearchFilters:
    category: str | None = None
    brand: str | None = None
    min_price_cents: int | None = None
    max_price_cents: int | None = None

    def as_params(self) -> dict:
        return {
            "category": self.category,
            "brand": self.brand,
            "min_price_cents": self.min_price_cents,
            "max_price_cents": self.max_price_cents,
        }

    def applied(self) -> list[dict]:
        return [
            {"field": field, "value": value} for field, value in self.as_params().items() if value is not None
        ]


def keyword_query(text: str) -> str:
    return " | ".join(dict.fromkeys(re.findall(r"[a-z0-9]{2,}", text.lower())))


def embedding_literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{x:.7f}" for x in vector) + "]"


class ProductRepository:
    def __init__(
        self, pool: AsyncConnectionPool, embeddings: Embeddings, embedding_model: str, top_k: int
    ) -> None:
        self._pool = pool
        self._embeddings = embeddings
        self._embedding_model = embedding_model
        self._top_k = top_k

    async def search(self, query: str, filters: SearchFilters) -> list[dict]:
        embedding = await self._embeddings.aembed_query(query)
        params = {
            **filters.as_params(),
            "embedding": embedding_literal(embedding),
            "embedding_model": self._embedding_model,
            "keywords": keyword_query(query),
            "top_k": self._top_k,
        }
        async with self._pool.connection() as conn:
            rows = await (await conn.execute(_HYBRID_SEARCH_SQL, params)).fetchall()
        logger.info(
            "RETRIEVAL | top_k=%d | filters=%s | hits=%s",
            self._top_k,
            filters.applied(),
            [(row["id"], round(float(row["score"]), 4)) for row in rows],
        )
        return [{key: value for key, value in row.items() if key != "score"} for row in rows]

    async def find(self, filters: SearchFilters) -> list[dict]:
        sql = (
            f"SELECT {_PRODUCT_COLUMNS} FROM products p WHERE {_FILTER_CLAUSE} "
            "ORDER BY p.category, p.price_cents"
        )
        async with self._pool.connection() as conn:
            return await (await conn.execute(sql, filters.as_params())).fetchall()

    async def get_many(self, product_ids: list[str]) -> dict[str, dict]:
        sql = f"SELECT {_PRODUCT_COLUMNS} FROM products p WHERE p.id = ANY(%s)"
        async with self._pool.connection() as conn:
            rows = await (await conn.execute(sql, (product_ids,))).fetchall()
        return {row["id"]: row for row in rows}

    async def all(self) -> list[dict]:
        return await self.find(SearchFilters())

    async def embedded_product_count(self) -> int:
        async with self._pool.connection() as conn:
            row = await (
                await conn.execute(
                    "SELECT count(*) AS n FROM product_embeddings WHERE embedding_model = %s",
                    (self._embedding_model,),
                )
            ).fetchone()
        return row["n"]
