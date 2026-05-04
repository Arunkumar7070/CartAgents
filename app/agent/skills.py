from app.agent.state import AgentState
from app.llm.response_generator import OrderDraftGenerator, QaResponseGenerator
from app.llm.skill_router import SkillRouter
from app.order.service import OrderService
from app.product.service import ProductService


class AgentSkills:
    """All agent skills wired together with constructor-based DI.

    Each skill is a method that receives AgentState and returns a partial
    state update dict — the standard LangGraph node signature.
    """

    def __init__(
        self,
        skill_router: SkillRouter,
        qa_generator: QaResponseGenerator,
        order_generator: OrderDraftGenerator,
        product_service: ProductService,
        order_service: OrderService,
    ) -> None:
        self._skill_router = skill_router
        self._qa_generator = qa_generator
        self._order_generator = order_generator
        self._product_service = product_service
        self._order_service = order_service

    async def route_skill(self, state: AgentState) -> dict:
        """Classify user intent: Q&A, Order, or Track."""
        last_message: str = state["messages"][-1]["content"]
        result = await self._skill_router.classify(last_message)
        return {"skill": result.skill}

    def search_products(self, state: AgentState) -> dict:
        """Search product catalog via ProductService."""
        query: str = state["messages"][-1]["content"]
        results: list[dict[str, object]] = self._product_service.search(query)
        return {"product_results": results}

    async def generate_qa_answer(self, state: AgentState) -> dict:
        """Compose product Q&A response - LLM with search results as context (RAG generation)."""
        products = state.get("product_results", [])
        user_message: str = state["messages"][-1]["content"]
        answer: str = await self._qa_generator.generate(user_message, products)

        sources = [str(p["name"]) for p in products] if products else []
        return {
            "final_answer": answer,
            "messages": [*state["messages"], {"role": "assistant", "content": answer}],
            "product_results": sources,
        }
