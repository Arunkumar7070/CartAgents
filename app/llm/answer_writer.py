from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.llm.prompts import QA_ANSWER_PROMPT
from app.llm.skill_router import format_conversation
from app.order.policy import POLICY_CLAUSES
from app.order.pricing import format_cents


def product_context(products: list[dict]) -> str:
    return "\n".join(
        f"- {p['name']} ({p['brand']}, {p['category']}): {format_cents(p['price_cents'])} | "
        f"stock: {p['stock']} | {p['specs']} | {p['description']}"
        for p in products
    )


def policy_context() -> str:
    return "\n".join(f"{clause} {text}" for clause, text in POLICY_CLAUSES.items())


def answer_evidence(message: str, products: list[dict]) -> str:
    return "\n".join([message, product_context(products), policy_context()])


class QaAnswerWriter:
    def __init__(self, llm: BaseChatModel) -> None:
        self._llm = llm

    async def write(self, message: str, history: list[dict[str, str]], products: list[dict]) -> str:
        prompt = QA_ANSWER_PROMPT.format(
            product_context=product_context(products) or "(no matching products)",
            policy_context=policy_context(),
            conversation=format_conversation(history),
        )
        response = await self._llm.ainvoke([SystemMessage(content=prompt), HumanMessage(content=message)])
        return response.text
