"""Pydantic schemas for message endpoints."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MessageCreate(BaseModel):
    """Request body for sending a message.

    content:   The text the user sends (required, 1-4000 chars).
    asset_ids: Optional list of previously-uploaded input-image asset UUIDs.
               Phase 4: used for transformation and multi-image requests.
               Ownership is verified server-side — never trust client-supplied IDs.
               Maximum 5 asset IDs per request.
    """

    content: str = Field(..., min_length=1, max_length=4000)
    asset_ids: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="Optional list of input asset UUIDs for transformation.",
    )


class MessageResponse(BaseModel):
    """Single message response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str
    content: str
    created_at: datetime
    generated_asset: "GeneratedAssetResponse | None" = None
    image_url: str | None = None


class MessageListResponse(BaseModel):
    """Ordered list of messages in a conversation."""

    items: list[MessageResponse]


class GeneratedAssetResponse(BaseModel):
    """Metadata for a generated image asset (Phase 4 extended)."""

    id: str
    type: str
    storage_path: str
    mime_type: str
    generation_type: str = "text_to_image"
    parent_asset_id: str | None = None
    prompt: str | None = None
    created_at: datetime | None = None
    signed_url: str | None = None


class SendMessageResponse(BaseModel):
    """Full response from POST /conversations/{id}/messages."""

    user_message: MessageResponse
    assistant_message: MessageResponse
    generated_asset: GeneratedAssetResponse | None = None
    image_url: str | None = None  # Convenience alias for the signed URL
