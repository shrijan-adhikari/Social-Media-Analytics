"""Pydantic v2 schemas for User entities.

`UserCreate` is used for write operations (ingestion pipeline).
`UserRead` is the API response shape — does not expose internal database details.

Twitter IDs are kept as strings in the API to prevent JSON integer precision loss.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    """Data required to create or upsert a user record."""

    twitter_user_id: str = Field(..., description="Twitter snowflake user ID (as string)")
    username: str = Field(..., min_length=1, max_length=255)
    display_name: str | None = None
    bio: str | None = None
    profile_image_url: str | None = None
    declared_location: str | None = None
    followers_count: int | None = None
    following_count: int | None = None
    created_at: datetime | None = Field(
        None, description="Twitter account creation timestamp (UTC)"
    )
    last_seen_at: datetime | None = None


class UserRead(BaseModel):
    """API response schema for a user."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    twitter_user_id: str
    username: str
    display_name: str | None = None
    bio: str | None = None
    profile_image_url: str | None = None
    declared_location: str | None = None
    followers_count: int | None = None
    following_count: int | None = None
    created_at: datetime | None = None
    last_seen_at: datetime | None = None
    ingested_at: datetime
