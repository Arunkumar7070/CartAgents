from typing import Literal

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_google_genai.chat_models import GoogleAPIError, GoogleRateLimitError

EMBEDDING_DIMENSIONS = 768
UPSTREAM_UNAVAILABLE_ERRORS = (GoogleAPIError, GoogleRateLimitError)

ThinkingLevel = Literal["minimal", "low", "medium", "high"]


def build_chat_model(api_key: str, model: str, thinking_level: ThinkingLevel) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=api_key,
        thinking_level=thinking_level,
        max_retries=3,
    )


def build_embeddings(api_key: str, model: str) -> GoogleGenerativeAIEmbeddings:
    return GoogleGenerativeAIEmbeddings(
        model=model,
        google_api_key=api_key,
        output_dimensionality=EMBEDDING_DIMENSIONS,
    )
