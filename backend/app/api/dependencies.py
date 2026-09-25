"""FastAPI dependency injection providers.

Centralises all reusable ``Depends`` factories so route files stay clean
and business logic is kept out of route handlers.
"""

from fastapi import Depends
from supabase_auth.types import User

from app.core.security import verify_token


async def get_current_user(user: User = Depends(verify_token)) -> User:
    """FastAPI dependency that enforces authentication.

    Validates the ``Authorization: Bearer <token>`` header and returns
    the authenticated Supabase :class:`~gotrue.types.User`.

    Raises:
        AuthenticationError: Propagated from :func:`~app.core.security.verify_token`
            when the token is missing, malformed, or invalid.

    Example usage in a route::

        @router.get("/me")
        async def me(current_user: User = Depends(get_current_user)):
            ...
    """
    return user
