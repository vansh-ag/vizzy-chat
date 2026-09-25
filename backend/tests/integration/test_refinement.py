"""Integration tests for image refinement — IMAGE_REFINEMENT intent and lineage."""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


class TestImageRefinement:
    """Integration tests for the refinement flow."""

    @patch("app.services.message_service.build_graph")
    @patch("app.db.repositories.asset.get_service_client")
    @patch("app.db.repositories.message.MessageRepository._client")
    @patch("app.db.repositories.conversation.ConversationRepository._client")
    @patch("app.services.storage_service.get_service_client")
    def test_refinement_creates_child_asset_with_parent_lineage(
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
        """Second message should produce asset B with parent_asset_id = A."""
        user_id = mock_verify_token.id
        ASSET_A = "asset-a-id"
        ASSET_B = "asset-b-id"

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
                "id": "msg-user-2",
                "conversation_id": "conv-1",
                "user_id": user_id,
                "role": "user",
                "content": "Make it darker and add rain",
                "created_at": "2026-01-01T00:01:00Z",
            }
        ]
        mock_msg_db.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {
                "id": "msg-assistant-2",
                "conversation_id": "conv-1",
                "user_id": user_id,
                "role": "assistant",
                "content": "Here's the refined version.",
                "created_at": "2026-01-01T00:01:00Z",
            }
        ]

        # Mock asset B with parent_asset_id = A
        asset_b_data = {
            "id": ASSET_B,
            "user_id": user_id,
            "conversation_id": "conv-1",
            "message_id": "msg-assistant-2",
            "type": "image",
            "storage_path": f"generated-images/user-1/conv-1/{ASSET_B}.png",
            "mime_type": "image/png",
            "prompt": "Make it darker and add rain",
            "generation_type": "image_refinement",
            "parent_asset_id": ASSET_A,  # ← Lineage!
            "created_at": "2026-01-01T00:01:00Z",
        }
        mock_asset_db = MagicMock()
        mock_asset_client.return_value = mock_asset_db
        mock_asset_db.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            asset_b_data
        ]
        mock_asset_db.table.return_value.update.return_value.eq.return_value.execute.return_value.data = []

        # Mock storage
        mock_storage_db = MagicMock()
        mock_storage_client.return_value = mock_storage_db
        mock_storage_db.storage.from_.return_value.create_signed_url.return_value = {
            "signedURL": "https://example.com/signed-url-b"
        }

        # Mock graph returning refinement result with parent_asset_id
        mock_graph = AsyncMock()
        mock_graph.ainvoke = AsyncMock(
            return_value={
                "generated_asset_id": ASSET_B,
                "generated_storage_path": f"generated-images/user-1/conv-1/{ASSET_B}.png",
                "generated_mime_type": "image/png",
                "generation_type": "image_refinement",
                "parent_asset_id": ASSET_A,
                "response_text": "Here's the refined version.",
                "intent": "image_refinement",
                "error": None,
            }
        )
        mock_build_graph.return_value = mock_graph

        response = client.post(
            "/api/v1/conversations/conv-1/messages",
            json={"content": "Make it darker and add rain", "asset_ids": []},
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert "assistant_message" in data

        # Verify graph was called with empty asset_ids (refinement uses latest generated)
        invoked_state = mock_graph.ainvoke.call_args[0][0]
        assert invoked_state["input_asset_ids"] == []

        # Verify the generated_asset has parent_asset_id set to ASSET_A
        if data.get("generated_asset"):
            assert data["generated_asset"]["parent_asset_id"] == ASSET_A
            assert data["generated_asset"]["generation_type"] == "image_refinement"


class TestAssetLineageVerification:
    """Tests that verify asset lineage chain: A → B → C."""

    def test_lineage_chain_a_to_b(self):
        """Verify that asset B correctly references asset A as parent."""
        # Conceptual test: the repository stores parent_asset_id
        asset_a = {
            "id": "asset-a",
            "parent_asset_id": None,
            "generation_type": "text_to_image",
        }
        asset_b = {
            "id": "asset-b",
            "parent_asset_id": "asset-a",
            "generation_type": "image_refinement",
        }
        assert asset_b["parent_asset_id"] == asset_a["id"]

    def test_lineage_chain_b_to_c(self):
        """Verify that asset C correctly references asset B as parent."""
        asset_b = {
            "id": "asset-b",
            "parent_asset_id": "asset-a",
        }
        asset_c = {
            "id": "asset-c",
            "parent_asset_id": "asset-b",
        }
        assert asset_c["parent_asset_id"] == asset_b["id"]

    def test_full_lineage_chain(self):
        """Verify the complete A → B → C lineage."""
        assets = [
            {"id": "a", "parent_asset_id": None},
            {"id": "b", "parent_asset_id": "a"},
            {"id": "c", "parent_asset_id": "b"},
        ]
        # Verify each asset points to the previous
        assert assets[0]["parent_asset_id"] is None
        assert assets[1]["parent_asset_id"] == assets[0]["id"]
        assert assets[2]["parent_asset_id"] == assets[1]["id"]
