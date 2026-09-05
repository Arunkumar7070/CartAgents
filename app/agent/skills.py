import re
import secrets
from collections.abc import Callable
from datetime import datetime

from langgraph.types import interrupt

from app.agent import blocks
from app.agent.confirmation import parse_confirmation
from app.agent.decision import sanitize_decision
from app.agent.state import AgentState
from app.llm.answer_writer import QaAnswerWriter, answer_evidence
from app.llm.grounding import ungrounded_numbers
from app.llm.skill_router import SkillRouter
from app.logger import setup_logger
from app.order.policy import POLICY_CLAUSES, check_eligibility
from app.order.pricing import build_cart, format_cents, stock_shortfalls
from app.order.repository import OrderRepository, OutOfStockError
from app.product.repository import ProductRepository, SearchFilters
from app.session import LlmBudget

logger = setup_logger("agent")

HISTORY_WINDOW = 6
OFF_TOPIC_REPLY = "I can only help with shopping here: products, orders, deliveries and returns."


def _last_user_message(state: AgentState) -> str:
    return state["messages"][-1]["content"]


def _history(state: AgentState) -> list[dict[str, str]]:
    return state["messages"][:-1][-HISTORY_WINDOW:]


def _reply(markdown: str, *extra_blocks: dict) -> dict:
    return {
        "blocks": [blocks.text(markdown), *extra_blocks],
        "messages": [{"role": "assistant", "content": markdown}],
    }


