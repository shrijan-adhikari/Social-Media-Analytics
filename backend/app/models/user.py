"""User ORM model — Twitter identity and profile information.

Twitter user IDs are stored as TEXT to preserve full 64-bit integer precision.
JavaScript's JSON parser silently loses precision on integers >2^53, so keeping
IDs as strings throughout the stack is safer than casting back and forth.

All timestamps are TIMESTAMPTZ (UTC) per DATABASE.md requirements.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class User(Base):
    """Represents a Twitter/X user profile.

    `twitter_user_id` is the canonical Twitter snowflake ID stored as TEXT.
    `created_at` is the Twitter account creation date (from the API).
    `last_seen_at` is the timestamp of the most recent observation in our dataset.
    `ingested_at` is the row-insertion time (our system clock, UTC).

    Demographic predictions are kept in a separate `demographic_estimates` table
    (Phase 2) so this table does not need to be updated when models are re-run.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Twitter's snowflake ID — stored as TEXT to preserve 64-bit precision.
    twitter_user_id: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False, index=True
    )

    username: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    profile_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    declared_location: Mapped[str | None] = mapped_column(String(255), nullable=True)

    followers_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    following_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Twitter account creation date as reported by the API.
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Most recent time we observed this user in collected data.
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Row insertion time (our ingestion system clock, always UTC).
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
    )

    # Relationships (back-populated from Tweet and Interaction)
    tweets: Mapped[list["Tweet"]] = relationship(  # noqa: F821
        "Tweet", back_populates="author", foreign_keys="Tweet.author_id"
    )
    outgoing_interactions: Mapped[list["Interaction"]] = relationship(  # noqa: F821
        "Interaction",
        back_populates="source_user",
        foreign_keys="Interaction.source_user_id",
    )
    incoming_interactions: Mapped[list["Interaction"]] = relationship(  # noqa: F821
        "Interaction",
        back_populates="target_user",
        foreign_keys="Interaction.target_user_id",
    )

    __table_args__ = (
        Index("ix_users_username", "username"),
        Index("ix_users_last_seen_at", "last_seen_at"),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} twitter_user_id={self.twitter_user_id!r} username={self.username!r}>"
