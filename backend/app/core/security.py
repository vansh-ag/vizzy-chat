"""JWT / access-token verification logic.

The frontend sends:  Authorization: Bearer <supabase_access_token>

This module:
1. Extracts the raw token from the Authorization header.
2. Verifies it against Supabase Auth (get_user call).
3. Returns the authenticated Supabase user object.

Supabase Auth owns signup / login / session management.
We only verify the token here — we do NOT issue tokens ourselves.
"""

import logging

from fastapi import Header
from fastapi.security.utils import get_authorization_scheme_param
from supabase_auth.types import User

from app.core.exceptions import AuthenticationError
from app.db.supabase import get_anon_client

logger = logging.getLogger(__name__)


def _extract_bearer_token(authorization: str) -> str:
    """Parse 'Bearer <token>' and return the raw token.

    Args:
        authorization: The raw Authorization header value.

    Returns:
        The extracted token string.

    Raises:
        AuthenticationError: If the header is missing or not Bearer scheme.
    """
    if not authorization:
        raise AuthenticationError("Authorization header is missing.")

    scheme, token = get_authorization_scheme_param(authorization)

    if scheme.lower() != "bearer":
        raise AuthenticationError("Invalid authentication scheme. Expected Bearer.")

    if not token:
        raise AuthenticationError("Bearer token is missing.")

    return token


async def verify_token(authorization: str = Header(default="")) -> User:
    """Verify a Supabase access token and return the authenticated user.

    Args:
        authorization: The raw Authorization header (injected by FastAPI).

    Returns:
        The authenticated :class:`gotrue.types.User` object.

    Raises:
        AuthenticationError: On any authentication failure.
    """
    token = _extract_bearer_token(authorization)

    try:
        client = get_anon_client()
        response = client.auth.get_user(token)
    except Exception as exc:
        # Do NOT log the token itself
        logger.warning("Token verification failed: %s", type(exc).__name__)
        raise AuthenticationError("Invalid or expired token.") from exc

    # supabase_auth returns Optional[UserResponse] where .user is the User
    user = response.user if response is not None else None
    if user is None:
        raise AuthenticationError("Invalid or expired token.")

    return user
