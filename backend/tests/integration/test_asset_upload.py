"""Integration tests for asset upload endpoint."""

from io import BytesIO
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from PIL import Image


def _make_png_bytes(width: int = 32, height: int = 32) -> bytes:
    """Create minimal PNG bytes for testing."""
    img = Image.new("RGB", (width, height), color=(100, 150, 200))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestAssetUpload:
    """Integration tests for POST /api/v1/assets/upload."""

    @patch("app.db.repositories.asset.get_service_client")
    @patch("app.services.storage_service.get_service_client")
    def test_upload_valid_png(
        self,
        mock_storage_client,
        mock_asset_client,
        client: TestClient,
        mock_verify_token,
        auth_headers: dict,
    ):
        """Should upload a valid PNG and return asset metadata."""
        # Mock storage upload
        mock_storage = MagicMock()
        mock_storage_client.return_value = mock_storage
        mock_storage.storage.from_.return_value.upload.return_value = None

        # Mock asset DB insert
        mock_db = MagicMock()
        mock_asset_client.return_value = mock_db
        mock_db.table.return_value.insert.return_value.execute.return_value.data = [
            {
                "id": "asset-upload-1",
                "user_id": mock_verify_token.id,
                "conversation_id": "conv-1",
                "message_id": None,
                "type": "image",
                "storage_path": "input-images/user-1/conv-1/abc.png",
                "mime_type": "image/png",
                "prompt": None,
                "generation_type": "uploaded",
                "parent_asset_id": None,
                "created_at": "2026-01-01T00:00:00Z",
            }
        ]

        png_bytes = _make_png_bytes()
        response = client.post(
            "/api/v1/assets/upload?conversation_id=conv-1",
            headers=auth_headers,
            files={"file": ("test.png", png_bytes, "image/png")},
        )

        assert response.status_code == 201
        data = response.json()
        assert "asset" in data
        assert data["asset"]["id"] == "asset-upload-1"
        assert data["asset"]["mime_type"] == "image/png"
        assert data["asset"]["generation_type"] == "uploaded"

    def test_upload_unauthenticated(self, client: TestClient):
        """Should return 401 without auth headers."""
        png_bytes = _make_png_bytes()
        response = client.post(
            "/api/v1/assets/upload?conversation_id=conv-1",
            files={"file": ("test.png", png_bytes, "image/png")},
        )
        assert response.status_code == 401

    def test_upload_invalid_mime_type(self, client: TestClient, mock_verify_token, auth_headers: dict):
        """Should return 400 for unsupported file types."""
        response = client.post(
            "/api/v1/assets/upload?conversation_id=conv-1",
            headers=auth_headers,
            files={"file": ("test.gif", b"GIF87a...", "image/gif")},
        )
        assert response.status_code == 400

    def test_upload_missing_conversation_id(self, client: TestClient, mock_verify_token, auth_headers: dict):
        """Should return 422 if conversation_id is missing."""
        png_bytes = _make_png_bytes()
        response = client.post(
            "/api/v1/assets/upload",  # No conversation_id
            headers=auth_headers,
            files={"file": ("test.png", png_bytes, "image/png")},
        )
        assert response.status_code == 422
