"""Supabase client factory.

Two client types are provided:

1. **Anonymous client** (``get_anon_client``):
   - Uses the public anon key.
   - Used for user-facing operations such as token verification.
   - Safe to use in the context of an authenticated request.

2. **Service-role client** (``get_service_client``):
   - Uses the service-role key which bypasses Row Level Security.
   - MUST only be used server-side for privileged backend operations.
   - NEVER sent to or exposed in responses to the frontend.

Both clients are module-level singletons — they are created once and
reused for the lifetime of the process.
"""

import logging

from supabase import Client, create_client

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_anon_client: Client | None = None
_service_client: Client | None = None


def get_anon_client() -> Client:
    """Return the shared anonymous/public Supabase client.

    The client is initialised lazily on first call and cached.

    Returns:
        A :class:`supabase.Client` authenticated with the anon key.
    """
    global _anon_client  # noqa: PLW0603
    if _anon_client is None:
        settings = get_settings()
        logger.debug("Initialising anonymous Supabase client.")
        _anon_client = create_client(settings.supabase_url, settings.supabase_anon_key)
    return _anon_client


def get_service_client() -> Client:
    """Return the shared service-role Supabase client.

    .. warning::
        This client bypasses Row Level Security (RLS).
        Use only for privileged server-side operations.
        NEVER expose this client or its key to the frontend.

    Returns:
        A :class:`supabase.Client` authenticated with the service-role key.
    """
    global _service_client  # noqa: PLW0603
    if _service_client is None:
        settings = get_settings()
        logger.debug("Initialising service-role Supabase client.")
        _service_client = create_client(settings.supabase_url, settings.supabase_service_role_key)
    return _service_client
