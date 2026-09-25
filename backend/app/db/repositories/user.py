"""User repository — database operations for user/profile data.

Phase 1 scope:
- Minimal repository stub.
- ``get_user_by_id`` is a Phase 2 implementation hook; it returns None in Phase 1
  since there is no profiles table yet.

Future phases will extend this with profile CRUD once a ``profiles`` table
is created. Expected schema (document in README):

    CREATE TABLE profiles (
        id          UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
        email       TEXT,
        display_name TEXT,
        avatar_url  TEXT,
        created_at  TIMESTAMPTZ DEFAULT NOW(),
        updated_at  TIMESTAMPTZ DEFAULT NOW()
    );

When the profiles table exists, implement get_user_by_id like:

    def get_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        client = get_service_client()
        response = (
            client.table("profiles")
            .select("id, email, display_name, avatar_url")
            .eq("id", user_id)
            .single()
            .execute()
        )
        return response.data
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class UserRepository:
    """Repository for user-related database operations."""

    def get_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        """Fetch user profile data by ID.

        Phase 1: Returns None — profiles table does not exist yet.
        Phase 2: Query the ``profiles`` table via the service-role client.

        Args:
            user_id: The UUID of the user (from Supabase Auth).

        Returns:
            A dict with profile fields, or ``None`` if not found / Phase 1.
        """
        # Phase 2: replace with actual profiles table query
        logger.debug("UserRepository.get_user_by_id called for %s (Phase 1 stub)", user_id)
        return None
