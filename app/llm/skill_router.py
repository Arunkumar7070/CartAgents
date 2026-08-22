from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.llm.prompts import ROUTER_PROMPT
from app.llm.types import RouteDecision
from app.order.pricing import format_cents


def format_conversation(history: list[dict[str, str]]) -> str:
    if not history:
        return "(no earlier messages)"
    return "\n".join(f"[{m['role']}] {m['content'][:300]}" for m in history)


class SkillRouter:
    def __init__(self, llm: BaseChatModel) -> None:
        self._llm = llm.with_structured_output(RouteDecision)

    async def decide(self, message: str, history: list[dict[str, str]], catalog: list[dict]) -> RouteDecision:
        catalog_text = "\n".join(
            f"{p['id']} | {p['name']} | {p['category']} | {p['brand']} | {format_cents(p['price_cents'])}"
            for p in catalog
        )
        prompt = ROUTER_PROMPT.format(catalog=catalog_text, conversation=format_conversation(history))
        return await self._llm.ainvoke([SystemMessage(content=prompt), HumanMessage(content=message)])
