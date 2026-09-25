"""User endpoints.

GET /api/v1/users/me

- Requires authentication (Bearer token).
- Returns safe user info — no tokens, no secrets.
"""

from fastapi import APIRouter, Depends
from supabase_auth.types import User

from app.api.dependencies import get_current_user
from app.schemas.common import UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user",
    description=(
        "Returns the authenticated user's safe profile information. "
        "Requires a valid Supabase access token in the Authorization header."
    ),
)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Return the authenticated user's public information."""
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        role=current_user.role or "authenticated",
    )
