import os
from dataclasses import dataclass


def _required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is not set. Copy .env.example to .env and fill it in.")
    return value


@dataclass(frozen=True)
class Settings:
    google_api_key: str
    database_url: str
    chat_model: str = "gemini-3.5-flash-lite"
    thinking_level: str = "minimal"
    embedding_model: str = "gemini-embedding-001"
    cors_origins: tuple[str, ...] = ("http://localhost:5173",)
    daily_llm_call_cap: int = 300
    session_llm_call_cap: int = 60
    rag_top_k: int = 4
    trust_proxy: bool = False
    log_prompts: bool = False
    db_pool_size: int = 5

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            google_api_key=_required("GOOGLE_API_KEY"),
            database_url=_required("DATABASE_URL"),
            chat_model=os.environ.get("GEMINI_CHAT_MODEL", cls.chat_model),
            thinking_level=os.environ.get("GEMINI_THINKING_LEVEL", cls.thinking_level),
            embedding_model=os.environ.get("GEMINI_EMBEDDING_MODEL", cls.embedding_model),
            cors_origins=tuple(
                origin.strip()
                for origin in os.environ.get("CORS_ORIGINS", ",".join(cls.cors_origins)).split(",")
                if origin.strip()
            ),
            daily_llm_call_cap=int(os.environ.get("DAILY_LLM_CALL_CAP", cls.daily_llm_call_cap)),
            session_llm_call_cap=int(os.environ.get("SESSION_LLM_CALL_CAP", cls.session_llm_call_cap)),
            rag_top_k=int(os.environ.get("RAG_TOP_K", cls.rag_top_k)),
            trust_proxy=os.environ.get("TRUST_PROXY", "false").lower() == "true",
            log_prompts=os.environ.get("LOG_PROMPTS", "false").lower() == "true",
            db_pool_size=int(os.environ.get("DB_POOL_SIZE", cls.db_pool_size)),
        )
