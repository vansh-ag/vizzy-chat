"""Image utility helpers (PIL conversions, compositing).

These are pure-function utilities with no external dependencies beyond Pillow.
They must NOT make network calls or database queries.
"""

import logging
from io import BytesIO

from PIL import Image, ImageDraw, UnidentifiedImageError

from app.core.exceptions import InvalidImageError

logger = logging.getLogger(__name__)

# Supported MIME types for transformation inputs
SUPPORTED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}


def pil_to_bytes(image: Image.Image, fmt: str = "PNG") -> bytes:
    """Convert a PIL Image to raw bytes.

    Args:
        image: A PIL Image object.
        fmt:   Output format. Defaults to PNG.

    Returns:
        Raw bytes of the image in the specified format.
    """
    output = BytesIO()
    # Convert to RGB if needed (e.g. RGBA not supported by JPEG)
    if fmt.upper() == "JPEG" and image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    image.save(output, format=fmt)
    return output.getvalue()


def bytes_to_pil(data: bytes) -> Image.Image:
    """Convert raw image bytes to a PIL Image.

    Args:
        data: Raw image bytes (JPEG, PNG, or WebP).

    Returns:
        PIL Image object.

    Raises:
        InvalidImageError: If the bytes cannot be decoded as an image.
    """
    try:
        img = Image.open(BytesIO(data))
        img.load()  # Force full decode to catch truncated files early
        return img
    except UnidentifiedImageError as exc:
        raise InvalidImageError("Cannot read image data.") from exc
    except Exception as exc:
        logger.warning("Image decoding failed: %s", type(exc).__name__)
        raise InvalidImageError("Cannot read image data.") from exc


def validate_image_bytes(data: bytes, mime_type: str | None = None) -> None:
    """Validate raw image bytes using Pillow.

    Args:
        data:      Raw image bytes.
        mime_type: Optional MIME type to check against the allow-list.

    Raises:
        InvalidImageError: If the image cannot be decoded.
        UnsupportedImageTypeError: If mime_type is not in the allowed set.
    """
    from app.core.exceptions import UnsupportedImageTypeError

    if mime_type and mime_type not in SUPPORTED_MIME_TYPES:
        raise UnsupportedImageTypeError(
            f"Image type '{mime_type}' is not supported. Use one of: {', '.join(sorted(SUPPORTED_MIME_TYPES))}"
        )
    # Decode using PIL to verify integrity
    bytes_to_pil(data)


def composite_images(images_bytes: list[bytes], max_dimension: int = 1024) -> Image.Image:
    """Composite multiple images side-by-side into a single PIL Image.

    This is the provider-level strategy for handling multi-image transformation
    when the underlying model (FLUX.1-Kontext-dev) accepts a single image input.
    Images are resized proportionally to fit within max_dimension and placed
    side-by-side on a white canvas.

    Args:
        images_bytes:  List of raw image bytes (2+).
        max_dimension: Maximum width or height for individual image thumbnails.

    Returns:
        A single PIL Image containing all input images arranged side-by-side.
    """
    pil_images: list[Image.Image] = []
    for data in images_bytes:
        img = bytes_to_pil(data)
        if img.mode != "RGB":
            img = img.convert("RGB")
        # Proportional resize so no image is larger than max_dimension
        img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
        pil_images.append(img)

    if not pil_images:
        raise InvalidImageError("No valid images to composite.")

    # Calculate combined canvas dimensions
    total_width = sum(img.width for img in pil_images)
    max_height = max(img.height for img in pil_images)

    # Add small separator lines between images
    sep = 4
    total_width += sep * (len(pil_images) - 1)

    canvas = Image.new("RGB", (total_width, max_height), color=(255, 255, 255))
    draw = ImageDraw.Draw(canvas)

    x_offset = 0
    for i, img in enumerate(pil_images):
        # Vertically center each image
        y_offset = (max_height - img.height) // 2
        canvas.paste(img, (x_offset, y_offset))
        x_offset += img.width
        # Draw separator
        if i < len(pil_images) - 1:
            draw.rectangle(
                [(x_offset, 0), (x_offset + sep - 1, max_height - 1)],
                fill=(200, 200, 200),
            )
            x_offset += sep

    logger.debug(
        "Composited %d images into %dx%d canvas",
        len(pil_images),
        total_width,
        max_height,
    )
    return canvas
