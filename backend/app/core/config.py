"""Application configuration via environment variables.

Required in non-development environments:
- DATABASE_URL

Optional (defaults supplied for development):
- APP_ENV  (default: "development")
"""

from __future__ import annotations

import os
from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application configuration.

    Values are read from environment variables / .env file.
    Fails clearly when required production configuration is absent.
    """

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_ENV: str = "development"

    # PostgreSQL connection URL.
    # Format: postgresql+psycopg://USER:PASSWORD@HOST:PORT/DBNAME
    DATABASE_URL: str = ""
    
    # Twitter Credentials for twscrape
    TWITTER_USERNAME: str = ""
    TWITTER_EMAIL: str = ""
    TWITTER_PASSWORD: str = ""
    TWITTER_COOKIES: str = ""

    # CORS origins for frontend integration
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    @model_validator(mode="after")
    def require_database_url_in_production(self) -> "Settings":
        """Raise an explicit error when DATABASE_URL is missing in production."""
        if self.APP_ENV != "development" and not self.DATABASE_URL:
            raise ValueError(
                "DATABASE_URL must be set in non-development environments. "
                "Set APP_ENV=development to suppress this check locally."
            )
        return self

    @field_validator("APP_ENV")
    @classmethod
    def validate_app_env(cls, v: str) -> str:
        allowed = {"development", "staging", "production", "test"}
        if v not in allowed:
            raise ValueError(f"APP_ENV must be one of {allowed}, got '{v}'")
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings singleton."""
    return Settings()
