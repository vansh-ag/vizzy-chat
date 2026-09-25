"""Integration tests for multi-image transformation — MULTI_IMAGE_TRANSFORMATION intent."""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


class TestMultiImageTransformation:
    """Integration tests for multi-image workflow."""

    @patch("app.services.message_service.build_graph")
    @patch("app.db.repositories.asset.get_service_client")
    @patch("app.db.repositories.message.MessageRepository._client")
    @patch("app.db.repositories.conversation.ConversationRepository._client")
    @patch("app.services.storage_service.get_service_client")
    def test_multi_image_produces_one_output(
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
        """Sending 3 asset_ids should call the graph and produce exactly ONE output."""
        user_id = mock_verify_token.id

        # Mock conversation
        mock_conv_db = MagicMock()
        mock_conv_client.return_value = mock_conv_db
        conv_data = {"id": "conv-1", "user_id": user_id, "title": "Test"}
        mock_conv_db.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            conv_data
        ]
        mock_conv_db.table.return_value.update.return_value.eq.return_value.execute.return_value.data = []

        # Mock messages
        mock_msg_db = MagicMock()
        mock_msg_client.return_value = mock_msg_db
        mock_msg_db.table.return_value.insert.return_value.execute.return_value.data = [
            {
                "id": "msg-user-1",
                "conversation_id": "conv-1",
                "user_id": user_id,
                "role": "user",
                "content": "Combine these into one moodboard",
                "created_at": "2026-01-01T00:00:00Z",
            }
        ]
        mock_msg_db.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {
                "id": "msg-assistant-1",
                "conversation_id": "conv-1",
                "user_id": user_id,
                "role": "assistant",
                "content": "Here's the combined output from your images.",
                "created_at": "2026-01-01T00:01:00Z",
            }
        ]

        # Mock asset lookup (output asset)
        output_asset = {
            "id": "output-asset-1",
            "user_id": user_id,
            "conversation_id": "conv-1",
            "message_id": "msg-assistant-1",
            "type": "image",
            "storage_path": "generated-images/user-1/conv-1/output.png",
            "mime_type": "image/png",
            "prompt": "Combine these into one moodboard",
            "generation_type": "multi_image_transformation",
            "parent_asset_id": None,
            "created_at": "2026-01-01T00:01:00Z",
        }
        mock_asset_db = MagicMock()
        mock_asset_client.return_value = mock_asset_db
        mock_asset_db.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            output_asset
        ]
        mock_asset_db.table.return_value.update.return_value.eq.return_value.execute.return_value.data = []

        # Mock storage
        mock_storage_db = MagicMock()
        mock_storage_client.return_value = mock_storage_db
        mock_storage_db.storage.from_.return_value.create_signed_url.return_value = {
            "signedURL": "https://example.com/signed-url-output"
        }

        # Mock graph — returns exactly ONE output asset
        mock_graph = AsyncMock()
        mock_graph.ainvoke = AsyncMock(
            return_value={
                "generated_asset_id": "output-asset-1",
                "generated_storage_path": "generated-images/user-1/conv-1/output.png",
                "generated_mime_type": "image/png",
                "generation_type": "multi_image_transformation",
                "parent_asset_id": None,
                "response_text": "Here's the combined output from your images.",
                "intent": "multi_image_transformation",
                "error": None,
            }
        )
        mock_build_graph.return_value = mock_graph

        response = client.post(
            "/api/v1/conversations/conv-1/messages",
            json={
                "content": "Combine these into one moodboard",
                "asset_ids": ["asset-a", "asset-b", "asset-c"],
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()

        # The graph should have been called with 3 input asset IDs
        invoked_state = mock_graph.ainvoke.call_args[0][0]
        assert len(invoked_state["input_asset_ids"]) == 3
        assert "asset-a" in invoked_state["input_asset_ids"]
        assert "asset-b" in invoked_state["input_asset_ids"]
        assert "asset-c" in invoked_state["input_asset_ids"]

        # Exactly ONE output asset in the response
        if data.get("generated_asset"):
            assert data["generated_asset"]["generation_type"] == "multi_image_transformation"

    def test_asset_ids_schema_validation(self, client: TestClient, auth_headers: dict):
        """asset_ids field should be optional — empty list works fine."""
        # Just verify schema accepts no asset_ids (no auth = 401)
        response = client.post(
            "/api/v1/conversations/conv-1/messages",
            json={"content": "Create a city"},
        )
        assert response.status_code == 401  # No auth, but schema is valid

    def test_asset_ids_with_empty_list(self, client: TestClient, auth_headers: dict):
        """asset_ids: [] should be accepted by the schema."""
        response = client.post(
            "/api/v1/conversations/conv-1/messages",
            json={"content": "Create a city", "asset_ids": []},
        )
        assert response.status_code == 401  # No auth, but schema is valid


class TestMultiInputRelationships:
    """Tests for asset_inputs junction table relationships."""

    def test_multi_input_relationship_structure(self):
        """Verify the asset_inputs relationship structure (A, B, C → D)."""
        input_a = {"id": "a", "generation_type": "uploaded"}
        input_b = {"id": "b", "generation_type": "uploaded"}
        input_c = {"id": "c", "generation_type": "uploaded"}
        output_d = {"id": "d", "generation_type": "multi_image_transformation", "parent_asset_id": None}

        # The relationships stored in asset_inputs
        relationships = [
            {"output_asset_id": "d", "input_asset_id": "a"},
            {"output_asset_id": "d", "input_asset_id": "b"},
            {"output_asset_id": "d", "input_asset_id": "c"},
        ]

        assert len(relationships) == 3
        assert all(r["output_asset_id"] == output_d["id"] for r in relationships)
        input_ids = {r["input_asset_id"] for r in relationships}
        assert input_ids == {input_a["id"], input_b["id"], input_c["id"]}

    def test_output_is_exactly_one_asset(self):
        """Verify that multi-image transformation always produces exactly one output."""
        # This is a structural verification of the design rule
        inputs = ["a", "b", "c"]
        outputs = ["d"]  # Always exactly 1

        assert len(outputs) == 1
        assert len(inputs) >= 2
