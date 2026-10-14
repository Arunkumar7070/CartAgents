import re
import secrets
from datetime import UTC, datetime, timedelta
from typing import Literal

from psycopg_pool import AsyncConnectionPool

SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{43}$")


class BudgetExceededError(Exception):
    def __init__(self, scope: Literal["daily", "session"]) -> None:
        super().__init__(f"LLM call budget exhausted ({scope})")
        self.scope = scope

    def retry_after_seconds(self, now: datetime) -> int | None:
        if self.scope == "session":
            return None
        tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return int((tomorrow - now).total_seconds())


class SessionStore:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def create(self) -> str:
        session_id = secrets.token_urlsafe(32)
        async with self._pool.connection() as conn:
            await conn.execute("INSERT INTO sessions (id) VALUES (%s)", (session_id,))
        return session_id

    async def exists(self, session_id: str) -> bool:
        if not SESSION_ID_PATTERN.fullmatch(session_id):
            return False
        async with self._pool.connection() as conn:
            row = await (await conn.execute("SELECT 1 FROM sessions WHERE id = %s", (session_id,))).fetchone()
        return row is not None


class LlmBudget:
    def __init__(self, pool: AsyncConnectionPool, daily_cap: int, session_cap: int) -> None:
        self._pool = pool
        self._daily_cap = daily_cap
        self._session_cap = session_cap

    async def spend(self, session_id: str) -> None:
        async with self._pool.connection() as conn, conn.transaction():
            session_row = await (
                await conn.execute(
                    "UPDATE sessions SET llm_calls = llm_calls + 1 "
                    "WHERE id = %s AND llm_calls < %s RETURNING id",
                    (session_id, self._session_cap),
                )
            ).fetchone()
            if session_row is None:
                raise BudgetExceededError("session")
            daily_row = await (
                await conn.execute(
                    """
                    INSERT INTO llm_usage (day, calls) VALUES ((now() AT TIME ZONE 'utc')::date, 1)
                    ON CONFLICT (day) DO UPDATE SET calls = llm_usage.calls + 1
                    WHERE llm_usage.calls < %s
                    RETURNING calls
                    """,
                    (self._daily_cap,),
                )
            ).fetchone()
            if daily_row is None:
                raise BudgetExceededError("daily")


def utc_now() -> datetime:
    return datetime.now(UTC)
