"""Pydantic schemas for conversation endpoints."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ConversationCreate(BaseModel):
    """Request body for creating a conversation."""

    title: str = Field(default="New conversation", max_length=200)


class ConversationResponse(BaseModel):
    """Single conversation response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    """Paginated list of conversations."""

    items: list[ConversationResponse]
