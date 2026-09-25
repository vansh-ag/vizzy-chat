"""Asset repository — Phase 4 full implementation.

Handles:
- Input image assets (user-uploaded)
- Generated image assets (AI-generated, with lineage)
- asset_inputs junction table (multi-image relationships)

ALL queries enforce user ownership via user_id.
Service role client is used to bypass RLS (backend enforces ownership in code).
"""

import logging
from typing import Any

from app.db.supabase import get_service_client
from app.utils.id_utils import new_uuid

logger = logging.getLogger(__name__)

TABLE = "assets"
INPUTS_TABLE = "asset_inputs"

# generation_type values for generated (non-input) assets
GENERATED_TYPES = {
    "text_to_image",
    "image_transformation",
    "image_refinement",
    "multi_image_transformation",
}


class AssetRepository:
    """Database access for image assets and asset relationships."""

    def _client(self):  # type: ignore[return]
        return get_service_client()

    # ── Creation ─────────────────────────────────────────────────────────────

    def create_input_asset(
        self,
        user_id: str,
        conversation_id: str,
        storage_path: str,
        mime_type: str,
    ) -> dict[str, Any]:
        """Insert an uploaded (input) image asset record.

        Args:
            user_id:         Owner of the asset.
            conversation_id: Conversation this upload belongs to.
            storage_path:    Full path in the input-images bucket.
            mime_type:       MIME type of the uploaded file.

        Returns:
            The created asset row as a dict.
        """
        record = {
            "id": new_uuid(),
            "user_id": user_id,
            "conversation_id": conversation_id,
            "message_id": None,
            "type": "image",
            "storage_path": storage_path,
            "mime_type": mime_type,
            "prompt": None,
            "generation_type": "uploaded",
            "parent_asset_id": None,
        }
        response = self._client().table(TABLE).insert(record).execute()
        return response.data[0]

    def create_generated_asset(
        self,
        user_id: str,
        conversation_id: str,
        message_id: str | None,
        storage_path: str,
        mime_type: str,
        prompt: str,
        generation_type: str = "text_to_image",
        parent_asset_id: str | None = None,
    ) -> dict[str, Any]:
        """Insert a generated/transformed image asset record.

        Args:
            user_id:          Owner of the asset.
            conversation_id:  The conversation it belongs to.
            message_id:       The assistant message (may be None until linked).
            storage_path:     Path within the generated-images bucket.
            mime_type:        MIME type of the image file.
            prompt:           The image-generation/transformation prompt used.
            generation_type:  One of: text_to_image, image_transformation,
                              image_refinement, multi_image_transformation.
            parent_asset_id:  For lineage: the asset this was derived from.

        Returns:
            The created asset row as a dict.
        """
        record = {
            "id": new_uuid(),
            "user_id": user_id,
            "conversation_id": conversation_id,
            "message_id": message_id,
            "type": "image",
            "storage_path": storage_path,
            "mime_type": mime_type,
            "prompt": prompt,
            "generation_type": generation_type,
            "parent_asset_id": parent_asset_id,
        }
        response = self._client().table(TABLE).insert(record).execute()
        return response.data[0]

    # Phase 3 compatibility alias — wraps create_generated_asset
    def create(
        self,
        user_id: str,
        conversation_id: str,
        message_id: str | None,
        storage_path: str,
        mime_type: str,
        prompt: str,
        generation_type: str = "text_to_image",
        parent_asset_id: str | None = None,
    ) -> dict[str, Any]:
        """Backward-compatible alias for create_generated_asset."""
        return self.create_generated_asset(
            user_id=user_id,
            conversation_id=conversation_id,
            message_id=message_id,
            storage_path=storage_path,
            mime_type=mime_type,
            prompt=prompt,
            generation_type=generation_type,
            parent_asset_id=parent_asset_id,
        )

    # ── Queries ───────────────────────────────────────────────────────────────

    def get_by_id_and_user(self, asset_id: str, user_id: str) -> dict[str, Any] | None:
        """Fetch an asset only if it belongs to user_id (ownership check)."""
        response = self._client().table(TABLE).select("*").eq("id", asset_id).eq("user_id", user_id).limit(1).execute()
        data = response.data
        return data[0] if data else None

    def get_latest_generated_asset(self, conversation_id: str, user_id: str) -> dict[str, Any] | None:
        """Return the most recent AI-generated asset in a conversation.

        Only searches for assets with a generation_type that indicates they were
        AI-generated (not user-uploaded).

        Args:
            conversation_id: The conversation to search within.
            user_id:         The authenticated user's ID (ownership check).

        Returns:
            Asset dict of the latest generated image, or None if not found.
        """
        response = (
            self._client()
            .table(TABLE)
            .select("*")
            .eq("conversation_id", conversation_id)
            .eq("user_id", user_id)
            .in_("generation_type", list(GENERATED_TYPES))
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        data = response.data
        return data[0] if data else None

    def get_asset_children(self, parent_asset_id: str, user_id: str) -> list[dict[str, Any]]:
        """Return all assets that have the given parent_asset_id.

        Args:
            parent_asset_id: The parent asset's UUID.
            user_id:         Ownership check.

        Returns:
            List of child asset dicts ordered by creation time.
        """
        response = (
            self._client()
            .table(TABLE)
            .select("*")
            .eq("parent_asset_id", parent_asset_id)
            .eq("user_id", user_id)
            .order("created_at", desc=False)
            .execute()
        )
        return response.data or []

    # ── asset_inputs relationships ────────────────────────────────────────────

    def create_asset_input_relationship(self, output_asset_id: str, input_asset_id: str) -> dict[str, Any]:
        """Create a record linking an input asset to an output asset.

        Args:
            output_asset_id: The asset that was produced.
            input_asset_id:  An asset that was used as input.

        Returns:
            The created asset_inputs row.
        """
        record = {
            "id": new_uuid(),
            "output_asset_id": output_asset_id,
            "input_asset_id": input_asset_id,
        }
        response = self._client().table(INPUTS_TABLE).insert(record).execute()
        return response.data[0]

    def get_asset_inputs(self, output_asset_id: str, user_id: str) -> list[dict[str, Any]]:
        """Return all input assets used to produce the given output asset.

        Verifies ownership by joining on the assets table.

        Args:
            output_asset_id: The output asset UUID.
            user_id:         The authenticated user (ownership check on output).

        Returns:
            List of asset_inputs rows. Empty if not found or not owned.
        """
        response = (
            self._client()
            .table(INPUTS_TABLE)
            .select("*, output_asset:output_asset_id(user_id)")
            .eq("output_asset_id", output_asset_id)
            .execute()
        )
        rows = response.data or []
        # Filter: only return if the output asset is owned by user_id
        return [r for r in rows if r.get("output_asset", {}).get("user_id") == user_id]

    # ── Mutations ─────────────────────────────────────────────────────────────

    def update_message_id(self, asset_id: str, message_id: str) -> None:
        """Link an asset to the assistant message after message creation."""
        try:
            self._client().table(TABLE).update({"message_id": message_id}).eq("id", asset_id).execute()
        except Exception:
            logger.warning("Failed to update asset message_id: %s", asset_id)
