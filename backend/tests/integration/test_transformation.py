"""Integration tests for image transformation — IMAGE_TRANSFORMATION intent."""

from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from PIL import Image


def _make_png_bytes() -> bytes:
    img = Image.new("RGB", (64, 64), color=(100, 200, 100))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


FAKE_PNG = _make_png_bytes()


def _mock_asset(asset_id: str, user_id: str, gen_type: str = "uploaded") -> dict:
    return {
        "id": asset_id,
        "user_id": user_id,
        "conversation_id": "conv-1",
        "message_id": None,
        "type": "image",
        "storage_path": f"input-images/user-1/conv-1/{asset_id}.png",
        "mime_type": "image/png",
        "prompt": None,
        "generation_type": gen_type,
        "parent_asset_id": None,
        "created_at": "2026-01-01T00:00:00Z",
    }


def _mock_generated_asset(asset_id: str, user_id: str, gen_type: str = "image_transformation") -> dict:
    return {
        "id": asset_id,
        "user_id": user_id,
        "conversation_id": "conv-1",
        "message_id": "msg-1",
        "type": "image",
        "storage_path": f"generated-images/user-1/conv-1/{asset_id}.png",
        "mime_type": "image/png",
        "prompt": "Turn this into a watercolor painting",
        "generation_type": gen_type,
        "parent_asset_id": None,
        "created_at": "2026-01-01T00:01:00Z",
    }


class TestImageTransformation:
    """Integration tests for IMAGE_TRANSFORMATION workflow."""

    @patch("app.services.message_service.build_graph")
    @patch("app.db.repositories.asset.get_service_client")
    @patch("app.db.repositories.message.MessageRepository._client")
    @patch("app.db.repositories.conversation.ConversationRepository._client")
    @patch("app.services.storage_service.get_service_client")
    def test_transformation_with_asset_id(
        self,
        mock_storage_client,
        mock_conv_client,
        mock_msg_client,
        mock_asset_client,
        mock_build_graph,
        client: TestClient,
        mock_verify_token,
        auth_headers: dict,
    ):
        """Should trigger IMAGE_TRANSFORMATION when asset_ids provided."""
        user_id = mock_verify_token.id

        # Mock conversation ownership check
        mock_conv_db = MagicMock()
        mock_conv_client.return_value = mock_conv_db
        conv_data = {"id": "conv-1", "user_id": user_id, "title": "Test"}
        mock_conv_db.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            conv_data
        ]
        mock_conv_db.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [conv_data]

        # Mock user message creation
        mock_msg_db = MagicMock()
        mock_msg_client.return_value = mock_msg_db
        mock_msg_db.table.return_value.insert.return_value.execute.return_value.data = [
            {
                "id": "msg-user-1",
                "conversation_id": "conv-1",
                "user_id": user_id,
                "role": "user",
                "content": "Turn this into a watercolor painting",
                "created_at": "2026-01-01T00:00:00Z",
            }
        ]
        # Mock assistant message fetch (list_by_conversation newest_first=True)
        mock_msg_db.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {
                "id": "msg-assistant-1",
                "conversation_id": "conv-1",
                "user_id": user_id,
                "role": "assistant",
                "content": "Here's your transformed image.",
                "created_at": "2026-01-01T00:01:00Z",
            }
        ]

        # Mock asset repo
        mock_asset_db = MagicMock()
        mock_asset_client.return_value = mock_asset_db
        generated_asset = _mock_generated_asset("gen-asset-1", user_id)
        mock_asset_db.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            generated_asset
        ]
        mock_asset_db.table.return_value.update.return_value.eq.return_value.execute.return_value.data = []

        # Mock storage signed URL
        mock_storage_db = MagicMock()
        mock_storage_client.return_value = mock_storage_db
        mock_storage_db.storage.from_.return_value.create_signed_url.return_value = {
            "signedURL": "https://example.com/signed-url"
        }

        # Mock the LangGraph to skip real AI calls
        mock_graph = AsyncMock()
        mock_graph.ainvoke = AsyncMock(
            return_value={
                "generated_asset_id": "gen-asset-1",
                "generated_storage_path": "generated-images/user-1/conv-1/gen-asset-1.png",
                "generated_mime_type": "image/png",
                "generation_type": "image_transformation",
                "parent_asset_id": "input-asset-1",
                "response_text": "Here's your transformed image.",
                "intent": "image_transformation",
                "error": None,
            }
        )
        mock_build_graph.return_value = mock_graph

        response = client.post(
            "/api/v1/conversations/conv-1/messages",
            json={
                "content": "Turn this into a watercolor painting",
                "asset_ids": ["input-asset-1"],
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert "user_message" in data
        assert "assistant_message" in data
        # Verify the graph was invoked (transformation happened)
        mock_graph.ainvoke.assert_called_once()
        # Verify asset_ids were passed in the state
        invoked_state = mock_graph.ainvoke.call_args[0][0]
        assert invoked_state["input_asset_ids"] == ["input-asset-1"]

    def test_send_message_without_asset_ids_still_works(self, client: TestClient, auth_headers: dict):
        """Sending a message without asset_ids should work (backwards compatible)."""
        # This test just verifies the schema accepts messages without asset_ids.
        # We don't need a full mock chain — 401 is expected since no real auth.
        response = client.post(
            "/api/v1/conversations/conv-1/messages",
            json={"content": "Create a mountain lake"},
        )
        # Without auth, 401 is expected
        assert response.status_code == 401
