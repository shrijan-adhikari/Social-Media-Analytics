"""Pydantic schemas for topics, trend windows, and topic-specific analytics."""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class TrendItem(BaseModel):
    """Real metric summary for a discovered topic from the latest trend analysis run."""

    topic_id: int
    topic_type: str = Field(..., description="'semantic' (MiniLM+HDBSCAN) or 'lexical' (hashtag)")
    label: str
    representative_terms: list[str] = Field(
        default_factory=list, description="Top c-TF-IDF keywords distinguishing this topic"
    )
    tweet_count: int = Field(..., description="Total tweets currently assigned to this topic")
    current_mentions: int = Field(..., description="Mentions in the latest 15-minute evaluation window")
    baseline_mentions: float = Field(..., description="Rolling average baseline mentions")
    velocity: float = Field(..., description="Current window velocity multiplier (current / baseline)")
    acceleration: float = Field(..., description="Change in velocity relative to preceding window")
    latest_window_start: datetime | None = None
    latest_window_end: datetime | None = None


class TrendListResponse(BaseModel):
    """List of all discovered topics and velocity metrics from the latest analysis run."""

    run_id: int
    pipeline_version: str
    clustering_algorithm: str
    topics: list[TrendItem]


class TrendDetailResponse(BaseModel):
    """Detailed topic intelligence with term importance and run provenance."""

    topic_id: int
    run_id: int
    label: str
    topic_type: str
    representative_terms: list[str]
    tweet_count: int
    current_mentions: int
    baseline_mentions: float
    velocity: float
    acceleration: float
    created_at: datetime


class TrendTimelinePoint(BaseModel):
    """Time-series entry from 15-minute windowed evaluations."""

    window_start: datetime
    window_end: datetime
    mention_count: int
    baseline_mentions: float
    velocity: float
    acceleration: float
    like_count: int = 0
    repost_count: int = 0
    reply_count: int = 0
    quote_count: int = 0


class TrendTimelineResponse(BaseModel):
    """Chronological windowed velocity progression for a topic."""

    topic_id: int
    label: str
    points: list[TrendTimelinePoint]


class TopicSentimentResponse(BaseModel):
    """Read-only join of topic tweets with sentiment and sarcasm fusion records."""

    topic_id: int
    label: str
    tweet_count: int
    positive: int = 0
    neutral: int = 0
    negative: int = 0
    high_sarcasm_evidence: int = 0
    fusion_statuses: dict[str, int] = Field(
        default_factory=dict,
        description="Distribution across NO_SARCASM, SARCASM_UNCERTAIN, SARCASM_CONSISTENT, SARCASM_AMBIGUOUS",
    )
