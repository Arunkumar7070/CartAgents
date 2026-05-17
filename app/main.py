import time
import uuid
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import StateGraph

from app.config.di import agent_graph_builder, guardrail
from app.logger import setup_logger
from app.models import ChatRequest, ChatResponse

load_dotenv()

agent: StateGraph | None = None
logger = setup_logger("agent")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown: manage AsyncSqliteSaver lifecycle."""
    global agent
    async with AsyncSqliteSaver.from_conn_string("data/checkpoints.db") as checkpointer:
        agent = agent_graph_builder.build(checkpointer=checkpointer)
        logger.info("Checkpointer ready (AsyncSqliteSaver: data/checkpoints.db)")
        yield
    logger.info("Checkpointer closed")


app = FastAPI(title="E-commerce AI Agent", lifespan=lifespan)
