import secrets
from collections.abc import AsyncIterator

from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command

from app.agent.state import new_turn_input
from app.models import ChatResponse


def _turn_input(
    snapshot_values: dict, is_paused: bool, session_id: str, message: str, confirm_token: str | None
):
    pending = snapshot_values.get("pending") if is_paused else None
    if pending and confirm_token and secrets.compare_digest(confirm_token, pending["token"]):
        return Command(resume=message)
    return new_turn_input(session_id, message)


async def run_turn(
    graph: CompiledStateGraph, session_id: str, message: str, confirm_token: str | None
) -> AsyncIterator[dict]:
    config = {"configurable": {"thread_id": session_id}}
    snapshot = await graph.aget_state(config)
    graph_input = _turn_input(snapshot.values, bool(snapshot.next), session_id, message, confirm_token)

    async for mode, chunk in graph.astream(graph_input, config, stream_mode=["tasks", "messages"]):
        if mode == "tasks":
            yield {
                "event": "step",
                "data": {"node": chunk["name"], "status": "start" if "triggers" in chunk else "done"},
            }
        else:
            message_chunk, metadata = chunk
            if metadata.get("langgraph_node") == "generate_qa_answer" and message_chunk.text:
                yield {"event": "delta", "data": {"text": message_chunk.text}}

    final = await graph.aget_state(config)
    pending = final.values.get("pending") if final.next else None
    decision = final.values.get("decision") or {}
    response = ChatResponse(
        session_id=session_id,
        skill=decision.get("skill"),
        blocks=final.values.get("blocks", []),
        pending_confirmation=pending is not None,
        confirm_token=pending["token"] if pending else None,
    )
    yield {"event": "done", "data": response.model_dump()}
