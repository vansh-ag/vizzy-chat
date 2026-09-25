"""Deterministic router for LangGraph.

Maps IntentType values to LangGraph node names.
The LLM never makes routing decisions — only intent classification.
Routing is purely a function of the classified intent.
"""

from app.ai.intent.schemas import IntentType

_INTENT_TO_NODE: dict[IntentType, str] = {
    IntentType.IMAGE_GENERATION: "generate_image",
    IntentType.IMAGE_TRANSFORMATION: "transform_image",
    IntentType.IMAGE_REFINEMENT: "refine_image",
    IntentType.MULTI_IMAGE_TRANSFORMATION: "transform_multiple_images",
    IntentType.UNSUPPORTED: "unsupported_request",
}


def route_intent(intent: IntentType) -> str:
    """Map the classified intent to the next LangGraph node.

    This is a deterministic router. No LLM decision is made here.
    """
    return _INTENT_TO_NODE.get(intent, "unsupported_request")
