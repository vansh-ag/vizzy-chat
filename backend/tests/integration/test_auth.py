"""Integration tests for authentication — GET /api/v1/users/me.

Tests cover:
- Missing Authorization header → 401
- Malformed Authorization header → 401
- Invalid/expired token → 401
- Authenticated request (mocked) → 200 with user data

Real Supabase credentials are NOT required — token verification is mocked.
"""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from supabase_auth.types import User


class TestAuthEndpoint:
    """Tests for /api/v1/users/me authentication behaviour."""

    def test_missing_auth_header_returns_401(self, client: TestClient) -> None:
        """Missing Authorization header must return 401."""
        response = client.get("/api/v1/users/me")
        assert response.status_code == 401

    def test_malformed_auth_header_returns_401(self, client: TestClient) -> None:
        """Malformed Authorization header (wrong scheme) must return 401."""
        response = client.get("/api/v1/users/me", headers={"Authorization": "Basic dXNlcjpwYXNz"})
        assert response.status_code == 401

    def test_bearer_with_no_token_returns_401(self, client: TestClient) -> None:
        """'Bearer ' with no token must return 401."""
        response = client.get("/api/v1/users/me", headers={"Authorization": "Bearer "})
        assert response.status_code == 401

    def test_invalid_token_returns_401(self, client: TestClient) -> None:
        """An invalid/expired token must return 401."""
        with patch("app.core.security.get_anon_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.auth.get_user.side_effect = Exception("Invalid JWT")
            mock_get_client.return_value = mock_client

            response = client.get(
                "/api/v1/users/me",
                headers={"Authorization": "Bearer invalid.jwt.token"},
            )
        assert response.status_code == 401

    def test_invalid_token_does_not_expose_secrets(self, client: TestClient) -> None:
        """401 response must not contain internal error details."""
        with patch("app.core.security.get_anon_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.auth.get_user.side_effect = Exception("supabase internal detail")
            mock_get_client.return_value = mock_client

            response = client.get("/api/v1/users/me", headers={"Authorization": "Bearer bad-token"})

        body = response.text
        assert "supabase internal detail" not in body
        assert "service_role" not in body

    def test_authenticated_user_returns_200(self, client: TestClient, valid_user: User) -> None:
        """A valid (mocked) token should return 200 with user data."""
        from app.api.dependencies import get_current_user
        from app.main import app

        async def _mock_user() -> User:
            return valid_user

        app.dependency_overrides[get_current_user] = _mock_user
        try:
            response = client.get(
                "/api/v1/users/me",
                headers={"Authorization": "Bearer valid-mock-token"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == str(valid_user.id)
            assert data["email"] == valid_user.email
            assert data["role"] == valid_user.role
        finally:
            app.dependency_overrides.clear()

    def test_me_response_excludes_sensitive_fields(self, client: TestClient, valid_user: User) -> None:
        """The /me response must never contain tokens or secret keys."""
        from app.api.dependencies import get_current_user
        from app.main import app

        async def _mock_user() -> User:
            return valid_user

        app.dependency_overrides[get_current_user] = _mock_user
        try:
            response = client.get(
                "/api/v1/users/me",
                headers={"Authorization": "Bearer valid-mock-token"},
            )
            data = response.json()
            # Ensure no sensitive fields leak into the response
            assert "access_token" not in data
            assert "refresh_token" not in data
            assert "service_role" not in str(data)
        finally:
            app.dependency_overrides.clear()

    def test_401_response_has_error_envelope(self, client: TestClient) -> None:
        """401 response should follow the standard error envelope."""
        response = client.get("/api/v1/users/me")
        data = response.json()
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
