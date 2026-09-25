"""Shared pytest fixtures for Vizzy Chat Phase 1 tests.

Fixtures provided:
- ``client``: Synchronous TestClient with the FastAPI app.
- ``valid_user``: A mock Supabase User object for use in auth mocks.
- ``auth_headers``: Authorization headers with a dummy Bearer token.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from supabase_auth.types import User

from app.main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Return a synchronous TestClient for the FastAPI application."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def valid_user() -> User:
    """Return a mock Supabase User for testing authenticated endpoints."""
    user = MagicMock(spec=User)
    user.id = "00000000-0000-0000-0000-000000000001"
    user.email = "test@example.com"
    user.role = "authenticated"
    return user


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Return Authorization headers with a dummy Bearer token."""
    return {"Authorization": "Bearer dummy-test-token"}


@pytest.fixture
def mock_verify_token(valid_user: User):
    """Override the verify_token dependency to return a mock user."""
    from app.api.dependencies import get_current_user

    async def _override() -> User:
        return valid_user

    with patch.object(app, "dependency_overrides", {get_current_user: _override}):
        # FastAPI dependency_overrides dict mutation
        app.dependency_overrides[get_current_user] = _override
        yield valid_user
        app.dependency_overrides.clear()
