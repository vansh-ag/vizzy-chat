"""Pydantic schemas for image generation responses."""

from pydantic import BaseModel


class GenerationResponse(BaseModel):
    """Result of a successful image generation pipeline."""

    asset_id: str
    storage_path: str
    mime_type: str
    prompt: str
    signed_url: str | None = None
