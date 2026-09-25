"""Health check endpoint.

GET /api/v1/health

- Public (no authentication required).
- Lightweight — no external calls.
- Returns service name and current environment.
"""

from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.common import HealthResponse

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns service status. No authentication required.",
)
async def health() -> HealthResponse:
    """Return the current service health status."""
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        environment=settings.app_env,
    )
