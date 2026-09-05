import operator
from typing import Annotated, NotRequired, TypedDict


class AgentState(TypedDict):
    session_id: str
    messages: Annotated[list[dict[str, str]], operator.add]
    decision: dict | None
    products: list[dict]
    pending: dict | None
    blocks: list[dict]
    confirmation: NotRequired[str]


def new_turn_input(session_id: str, message: str) -> AgentState:
    return {
        "session_id": session_id,
        "messages": [{"role": "user", "content": message}],
        "decision": None,
        "products": [],
        "pending": None,
        "blocks": [],
    }
