"""SQLAlchemy ORM models for trend and topic analysis.

Implements Phase 3A Trend & Topic Detection persistence:
- TrendAnalysisRun: Versioned execution run metadata
- Topic: Lexical or semantic detected topics with representative terms
- TweetTopic: Tweet-to-topic memberships and HDBSCAN outlier/cluster tracking
- TrendWindow: Temporal windowed mention velocity, acceleration, and engagement aggregates
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    JSON,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.tweet import Base


class TrendAnalysisRun(Base):
    """Execution run tracking for trend and topic detection.

    Ensures HDBSCAN cluster fitting and windowed trend computation are
    explicitly scoped to a reproducible analysis run, preventing stale
    or orphaned topic identities.
    """

    __tablename__ = "trend_analysis_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pipeline_version: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    dataset_tweet_count: Mapped[int] = mapped_column(Integer, nullable=False)
    earliest_tweet_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    latest_tweet_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    window_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    embedding_model_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    embedding_model_revision: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    clustering_params: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    topics: Mapped[List["Topic"]] = relationship("Topic", back_populates="run", cascade="all, delete-orphan")
    tweet_topics: Mapped[List["TweetTopic"]] = relationship("TweetTopic", back_populates="run", cascade="all, delete-orphan")
    trend_windows: Mapped[List["TrendWindow"]] = relationship("TrendWindow", back_populates="run", cascade="all, delete-orphan")


class Topic(Base):
    """Semantic cluster or lexical keyword/hashtag topic."""

    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("trend_analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    representative_terms: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    # Explicit separation: 'semantic' vs 'lexical'
    topic_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    run: Mapped["TrendAnalysisRun"] = relationship("TrendAnalysisRun", back_populates="topics")
    tweet_assignments: Mapped[List["TweetTopic"]] = relationship("TweetTopic", back_populates="topic", cascade="all, delete-orphan")
    windows: Mapped[List["TrendWindow"]] = relationship("TrendWindow", back_populates="topic", cascade="all, delete-orphan")


class TweetTopic(Base):
    """Maps a tweet to a topic within a specific analysis run.

    Explicitly preserves HDBSCAN cluster ID, membership probability,
    and outlier status (cluster_id = -1).
    """

    __tablename__ = "tweet_topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("trend_analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tweet_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tweets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("topics.id", ondelete="CASCADE"), nullable=True, index=True
    )
    cluster_id: Mapped[int] = mapped_column(Integer, nullable=False)  # -1 for noise
    is_outlier: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    membership_probability: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    run: Mapped["TrendAnalysisRun"] = relationship("TrendAnalysisRun", back_populates="tweet_topics")
    topic: Mapped[Optional["Topic"]] = relationship("Topic", back_populates="tweet_assignments")

    __table_args__ = (
        UniqueConstraint("run_id", "tweet_id", "topic_id", name="uq_tweet_topics_run_tweet_topic"),
    )


class TrendWindow(Base):
    """Chronological window metrics for a topic.

    Stores mention frequency, velocity, acceleration, and aggregated engagement.
    """

    __tablename__ = "trend_windows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("trend_analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    mention_count: Mapped[int] = mapped_column(Integer, nullable=False)
    baseline_mentions: Mapped[float] = mapped_column(Float, nullable=False)
    velocity: Mapped[float] = mapped_column(Float, nullable=False)
    acceleration: Mapped[float] = mapped_column(Float, nullable=False)

    # Standardized engagement metrics (repost_count instead of retweet_count)
    like_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    repost_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reply_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quote_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    run: Mapped["TrendAnalysisRun"] = relationship("TrendAnalysisRun", back_populates="trend_windows")
    topic: Mapped["Topic"] = relationship("Topic", back_populates="windows")

    __table_args__ = (
        UniqueConstraint("run_id", "topic_id", "window_start", "window_end", name="uq_trend_windows_run_topic_window"),
    )
