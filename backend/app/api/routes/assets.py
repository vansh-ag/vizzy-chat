"""Asset API endpoints — Phase 4.

Provides:
  POST /assets/upload  — Upload one image file, returns asset metadata.
  GET  /assets/{id}    — Retrieve asset metadata + signed URL.
"""

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from supabase_auth.types import User

from app.api.dependencies import get_current_user
from app.schemas.asset import AssetResponse, AssetUploadResponse
from app.services.asset_service import AssetService

router = APIRouter(
    prefix="/assets",
    tags=["assets"],
)


def get_asset_service() -> AssetService:
    """Dependency provider for AssetService."""
    return AssetService()


@router.post(
    "/upload",
    response_model=AssetUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload an input image",
    description=(
        "Upload one image file (JPEG, PNG, or WebP) to the private input-images bucket. "
        "The returned asset ID can be passed as `asset_ids` in subsequent message requests "
        "to use this image as transformation input. "
        "Requires a `conversation_id` query parameter to associate the upload with a conversation."
    ),
)
async def upload_asset(
    conversation_id: str = Query(..., description="UUID of the conversation this image belongs to."),
    file: UploadFile = File(..., description="Image file to upload (JPEG, PNG, WebP, max 10 MB)."),
    current_user: User = Depends(get_current_user),
    service: AssetService = Depends(get_asset_service),
) -> AssetUploadResponse:
    """Upload and validate an image, store it in private storage, create asset record."""
    return await service.upload_input_asset(
        user_id=current_user.id,
        conversation_id=conversation_id,
        upload=file,
    )


@router.get(
    "/{asset_id}",
    response_model=AssetResponse,
    summary="Get asset metadata and signed URL",
    description=(
        "Retrieve metadata for an asset owned by the current user. "
        "Includes a signed URL for temporary private access to the image file."
    ),
)
def get_asset(
    asset_id: str,
    current_user: User = Depends(get_current_user),
    service: AssetService = Depends(get_asset_service),
) -> AssetResponse:
    """Return asset metadata with a signed URL."""
    asset = service.get_asset(asset_id, current_user.id)
    try:
        signed_url = service.get_signed_url(asset_id, current_user.id)
    except Exception:
        signed_url = None

    return AssetResponse(
        id=asset["id"],
        type=asset["type"],
        storage_path=asset["storage_path"],
        mime_type=asset["mime_type"],
        generation_type=asset.get("generation_type", ""),
        parent_asset_id=asset.get("parent_asset_id"),
        prompt=asset.get("prompt"),
        conversation_id=asset.get("conversation_id"),
        message_id=asset.get("message_id"),
        created_at=asset.get("created_at"),
        signed_url=signed_url,
    )
