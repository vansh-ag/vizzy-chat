"""Integration tests for StorageService.

All Supabase Storage calls are mocked — no real bucket access required.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import StorageError
from app.services.storage_service import StorageService, UploadResult


@pytest.fixture
def storage_service() -> StorageService:
    """Return a StorageService instance."""
    return StorageService()


@pytest.fixture
def mock_storage_client():
    """Patch get_service_client to return a mock Supabase client."""
    mock_client = MagicMock()
    mock_bucket = MagicMock()
    mock_client.storage.from_.return_value = mock_bucket
    with patch(
        "app.services.storage_service.get_service_client",
        return_value=mock_client,
    ):
        yield mock_client, mock_bucket


class TestUploadFile:
    """Tests for StorageService.upload_file."""

    def test_upload_success(self, storage_service: StorageService, mock_storage_client: tuple) -> None:
        """Successful upload should return an UploadResult."""
        _, mock_bucket = mock_storage_client
        mock_bucket.upload.return_value = {"Key": "input-images/user-id/image.png"}

        result = storage_service.upload_file(
            bucket="input-images",
            path="user-id/image.png",
            data=b"fake-image-bytes",
            content_type="image/png",
        )

        assert isinstance(result, UploadResult)
        assert result.bucket == "input-images"
        assert result.path == "user-id/image.png"
        assert "input-images" in result.full_path

    def test_upload_failure_raises_storage_error(
        self, storage_service: StorageService, mock_storage_client: tuple
    ) -> None:
        """Upload failure should raise StorageError."""
        _, mock_bucket = mock_storage_client
        mock_bucket.upload.side_effect = Exception("bucket error")

        with pytest.raises(StorageError):
            storage_service.upload_file(
                bucket="input-images",
                path="user-id/image.png",
                data=b"fake-bytes",
            )


class TestDeleteFile:
    """Tests for StorageService.delete_file."""

    def test_delete_success(self, storage_service: StorageService, mock_storage_client: tuple) -> None:
        """Successful delete should not raise."""
        _, mock_bucket = mock_storage_client
        mock_bucket.remove.return_value = [{"name": "user-id/image.png"}]

        # Should complete without raising
        storage_service.delete_file(bucket="input-images", path="user-id/image.png")
        mock_bucket.remove.assert_called_once_with(["user-id/image.png"])

    def test_delete_failure_raises_storage_error(
        self, storage_service: StorageService, mock_storage_client: tuple
    ) -> None:
        """Delete failure should raise StorageError."""
        _, mock_bucket = mock_storage_client
        mock_bucket.remove.side_effect = Exception("delete error")

        with pytest.raises(StorageError):
            storage_service.delete_file(bucket="input-images", path="user-id/image.png")


class TestCreateSignedUrl:
    """Tests for StorageService.create_signed_url."""

    def test_create_signed_url_success(self, storage_service: StorageService, mock_storage_client: tuple) -> None:
        """Signed URL creation should return the URL string."""
        _, mock_bucket = mock_storage_client
        mock_bucket.create_signed_url.return_value = {"signedURL": "https://example.supabase.co/storage/v1/signed/..."}

        url = storage_service.create_signed_url(bucket="input-images", path="user-id/image.png", expires_in=3600)

        assert url.startswith("https://")

    def test_create_signed_url_failure_raises_storage_error(
        self, storage_service: StorageService, mock_storage_client: tuple
    ) -> None:
        """Signed URL failure should raise StorageError."""
        _, mock_bucket = mock_storage_client
        mock_bucket.create_signed_url.side_effect = Exception("storage error")

        with pytest.raises(StorageError):
            storage_service.create_signed_url(bucket="input-images", path="user-id/image.png")

    def test_empty_signed_url_raises_storage_error(
        self, storage_service: StorageService, mock_storage_client: tuple
    ) -> None:
        """An empty signed URL from Supabase should raise StorageError."""
        _, mock_bucket = mock_storage_client
        mock_bucket.create_signed_url.return_value = {"signedURL": ""}

        with pytest.raises(StorageError):
            storage_service.create_signed_url(bucket="generated-images", path="user-id/output.png")


class TestBucketConfiguration:
    """Tests that the service works with both configured buckets."""

    def test_input_images_bucket(self, storage_service: StorageService, mock_storage_client: tuple) -> None:
        """StorageService should work with the input-images bucket."""
        from app.core.config import get_settings

        settings = get_settings()
        _, mock_bucket = mock_storage_client
        mock_bucket.upload.return_value = {}

        result = storage_service.upload_file(
            bucket=settings.input_image_bucket,
            path="test/image.png",
            data=b"bytes",
        )
        assert result.bucket == settings.input_image_bucket

    def test_generated_images_bucket(self, storage_service: StorageService, mock_storage_client: tuple) -> None:
        """StorageService should work with the generated-images bucket."""
        from app.core.config import get_settings

        settings = get_settings()
        _, mock_bucket = mock_storage_client
        mock_bucket.upload.return_value = {}

        result = storage_service.upload_file(
            bucket=settings.generated_image_bucket,
            path="test/output.png",
            data=b"bytes",
        )
        assert result.bucket == settings.generated_image_bucket
