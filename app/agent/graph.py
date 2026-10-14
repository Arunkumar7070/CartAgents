from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agent.skills import AgentSkills
from app.agent.state import AgentState

SKILL_ENTRY_NODES = {
    "qa": "search_products",
    "order": "prepare_order",
    "track": "track_order",
    "returns": "prepare_return",
    "compare": "compare_products",
}


def _after_route(state: AgentState) -> str:
    if not state["decision"]["on_topic"]:
        return END
    return SKILL_ENTRY_NODES[state["decision"]["skill"]]


def _after_preparation(state: AgentState) -> str:
    return "await_confirmation" if state.get("pending") else END


def _after_confirmation(state: AgentState) -> str:
    return "clarify_confirmation" if state["confirmation"] == "unclear" else "finalize_action"


def build_graph(skills: AgentSkills, checkpointer: BaseCheckpointSaver) -> CompiledStateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("route_skill", skills.route_skill)
    graph.add_node("search_products", skills.search_products)
    graph.add_node("generate_qa_answer", skills.generate_qa_answer)
    graph.add_node("prepare_order", skills.prepare_order)
    graph.add_node("prepare_return", skills.prepare_return)
    graph.add_node("await_confirmation", skills.await_confirmation)
    graph.add_node("clarify_confirmation", skills.clarify_confirmation)
    graph.add_node("finalize_action", skills.finalize_action)
    graph.add_node("track_order", skills.track_order)
    graph.add_node("compare_products", skills.compare_products)

    graph.set_entry_point("route_skill")
    graph.add_conditional_edges("route_skill", _after_route, [*SKILL_ENTRY_NODES.values(), END])
    graph.add_edge("search_products", "generate_qa_answer")
    graph.add_edge("generate_qa_answer", END)
    graph.add_conditional_edges("prepare_order", _after_preparation, ["await_confirmation", END])
    graph.add_conditional_edges("prepare_return", _after_preparation, ["await_confirmation", END])
    graph.add_conditional_edges(
        "await_confirmation", _after_confirmation, ["clarify_confirmation", "finalize_action"]
    )
    graph.add_edge("clarify_confirmation", "await_confirmation")
    graph.add_edge("finalize_action", END)
    graph.add_edge("track_order", END)
    graph.add_edge("compare_products", END)

    return graph.compile(checkpointer=checkpointer)
