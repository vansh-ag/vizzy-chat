"""Base classes for AI providers."""

import abc

from app.ai.intent.schemas import IntentResult


class LLMProvider(abc.ABC):
    """Abstract base class for LLM providers."""

    @abc.abstractmethod
    async def classify_intent(self, messages: list[dict[str, str]]) -> IntentResult:
        """Classify the intent of the user request based on the conversation context.

        Args:
            messages: A list of message dicts (role, content).

        Returns:
            An IntentResult containing the structured intent and instruction.
        """
        pass


class ImageProvider(abc.ABC):
    """Abstract base class for image generation and transformation providers.

    All methods return exactly ONE image as raw bytes.
    """

    @abc.abstractmethod
    async def generate_image(self, prompt: str) -> bytes:
        """Generate a single image from a prompt.

        Args:
            prompt: The instruction for image generation.

        Returns:
            Raw bytes of the generated image (e.g. PNG).
        """
        pass

    @abc.abstractmethod
    async def transform_image(self, images: list[bytes], instruction: str) -> bytes:
        """Transform one or more input images according to an instruction.

        For single-image transformation (IMAGE_TRANSFORMATION, IMAGE_REFINEMENT):
            Pass a list of length 1.

        For multi-image transformation (MULTI_IMAGE_TRANSFORMATION):
            Pass a list of 2+ images. The provider may composite them or use the
            first image as primary with the others as style references.

        Args:
            images:      List of raw image bytes (at least 1 item).
            instruction: The editing/transformation instruction.

        Returns:
            Raw bytes of the single output image (PNG).

        Raises:
            ImageTransformationError: If the provider fails to transform.
        """
        pass
