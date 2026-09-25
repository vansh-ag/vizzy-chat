"""UUID generation utilities."""

import uuid


def new_uuid() -> str:
    """Generate a new UUID4 string."""
    return str(uuid.uuid4())
