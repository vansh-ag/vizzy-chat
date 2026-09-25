"""Pydantic schemas for asset endpoints."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AssetResponse(BaseModel):
    """Full asset metadata response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    type: str
    storage_path: str
    mime_type: str
    generation_type: str
    parent_asset_id: str | None = None
    prompt: str | None = None
    conversation_id: str | None = None
    message_id: str | None = None
    created_at: datetime | None = None
    signed_url: str | None = None


class AssetUploadResponse(BaseModel):
    """Response from POST /assets/upload."""

    asset: AssetResponse
    message: str = "Image uploaded successfully."
