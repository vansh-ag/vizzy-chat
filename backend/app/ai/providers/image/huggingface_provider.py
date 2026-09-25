"""Hugging Face image provider implementation.

Uses:
  - FLUX.1-schnell    for text-to-image generation
  - FLUX.1-Kontext-dev for image-to-image transformation/refinement

All Hugging Face SDK calls are isolated in this module.
No HF-specific logic should appear in nodes, services, or routes.
"""

import logging
from io import BytesIO

from huggingface_hub import AsyncInferenceClient

from app.ai.providers.base import ImageProvider
from app.core.config import get_settings
from app.core.exceptions import ImageGenerationError, ImageTransformationError
from app.utils.image_utils import composite_images, pil_to_bytes

logger = logging.getLogger(__name__)


class HuggingFaceImageProvider(ImageProvider):
    """Implementation of ImageProvider using Hugging Face Inference API."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.hf_token:
            raise ValueError("HF_TOKEN is not configured.")
        # Async client is required since LangGraph nodes run async
        self.client = AsyncInferenceClient(token=settings.hf_token)
        self.generation_model = settings.image_generation_model
        self.edit_model = settings.image_edit_model

    async def generate_image(self, prompt: str) -> bytes:
        """Generate a single image from the prompt using FLUX.1-schnell."""
        try:
            logger.info("Requesting image generation from HF model: %s", self.generation_model)
            # text_to_image returns a PIL Image
            image = await self.client.text_to_image(prompt, model=self.generation_model)

            image_bytes = pil_to_bytes(image)
            logger.debug("Successfully generated image of size %d bytes", len(image_bytes))
            return image_bytes

        except Exception as exc:
            msg = "Failed to generate image due to provider error."
            # Attempt to safely inspect if it's an HfHubHTTPError without strict importing
            # to handle 402/429 gracefully based on response status code
            if hasattr(exc, "response") and hasattr(exc.response, "status_code"):
                if exc.response.status_code == 402:
                    msg = "Image generation is temporarily unavailable because the image provider has no remaining credits."
                elif exc.response.status_code == 429:
                    msg = "Image generation is temporarily unavailable due to rate limits. Please try again later."
            logger.exception("Hugging Face image generation failed.")
            raise ImageGenerationError(msg) from exc

    async def transform_image(self, images: list[bytes], instruction: str) -> bytes:
        """Transform one or more images using FLUX.1-Kontext-dev.

        FLUX.1-Kontext-dev accepts a single image + text prompt for image-to-image
        editing. For multi-image inputs, we composite the images side-by-side into
        a single reference image before calling the API — this is a documented
        provider-level strategy given the model's single-image input constraint.

        Args:
            images:      List of raw image bytes (1 or more).
            instruction: Editing instruction (e.g. "Make it darker and add rain").

        Returns:
            PNG bytes of the transformed output image.
        """
        if not images:
            raise ImageTransformationError("No input images provided for transformation.")

        try:
            # If multiple images, composite them into one reference image
            if len(images) > 1:
                logger.info(
                    "Compositing %d input images for multi-image transformation",
                    len(images),
                )
                input_pil = composite_images(images)
            else:
                from PIL import Image

                input_pil = Image.open(BytesIO(images[0]))
                # Ensure consistent format
                if input_pil.mode != "RGB":
                    input_pil = input_pil.convert("RGB")

            logger.info("Requesting image transformation from HF model: %s", self.edit_model)

            # FLUX.1-Kontext-dev image_to_image: pass PIL image + prompt
            result_image = await self.client.image_to_image(
                image=input_pil,
                prompt=instruction,
                model=self.edit_model,
            )

            image_bytes = pil_to_bytes(result_image)
            logger.debug("Successfully transformed image, output size %d bytes", len(image_bytes))
            return image_bytes

        except ImageTransformationError:
            raise
        except Exception as exc:
            msg = "Failed to transform image due to provider error."
            if hasattr(exc, "response") and hasattr(exc.response, "status_code"):
                if exc.response.status_code == 402:
                    msg = "Image generation is temporarily unavailable because the image provider has no remaining credits."
                elif exc.response.status_code == 429:
                    msg = "Image generation is temporarily unavailable due to rate limits. Please try again later."
            logger.exception("Hugging Face image transformation failed.")
            raise ImageTransformationError(msg) from exc
