"""Shared Pydantic response schemas used across the API.

All response models use ``model_config`` with ``from_attributes=True`` so they
can be populated from ORM objects or plain dicts alike.
"""

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    """Response schema for the health check endpoint."""

    model_config = ConfigDict(from_attributes=True)

    status: str
    service: str
    environment: str


class UserResponse(BaseModel):
    """Safe user representation returned from /users/me.

    Does NOT include the access token, refresh token, raw JWT,
    service-role key, or any sensitive authentication metadata.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str | None
    role: str


class ErrorDetail(BaseModel):
    """Inner error detail object."""

    code: str
    message: str


class ErrorResponse(BaseModel):
    """Consistent error response envelope."""

    error: ErrorDetail
