"""File validation utilities for uploaded images.

Validates:
- MIME type (allow-list: image/jpeg, image/png, image/webp)
- File extension
- File size (against MAX_UPLOAD_SIZE_MB)
- Basic image integrity via Pillow

Does NOT perform OCR, resizing, or any image processing.
"""

import io
import logging
import os

from fastapi import HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError

from app.core.config import get_settings
from app.core.constants import ALLOWED_IMAGE_EXTENSIONS, ALLOWED_IMAGE_MIME_TYPES

logger = logging.getLogger(__name__)


def _check_mime_type(content_type: str | None) -> None:
    """Raise 400 if the MIME type is not in the allow-list."""
    if content_type not in ALLOWED_IMAGE_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(f"Unsupported image type '{content_type}'. Allowed: {', '.join(sorted(ALLOWED_IMAGE_MIME_TYPES))}"),
        )


def _check_extension(filename: str | None) -> None:
    """Raise 400 if the file extension is not in the allow-list."""
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required.",
        )
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(f"Unsupported file extension '{ext}'. Allowed: {', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS))}"),
        )


def _check_size(data: bytes) -> None:
    """Raise 413 if the file exceeds MAX_UPLOAD_SIZE_MB."""
    settings = get_settings()
    max_bytes = settings.max_upload_size_bytes
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(f"File exceeds maximum upload size of {settings.max_upload_size_mb} MB."),
        )


def _check_image_integrity(data: bytes) -> None:
    """Raise 400 if Pillow cannot open the file as a valid image."""
    try:
        image = Image.open(io.BytesIO(data))
        image.verify()  # Does not decode pixel data — lightweight check
    except UnidentifiedImageError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is not a valid image.",
        ) from None
    except Exception as exc:
        logger.warning("Image integrity check failed: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is not a valid image.",
        ) from exc


async def validate_image_file(upload: UploadFile) -> bytes:
    """Validate an uploaded image file end-to-end.

    Checks:
    1. MIME type is in the allow-list.
    2. File extension is in the allow-list.
    3. File size does not exceed MAX_UPLOAD_SIZE_MB.
    4. Pillow can verify the image is valid.

    Args:
        upload: The :class:`fastapi.UploadFile` from a multipart request.

    Returns:
        The raw file bytes (already read — callers do not need to re-read).

    Raises:
        HTTPException 400: Invalid MIME type, extension, or image integrity.
        HTTPException 413: File size exceeds the configured limit.
    """
    _check_mime_type(upload.content_type)
    _check_extension(upload.filename)

    data = await upload.read()
    _check_size(data)
    _check_image_integrity(data)

    logger.debug(
        "Image validated: filename=%s, size=%d bytes, type=%s",
        upload.filename,
        len(data),
        upload.content_type,
    )
    return data
