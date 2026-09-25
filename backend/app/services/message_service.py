"""Message service — business logic for messages and AI dispatch — Phase 4."""

import logging
from typing import Any

from langgraph.graph.state import CompiledStateGraph

from app.ai.graph.builder import build_graph
from app.ai.graph.state import VizzyState
from app.core.config import get_settings
from app.core.exceptions import ConversationNotFoundError, MessageInvalidError
from app.db.repositories.asset import AssetRepository
from app.db.repositories.conversation import ConversationRepository
from app.db.repositories.message import MessageRepository
from app.schemas.message import (
    GeneratedAssetResponse,
    MessageResponse,
    SendMessageResponse,
)
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)


class MessageService:
    """Service layer for messages and AI coordination."""

    def __init__(self) -> None:
        self.message_repo = MessageRepository()
        self.conversation_repo = ConversationRepository()
        self.asset_repo = AssetRepository()
        self.storage = StorageService()
        self.settings = get_settings()
        self.graph: CompiledStateGraph = build_graph()

    def list_messages(self, conversation_id: str, user_id: str) -> list[dict[str, Any]]:
        """Retrieve all messages for a conversation, verifying ownership."""
        if not self.conversation_repo.get_by_id_and_user(conversation_id, user_id):
            raise ConversationNotFoundError()
        messages = self.message_repo.list_by_conversation(conversation_id, user_id, newest_first=False)

        # Post-process messages to attach generated_asset and signed URL
        for msg in messages:
            assets = msg.pop("assets", [])
            if assets:
                # Find the first generated asset (or just use the first one)
                # Typically there's only one output asset per message.
                asset_data = assets[0]
                signed_url = None
                try:
                    storage_path = asset_data["storage_path"]
                    if storage_path.startswith(self.settings.generated_image_bucket + "/"):
                        path = storage_path[len(self.settings.generated_image_bucket) + 1 :]
                        bucket = self.settings.generated_image_bucket
                    else:
                        path = storage_path
                        bucket = self.settings.generated_image_bucket

                    signed_url = self.storage.create_signed_url(bucket=bucket, path=path)
                except Exception as exc:
                    logger.warning("Failed to generate signed URL for historical asset %s: %s", asset_data["id"], exc)

                msg["generated_asset"] = GeneratedAssetResponse(
                    id=asset_data["id"],
                    type=asset_data["type"],
                    storage_path=asset_data["storage_path"],
                    mime_type=asset_data["mime_type"],
                    generation_type=asset_data.get("generation_type", "text_to_image"),
                    parent_asset_id=asset_data.get("parent_asset_id"),
                    prompt=asset_data.get("prompt"),
                    created_at=asset_data.get("created_at"),
                    signed_url=signed_url,
                )
                msg["image_url"] = signed_url

        return messages

    async def send_message(
        self,
        conversation_id: str,
        user_id: str,
        content: str,
        asset_ids: list[str] | None = None,
    ) -> SendMessageResponse:
        """Process a user message and trigger the AI workflow.

        Steps:
        1. Verify conversation ownership.
        2. Validate message content.
        3. Save user message.
        4. Execute LangGraph (with asset_ids injected into state).
        5. Gather results (assistant message + generated asset).
        6. Generate signed URL for generated image.
        7. Return full response.

        Args:
            conversation_id: UUID of the target conversation.
            user_id:         Authenticated user's ID.
            content:         The user's message text.
            asset_ids:       Optional list of previously-uploaded asset UUIDs.
        """
        # 1. Verify ownership
        if not self.conversation_repo.get_by_id_and_user(conversation_id, user_id):
            raise ConversationNotFoundError()

        # 2. Validate content
        content = content.strip()
        if not content:
            raise MessageInvalidError()

        # Normalise asset_ids
        validated_asset_ids: list[str] = list(asset_ids) if asset_ids else []

        # 3. Save user message
        user_message_data = self.message_repo.create(
            conversation_id=conversation_id,
            user_id=user_id,
            role="user",
            content=content,
        )
        user_message = MessageResponse.model_validate(user_message_data)
        self.conversation_repo.update_timestamp(conversation_id)

        logger.info(
            "message_received conversation_id=%s user_message_id=%s asset_ids=%s",
            conversation_id,
            user_message.id,
            validated_asset_ids,
        )

        # 4. Execute LangGraph
        initial_state = VizzyState(
            user_id=user_id,
            conversation_id=conversation_id,
            user_message_id=user_message.id,
            user_message_content=content,
            input_asset_ids=validated_asset_ids,
            conversation_history=[],
            resolved_input_assets=[],
            resolved_target_asset=None,
            intent=None,
            instruction=None,
            generated_image_bytes=None,
            generated_asset_id=None,
            generated_storage_path=None,
            generated_mime_type=None,
            generation_type=None,
            parent_asset_id=None,
            response_text=None,
            error=None,
        )

        logger.info("Starting AI workflow for message %s", user_message.id)
        final_state = await self.graph.ainvoke(initial_state)

        # 5. Gather results — fetch the newest assistant message
        messages = self.message_repo.list_by_conversation(conversation_id, user_id, limit=1, newest_first=True)
        assistant_message_data = messages[0]
        assistant_message = MessageResponse.model_validate(assistant_message_data)

        self.conversation_repo.update_timestamp(conversation_id)

        # 6. Did we generate an asset?
        asset_id = final_state.get("generated_asset_id")
        generated_asset: GeneratedAssetResponse | None = None
        signed_url: str | None = None

        if asset_id:
            asset_data = self.asset_repo.get_by_id_and_user(asset_id, user_id)
            if asset_data:
                # Generate signed URL for the output image
                try:
                    storage_path: str = asset_data["storage_path"]
                    if storage_path.startswith(self.settings.generated_image_bucket + "/"):
                        path = storage_path[len(self.settings.generated_image_bucket) + 1 :]
                        bucket = self.settings.generated_image_bucket
                    else:
                        path = storage_path
                        bucket = self.settings.generated_image_bucket

                    signed_url = self.storage.create_signed_url(
                        bucket=bucket,
                        path=path,
                    )
                    logger.info("asset_signed_url_generated asset_id=%s", asset_id)
                except Exception as exc:
                    logger.warning("Failed to generate signed URL for asset %s: %s", asset_id, exc)
                    signed_url = None

                generated_asset = GeneratedAssetResponse(
                    id=asset_data["id"],
                    type=asset_data["type"],
                    storage_path=asset_data["storage_path"],
                    mime_type=asset_data["mime_type"],
                    generation_type=asset_data.get("generation_type", "text_to_image"),
                    parent_asset_id=asset_data.get("parent_asset_id"),
                    prompt=asset_data.get("prompt"),
                    created_at=asset_data.get("created_at"),
                    signed_url=signed_url,
                )

        # 7. Return full response
        return SendMessageResponse(
            user_message=user_message,
            assistant_message=assistant_message,
            generated_asset=generated_asset,
            image_url=signed_url,
        )
