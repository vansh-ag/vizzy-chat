"""State definition for the Vizzy LangGraph — Phase 4."""

from typing import Any, TypedDict

from app.ai.intent.schemas import IntentType


class VizzyState(TypedDict):
    """The state dictionary passed between LangGraph nodes.

    Fields are grouped by lifecycle phase:

    INPUT — set before graph execution starts
    CONTEXT — set by load_context
    ASSET RESOLUTION — set by resolve_assets
    INTENT — set by understand_intent
    GENERATION — set by generate_image / transform_image / refine_image / transform_multiple_images
    OUTPUT — set by save_assistant_message
    ERROR — set on any failure
    """

    # ── INPUT ────────────────────────────────────────────────────────────────
    user_id: str
    conversation_id: str
    user_message_id: str
    user_message_content: str

    # Asset IDs provided by the frontend (validated by service before graph entry)
    input_asset_ids: list[str]

    # ── CONTEXT ──────────────────────────────────────────────────────────────
    conversation_history: list[dict[str, str]]

    # ── ASSET RESOLUTION ─────────────────────────────────────────────────────
    # Resolved asset dicts (metadata only; no binary image data)
    resolved_input_assets: list[dict[str, Any]]

    # For refinement: the target asset to transform (e.g. last generated image)
    resolved_target_asset: dict[str, Any] | None

    # ── INTENT ───────────────────────────────────────────────────────────────
    intent: IntentType | None
    instruction: str | None

    # ── GENERATION ───────────────────────────────────────────────────────────
    # Raw bytes of the newly generated/transformed image
    generated_image_bytes: bytes | None

    # Asset record for the newly generated image (after save_result)
    generated_asset_id: str | None
    generated_storage_path: str | None
    generated_mime_type: str | None
    generation_type: str | None  # e.g. text_to_image, image_refinement
    parent_asset_id: str | None  # For lineage tracking

    # ── OUTPUT ───────────────────────────────────────────────────────────────
    response_text: str | None

    # ── ERROR ────────────────────────────────────────────────────────────────
    error: str | None
