"""Pydantic schemas for intent classification."""

from enum import StrEnum

from pydantic import BaseModel, Field


class IntentType(StrEnum):
    """Supported intent types for Phase 4.

    IMAGE_GENERATION: Create a brand new image from a text description.
    IMAGE_TRANSFORMATION: Transform one existing image with an instruction.
    IMAGE_REFINEMENT: Refine the most-recently-generated image in the conversation.
    MULTI_IMAGE_TRANSFORMATION: Combine multiple input images into one output.
    UNSUPPORTED: Request cannot be handled.
    """

    IMAGE_GENERATION = "image_generation"
    IMAGE_TRANSFORMATION = "image_transformation"
    IMAGE_REFINEMENT = "image_refinement"
    MULTI_IMAGE_TRANSFORMATION = "multi_image_transformation"
    UNSUPPORTED = "unsupported"


class IntentResult(BaseModel):
    """Structured result from the LLM intent classifier."""

    intent: IntentType
    instruction: str

    # For IMAGE_REFINEMENT with explicit asset reference.
    # The LLM may suggest an asset ID from context, but the backend
    # ALWAYS verifies ownership independently and does NOT trust this value blindly.
    target_asset_id: str | None = Field(
        default=None,
        description="Optional explicit asset ID if the user clearly references one.",
    )

    # For IMAGE_TRANSFORMATION or MULTI_IMAGE_TRANSFORMATION.
    # These are populated from the request's asset_ids, not from the LLM.
    # The LLM does NOT generate these — they are injected by the service layer.
    input_asset_ids: list[str] = Field(
        default_factory=list,
        description="Asset IDs to use as transformation inputs (set by service, not LLM).",
    )
