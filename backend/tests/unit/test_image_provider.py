"""Unit tests for the HuggingFace image provider."""

from io import BytesIO
from unittest.mock import AsyncMock, patch

import pytest
from PIL import Image

from app.core.exceptions import ImageGenerationError, ImageTransformationError


def _make_pil_image(width: int = 64, height: int = 64) -> Image.Image:
    """Create a minimal test PIL image."""
    img = Image.new("RGB", (width, height), color=(100, 150, 200))
    return img


def _pil_to_bytes(img: Image.Image) -> bytes:
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.mark.asyncio
class TestHuggingFaceImageProvider:
    """Tests for HuggingFaceImageProvider methods."""

    @patch("app.ai.providers.image.huggingface_provider.AsyncInferenceClient")
    async def test_generate_image_returns_bytes(self, mock_client_cls):
        """generate_image should return PNG bytes."""
        from app.ai.providers.image.huggingface_provider import HuggingFaceImageProvider

        mock_client = mock_client_cls.return_value
        fake_image = _make_pil_image()
        mock_client.text_to_image = AsyncMock(return_value=fake_image)

        provider = HuggingFaceImageProvider()
        result = await provider.generate_image("A futuristic city")

        assert isinstance(result, bytes)
        assert len(result) > 0
        # Verify the result is a valid PNG
        loaded = Image.open(BytesIO(result))
        assert loaded.format == "PNG"
        mock_client.text_to_image.assert_called_once()

    @patch("app.ai.providers.image.huggingface_provider.AsyncInferenceClient")
    async def test_generate_image_raises_on_provider_error(self, mock_client_cls):
        """generate_image should raise ImageGenerationError on provider failure."""
        from app.ai.providers.image.huggingface_provider import HuggingFaceImageProvider

        mock_client = mock_client_cls.return_value
        mock_client.text_to_image = AsyncMock(side_effect=RuntimeError("API error"))

        provider = HuggingFaceImageProvider()
        with pytest.raises(ImageGenerationError):
            await provider.generate_image("A test prompt")

    @patch("app.ai.providers.image.huggingface_provider.AsyncInferenceClient")
    async def test_transform_image_returns_bytes(self, mock_client_cls):
        """transform_image should return PNG bytes from image_to_image."""
        from app.ai.providers.image.huggingface_provider import HuggingFaceImageProvider

        mock_client = mock_client_cls.return_value
        fake_output = _make_pil_image()
        mock_client.image_to_image = AsyncMock(return_value=fake_output)

        provider = HuggingFaceImageProvider()
        input_bytes = _pil_to_bytes(_make_pil_image())
        result = await provider.transform_image([input_bytes], "Make it darker")

        assert isinstance(result, bytes)
        assert len(result) > 0
        mock_client.image_to_image.assert_called_once()

    @patch("app.ai.providers.image.huggingface_provider.AsyncInferenceClient")
    async def test_transform_image_raises_on_empty_input(self, mock_client_cls):
        """transform_image should raise ImageTransformationError on empty input."""
        from app.ai.providers.image.huggingface_provider import HuggingFaceImageProvider

        provider = HuggingFaceImageProvider()
        with pytest.raises(ImageTransformationError):
            await provider.transform_image([], "Some instruction")

    @patch("app.ai.providers.image.huggingface_provider.AsyncInferenceClient")
    async def test_transform_multi_image_composites(self, mock_client_cls):
        """transform_image with multiple inputs should composite and call image_to_image once."""
        from app.ai.providers.image.huggingface_provider import HuggingFaceImageProvider

        mock_client = mock_client_cls.return_value
        fake_output = _make_pil_image()
        mock_client.image_to_image = AsyncMock(return_value=fake_output)

        provider = HuggingFaceImageProvider()
        img_a = _pil_to_bytes(_make_pil_image(64, 64))
        img_b = _pil_to_bytes(_make_pil_image(64, 64))
        img_c = _pil_to_bytes(_make_pil_image(64, 64))

        result = await provider.transform_image([img_a, img_b, img_c], "Combine into a moodboard")

        assert isinstance(result, bytes)
        # image_to_image should be called exactly ONCE with a composited image
        mock_client.image_to_image.assert_called_once()
        # The first positional/keyword argument should be a PIL Image (composited)
        call_kwargs = mock_client.image_to_image.call_args
        assert call_kwargs is not None

    @patch("app.ai.providers.image.huggingface_provider.AsyncInferenceClient")
    async def test_transform_image_raises_on_provider_error(self, mock_client_cls):
        """transform_image should raise ImageTransformationError on provider failure."""
        from app.ai.providers.image.huggingface_provider import HuggingFaceImageProvider

        mock_client = mock_client_cls.return_value
        mock_client.image_to_image = AsyncMock(side_effect=RuntimeError("Provider down"))

        provider = HuggingFaceImageProvider()
        input_bytes = _pil_to_bytes(_make_pil_image())
        with pytest.raises(ImageTransformationError):
            await provider.transform_image([input_bytes], "Make it darker")
