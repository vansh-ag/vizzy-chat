"""Unit tests for app/core/config.py."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings


class TestSettings:
    """Tests for the Settings Pydantic model."""

    def test_get_settings_returns_instance(self) -> None:
        """get_settings() should return a Settings instance."""
        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_get_settings_is_cached(self) -> None:
        """get_settings() should return the same object on repeated calls."""
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_default_values(self) -> None:
        """Non-required fields should have sensible defaults."""
        settings = get_settings()
        assert settings.app_name == "vizzy-api"
        assert settings.input_image_bucket == "input-images"
        assert settings.generated_image_bucket == "generated-images"
        assert settings.max_upload_size_mb == 10
        assert settings.max_input_images == 5

    def test_cors_origins_list_single(self) -> None:
        """cors_origins_list should parse a single origin."""
        settings = get_settings()
        origins = settings.cors_origins_list
        assert isinstance(origins, list)
        assert len(origins) >= 1

    def test_cors_origins_list_multiple(self) -> None:
        """cors_origins_list should handle comma-separated origins."""
        settings = Settings.model_construct(
            app_name="test",
            app_env="test",
            debug=False,
            cors_origins="http://localhost:3000,http://localhost:4000",
            supabase_url="https://example.supabase.co",
            supabase_anon_key="anon-key",
            supabase_service_role_key="service-key",
        )
        origins = settings.cors_origins_list
        assert "http://localhost:3000" in origins
        assert "http://localhost:4000" in origins

    def test_max_upload_size_bytes(self) -> None:
        """max_upload_size_bytes should be max_upload_size_mb * 1024 * 1024."""
        settings = get_settings()
        expected = settings.max_upload_size_mb * 1024 * 1024
        assert settings.max_upload_size_bytes == expected

    def test_missing_supabase_url_raises(self) -> None:
        """Settings should raise ValidationError when supabase_url is empty."""
        with pytest.raises(ValidationError):
            Settings(
                supabase_url="",
                supabase_anon_key="anon-key",
                supabase_service_role_key="service-key",
            )

    def test_missing_supabase_anon_key_raises(self) -> None:
        """Settings should raise ValidationError when supabase_anon_key is empty."""
        with pytest.raises(ValidationError):
            Settings(
                supabase_url="https://example.supabase.co",
                supabase_anon_key="",
                supabase_service_role_key="service-key",
            )

    def test_missing_service_role_key_raises(self) -> None:
        """ValidationError when supabase_service_role_key is empty."""
        with pytest.raises(ValidationError):
            Settings(
                supabase_url="https://example.supabase.co",
                supabase_anon_key="anon-key",
                supabase_service_role_key="",
            )
