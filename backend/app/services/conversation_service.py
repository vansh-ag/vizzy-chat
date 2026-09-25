"""Conversation service — business logic for conversations."""

import logging
from typing import Any

from app.core.exceptions import ConversationNotFoundError
from app.db.repositories.conversation import ConversationRepository
from app.db.repositories.message import MessageRepository

logger = logging.getLogger(__name__)


class ConversationService:
    """Service layer for conversation operations."""

    def __init__(self) -> None:
        self.repo = ConversationRepository()
        self.message_repo = MessageRepository()

    def create_conversation(self, user_id: str, title: str) -> dict[str, Any]:
        """Create a new conversation."""
        logger.info("User %s creating new conversation", user_id)
        return self.repo.create(user_id, title)

    def list_conversations(self, user_id: str) -> list[dict[str, Any]]:
        """List all conversations for a user."""
        return self.repo.list_by_user(user_id)

    def get_conversation(self, conversation_id: str, user_id: str) -> dict[str, Any]:
        """Retrieve a specific conversation, verifying ownership."""
        conv = self.repo.get_by_id_and_user(conversation_id, user_id)
        if not conv:
            raise ConversationNotFoundError()
        return conv

    def delete_conversation(self, conversation_id: str, user_id: str) -> None:
        """Delete a conversation and its messages."""
        # Verify ownership first implicitly via the repo method
        deleted = self.repo.delete_by_id_and_user(conversation_id, user_id)
        if not deleted:
            raise ConversationNotFoundError()

        # We don't strictly need to delete messages manually if ON DELETE CASCADE
        # is set up in Supabase, but doing it explicitly guarantees clean up.
        self.message_repo.delete_by_conversation(conversation_id)
        logger.info("User %s deleted conversation %s", user_id, conversation_id)
