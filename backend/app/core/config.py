"""Application configuration loaded from environment variables.

All settings are read via Pydantic Settings from the .env file.
No secrets are hard-coded or printed in logs.
"""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for Vizzy API."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    app_name: str = "vizzy-api"
    app_env: str = "development"
    debug: bool = False

    # ── CORS ─────────────────────────────────────────────────────────────────
    cors_origins: str = "http://localhost:3000"

    # ── Supabase ─────────────────────────────────────────────────────────────
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str

    # ── Storage buckets ───────────────────────────────────────────────────────
    input_image_bucket: str = "input-images"
    generated_image_bucket: str = "generated-images"

    # ── Upload limits ─────────────────────────────────────────────────────────
    max_upload_size_mb: int = 10
    max_input_images: int = 5

    # ── LLM (Phase 2+) ────────────────────────────────────────────────────────
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"

    # ── Image generation (Phase 2+) ───────────────────────────────────────────
    hf_token: str = ""
    image_provider: str = "huggingface"
    image_generation_model: str = "black-forest-labs/FLUX.1-schnell"
    # Phase 4 — declared but NOT used in Phase 2/3
    image_edit_model: str = "black-forest-labs/FLUX.1-Kontext-dev"

    # ── Conversation context ──────────────────────────────────────────────────
    max_context_messages: int = 20

    @field_validator("supabase_url", "supabase_anon_key", "supabase_service_role_key")
    @classmethod
    def must_not_be_empty(cls, value: str, info: object) -> str:
        if not value or not value.strip():
            raise ValueError(f"{info} must not be empty")
        return value

    @property
    def cors_origins_list(self) -> list[str]:
        """Return CORS origins as a list (supports comma-separated values)."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings instance."""
    return Settings()  # type: ignore[call-arg]
