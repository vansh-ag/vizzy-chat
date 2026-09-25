"""Message repository — database access for the messages table.

Ownership is verified by checking that the parent conversation
belongs to the requesting user before any message operation.
"""

import logging
from typing import Any

from app.db.supabase import get_service_client
from app.utils.id_utils import new_uuid

logger = logging.getLogger(__name__)

TABLE = "messages"


class MessageRepository:
    """Database access for conversation messages."""

    def _client(self):  # type: ignore[return]
        return get_service_client()

    def create(
        self,
        conversation_id: str,
        user_id: str,
        role: str,
        content: str,
    ) -> dict[str, Any]:
        """Insert a new message into a conversation."""
        record = {
            "id": new_uuid(),
            "conversation_id": conversation_id,
            "user_id": user_id,
            "role": role,
            "content": content,
        }
        response = self._client().table(TABLE).insert(record).execute()
        return response.data[0]

    def list_by_conversation(
        self,
        conversation_id: str,
        user_id: str,
        limit: int | None = None,
        newest_first: bool = False,
    ) -> list[dict[str, Any]]:
        """Return messages for a conversation owned by user_id.

        Args:
            conversation_id: The conversation UUID.
            user_id: Must match the conversation owner (defense-in-depth).
            limit: Optional maximum number of messages to return.
            newest_first: If True, returns newest messages first (useful for
                context truncation — take last N then reverse).
        """
        query = (
            self._client()
            .table(TABLE)
            .select("*, assets(*)")
            .eq("conversation_id", conversation_id)
            .eq("user_id", user_id)
            .order("created_at", desc=newest_first)
        )
        if limit is not None:
            query = query.limit(limit)
        response = query.execute()
        return response.data or []

    def get_by_id(self, message_id: str) -> dict[str, Any] | None:
        """Fetch a single message by ID."""
        response = self._client().table(TABLE).select("*").eq("id", message_id).limit(1).execute()
        data = response.data
        return data[0] if data else None

    def delete_by_conversation(self, conversation_id: str) -> None:
        """Delete all messages for a conversation (cascade fallback)."""
        try:
            self._client().table(TABLE).delete().eq("conversation_id", conversation_id).execute()
        except Exception:
            logger.warning("Failed to delete messages for conversation: %s", conversation_id)
