"""Edge and routing logic for the LangGraph workflow — Phase 4."""

from app.ai.graph.state import VizzyState
from app.ai.router.task_router import route_intent


def route_after_intent(state: VizzyState) -> str:
    """Determine the next node based on the classified intent.

    If an error occurred during intent classification or asset resolution,
    skip directly to save_assistant_message to report the error.
    """
    if state.get("error"):
        return "save_assistant_message"

    intent = state.get("intent")
    if not intent:
        return "unsupported_request"

    # Use the deterministic router — LLM has no say in routing
    return route_intent(intent)


def route_after_generation(state: VizzyState) -> str:
    """Determine the next node after any generation/transformation.

    If the generation failed, skip save_result and go straight to
    save_assistant_message to deliver the error response.
    """
    if state.get("error"):
        return "save_assistant_message"
    return "save_result"
