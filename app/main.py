import asyncio
import json
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph.state import CompiledStateGraph
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool, PoolTimeout

from app.agent import blocks
from app.agent.graph import build_graph
from app.agent.skills import AgentSkills
from app.agent.turn import run_turn
from app.config.settings import Settings
from app.llm.answer_writer import QaAnswerWriter
from app.llm.gemini import UPSTREAM_UNAVAILABLE_ERRORS, build_chat_model, build_embeddings
from app.llm.skill_router import SkillRouter
from app.logger import session_ref, setup_logger
from app.models import ChatRequest, ChatResponse, HealthResponse, OrderBlock, ProductCard
from app.order.repository import OrderRepository
from app.product.repository import ProductRepository, SearchFilters
from app.rate_limit import TokenBucketLimiter, client_ip
from app.session import BudgetExceededError, LlmBudget, SessionStore, utc_now

logger = setup_logger("api")

MAX_CONCURRENT_STREAMS = 20
STREAM_TIMEOUT_SECONDS = 60
UPSTREAM_RETRY_AFTER_SECONDS = 15
UPSTREAM_BUSY_MESSAGE = "The AI model is busy right now. Please try again in a few seconds."
SESSION_HEADER = "X-Session-Id"
EVAL_RESULTS_PATH = Path(__file__).resolve().parents[1] / "evaluation" / "results.json"


@dataclass
class Runtime:
    graph: CompiledStateGraph
    products: ProductRepository
    orders: OrderRepository
    sessions: SessionStore
    pool: AsyncConnectionPool
    limiter: TokenBucketLimiter
    stream_slots: asyncio.Semaphore
    active_stream_sessions: set[str]


def create_app(
    settings: Settings | None = None,
    chat_model: BaseChatModel | None = None,
    embeddings: Embeddings | None = None,
) -> FastAPI:
    if settings is None:
        load_dotenv()
        settings = Settings.from_env()
    chat_model = chat_model or build_chat_model(
        settings.google_api_key, settings.chat_model, settings.thinking_level
    )
    embeddings = embeddings or build_embeddings(settings.google_api_key, settings.embedding_model)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with AsyncConnectionPool(
            settings.database_url,
            min_size=1,
            max_size=settings.db_pool_size,
            kwargs={"autocommit": True, "row_factory": dict_row, "prepare_threshold": None},
            check=AsyncConnectionPool.check_connection,
            open=False,
        ) as pool:
            products = ProductRepository(pool, embeddings, settings.embedding_model, settings.rag_top_k)
            orders = OrderRepository(pool)
            skills = AgentSkills(
                router=SkillRouter(chat_model),
                answer_writer=QaAnswerWriter(chat_model),
                products=products,
                orders=orders,
                budget=LlmBudget(pool, settings.daily_llm_call_cap, settings.session_llm_call_cap),
                clock=utc_now,
            )
            app.state.runtime = Runtime(
                graph=build_graph(skills, AsyncPostgresSaver(pool)),
                products=products,
                orders=orders,
                sessions=SessionStore(pool),
                pool=pool,
                limiter=TokenBucketLimiter(capacity=10, refill_per_second=0.2),
                stream_slots=asyncio.Semaphore(MAX_CONCURRENT_STREAMS),
                active_stream_sessions=set(),
            )
            logger.info("Ready | chat=%s embeddings=%s", settings.chat_model, settings.embedding_model)
            yield

    app = FastAPI(title="CartAgent API", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", SESSION_HEADER],
        expose_headers=[SESSION_HEADER],
    )

    def runtime(request: Request) -> Runtime:
        return request.app.state.runtime

    def rate_limited(request: Request, rt: Runtime = Depends(runtime)) -> None:
        if not rt.limiter.allow(client_ip(request, settings.trust_proxy)):
            raise HTTPException(
                429, "Too many messages. Wait a few seconds and try again.", {"Retry-After": "5"}
            )

    async def chat_session(
        session_id: str | None = Header(default=None, alias=SESSION_HEADER), rt: Runtime = Depends(runtime)
    ) -> str:
        if session_id is None:
            return await rt.sessions.create()
        if not await rt.sessions.exists(session_id):
            raise HTTPException(404, "Unknown session. Start a new one by omitting the session header.")
        return session_id

    async def existing_session(
        session_id: str | None = Header(default=None, alias=SESSION_HEADER), rt: Runtime = Depends(runtime)
    ) -> str:
        if session_id is None or not await rt.sessions.exists(session_id):
            raise HTTPException(401, "A valid session header is required.")
        return session_id

    @app.exception_handler(BudgetExceededError)
    async def budget_exceeded(request: Request, error: BudgetExceededError) -> JSONResponse:
        retry_after = error.retry_after_seconds(utc_now())
        return JSONResponse(
            status_code=429,
            content={"detail": _budget_message(error)},
            headers={"Retry-After": str(retry_after)} if retry_after else None,
        )

    @app.exception_handler(UPSTREAM_UNAVAILABLE_ERRORS[0])
    @app.exception_handler(UPSTREAM_UNAVAILABLE_ERRORS[1])
    async def upstream_unavailable(request: Request, error: Exception) -> JSONResponse:
        logger.warning("UPSTREAM | %s: %s", type(error).__name__, str(error)[:200])
        return JSONResponse(
            status_code=503,
            content={"detail": UPSTREAM_BUSY_MESSAGE},
            headers={"Retry-After": str(UPSTREAM_RETRY_AFTER_SECONDS)},
        )

    @app.post("/chat", response_model=ChatResponse, dependencies=[Depends(rate_limited)])
    async def chat(
        body: ChatRequest, session_id: str = Depends(chat_session), rt: Runtime = Depends(runtime)
    ) -> dict:
        started = time.perf_counter()
        async for event in run_turn(rt.graph, session_id, body.message, body.confirm_token):
            if event["event"] == "done":
                _log_turn(session_id, body, event["data"], started, settings.log_prompts)
                return event["data"]
        raise RuntimeError("Agent turn finished without a final response")

    @app.post("/chat/stream", dependencies=[Depends(rate_limited)])
    async def chat_stream(
        body: ChatRequest, session_id: str = Depends(chat_session), rt: Runtime = Depends(runtime)
    ) -> StreamingResponse:
        if session_id in rt.active_stream_sessions or rt.stream_slots.locked():
            raise HTTPException(429, "Another reply is still streaming. Try again in a moment.")
        return StreamingResponse(
            _sse_turn(rt, session_id, body, settings.log_prompts),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", SESSION_HEADER: session_id},
        )

    @app.get("/products", response_model=list[ProductCard])
    async def list_products(
        category: str | None = None,
        brand: str | None = None,
        max_price_cents: int | None = Query(default=None, ge=0),
        rt: Runtime = Depends(runtime),
    ) -> list[dict]:
        return await rt.products.find(
            SearchFilters(category=category, brand=brand, max_price_cents=max_price_cents)
        )

    @app.get("/products/{product_id}", response_model=ProductCard)
    async def get_product(product_id: str, rt: Runtime = Depends(runtime)) -> dict:
        found = await rt.products.get_many([product_id])
        if product_id not in found:
            raise HTTPException(404, "Product not found")
        return found[product_id]

    @app.get("/orders", response_model=list[OrderBlock])
    async def list_orders(
        session_id: str = Depends(existing_session), rt: Runtime = Depends(runtime)
    ) -> list[dict]:
        now = utc_now()
        return [blocks.order(order, now) for order in await rt.orders.find_by_session(session_id)]

    @app.get("/evals")
    async def eval_results() -> dict:
        if not EVAL_RESULTS_PATH.exists():
            raise HTTPException(404, "No benchmark results have been published yet.")
        return json.loads(EVAL_RESULTS_PATH.read_text())

    @app.get("/health", response_model=HealthResponse)
    async def health(rt: Runtime = Depends(runtime)) -> JSONResponse:
        try:
            ready = await rt.products.embedded_product_count() > 0
        except (psycopg.Error, PoolTimeout):
            logger.exception("HEALTH | database check failed")
            ready = False
        if not ready:
            return JSONResponse(status_code=503, content={"status": "unavailable"})
        return JSONResponse(content={"status": "ok"})

    return app


