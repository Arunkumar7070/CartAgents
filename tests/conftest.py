import asyncio
import hashlib
import os
import re
from collections.abc import AsyncIterator, Callable
from unittest.mock import AsyncMock, patch

import psycopg
import pytest
from httpx import ASGITransport, AsyncClient
from langchain_core.embeddings import Embeddings
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.config.settings import Settings
from app.db.migrate import migrate
from app.llm.types import RouteDecision
from app.main import create_app
from embedding.index import build_index

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://cartagent:cartagent@localhost:5433/cartagent_test"
)
EMBEDDING_MODEL = "fake-embedding"

_TABLES = (
    "order_lines, orders, llm_usage, sessions, product_embeddings, products, "
    "checkpoints, checkpoint_blobs, checkpoint_writes"
)


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session")
def migrated_database() -> str:
    asyncio.run(migrate(TEST_DATABASE_URL))
    return TEST_DATABASE_URL


class BagOfWordsEmbeddings(Embeddings):
    def embed_query(self, text: str) -> list[float]:
        vector = [0.0] * 768
        for word in re.findall(r"[a-z0-9]+", text.lower()):
            vector[int(hashlib.md5(word.encode()).hexdigest(), 16) % 768] += 1.0
        vector[0] += 0.01
        return vector

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(text) for text in texts]


@pytest.fixture
def fake_embeddings() -> BagOfWordsEmbeddings:
    return BagOfWordsEmbeddings()


@pytest.fixture
async def seeded_database(migrated_database: str, fake_embeddings: BagOfWordsEmbeddings) -> str:
    async with await psycopg.AsyncConnection.connect(migrated_database, autocommit=True) as conn:
        await conn.execute(f"TRUNCATE {_TABLES} RESTART IDENTITY CASCADE")
        await conn.execute("ALTER SEQUENCE order_number_seq RESTART WITH 1000")
    await build_index(migrated_database, fake_embeddings, EMBEDDING_MODEL)
    return migrated_database


@pytest.fixture
async def pool(seeded_database: str) -> AsyncIterator[AsyncConnectionPool]:
    async with AsyncConnectionPool(
        seeded_database, kwargs={"autocommit": True, "row_factory": dict_row}, open=False
    ) as p:
        yield p


def make_settings(**overrides) -> Settings:
    defaults = dict(
        google_api_key="test-key",
        database_url=TEST_DATABASE_URL,
        embedding_model=EMBEDDING_MODEL,
        cors_origins=("http://localhost:5173",),
    )
    return Settings(**{**defaults, **overrides})


@pytest.fixture
def client_factory(
    seeded_database: str, fake_embeddings: BagOfWordsEmbeddings
) -> Callable[..., AsyncIterator[AsyncClient]]:
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def factory(**settings_overrides) -> AsyncIterator[AsyncClient]:
        app = create_app(make_settings(**settings_overrides), embeddings=fake_embeddings)
        async with app.router.lifespan_context(app):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                yield client

    return factory


@pytest.fixture
async def client(client_factory) -> AsyncIterator[AsyncClient]:
    async with client_factory() as c:
        yield c


@pytest.fixture
def route() -> Callable[..., AsyncMock]:
    def _patch(*decisions: RouteDecision):
        return patch("app.llm.skill_router.SkillRouter.decide", AsyncMock(side_effect=list(decisions)))

    return _patch


@pytest.fixture
def qa_answer() -> Callable[[str], AsyncMock]:
    def _patch(answer: str):
        return patch("app.llm.answer_writer.QaAnswerWriter.write", AsyncMock(return_value=answer))

    return _patch


def decision(skill: str, **fields) -> RouteDecision:
    return RouteDecision(on_topic=fields.pop("on_topic", True), skill=skill, **fields)
