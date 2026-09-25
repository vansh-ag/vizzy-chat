"""Graph construction and compilation — Phase 4.

Graph topology:

START
  ↓
load_context
  ↓
resolve_assets
  ↓
understand_intent
  ↓ (conditional)
  ├── generate_image            (IMAGE_GENERATION)
  ├── transform_image           (IMAGE_TRANSFORMATION)
  ├── refine_image              (IMAGE_REFINEMENT)
  ├── transform_multiple_images (MULTI_IMAGE_TRANSFORMATION)
  └── unsupported_request       (UNSUPPORTED / error)

All generation nodes → (conditional) → save_result → save_assistant_message → END
Errors at any stage → save_assistant_message → END
"""

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.ai.graph.edges import route_after_generation, route_after_intent
from app.ai.graph.nodes import (
    generate_image,
    load_context,
    refine_image,
    resolve_assets,
    save_assistant_message,
    save_result,
    transform_image,
    transform_multiple_images,
    understand_intent,
    unsupported_request,
)
from app.ai.graph.state import VizzyState

# Generation nodes that share the same post-generation routing
_GENERATION_NODES = [
    "generate_image",
    "transform_image",
    "refine_image",
    "transform_multiple_images",
]


def build_graph() -> CompiledStateGraph:
    """Build and compile the LangGraph workflow for Vizzy Chat."""
    workflow = StateGraph(VizzyState)

    # ── Add all nodes ─────────────────────────────────────────────────────────
    workflow.add_node("load_context", load_context)
    workflow.add_node("resolve_assets", resolve_assets)
    workflow.add_node("understand_intent", understand_intent)
    workflow.add_node("generate_image", generate_image)
    workflow.add_node("transform_image", transform_image)
    workflow.add_node("refine_image", refine_image)
    workflow.add_node("transform_multiple_images", transform_multiple_images)
    workflow.add_node("save_result", save_result)
    workflow.add_node("unsupported_request", unsupported_request)
    workflow.add_node("save_assistant_message", save_assistant_message)

    # ── Linear path until routing ─────────────────────────────────────────────
    workflow.add_edge(START, "load_context")
    workflow.add_edge("load_context", "resolve_assets")
    workflow.add_edge("resolve_assets", "understand_intent")

    # ── Conditional routing after intent classification ────────────────────────
    workflow.add_conditional_edges(
        "understand_intent",
        route_after_intent,
        {
            "generate_image": "generate_image",
            "transform_image": "transform_image",
            "refine_image": "refine_image",
            "transform_multiple_images": "transform_multiple_images",
            "unsupported_request": "unsupported_request",
            "save_assistant_message": "save_assistant_message",  # Error path
        },
    )

    # ── All generation nodes share the same post-generation routing ───────────
    for node_name in _GENERATION_NODES:
        workflow.add_conditional_edges(
            node_name,
            route_after_generation,
            {
                "save_result": "save_result",
                "save_assistant_message": "save_assistant_message",  # Error path
            },
        )

    # ── Linear termination ────────────────────────────────────────────────────
    workflow.add_edge("save_result", "save_assistant_message")
    workflow.add_edge("unsupported_request", "save_assistant_message")
    workflow.add_edge("save_assistant_message", END)

    return workflow.compile()
