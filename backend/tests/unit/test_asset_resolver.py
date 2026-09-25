"""Unit tests for AssetResolver."""

from unittest.mock import patch

import pytest

from app.ai.context.asset_resolver import AssetResolver
from app.core.exceptions import AssetNotFoundError, NoTargetImageError


def _make_asset(asset_id: str, user_id: str, gen_type: str = "text_to_image") -> dict:
    return {
        "id": asset_id,
        "user_id": user_id,
        "conversation_id": "conv-1",
        "generation_type": gen_type,
        "storage_path": "generated-images/path/file.png",
        "mime_type": "image/png",
    }


class TestResolveExplicit:
    """Tests for resolve_explicit (explicit asset ID resolution)."""

    @patch("app.ai.context.asset_resolver.AssetRepository")
    def test_resolves_owned_asset(self, mock_repo_cls):
        """Should return asset dict for a valid, owned asset ID."""
        asset = _make_asset("asset-1", "user-1")
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_by_id_and_user.return_value = asset

        resolver = AssetResolver()
        result = resolver.resolve_explicit(["asset-1"], "user-1")

        assert len(result) == 1
        assert result[0]["id"] == "asset-1"
        mock_repo.get_by_id_and_user.assert_called_once_with("asset-1", "user-1")

    @patch("app.ai.context.asset_resolver.AssetRepository")
    def test_raises_on_missing_asset(self, mock_repo_cls):
        """Should raise AssetNotFoundError if asset does not exist."""
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_by_id_and_user.return_value = None

        resolver = AssetResolver()
        with pytest.raises(AssetNotFoundError):
            resolver.resolve_explicit(["nonexistent-id"], "user-1")

    @patch("app.ai.context.asset_resolver.AssetRepository")
    def test_cross_user_access_rejected(self, mock_repo_cls):
        """Should raise AssetNotFoundError when user-2 tries to access user-1's asset."""
        # The repo returns None for cross-user queries (enforced by user_id filter)
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_by_id_and_user.return_value = None

        resolver = AssetResolver()
        with pytest.raises(AssetNotFoundError):
            resolver.resolve_explicit(["asset-1"], "user-2")

    @patch("app.ai.context.asset_resolver.AssetRepository")
    def test_resolves_multiple_assets(self, mock_repo_cls):
        """Should resolve multiple asset IDs and return them in order."""
        assets = [
            _make_asset("asset-1", "user-1"),
            _make_asset("asset-2", "user-1"),
        ]
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_by_id_and_user.side_effect = assets

        resolver = AssetResolver()
        result = resolver.resolve_explicit(["asset-1", "asset-2"], "user-1")

        assert len(result) == 2
        assert result[0]["id"] == "asset-1"
        assert result[1]["id"] == "asset-2"


class TestResolveLatestGenerated:
    """Tests for resolve_latest_generated."""

    @patch("app.ai.context.asset_resolver.AssetRepository")
    def test_returns_latest_asset(self, mock_repo_cls):
        """Should return the most recent generated asset."""
        asset = _make_asset("asset-latest", "user-1")
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_latest_generated_asset.return_value = asset

        resolver = AssetResolver()
        result = resolver.resolve_latest_generated("conv-1", "user-1")

        assert result is not None
        assert result["id"] == "asset-latest"
        mock_repo.get_latest_generated_asset.assert_called_once_with("conv-1", "user-1")

    @patch("app.ai.context.asset_resolver.AssetRepository")
    def test_returns_none_when_no_assets(self, mock_repo_cls):
        """Should return None if no generated assets exist in the conversation."""
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_latest_generated_asset.return_value = None

        resolver = AssetResolver()
        result = resolver.resolve_latest_generated("conv-1", "user-1")

        assert result is None


class TestResolveTargetAsset:
    """Tests for resolve_target_asset (priority-ordered resolution)."""

    @patch("app.ai.context.asset_resolver.AssetRepository")
    def test_explicit_id_takes_priority(self, mock_repo_cls):
        """Explicit asset_id should take priority over latest generated."""
        explicit_asset = _make_asset("explicit-id", "user-1")
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_by_id_and_user.return_value = explicit_asset
        mock_repo.get_latest_generated_asset.return_value = _make_asset("latest-id", "user-1")

        resolver = AssetResolver()
        result = resolver.resolve_target_asset("explicit-id", "conv-1", "user-1")

        assert result is not None
        assert result["id"] == "explicit-id"
        # Should NOT query latest if explicit ID provided and found
        mock_repo.get_latest_generated_asset.assert_not_called()

    @patch("app.ai.context.asset_resolver.AssetRepository")
    def test_falls_back_to_latest_generated(self, mock_repo_cls):
        """Should fall back to latest generated when no explicit ID provided."""
        latest_asset = _make_asset("latest-id", "user-1")
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_latest_generated_asset.return_value = latest_asset

        resolver = AssetResolver()
        result = resolver.resolve_target_asset(None, "conv-1", "user-1")

        assert result is not None
        assert result["id"] == "latest-id"

    @patch("app.ai.context.asset_resolver.AssetRepository")
    def test_raises_no_target_image_error_when_nothing_found(self, mock_repo_cls):
        """Should raise NoTargetImageError when nothing is available."""
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_latest_generated_asset.return_value = None

        resolver = AssetResolver()
        with pytest.raises(NoTargetImageError):
            resolver.resolve_target_asset(None, "conv-1", "user-1", require=True)

    @patch("app.ai.context.asset_resolver.AssetRepository")
    def test_returns_none_when_nothing_found_and_not_required(self, mock_repo_cls):
        """Should return None when nothing found and require=False."""
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_latest_generated_asset.return_value = None

        resolver = AssetResolver()
        result = resolver.resolve_target_asset(None, "conv-1", "user-1", require=False)

        assert result is None

    @patch("app.ai.context.asset_resolver.AssetRepository")
    def test_explicit_id_cross_user_raises(self, mock_repo_cls):
        """Cross-user explicit resolution must raise AssetNotFoundError."""
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_by_id_and_user.return_value = None  # Not owned

        resolver = AssetResolver()
        with pytest.raises(AssetNotFoundError):
            resolver.resolve_target_asset("other-user-asset", "conv-1", "user-2")
