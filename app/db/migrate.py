import asyncio
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


async def migrate(database_url: str) -> None:
    async with await psycopg.AsyncConnection.connect(database_url, autocommit=True) as conn:
        await conn.execute(SCHEMA_PATH.read_text())
    async with AsyncPostgresSaver.from_conn_string(database_url) as saver:
        await saver.setup()


if __name__ == "__main__":
    load_dotenv()
    asyncio.run(migrate(os.environ["DATABASE_URL"]))
    print("Schema and checkpoint tables are up to date.")
