"""SQLAlchemy models for Twitter collection queries and data provenance.

Maintains complete provenance of which search query and run retrieved each tweet,
while strictly separating collection query metadata from discovered semantic topics.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.tweet import Base


class CollectionQuery(Base):
    """Configured search query definition for Twitter collection."""

    __tablename__ = "collection_queries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    query_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    query_text: Mapped[str] = mapped_column(String(500), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    default_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    runs: Mapped[List["CollectionRun"]] = relationship(
        "CollectionRun", back_populates="query", cascade="all, delete-orphan"
    )


class CollectionRun(Base):
    """Specific execution instance of a collection query.

    Preserves snapshot of effective query text and config version for reproducibility.
    """

    __tablename__ = "collection_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    query_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("collection_queries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    config_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    effective_query_text: Mapped[str] = mapped_column(String(500), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    requested_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    retrieved_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    inserted_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running")
    error_category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Relationships
    query: Mapped["CollectionQuery"] = relationship("CollectionQuery", back_populates="runs")
    tweet_sources: Mapped[List["TweetCollectionSource"]] = relationship(
        "TweetCollectionSource", back_populates="run", cascade="all, delete-orphan"
    )


class TweetCollectionSource(Base):
    """Associates a tweet with the collection run that retrieved it.

    Enables many-to-many relationship: a single tweet can be retrieved by multiple
    different queries/runs over time without duplicating the tweet record.
    """

    __tablename__ = "tweet_collection_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tweet_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tweets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    collection_run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("collection_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    run: Mapped["CollectionRun"] = relationship("CollectionRun", back_populates="tweet_sources")

    __table_args__ = (
        UniqueConstraint("tweet_id", "collection_run_id", name="uq_tweet_collection_sources_tweet_run"),
    )
