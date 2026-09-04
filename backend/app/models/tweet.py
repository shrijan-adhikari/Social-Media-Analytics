"""Tweet ORM model — normalized tweet content, relationships, and metadata.

Design decisions:
- `twitter_tweet_id` stored as TEXT (see user.py comment on ID precision).
- `conversation_id`, `reply_to_tweet_id`, etc. are also TEXT — they are Twitter
  IDs and must not lose precision through integer casting.
- `created_at_utc` is when Twitter says the tweet was published (UTC).
- `ingested_at` is when we inserted this row — distinct from tweet creation time.
- `raw_payload` (JSONB) stores the original twscrape response for replay/debugging.
- Sentiment results will live in a separate `sentiment_results` table (Phase 2).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Tweet(Base):
    """Represents a normalized Twitter/X tweet."""

    __tablename__ = "tweets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Twitter snowflake ID stored as TEXT to preserve 64-bit precision.
    twitter_tweet_id: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False, index=True
    )

    # FK to our internal users.id (not to twitter_user_id).
    author_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    text: Mapped[str] = mapped_column(Text, nullable=False)

    # UTC timestamp from Twitter — distinct from our ingestion time.
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    # Twitter conversation thread root ID (TEXT to preserve precision).
    conversation_id: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Tweet relationship IDs — all TEXT snowflakes.
    reply_to_tweet_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reply_to_user_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    repost_of_tweet_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    quoted_tweet_id: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Engagement counters — nullable because not always available from the API.
    like_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retweet_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reply_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quote_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bookmark_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Raw payload from twscrape for replay and provenance.
    # JSON type used here for SQLite/test compatibility; the migration uses JSONB
    # on PostgreSQL for efficient operator support in production.
    raw_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Row insertion timestamp — always set by our system, not Twitter.
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
    )

    # Relationships
    author: Mapped["User"] = relationship(  # noqa: F821
        "User", back_populates="tweets", foreign_keys=[author_id]
    )
    interactions: Mapped[list["Interaction"]] = relationship(  # noqa: F821
        "Interaction", back_populates="tweet"
    )

    __table_args__ = (
        Index("ix_tweets_author_created", "author_id", "created_at_utc"),
        Index("ix_tweets_conversation_id", "conversation_id"),
        Index("ix_tweets_ingested_at", "ingested_at"),
    )

    def __repr__(self) -> str:
        return f"<Tweet id={self.id} twitter_tweet_id={self.twitter_tweet_id!r}>"
