"""Groq LLM provider implementation."""

import json
import logging
from typing import cast

from groq import AsyncGroq
from groq.types.chat import (
    ChatCompletion,
    ChatCompletionAssistantMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)
from groq.types.chat.completion_create_params import ResponseFormatResponseFormatJsonObject

from app.ai.intent.schemas import IntentResult
from app.ai.providers.base import LLMProvider
from app.core.config import get_settings
from app.core.exceptions import IntentClassificationError

logger = logging.getLogger(__name__)

# Union of all message param types the Groq SDK accepts for non-streaming calls.
# Our internal representation is list[dict[str, str]] with keys "role" and "content".
# The SDK types are TypedDicts with the same shape, so a narrow cast at the provider
# boundary is the correct approach — no broad Any, no type: ignore.
_GroqMessageParam = (
    ChatCompletionSystemMessageParam | ChatCompletionUserMessageParam | ChatCompletionAssistantMessageParam
)


def _to_groq_messages(
    messages: list[dict[str, str]],
) -> list[_GroqMessageParam]:
    """Convert Vizzy's internal message dicts to Groq SDK-typed message params.

    Each internal message has {"role": str, "content": str}.
    The Groq SDK TypedDicts for system/user/assistant messages have the same
    shape, so we dispatch by role and cast narrowly at the provider boundary.

    Roles not in the set (system, user, assistant) are silently dropped — they
    cannot appear in intent-classification context and would be rejected by the API.
    """
    result: list[_GroqMessageParam] = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "system":
            result.append(cast(ChatCompletionSystemMessageParam, {"role": "system", "content": content}))
        elif role == "user":
            result.append(cast(ChatCompletionUserMessageParam, {"role": "user", "content": content}))
        elif role == "assistant":
            result.append(
                cast(
                    ChatCompletionAssistantMessageParam,
                    {"role": "assistant", "content": content},
                )
            )
        else:
            logger.warning("Dropping unknown message role at Groq provider boundary: %r", role)
    return result


class GroqProvider(LLMProvider):
    """Implementation of LLMProvider using Groq's API."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY is not configured.")
        self.client = AsyncGroq(api_key=settings.groq_api_key)
        self.model = settings.groq_model

    async def classify_intent(self, messages: list[dict[str, str]]) -> IntentResult:
        """Use Groq to classify intent with JSON output."""
        try:
            schema_instruction = (
                "You must respond in pure JSON format matching this schema:\n"
                '{"intent": "image_generation" | "image_transformation" | '
                '"image_refinement" | "multi_image_transformation" | "unsupported", '
                '"instruction": "string describing the image task", '
                '"target_asset_id": null}'
                "\n\nNOTE: Always set target_asset_id to null. "
                "Do NOT generate input_asset_ids — the backend sets those."
            )

            # Augment the system prompt with the schema instruction
            augmented_messages = list(messages)
            if augmented_messages and augmented_messages[0]["role"] == "system":
                augmented_messages[0] = {
                    "role": "system",
                    "content": f"{augmented_messages[0]['content']}\n\n{schema_instruction}",
                }
            else:
                augmented_messages.insert(0, {"role": "system", "content": schema_instruction})

            # Convert to Groq SDK-typed message params at the provider boundary
            groq_messages = _to_groq_messages(augmented_messages)

            response_format = cast(ResponseFormatResponseFormatJsonObject, {"type": "json_object"})

            response: ChatCompletion = await self.client.chat.completions.create(
                messages=groq_messages,
                model=self.model,
                response_format=response_format,
                temperature=0.0,  # Deterministic intent classification
            )

            content = response.choices[0].message.content
            if not content:
                raise IntentClassificationError("Empty response from LLM.")

            data = json.loads(content)

            # Validate and parse using Pydantic
            intent_result = IntentResult.model_validate(data)
            return intent_result

        except IntentClassificationError:
            raise
        except Exception as exc:
            logger.exception("Groq intent classification failed.")
            raise IntentClassificationError("Failed to classify intent due to provider error.") from exc
