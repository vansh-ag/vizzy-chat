"""Context formatting for the LLM."""


class ContextResolver:
    """Formats database messages for LLM consumption."""

    @staticmethod
    def resolve(messages: list[dict]) -> list[dict[str, str]]:
        """Convert database message records to LLM format.

        Filters out any unexpected roles.

        Args:
            messages: List of database row dicts.

        Returns:
            List of dicts with 'role' and 'content'.
        """
        resolved = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")
            if role in ("user", "assistant", "system") and content:
                resolved.append({"role": role, "content": content})
        return resolved