async def _sse_turn(rt: Runtime, session_id: str, body: ChatRequest, log_prompts: bool):
    started = time.perf_counter()
    rt.active_stream_sessions.add(session_id)
    try:
        async with rt.stream_slots, asyncio.timeout(STREAM_TIMEOUT_SECONDS):
            yield _sse("session", {"session_id": session_id})
            async for event in run_turn(rt.graph, session_id, body.message, body.confirm_token):
                if event["event"] == "done":
                    _log_turn(session_id, body, event["data"], started, log_prompts)
                yield _sse(event["event"], event["data"])
    except BudgetExceededError as error:
        yield _sse(
            "error",
            {
                "code": "budget_exhausted",
                "message": _budget_message(error),
                "retry_after": error.retry_after_seconds(utc_now()),
            },
        )
    except UPSTREAM_UNAVAILABLE_ERRORS as error:
        logger.warning("UPSTREAM | %s: %s", type(error).__name__, str(error)[:200])
        yield _sse(
            "error",
            {
                "code": "upstream_busy",
                "message": UPSTREAM_BUSY_MESSAGE,
                "retry_after": UPSTREAM_RETRY_AFTER_SECONDS,
            },
        )
    except TimeoutError:
        logger.warning("STREAM | session=%s timed out", session_ref(session_id))
        yield _sse("error", {"code": "timeout", "message": "That took too long. Please try again."})
    except Exception:
        error_id = uuid.uuid4().hex[:8]
        logger.exception("STREAM | session=%s failed | error_id=%s", session_ref(session_id), error_id)
        yield _sse("error", {"code": "internal", "message": f"Something went wrong (ref {error_id})."})
    finally:
        rt.active_stream_sessions.discard(session_id)


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


def _budget_message(error: BudgetExceededError) -> str:
    if error.scope == "daily":
        return "Today's demo budget is spent. It resets at 00:00 UTC."
    return "This session has used its message allowance. Start a new chat to continue."


def _log_turn(session_id: str, body: ChatRequest, response: dict, started: float, log_prompts: bool) -> None:
    logger.info(
        "TURN | session=%s | skill=%s | blocks=%s | pending=%s | %.2fs%s",
        session_ref(session_id),
        response["skill"],
        [b["type"] for b in response["blocks"]],
        response["pending_confirmation"],
        time.perf_counter() - started,
        f" | message={body.message[:200]!r}" if log_prompts else "",
    )
