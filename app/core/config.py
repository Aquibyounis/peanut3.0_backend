"""
Peanut 3.0 - Application Configuration
Centralized settings via pydantic-settings with .env support.
"""

try:
    from pydantic_settings import BaseSettings
except ImportError:  # fallback for environments without pydantic-settings
    from pydantic import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    # ── Database (Neon PostgreSQL) ──
    database_url: str = Field(
        default="",
        alias="DATABASE_URL",
    )
    database_url_sync: str = Field(
        default="",
        alias="DATABASE_URL_SYNC",
    )

    # ── Redis (Upstash) ──
    redis_url: str = Field(default="", alias="REDIS_URL")

    # ── Qdrant (Qdrant Cloud) ──
    qdrant_url: str = Field(default="", alias="QDRANT_URL")
    qdrant_api_key: str = Field(default="", alias="QDRANT_API_KEY")

    # ── Groq / LLM ──
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_model: str = Field(default="llama-3.3-70b-versatile", alias="GROQ_MODEL")
    embed_model: str = Field(default="nomic-ai/nomic-embed-text-v1.5", alias="EMBED_MODEL")

    # ── Remote Embedding Switch ──
    use_remote_embed: bool = Field(default=False, alias="USE_REMOTE_EMBED")
    remote_embed_provider: str = Field(default="hf", alias="REMOTE_EMBED_PROVIDER")  # "hf" or "openai"
    hf_token: str = Field(default="", alias="HF_TOKEN")
    hf_embed_endpoint: str = Field(default="", alias="HF_EMBED_ENDPOINT")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    remote_embed_model: str = Field(default="", alias="REMOTE_EMBED_MODEL")
    groq_embed_model: str = Field(default="embed-3.5", alias="GROQ_EMBED_MODEL")

    # ── JWT / Auth ──
    jwt_secret_key: str = Field(
        default="peanut-super-secret-key-change-in-production",
        alias="JWT_SECRET_KEY",
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(
        default=30, alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    jwt_refresh_token_expire_days: int = Field(
        default=7, alias="JWT_REFRESH_TOKEN_EXPIRE_DAYS"
    )

    # ── QStash (Upstash) ──
    qstash_token: str = Field(default="", alias="QSTASH_TOKEN")
    qstash_current_signing_key: str = Field(
        default="", alias="QSTASH_CURRENT_SIGNING_KEY"
    )
    qstash_next_signing_key: str = Field(
        default="", alias="QSTASH_NEXT_SIGNING_KEY"
    )

    # ── Resend / Email ──
    resend_api_key: str = Field(default="", alias="RESEND_API_KEY")
    resend_from_email: str = Field(default="onboarding@resend.dev", alias="RESEND_FROM_EMAIL")
    contact_recipient_email: str = Field(
        default="aquibyounis2@gmail.com", alias="CONTACT_RECIPIENT_EMAIL"
    )

    # ── Application ──
    app_name: str = Field(default="Peanut 3.0", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    cors_origins: str = Field(
        default="",
        alias="CORS_ORIGINS",
    )
    # Render provides the public URL via RENDER_EXTERNAL_URL
    render_public_url: str = Field(
        default="http://localhost:8000", alias="RENDER_EXTERNAL_URL"
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "populate_by_name": True,
        "extra": "ignore",
    }

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


settings = Settings()

# ── Backward-compatible module-level aliases ──
DATABASE_URL = settings.database_url
REDIS_URL = settings.redis_url
QDRANT_URL = settings.qdrant_url
QDRANT_API_KEY = settings.qdrant_api_key
GROQ_API_KEY = settings.groq_api_key
GROQ_MODEL = settings.groq_model
EMBED_MODEL = settings.embed_model
QSTASH_TOKEN = settings.qstash_token