class AgentSkills:
    def __init__(
        self,
        router: SkillRouter,
        answer_writer: QaAnswerWriter,
        products: ProductRepository,
        orders: OrderRepository,
        budget: LlmBudget,
        clock: Callable[[], datetime],
    ) -> None:
        self._router = router
        self._answer_writer = answer_writer
        self._products = products
        self._orders = orders
        self._budget = budget
        self._clock = clock

    async def route_skill(self, state: AgentState) -> dict:
        await self._budget.spend(state["session_id"])
        catalog = await self._products.all()
        raw = await self._router.decide(_last_user_message(state), _history(state), catalog)
        decision = sanitize_decision(raw, catalog)
        if not decision["on_topic"]:
            return {"decision": decision, **_reply(OFF_TOPIC_REPLY)}
        return {"decision": decision}

    async def search_products(self, state: AgentState) -> dict:
        await self._budget.spend(state["session_id"])
        query = _last_user_message(state)
        results = await self._products.search(query, SearchFilters(**state["decision"]["filters"]))
        return {"products": results}

    async def generate_qa_answer(self, state: AgentState) -> dict:
        products = state["products"]
        message = _last_user_message(state)
        await self._budget.spend(state["session_id"])
        answer = await self._answer_writer.write(message, _history(state), products)

        unknown = ungrounded_numbers(answer, answer_evidence(message, products))
        if unknown:
            logger.warning("GROUNDING | replaced answer with ungrounded numbers %s", unknown)
            answer = (
                "Here is what I found in the catalog:\n\n"
                + "\n".join(f"- **{p['name']}**: {format_cents(p['price_cents'])}" for p in products)
                if products
                else "I couldn't find products matching that. Try a category such as laptops or audio."
            )

        cited_clauses = [c for c in dict.fromkeys(re.findall(r"§\d", answer)) if c in POLICY_CLAUSES]
        mentioned = [p for p in products if p["name"].lower() in answer.lower()]
        shown = mentioned or products
        extra = []
        if shown:
            extra.append(blocks.product_cards(shown))
        applied = SearchFilters(**state["decision"]["filters"]).applied()
        if applied:
            extra.append(blocks.filters(applied))
        if shown or cited_clauses:
            extra.append(blocks.citations(shown, cited_clauses))
        return _reply(answer, *extra)

    async def prepare_order(self, state: AgentState) -> dict:
        items = state["decision"]["items"]
        if not items:
            return _reply(
                "Which product would you like to order? You can name it or pick one from the cards."
            )

        found = await self._products.get_many([item["product_id"] for item in items])
        selections = [(found[item["product_id"]], item["quantity"]) for item in items]
        shortfalls = stock_shortfalls(selections)
        if shortfalls:
            return _reply("I can't fill that order right now: " + ", ".join(shortfalls) + ".")

        cart = build_cart(selections)
        summary = (
            f"Here's your cart. The total of **{format_cents(cart['total_cents'])}** "
            "includes shipping and tax, so nothing changes at checkout [§5]."
        )
        return {
            "pending": {"action": "order", "cart": cart, "token": secrets.token_urlsafe(16)},
            **_reply(
                summary,
                blocks.cart(cart),
                blocks.citations([], ["§5"]),
                blocks.confirmation("order", "Place this order?"),
            ),
        }

    async def prepare_return(self, state: AgentState) -> dict:
        session_id = state["session_id"]
        decision = state["decision"]
        if decision["order_id"]:
            order = await self._orders.get(session_id, decision["order_id"])
        else:
            orders = await self._orders.find_by_session(session_id)
            order = orders[0] if orders else None
        if order is None:
            return _reply(
                "I couldn't find that order in this session. Ask me to track your orders to see them."
            )

        now = self._clock()
        action = decision["return_action"]
        eligibility = check_eligibility(order, action, now)
        order_block = blocks.order(order, now)
        policy_citation = blocks.citations([], [eligibility.clause])
        if not eligibility.allowed:
            return _reply(f"{eligibility.reason} [{eligibility.clause}]", order_block, policy_citation)

        verb = "cancel" if action == "cancel" else "start a return for"
        return {
            "pending": {"action": action, "order_id": order["id"], "token": secrets.token_urlsafe(16)},
            **_reply(
                f"{eligibility.reason} [{eligibility.clause}] Shall I {verb} it?",
                order_block,
                policy_citation,
                blocks.confirmation(action, f"{verb.capitalize()} {order['id']}?"),
            ),
        }

    def await_confirmation(self, state: AgentState) -> dict:
        reply: str = interrupt({"action": state["pending"]["action"]})
        return {
            "confirmation": parse_confirmation(reply),
            "messages": [{"role": "user", "content": reply}],
        }

    def clarify_confirmation(self, state: AgentState) -> dict:
        action = state["pending"]["action"]
        return _reply(
            "Sorry, I didn't catch that. Please answer yes or no.",
            blocks.confirmation(action, "Please confirm or cancel."),
        )

    async def finalize_action(self, state: AgentState) -> dict:
        pending = state["pending"]
        if state["confirmation"] == "cancel":
            return {"pending": None, **_reply("No problem, nothing was changed.")}

        session_id = state["session_id"]
        now = self._clock()
        if pending["action"] != "order":
            if pending["action"] == "cancel":
                order = await self._orders.cancel(session_id, pending["order_id"])
                message, clauses = f"Order {order['id']} is cancelled. You won't be charged.", ["§1"]
            else:
                order = await self._orders.request_return(session_id, pending["order_id"])
                message = f"Return started for {order['id']}. Your refund follows once it arrives [§4]."
                clauses = ["§4"]
            return {
                "pending": None,
                **_reply(message, blocks.order(order, now), blocks.citations([], clauses)),
            }

        approved = pending["cart"]
        current = await self._products.get_many([line["product_id"] for line in approved["lines"]])
        repriced = build_cart([(current[line["product_id"]], line["quantity"]) for line in approved["lines"]])
        if repriced["cart_hash"] != approved["cart_hash"]:
            return {
                "pending": None,
                **_reply("Prices changed since you approved this cart, so I stopped. Please order again."),
            }
        try:
            order = await self._orders.place(session_id, approved)
        except OutOfStockError as error:
            return {
                "pending": None,
                **_reply(f"Sorry, {error.product_name} just sold out. Nothing was charged."),
            }
        return {
            "pending": None,
            **_reply(
                f"Order **{order['id']}** is placed. Total charged: {format_cents(order['total_cents'])}.",
                blocks.order(order, now),
            ),
        }

    async def track_order(self, state: AgentState) -> dict:
        orders = await self._orders.find_by_session(state["session_id"])
        if not orders:
            return _reply("You haven't placed any orders in this session yet.")
        now = self._clock()
        noun = "order" if len(orders) == 1 else "orders"
        return _reply(
            f"Here {'is' if len(orders) == 1 else 'are'} your {noun}:",
            *[blocks.order(o, now) for o in orders],
        )

    async def compare_products(self, state: AgentState) -> dict:
        product_ids = state["decision"]["product_ids"]
        if len(product_ids) < 2:
            return _reply(
                "Tell me at least two products to compare, "
                "for example the ProBook 15 and the UltraBook 13 Air."
            )
        found = await self._products.get_many(product_ids)
        products = [found[pid] for pid in product_ids]
        cheapest = min(products, key=lambda p: p["price_cents"])
        return _reply(
            f"Side by side. The **{cheapest['name']}** is the least expensive "
            f"at {format_cents(cheapest['price_cents'])}.",
            blocks.comparison(products),
            blocks.citations(products, []),
        )
