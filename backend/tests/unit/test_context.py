"""Tests for context formatting and building."""

from unittest.mock import patch

from app.ai.context.resolver import ContextResolver


class TestContextResolver:
    def test_resolver_filters_invalid_roles(self):
        """Resolver should only include user, assistant, system roles."""
        raw_messages = [
            {"role": "user", "content": "Hello"},
            {"role": "unknown", "content": "Bad role"},
            {"role": "assistant", "content": "Hi"},
            {"role": "user", "content": ""},  # Empty content skipped
            {"content": "No role"},
        ]
        resolved = ContextResolver.resolve(raw_messages)
        assert len(resolved) == 2
        assert resolved[0] == {"role": "user", "content": "Hello"}
        assert resolved[1] == {"role": "assistant", "content": "Hi"}


class TestContextBuilder:
    @patch("app.ai.context.builder.MessageRepository")
    def test_build_context_reverses_order(self, mock_repo_class):
        """Context builder should fetch newest first and then reverse."""
        mock_repo = mock_repo_class.return_value
        # DB returns newest first: msg3, msg2, msg1
        mock_repo.list_by_conversation.return_value = [
            {"role": "user", "content": "msg3"},
            {"role": "assistant", "content": "msg2"},
            {"role": "user", "content": "msg1"},
        ]

        from app.ai.context.builder import ContextBuilder

        builder = ContextBuilder()
        builder.settings.max_context_messages = 3

        context = builder.build_context("conv1", "user1")

        # Result should be chronological: msg1, msg2, msg3
        assert len(context) == 3
        assert context[0]["content"] == "msg1"
        assert context[2]["content"] == "msg3"

        mock_repo.list_by_conversation.assert_called_once_with(
            conversation_id="conv1", user_id="user1", limit=3, newest_first=True
        )
