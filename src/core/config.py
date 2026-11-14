"""Application settings loaded from environment variables / ``.env``.

Usage::

    from src.core.config import settings

    settings.DATABASE_URL

Add new settings here (with a safe default for local dev) and to ``.env.example``.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_BASE_URL: str = "http://localhost:8000"

    SECRET_KEY: str = "dev-secret-key"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/cinema"
    REDIS_URL: str = "redis://localhost:6379/0"

    ACCESS_TOKEN_TTL_MINUTES: int = 15
    REFRESH_TOKEN_TTL_DAYS: int = 7
    ACTIVATION_TOKEN_TTL_HOURS: int = 24

    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    EMAIL_FROM: str = "noreply@cinema.local"

    MINIO_ENDPOINT: str = "http://localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "avatars"

    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""


settings = Settings()
