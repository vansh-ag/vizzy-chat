"""Supabase Storage service.

Provides a clean abstraction over Supabase Storage operations for two
private buckets:

- ``input-images``:     User-uploaded source images.
- ``generated-images``: AI-generated output images (Phase 2+).

Both buckets are PRIVATE — access is always through signed URLs.
Raw storage credentials are NEVER exposed to the frontend.

Phase 1 implements the storage foundation only.
Actual image generation is out of scope for Phase 1.
"""

import logging
from dataclasses import dataclass

from app.core.config import get_settings
from app.core.exceptions import StorageError
from app.db.supabase import get_service_client

logger = logging.getLogger(__name__)


@dataclass
class UploadResult:
    """Result of a successful file upload."""

    bucket: str
    path: str
    full_path: str


class StorageService:
    """Service layer for Supabase Storage operations.

    All operations use the service-role client because the buckets are private.
    The service-role key is NEVER passed through to API responses.
    """

    def __init__(self) -> None:
        self._settings = get_settings()

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _storage(self):  # type: ignore[return]
        """Return the Supabase storage interface from the service client."""
        return get_service_client().storage

    # ── Public API ────────────────────────────────────────────────────────────

    def upload_file(
        self,
        bucket: str,
        path: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> UploadResult:
        """Upload a file to a private Supabase Storage bucket.

        Args:
            bucket: Target bucket name (e.g. ``input-images``).
            path: Storage path within the bucket (e.g. ``user-id/filename.png``).
            data: Raw file bytes to upload.
            content_type: MIME type of the file.

        Returns:
            An :class:`UploadResult` with bucket, path, and full_path.

        Raises:
            StorageError: If the upload fails.
        """
        try:
            self._storage().from_(bucket).upload(
                path=path,
                file=data,
                file_options={"content-type": content_type, "upsert": "false"},
            )
            full_path = f"{bucket}/{path}"
            logger.info("Uploaded file to storage: %s", full_path)
            return UploadResult(bucket=bucket, path=path, full_path=full_path)
        except Exception as exc:
            logger.exception("Storage upload failed for path: %s", path)
            raise StorageError(f"Failed to upload file: {path}") from exc

    def delete_file(self, bucket: str, path: str) -> None:
        """Delete a file from a private Supabase Storage bucket.

        Args:
            bucket: Target bucket name.
            path: Storage path within the bucket.

        Raises:
            StorageError: If the deletion fails.
        """
        try:
            self._storage().from_(bucket).remove([path])
            logger.info("Deleted file from storage: %s/%s", bucket, path)
        except Exception as exc:
            logger.exception("Storage delete failed for path: %s/%s", bucket, path)
            raise StorageError(f"Failed to delete file: {path}") from exc

    def download_file(self, bucket: str, path: str) -> bytes:
        """Download a file from a private Supabase Storage bucket.

        Args:
            bucket: Target bucket name.
            path:   Storage path within the bucket.

        Returns:
            Raw bytes of the file.

        Raises:
            StorageError: If the download fails.
        """
        try:
            data: bytes = self._storage().from_(bucket).download(path)
            logger.debug("Downloaded file from storage: %s/%s (%d bytes)", bucket, path, len(data))
            return data
        except Exception as exc:
            logger.exception("Storage download failed for path: %s/%s", bucket, path)
            raise StorageError(f"Failed to download file: {path}") from exc

    def create_signed_url(
        self,
        bucket: str,
        path: str,
        expires_in: int = 3600,
    ) -> str:
        """Create a temporary signed URL for private file access.

        Args:
            bucket: Target bucket name.
            path: Storage path within the bucket.
            expires_in: URL expiry in seconds (default: 1 hour).

        Returns:
            A signed URL string.

        Raises:
            StorageError: If URL generation fails.
        """
        try:
            response = self._storage().from_(bucket).create_signed_url(path=path, expires_in=expires_in)
            signed_url: str = response.get("signedURL") or response.get("signed_url", "")
            if not signed_url:
                raise StorageError("Supabase returned an empty signed URL.")
            logger.debug("Created signed URL for: %s/%s", bucket, path)
            return signed_url
        except StorageError:
            raise
        except Exception as exc:
            logger.exception("Signed URL creation failed for: %s/%s", bucket, path)
            raise StorageError(f"Failed to create signed URL for: {path}") from exc

    def get_file_metadata(self, bucket: str, path: str) -> dict:
        """Retrieve file metadata from a private bucket.

        Args:
            bucket: Target bucket name.
            path: Storage path within the bucket.

        Returns:
            A dict containing file metadata (name, size, etc.).

        Raises:
            StorageError: If the metadata retrieval fails.
        """
        try:
            # List with a search prefix to find the exact file
            folder, _, filename = path.rpartition("/")
            files = self._storage().from_(bucket).list(path=folder, options={"search": filename})
            if not files:
                raise StorageError(f"File not found: {path}")
            return files[0]  # type: ignore[return-value]
        except StorageError:
            raise
        except Exception as exc:
            logger.exception("Metadata fetch failed for: %s/%s", bucket, path)
            raise StorageError(f"Failed to get file metadata: {path}") from exc
