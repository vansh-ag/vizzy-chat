"""Message API endpoints — Phase 4."""

from fastapi import APIRouter, Depends, status
from supabase_auth.types import User

from app.api.dependencies import get_current_user
from app.schemas.message import MessageCreate, MessageListResponse, SendMessageResponse
from app.services.message_service import MessageService

router = APIRouter(
    prefix="/conversations/{conversation_id}/messages",
    tags=["messages"],
)


def get_message_service() -> MessageService:
    """Dependency provider for MessageService."""
    return MessageService()


@router.get(
    "",
    response_model=MessageListResponse,
    summary="List conversation messages",
    description="Return all messages in a conversation, ordered chronologically.",
)
async def list_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    service: MessageService = Depends(get_message_service),
) -> MessageListResponse:
    """Retrieve all messages for a specific conversation."""
    msgs = service.list_messages(conversation_id, current_user.id)
    return MessageListResponse(items=msgs)  # type: ignore[arg-type]


@router.post(
    "",
    response_model=SendMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send a message",
    description=(
        "Send a message to a conversation and trigger the AI workflow. "
        "The backend always generates exactly ONE output image. "
        "\n\n**asset_ids** is optional. Pass one asset UUID for transformation or "
        "multiple for multi-image combination."
    ),
)
async def send_message(
    conversation_id: str,
    request: MessageCreate,
    current_user: User = Depends(get_current_user),
    service: MessageService = Depends(get_message_service),
) -> SendMessageResponse:
    """Send a message and trigger AI generation/transformation/refinement."""
    return await service.send_message(
        conversation_id=conversation_id,
        user_id=current_user.id,
        content=request.content,
        asset_ids=request.asset_ids,
    )
