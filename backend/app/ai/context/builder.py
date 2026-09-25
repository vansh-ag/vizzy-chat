"""Context builder for retrieving and limiting conversation history."""

import logging

from app.ai.context.resolver import ContextResolver
from app.core.config import get_settings
from app.db.repositories.message import MessageRepository

logger = logging.getLogger(__name__)


class ContextBuilder:
    """Retrieves and formats conversation context."""

    def __init__(self) -> None:
        self.message_repo = MessageRepository()
        self.settings = get_settings()

    def build_context(self, conversation_id: str, user_id: str) -> list[dict[str, str]]:
        """Retrieve the latest messages for a conversation up to the limit.

        Args:
            conversation_id: The conversation UUID.
            user_id: The owner's UUID.

        Returns:
            A list of formatted message dicts ordered chronologically.
        """
        limit = self.settings.max_context_messages
        # We fetch the newest N messages to respect the context window
        raw_messages = self.message_repo.list_by_conversation(
            conversation_id=conversation_id,
            user_id=user_id,
            limit=limit,
            newest_first=True,
        )

        # Reverse them to restore chronological order for the LLM
        raw_messages.reverse()

        resolved = ContextResolver.resolve(raw_messages)
        logger.debug("Built context with %d messages (limit %d)", len(resolved), limit)
        return resolved
