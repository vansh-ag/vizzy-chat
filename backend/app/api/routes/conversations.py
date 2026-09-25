"""Conversation API endpoints."""

from fastapi import APIRouter, Depends, status
from supabase_auth.types import User

from app.api.dependencies import get_current_user
from app.schemas.conversation import (
    ConversationCreate,
    ConversationListResponse,
    ConversationResponse,
)
from app.services.conversation_service import ConversationService

router = APIRouter(prefix="/conversations", tags=["conversations"])


def get_conversation_service() -> ConversationService:
    """Dependency provider for ConversationService."""
    return ConversationService()


@router.post(
    "",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    request: ConversationCreate,
    current_user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
):
    """Create a new conversation for the authenticated user."""
    conv = service.create_conversation(current_user.id, request.title)
    return conv


@router.get(
    "",
    response_model=ConversationListResponse,
)
async def list_conversations(
    current_user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
):
    """List all conversations owned by the authenticated user."""
    convs = service.list_conversations(current_user.id)
    return {"items": convs}


@router.get(
    "/{conversation_id}",
    response_model=ConversationResponse,
)
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
):
    """Retrieve a specific conversation (must be owned by the user)."""
    conv = service.get_conversation(conversation_id, current_user.id)
    return conv


@router.delete(
    "/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
):
    """Delete a specific conversation and all its messages."""
    service.delete_conversation(conversation_id, current_user.id)
