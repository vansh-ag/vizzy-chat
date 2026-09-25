"""Custom exception classes and global FastAPI exception handlers.

All error responses follow the consistent shape:

    {
        "error": {
            "code": "SOME_ERROR_CODE",
            "message": "Human-readable description"
        }
    }

Stack traces and internal details are never exposed to clients in production.
"""

import logging

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


# ── Custom exception hierarchy ────────────────────────────────────────────────


class VizzyException(Exception):
    """Base exception for all Vizzy application errors."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "INTERNAL_ERROR"
    message: str = "An unexpected error occurred."

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.__class__.message
        super().__init__(self.message)


class AuthenticationError(VizzyException):
    """Raised when a request cannot be authenticated."""

    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "AUTHENTICATION_ERROR"
    message = "Authentication required."


class AuthorizationError(VizzyException):
    """Raised when an authenticated user lacks permission."""

    status_code = status.HTTP_403_FORBIDDEN
    error_code = "AUTHORIZATION_ERROR"
    message = "You do not have permission to perform this action."


class NotFoundError(VizzyException):
    """Raised when a requested resource does not exist."""

    status_code = status.HTTP_404_NOT_FOUND
    error_code = "NOT_FOUND"
    message = "The requested resource was not found."


class ConversationNotFoundError(VizzyException):
    """Raised when a conversation is not found or doesn't belong to user."""

    status_code = status.HTTP_404_NOT_FOUND
    error_code = "CONVERSATION_NOT_FOUND"
    message = "Conversation not found."


class ValidationError(VizzyException):
    """Raised when request input is invalid."""

    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    error_code = "VALIDATION_ERROR"
    message = "Request validation failed."


class MessageInvalidError(VizzyException):
    """Raised when a message fails content validation."""

    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    error_code = "MESSAGE_INVALID"
    message = "Message content is invalid."


class StorageError(VizzyException):
    """Raised when a storage operation fails."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "STORAGE_ERROR"
    message = "A storage operation failed."


class IntentClassificationError(VizzyException):
    """Raised when intent classification by the LLM fails."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "INTENT_CLASSIFICATION_ERROR"
    message = "Failed to understand the request."


class ImageGenerationError(VizzyException):
    """Raised when image generation fails."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "IMAGE_GENERATION_ERROR"
    message = "Image generation failed."


class UnsupportedRequestError(VizzyException):
    """Raised when a user request cannot be handled in the current phase."""

    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "UNSUPPORTED_REQUEST"
    message = "This type of request is not supported yet."


# ── Phase 4 exceptions ────────────────────────────────────────────────────────


class AssetNotFoundError(VizzyException):
    """Raised when an asset is not found or doesn't exist."""

    status_code = status.HTTP_404_NOT_FOUND
    error_code = "ASSET_NOT_FOUND"
    message = "Asset not found."


class AssetAccessDeniedError(VizzyException):
    """Raised when a user tries to access another user's asset."""

    status_code = status.HTTP_404_NOT_FOUND  # 404 to avoid confirming existence
    error_code = "ASSET_NOT_FOUND"
    message = "Asset not found."


class InvalidImageError(VizzyException):
    """Raised when an image file is corrupt or unreadable."""

    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    error_code = "INVALID_IMAGE"
    message = "The provided image is invalid or unreadable."


class UnsupportedImageTypeError(VizzyException):
    """Raised when an image's MIME type is not supported."""

    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "UNSUPPORTED_IMAGE_TYPE"
    message = "This image format is not supported. Use JPEG, PNG, or WebP."


class ImageTransformationError(VizzyException):
    """Raised when image transformation fails."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "IMAGE_TRANSFORMATION_ERROR"
    message = "Image transformation failed."


class ImageRefinementError(VizzyException):
    """Raised when image refinement fails."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "IMAGE_REFINEMENT_ERROR"
    message = "Image refinement failed."


class MultiImageTransformationError(VizzyException):
    """Raised when multi-image transformation fails."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "MULTI_IMAGE_TRANSFORMATION_ERROR"
    message = "Multi-image transformation failed."


class NoTargetImageError(VizzyException):
    """Raised when a refinement/transformation is requested but no target image is found."""

    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "NO_TARGET_IMAGE"
    message = "No target image found. Please upload an image or reference a previously generated image."


class ProviderError(VizzyException):
    """Raised when an AI provider (LLM or image) returns an unexpected error."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code = "PROVIDER_ERROR"
    message = "The AI provider returned an error. Please try again."


# ── Error response helpers ────────────────────────────────────────────────────


def _error_body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


# ── FastAPI exception handlers ────────────────────────────────────────────────


async def vizzy_exception_handler(request: Request, exc: VizzyException) -> JSONResponse:
    """Handle all VizzyException subclasses."""
    logger.warning("VizzyException [%s]: %s", exc.error_code, exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(exc.error_code, exc.message),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic / FastAPI request validation errors."""
    logger.warning("RequestValidationError: %s", exc.errors())
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=_error_body("VALIDATION_ERROR", "Request validation failed."),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler — never exposes internal details to clients."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_error_body("INTERNAL_ERROR", "An unexpected error occurred."),
    )
