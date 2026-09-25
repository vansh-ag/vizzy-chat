"""Asset service — business logic for image upload and asset management.

This service is the single interface for:
- Validating and uploading user-provided images
- Retrieving asset metadata with ownership checks
- Generating signed URLs for private storage access

Provider calls (HF, Groq) do NOT happen here.
"""

import logging
import uuid

from fastapi import UploadFile

from app.core.config import get_settings
from app.core.exceptions import AssetNotFoundError
from app.db.repositories.asset import AssetRepository
from app.schemas.asset import AssetResponse, AssetUploadResponse
from app.services.storage_service import StorageService
from app.utils.file_validation import validate_image_file

logger = logging.getLogger(__name__)


class AssetService:
    """Service layer for image upload and asset management."""

    def __init__(self) -> None:
        self.asset_repo = AssetRepository()
        self.storage = StorageService()
        self.settings = get_settings()

    async def upload_input_asset(
        self,
        user_id: str,
        conversation_id: str,
        upload: UploadFile,
    ) -> AssetUploadResponse:
        """Validate, store, and record an uploaded input image.

        Steps:
        1. Validate MIME type, extension, size, and image integrity (Pillow).
        2. Generate a safe, unique storage path (no original filename used).
        3. Upload to the private input-images bucket.
        4. Create an asset record in the database.
        5. Return asset metadata.

        Args:
            user_id:         The authenticated user's ID.
            conversation_id: The conversation this upload is associated with.
            upload:          The multipart upload file from the FastAPI request.

        Returns:
            AssetUploadResponse with asset metadata.
        """
        # 1. Validate (raises HTTPException on failure)
        file_bytes = await validate_image_file(upload)
        content_type = upload.content_type or "image/jpeg"

        # 2. Generate safe storage path (never use original filename)
        ext_map = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
        }
        ext = ext_map.get(content_type, ".jpg")
        unique_name = f"{uuid.uuid4().hex}{ext}"
        path = f"{user_id}/{conversation_id}/{unique_name}"

        # 3. Upload to private bucket
        bucket = self.settings.input_image_bucket
        upload_result = self.storage.upload_file(
            bucket=bucket,
            path=path,
            data=file_bytes,
            content_type=content_type,
        )

        # 4. Create asset record
        asset_data = self.asset_repo.create_input_asset(
            user_id=user_id,
            conversation_id=conversation_id,
            storage_path=upload_result.full_path,
            mime_type=content_type,
        )

        logger.info(
            "asset_uploaded user_id=%s conversation_id=%s asset_id=%s path=%s",
            user_id,
            conversation_id,
            asset_data["id"],
            upload_result.full_path,
        )

        # 5. Build response
        asset_response = AssetResponse(
            id=asset_data["id"],
            type=asset_data["type"],
            storage_path=asset_data["storage_path"],
            mime_type=asset_data["mime_type"],
            generation_type=asset_data["generation_type"],
            parent_asset_id=asset_data.get("parent_asset_id"),
            prompt=asset_data.get("prompt"),
            conversation_id=asset_data.get("conversation_id"),
            message_id=asset_data.get("message_id"),
            created_at=asset_data.get("created_at"),
        )
        return AssetUploadResponse(asset=asset_response)

    def get_asset(self, asset_id: str, user_id: str) -> dict:
        """Retrieve asset metadata with ownership check.

        Args:
            asset_id: The asset UUID.
            user_id:  The authenticated user's ID.

        Returns:
            Asset dict.

        Raises:
            AssetNotFoundError: If not found or not owned by user_id.
        """
        asset = self.asset_repo.get_by_id_and_user(asset_id, user_id)
        if not asset:
            raise AssetNotFoundError()
        return asset

    def get_signed_url(self, asset_id: str, user_id: str, expires_in: int = 3600) -> str:
        """Get a signed URL for an asset after ownership verification.

        Args:
            asset_id:   The asset UUID.
            user_id:    The authenticated user's ID.
            expires_in: URL expiry in seconds.

        Returns:
            Signed URL string.

        Raises:
            AssetNotFoundError: If asset not found or not owned.
            StorageError: If URL generation fails.
        """
        asset = self.get_asset(asset_id, user_id)

        storage_path: str = asset["storage_path"]
        # Determine which bucket the asset is stored in
        if storage_path.startswith(self.settings.input_image_bucket + "/"):
            bucket = self.settings.input_image_bucket
            path = storage_path[len(self.settings.input_image_bucket) + 1 :]
        elif storage_path.startswith(self.settings.generated_image_bucket + "/"):
            bucket = self.settings.generated_image_bucket
            path = storage_path[len(self.settings.generated_image_bucket) + 1 :]
        else:
            # Fallback
            bucket = self.settings.generated_image_bucket
            path = storage_path

        return self.storage.create_signed_url(bucket=bucket, path=path, expires_in=expires_in)
