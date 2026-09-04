"""Tests for application configuration (app.core.config).

These tests are pure unit tests — no DB or network required.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError


def test_settings_default_app_env() -> None:
    """Settings should default APP_ENV to 'development'."""
    from app.core.config import Settings

    s = Settings(DATABASE_URL="postgresql+psycopg://u:p@localhost/db")
    assert s.APP_ENV == "development"


def test_settings_accepts_valid_app_env_values() -> None:
    """Settings should accept all valid APP_ENV values."""
    from app.core.config import Settings

    for env in ("development", "staging", "production", "test"):
        s = Settings(
            APP_ENV=env,
            DATABASE_URL="postgresql+psycopg://u:p@localhost/db",
        )
        assert s.APP_ENV == env


def test_settings_rejects_invalid_app_env() -> None:
    """Settings should raise ValidationError for unknown APP_ENV values."""
    from app.core.config import Settings

    with pytest.raises(ValidationError):
        Settings(APP_ENV="unknown", DATABASE_URL="postgresql+psycopg://u:p@localhost/db")


def test_settings_requires_database_url_in_production() -> None:
    """Settings should raise ValidationError when DATABASE_URL is missing in production."""
    from app.core.config import Settings

    with pytest.raises(ValidationError, match="DATABASE_URL"):
        Settings(APP_ENV="production", DATABASE_URL="")


def test_settings_allows_empty_database_url_in_development() -> None:
    """Settings should NOT raise when DATABASE_URL is empty in development mode."""
    from app.core.config import Settings

    # Should not raise
    s = Settings(APP_ENV="development", DATABASE_URL="")
    assert s.APP_ENV == "development"
    assert s.DATABASE_URL == ""


def test_settings_database_url_preserved() -> None:
    """Settings should preserve the DATABASE_URL as provided."""
    from app.core.config import Settings

    url = "postgresql+psycopg://user:pass@host:5432/mydb"
    s = Settings(DATABASE_URL=url)
    assert s.DATABASE_URL == url
