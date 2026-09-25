"""Application-level constants for Vizzy Chat."""

# Supported image MIME types for upload
ALLOWED_IMAGE_MIME_TYPES: frozenset[str] = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/webp",
    }
)

# Corresponding allowed file extensions
ALLOWED_IMAGE_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
    }
)

# API version prefix
API_V1_PREFIX = "/api/v1"
