"""Tests for intent classification and parsing — Phase 4."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from groq.types.chat.chat_completion import (
    ChatCompletion,
    ChatCompletionMessage,
    Choice,
)

from app.ai.intent.classifier import IntentClassifier
from app.ai.intent.schemas import IntentResult, IntentType
from app.core.exceptions import IntentClassificationError


def _make_completion(content: str) -> ChatCompletion:
    return ChatCompletion(
        id="test-id",
        choices=[
            Choice(
                finish_reason="stop",
                index=0,
                message=ChatCompletionMessage(content=content, role="assistant"),
            )
        ],
        created=1234567890,
        model="test-model",
        object="chat.completion",
    )


@pytest.mark.asyncio
class TestIntentClassifier:
    @patch("app.ai.providers.llm.groq_provider.AsyncGroq")
    async def test_successful_classification(self, mock_async_groq):
        """Intent classifier should successfully parse a valid JSON response."""
        mock_client = mock_async_groq.return_value
        mock_client.chat.completions.create = AsyncMock(
            return_value=_make_completion(
                json.dumps(
                    {
                        "intent": "image_generation",
                        "instruction": "A neon city",
                        "target_asset_id": None,
                    }
                )
            )
        )

        classifier = IntentClassifier()
        classifier.provider.model = "test-model"

        result = await classifier.classify([{"role": "user", "content": "Make a neon city"}])

        assert result.intent == IntentType.IMAGE_GENERATION
        assert result.instruction == "A neon city"
        assert result.target_asset_id is None

        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        assert messages[0]["role"] == "system"
        assert "You must respond in pure JSON format matching this schema" in messages[0]["content"]

    @patch("app.ai.providers.llm.groq_provider.AsyncGroq")
    async def test_classification_error_on_invalid_json(self, mock_async_groq):
        """Should raise IntentClassificationError if JSON is invalid."""
        mock_client = mock_async_groq.return_value
        mock_client.chat.completions.create = AsyncMock(return_value=_make_completion("Not json"))

        classifier = IntentClassifier()

        with pytest.raises(IntentClassificationError):
            await classifier.classify([{"role": "user", "content": "Make a neon city"}])

    @patch("app.ai.providers.llm.groq_provider.AsyncGroq")
    async def test_refinement_intent(self, mock_async_groq):
        """Intent classifier should parse IMAGE_REFINEMENT intent."""
        mock_client = mock_async_groq.return_value
        mock_client.chat.completions.create = AsyncMock(
            return_value=_make_completion(
                json.dumps(
                    {
                        "intent": "image_refinement",
                        "instruction": "Make the image darker and add rain",
                        "target_asset_id": None,
                    }
                )
            )
        )

        classifier = IntentClassifier()
        result = await classifier.classify([{"role": "user", "content": "Make it darker and add rain"}])

        assert result.intent == IntentType.IMAGE_REFINEMENT
        assert "darker" in result.instruction.lower() or "rain" in result.instruction.lower()

    @patch("app.ai.providers.llm.groq_provider.AsyncGroq")
    async def test_transformation_intent(self, mock_async_groq):
        """Intent classifier should parse IMAGE_TRANSFORMATION intent."""
        mock_client = mock_async_groq.return_value
        mock_client.chat.completions.create = AsyncMock(
            return_value=_make_completion(
                json.dumps(
                    {
                        "intent": "image_transformation",
                        "instruction": "Turn this into a watercolor painting",
                        "target_asset_id": None,
                    }
                )
            )
        )

        classifier = IntentClassifier()
        result = await classifier.classify([{"role": "user", "content": "Turn this into a watercolor painting"}])

        assert result.intent == IntentType.IMAGE_TRANSFORMATION

    @patch("app.ai.providers.llm.groq_provider.AsyncGroq")
    async def test_multi_image_transformation_intent(self, mock_async_groq):
        """Intent classifier should parse MULTI_IMAGE_TRANSFORMATION intent."""
        mock_client = mock_async_groq.return_value
        mock_client.chat.completions.create = AsyncMock(
            return_value=_make_completion(
                json.dumps(
                    {
                        "intent": "multi_image_transformation",
                        "instruction": "Combine these into one professional moodboard",
                        "target_asset_id": None,
                    }
                )
            )
        )

        classifier = IntentClassifier()
        result = await classifier.classify([{"role": "user", "content": "Combine these images into one moodboard"}])

        assert result.intent == IntentType.MULTI_IMAGE_TRANSFORMATION


class TestIntentResult:
    """Test IntentResult schema defaults."""

    def test_default_input_asset_ids_empty(self):
        """input_asset_ids should default to an empty list."""
        result = IntentResult(intent=IntentType.IMAGE_GENERATION, instruction="test")
        assert result.input_asset_ids == []

    def test_default_target_asset_id_none(self):
        """target_asset_id should default to None."""
        result = IntentResult(intent=IntentType.IMAGE_REFINEMENT, instruction="make darker")
        assert result.target_asset_id is None
