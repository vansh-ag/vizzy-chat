"""Unit tests for app/core/security.py — token extraction logic."""

import pytest

from app.core.exceptions import AuthenticationError
from app.core.security import _extract_bearer_token


class TestExtractBearerToken:
    """Tests for the internal _extract_bearer_token helper."""

    def test_valid_bearer_token(self) -> None:
        """Should return the raw token from a well-formed Bearer header."""
        token = _extract_bearer_token("Bearer mytoken123")
        assert token == "mytoken123"

    def test_empty_authorization_header(self) -> None:
        """Empty Authorization header should raise AuthenticationError."""
        with pytest.raises(AuthenticationError, match="missing"):
            _extract_bearer_token("")

    def test_missing_authorization_header(self) -> None:
        """None Authorization value should raise AuthenticationError."""
        with pytest.raises(AuthenticationError):
            _extract_bearer_token(None)  # type: ignore[arg-type]

    def test_wrong_scheme_basic(self) -> None:
        """Basic scheme should raise AuthenticationError."""
        with pytest.raises(AuthenticationError, match="scheme"):
            _extract_bearer_token("Basic dXNlcjpwYXNz")

    def test_wrong_scheme_apikey(self) -> None:
        """ApiKey scheme should raise AuthenticationError."""
        with pytest.raises(AuthenticationError, match="scheme"):
            _extract_bearer_token("ApiKey some-key")

    def test_bearer_without_token(self) -> None:
        """'Bearer ' with no token should raise AuthenticationError."""
        with pytest.raises(AuthenticationError, match="missing"):
            _extract_bearer_token("Bearer ")

    def test_bearer_case_insensitive(self) -> None:
        """Scheme matching should be case-insensitive (BEARER, bearer, Bearer)."""
        # FastAPI's get_authorization_scheme_param lowercases the scheme
        token = _extract_bearer_token("BEARER mytoken123")
        assert token == "mytoken123"
