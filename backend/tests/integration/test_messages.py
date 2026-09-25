"""Integration tests for the message API."""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.schemas.message import SendMessageResponse


class TestMessageEndpoints:
    @patch("app.db.repositories.conversation.ConversationRepository._client")
    @patch("app.db.repositories.message.MessageRepository._client")
    def test_list_messages_success(
        self, mock_msg_client, mock_conv_client, client: TestClient, mock_verify_token, auth_headers: dict
    ):
        """Should retrieve messages if user owns the conversation."""
        # 1. Mock conversation ownership check (get_by_id_and_user)
        mock_conv_db = MagicMock()
        mock_conv_client.return_value = mock_conv_db
        mock_conv_db.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"id": "conv-1"}
        ]

        # 2. Mock messages list
        mock_msg_db = MagicMock()
        mock_msg_client.return_value = mock_msg_db
        mock_msg_db.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value.data = [
            {"id": "msg-1", "role": "user", "content": "hello", "created_at": "2026-01-01T00:00:00Z"},
            {"id": "msg-2", "role": "assistant", "content": "hi", "created_at": "2026-01-01T00:01:00Z"},
        ]

        response = client.get("/api/v1/conversations/conv-1/messages", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["items"][0]["role"] == "user"

    @patch("app.services.message_service.MessageService.send_message")
    def test_post_message_calls_service(
        self, mock_send_message, client: TestClient, mock_verify_token, auth_headers: dict
    ):
        """POST should dispatch to the MessageService."""
        # Mock the service response
        mock_send_message.return_value = SendMessageResponse(
            user_message={"id": "msg-1", "role": "user", "content": "draw a cat", "created_at": "2026-01-01T00:00:00Z"},
            assistant_message={
                "id": "msg-2",
                "role": "assistant",
                "content": "done",
                "created_at": "2026-01-01T00:01:00Z",
            },
            generated_asset=None,
        )
        # Mock as async
        mock_send_message.side_effect = AsyncMock(return_value=mock_send_message.return_value)

        response = client.post(
            "/api/v1/conversations/conv-1/messages", json={"content": "draw a cat"}, headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["user_message"]["content"] == "draw a cat"
