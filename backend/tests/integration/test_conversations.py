"""Integration tests for the conversation API."""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


class TestConversationEndpoints:
    @patch("app.db.repositories.conversation.ConversationRepository._client")
    def test_create_conversation_success(self, mock_client, client: TestClient, mock_verify_token, auth_headers: dict):
        """Should create and return a conversation."""
        mock_db = MagicMock()
        mock_client.return_value = mock_db

        # Mock the Supabase chain: table("conversations").insert().execute()
        mock_db.table.return_value.insert.return_value.execute.return_value.data = [
            {
                "id": "conv-123",
                "user_id": mock_verify_token.id,
                "title": "My chat",
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
            }
        ]

        response = client.post("/api/v1/conversations", json={"title": "My chat"}, headers=auth_headers)

        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "conv-123"
        assert data["title"] == "My chat"

    @patch("app.db.repositories.conversation.ConversationRepository._client")
    def test_get_conversation_not_found(self, mock_client, client: TestClient, mock_verify_token, auth_headers: dict):
        """Should return 404 if conversation doesn't exist or isn't owned by user."""
        mock_db = MagicMock()
        mock_client.return_value = mock_db

        # Mock empty return from Supabase
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []

        response = client.get("/api/v1/conversations/missing-id", headers=auth_headers)

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "CONVERSATION_NOT_FOUND"

    @patch("app.db.repositories.conversation.ConversationRepository._client")
    @patch("app.db.repositories.message.MessageRepository._client")
    def test_delete_conversation(
        self, mock_msg_client, mock_conv_client, client: TestClient, mock_verify_token, auth_headers: dict
    ):
        """Should delete conversation and return 204."""
        mock_db = MagicMock()
        mock_conv_client.return_value = mock_db
        mock_msg_client.return_value = MagicMock()

        # Mock successful delete
        mock_db.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"id": "deleted"}
        ]

        response = client.delete("/api/v1/conversations/conv-123", headers=auth_headers)

        assert response.status_code == 204
