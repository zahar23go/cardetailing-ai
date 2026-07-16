"""
Application Configuration.

Loads environment variables from .env file using Pydantic Settings.
"""

import os
from functools import lru_cache
from typing import List, Optional

import chardet
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def detect_env_encoding(env_path: str = ".env") -> str:
    """Detect encoding of .env file, falling back to utf-8.

    Handles UTF-8 with BOM, UTF-16, and other common encodings
    that may be produced by PowerShell or Windows tools.
    """
    if not os.path.exists(env_path):
        return "utf-8"

    with open(env_path, "rb") as f:
        raw_data = f.read()

    if not raw_data:
        return "utf-8"

    result = chardet.detect(raw_data)
    encoding = result.get("encoding")

    if encoding is None:
        return "utf-8"

    encoding = encoding.lower()

    # Normalise common aliases to plain utf-8
    encoding_map = {
        "utf-8-sig": "utf-8",
        "utf-16": "utf-8",
        "utf-16le": "utf-8",
        "utf-16-le": "utf-8",
        "utf-16be": "utf-8",
        "utf-16-be": "utf-8",
        "ascii": "utf-8",
    }
    return encoding_map.get(encoding, encoding)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding=detect_env_encoding(),
        case_sensitive=False,
        extra="ignore",
    )

    # Project
    PROJECT_NAME: str = "CarDetailing Backend"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database — individual parts (used when no explicit DATABASE_URL)
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "cardetailing"

    # Explicit full URL override — takes priority over individual fields
    # Set via env var DATABASE_URL (e.g. in Docker / docker-compose)
    database_url_override: Optional[str] = Field(None, alias="DATABASE_URL")

    @property
    def DATABASE_URL(self) -> str:
        """Construct PostgreSQL database URL.

        Returns explicit DATABASE_URL if set (via env var or .env),
        otherwise constructs from individual POSTGRES_* fields.
        """
        if self.database_url_override:
            return self.database_url_override
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Redis
    REDIS_URL: str = "redis://redis:6379"

    # JWT
    JWT_SECRET: str = "v0JyqT6MUks2G-GM4UB-BKJva1iyZssWxOhNqSzgMko"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 30

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # File storage
    STORAGE_TYPE: str = "local"
    STORAGE_PATH: str = "./uploads"

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_WEBHOOK_URL: str = ""

    # SMS
    SMS_PROVIDER: str = "smsru"
    SMS_API_KEY: str = ""
    SMS_SENDER: str = "CarDetailing"

    # DeepSeek API
    DEEPSEEK_API_KEY: str = ""  # ← ДОБАВЛЕНО!


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()