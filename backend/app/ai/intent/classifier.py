"""Intent classifier module."""

import logging

from app.ai.intent.prompts import INTENT_CLASSIFICATION_SYSTEM_PROMPT
from app.ai.intent.schemas import IntentResult
from app.ai.providers.llm.groq_provider import GroqProvider

logger = logging.getLogger(__name__)


class IntentClassifier:
    """Classifies user intent using an LLM provider."""

    def __init__(self) -> None:
        # In a real app we might inject this, but for now instantiate directly
        self.provider = GroqProvider()

    async def classify(self, conversation_history: list[dict[str, str]]) -> IntentResult:
        """Classify the user intent based on the conversation history.

        Args:
            conversation_history: Formatted list of message dicts (role, content).

        Returns:
            An IntentResult containing the intent enum and instruction.
        """
        # Prepend the system prompt for intent classification
        messages = [{"role": "system", "content": INTENT_CLASSIFICATION_SYSTEM_PROMPT}] + conversation_history

        logger.debug("Classifying intent using %d messages", len(messages))
        result = await self.provider.classify_intent(messages)
        logger.info("Intent classified: %s", result.intent.value)
        return result
