"""Asset resolver — resolves input/target images for the AI workflow.

Priority order for target image resolution:
1. Explicit asset_id supplied by the frontend (from MessageCreate.asset_ids).
2. Most recent generated image in the current conversation.
3. Raise NoTargetImageError.

Cross-conversation and cross-user resolution is explicitly prohibited.
All ownership checks use user_id.
"""

import logging
from typing import Any

from app.core.exceptions import AssetNotFoundError, NoTargetImageError
from app.db.repositories.asset import AssetRepository

logger = logging.getLogger(__name__)


class AssetResolver:
    """Resolves asset metadata from IDs, with strict ownership enforcement."""

    def __init__(self) -> None:
        self.asset_repo = AssetRepository()

    def resolve_explicit(self, asset_ids: list[str], user_id: str) -> list[dict[str, Any]]:
        """Fetch and verify ownership for an explicit list of asset IDs.

        Args:
            asset_ids: List of asset UUID strings (e.g. from MessageCreate.asset_ids).
            user_id:   The authenticated user's ID.

        Returns:
            List of asset dicts in the same order as asset_ids.

        Raises:
            AssetNotFoundError: If any asset does not exist or is not owned by user_id.
        """
        assets: list[dict[str, Any]] = []
        for asset_id in asset_ids:
            asset = self.asset_repo.get_by_id_and_user(asset_id, user_id)
            if not asset:
                logger.warning("Asset %s not found or not owned by user %s", asset_id, user_id)
                raise AssetNotFoundError(f"Asset {asset_id} not found or you do not have access.")
            assets.append(asset)
        return assets

    def resolve_latest_generated(self, conversation_id: str, user_id: str) -> dict[str, Any] | None:
        """Find the most recent generated asset in a conversation.

        Only searches within the given conversation (no cross-conversation lookup).
        Only searches for assets with generation_type in (text_to_image,
        image_transformation, image_refinement, multi_image_transformation).

        Args:
            conversation_id: The conversation to search within.
            user_id:         The authenticated user's ID.

        Returns:
            The most recent generated asset dict, or None if not found.
        """
        return self.asset_repo.get_latest_generated_asset(conversation_id, user_id)

    def resolve_target_asset(
        self,
        explicit_asset_id: str | None,
        conversation_id: str,
        user_id: str,
        require: bool = True,
    ) -> dict[str, Any] | None:
        """Resolve the target asset for a refinement operation.

        Priority:
        1. explicit_asset_id (if provided and owned by user)
        2. Most recent generated image in the conversation

        Args:
            explicit_asset_id: Optional explicit asset UUID from the request.
            conversation_id:   The current conversation.
            user_id:           The authenticated user's ID.
            require:           If True, raise NoTargetImageError when nothing found.

        Returns:
            Asset dict or None (when require=False and nothing found).

        Raises:
            AssetNotFoundError: If explicit_asset_id is provided but not found/owned.
            NoTargetImageError: If require=True and no target is found.
        """
        # Priority 1: explicit ID
        if explicit_asset_id:
            asset = self.asset_repo.get_by_id_and_user(explicit_asset_id, user_id)
            if not asset:
                raise AssetNotFoundError(f"Asset {explicit_asset_id} not found or you do not have access.")
            logger.debug("Resolved explicit target asset: %s", explicit_asset_id)
            return asset

        # Priority 2: latest generated asset in the conversation
        asset = self.resolve_latest_generated(conversation_id, user_id)
        if asset:
            logger.debug("Resolved latest generated asset %s for refinement", asset["id"])
            return asset

        # Nothing found
        if require:
            raise NoTargetImageError()
        return None
