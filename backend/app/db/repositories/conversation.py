"""Conversation repository — database access for the conversations table.

All queries use the service-role client (bypasses RLS) but ALWAYS include
an explicit user_id filter as defense-in-depth ownership verification.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from app.db.supabase import get_service_client
from app.utils.id_utils import new_uuid

logger = logging.getLogger(__name__)

TABLE = "conversations"


class ConversationRepository:
    """Database access for conversations."""

    def _client(self):  # type: ignore[return]
        return get_service_client()

    def create(self, user_id: str, title: str) -> dict[str, Any]:
        """Insert a new conversation owned by user_id."""
        record = {
            "id": new_uuid(),
            "user_id": user_id,
            "title": title,
        }
        response = self._client().table(TABLE).insert(record).execute()
        return response.data[0]

    def list_by_user(self, user_id: str) -> list[dict[str, Any]]:
        """Return all conversations belonging to user, newest activity first."""
        response = (
            self._client().table(TABLE).select("*").eq("user_id", user_id).order("updated_at", desc=True).execute()
        )
        return response.data or []

    def get_by_id_and_user(self, conversation_id: str, user_id: str) -> dict[str, Any] | None:
        """Fetch a conversation only if it belongs to user_id.

        Returns None (not raises) to let the service decide the error shape.
        """
        response = (
            self._client().table(TABLE).select("*").eq("id", conversation_id).eq("user_id", user_id).limit(1).execute()
        )
        data = response.data
        return data[0] if data else None

    def delete_by_id_and_user(self, conversation_id: str, user_id: str) -> bool:
        """Delete a conversation owned by user_id.

        Returns True if a row was deleted, False if not found / not owned.
        """
        response = self._client().table(TABLE).delete().eq("id", conversation_id).eq("user_id", user_id).execute()
        return bool(response.data)

    def update_timestamp(self, conversation_id: str) -> None:
        """Bump updated_at so list ordering reflects recent activity."""
        now = datetime.now(UTC).isoformat()
        try:
            self._client().table(TABLE).update({"updated_at": now}).eq("id", conversation_id).execute()
        except Exception:
            # Non-critical — log and continue; don't fail the request
            logger.warning("Failed to update conversation timestamp: %s", conversation_id)
