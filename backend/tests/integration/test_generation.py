"""Integration tests for the AI generation workflow (LangGraph + Providers)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from groq.types.chat.chat_completion import (
    ChatCompletion,
    ChatCompletionMessage,
    Choice,
)

from app.services.message_service import MessageService


@pytest.mark.asyncio
class TestGenerationWorkflow:
    @patch("app.ai.providers.image.huggingface_provider.AsyncInferenceClient")
    @patch("app.ai.providers.llm.groq_provider.AsyncGroq")
    @patch("app.ai.graph.nodes.StorageService")
    @patch("app.services.message_service.StorageService")
    @patch("app.db.repositories.asset.AssetRepository._client")
    @patch("app.db.repositories.message.MessageRepository._client")
    @patch("app.db.repositories.conversation.ConversationRepository._client")
    async def test_full_text_to_image_flow(
        self,
        mock_conv_client,
        mock_msg_client,
        mock_asset_client,
        mock_service_storage,
        mock_node_storage,
        mock_groq,
        mock_hf,
    ):
        """Test the end-to-end Send Message -> LangGraph -> Image Generation flow."""

        # 1. Setup DB mocks
        mock_conv_db = MagicMock()
        mock_conv_client.return_value = mock_conv_db

        mock_msg_db = MagicMock()
        mock_msg_client.return_value = mock_msg_db

        mock_asset_db = MagicMock()
        mock_asset_client.return_value = mock_asset_db

        # We need to mock the entire Supabase ORM chain for the tables
        # For conversation ownership check:
        mock_conv_db.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"id": "conv-1"}
        ]

        # For message creation:
        mock_msg_db.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": "msg-new", "role": "user", "content": "make a cat", "created_at": "2026-01-01T00:00:00Z"}
        ]

        # For message list
        mock_msg_db.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value.data = [
            {
                "id": "msg-assistant",
                "role": "assistant",
                "content": "I generated the image based on your description.",
                "created_at": "2026-01-01T00:00:00Z",
            }
        ]
        mock_msg_db.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {
                "id": "msg-assistant",
                "role": "assistant",
                "content": "I generated the image based on your description.",
                "created_at": "2026-01-01T00:00:00Z",
            }
        ]

        # For asset retrieval:
        mock_asset_db.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": "asset-1", "type": "image", "storage_path": "path.png", "mime_type": "image/png", "prompt": "a cat"}
        ]
        mock_asset_db.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"id": "asset-1", "type": "image", "storage_path": "path.png", "mime_type": "image/png", "prompt": "a cat"}
        ]

        # For asset creation:
        # We already mocked insert above, but it returns a dict. It's fine if the ID doesn't match perfectly.

        # Storage mocks
        storage_upload_result = AsyncMock()
        storage_upload_result.full_path = "generated-images/path.png"
        mock_service_storage.return_value.create_signed_url.return_value = "https://signed.url"
        mock_node_storage.return_value.upload_file.return_value = storage_upload_result
        # 2. Setup AI mocks
        groq_client = mock_groq.return_value
        groq_client.chat.completions.create = AsyncMock(
            return_value=ChatCompletion(
                id="test",
                choices=[
                    Choice(
                        finish_reason="stop",
                        index=0,
                        message=ChatCompletionMessage(
                            content='{"intent": "image_generation", "instruction": "a cat"}', role="assistant"
                        ),
                    )
                ],
                created=123,
                model="test",
                object="chat.completion",
            )
        )

        hf_client = mock_hf.return_value
        # text_to_image returns a PIL Image. We mock it to just return a dummy PIL Image.
        from PIL import Image

        dummy_img = Image.new("RGB", (10, 10))
        hf_client.text_to_image = AsyncMock(return_value=dummy_img)

        # 3. Execute service
        service = MessageService()
        # Ensure graph uses the mock dependencies by patching at module level if needed,
        # but our graph nodes instantiate the classes directly, so our @patch decorators handle it.

        response = await service.send_message("conv-1", "user-1", "make a cat")

        # 4. Verify outputs
        assert response.user_message.content == "make a cat"
        assert response.assistant_message.role == "assistant"
        assert response.generated_asset is not None
        assert response.generated_asset.id == "asset-1"
        assert response.generated_asset.signed_url == "https://signed.url"

        # 5. Verify internal workflow execution
        hf_client.text_to_image.assert_called_once_with("a cat", model="black-forest-labs/FLUX.1-schnell")
        mock_node_storage.return_value.upload_file.assert_called_once()
        mock_asset_client.return_value.table.return_value.insert.assert_called()
