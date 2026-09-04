"""Pydantic v2 schemas for Tweet entities.

`TweetCreate` is used by the ingestion pipeline.
`TweetRead` is the API response shape.

All Twitter ID fields are strings to preserve 64-bit snowflake precision.
Sentiment data is deliberately excluded — it belongs in `sentiment_results`.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TweetCreate(BaseModel):
    """Data required to create a tweet record."""

    twitter_tweet_id: str = Field(..., description="Twitter snowflake tweet ID (as string)")
    author_id: int = Field(..., description="Internal users.id (not twitter_user_id)")
    text: str = Field(..., min_length=1)
    created_at_utc: datetime = Field(..., description="Tweet publication time (UTC)")
    conversation_id: str | None = None
    reply_to_tweet_id: str | None = None
    reply_to_user_id: str | None = None
    repost_of_tweet_id: str | None = None
    quoted_tweet_id: str | None = None
    like_count: int | None = None
    retweet_count: int | None = None
    reply_count: int | None = None
    quote_count: int | None = None
    bookmark_count: int | None = None
    raw_payload: dict | None = Field(
        None, description="Original twscrape response payload"
    )


class TweetRead(BaseModel):
    """API response schema for a tweet."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    twitter_tweet_id: str
    author_id: int | None = None
    text: str
    created_at_utc: datetime
    conversation_id: str | None = None
    reply_to_tweet_id: str | None = None
    reply_to_user_id: str | None = None
    repost_of_tweet_id: str | None = None
    quoted_tweet_id: str | None = None
    like_count: int | None = None
    retweet_count: int | None = None
    reply_count: int | None = None
    quote_count: int | None = None
    bookmark_count: int | None = None
    ingested_at: datetime
    # raw_payload intentionally omitted from read schema (internal provenance only)


class TweetSentimentInfo(BaseModel):
    """Enriched sentiment and sarcasm summary for a tweet."""

    final_sentiment: str = Field(..., description="Final sentiment label (positive, neutral, negative)")
    final_confidence: float = Field(..., description="Confidence of final sentiment decision [0.0 - 1.0]")
    sarcasm_score: float | None = Field(
        None, description="Uncalibrated model-derived proxy score from T5 generation log-likelihood"
    )
    high_sarcasm_evidence: bool = Field(
        False, description="True if sarcasm_score meets or exceeds the Phase 2 threshold (0.85)"
    )
    fusion_status: str | None = Field(
        None, description="Fusion status: NO_SARCASM, SARCASM_UNCERTAIN, SARCASM_CONSISTENT, SARCASM_AMBIGUOUS"
    )


class TweetTopicInfo(BaseModel):
    """Topic assignment metadata for a tweet."""

    topic_id: int
    label: str
    topic_type: str = Field(..., description="'semantic' or 'lexical'")


class TweetItem(BaseModel):
    """Frontend-ready tweet representation with author username, engagement, and analytics."""

    id: int
    tweet_id: str = Field(..., description="Twitter snowflake ID (string)")
    username: str
    text: str
    created_at_utc: datetime
    ingested_at: datetime
    like_count: int = 0
    retweet_count: int = 0
    reply_count: int = 0
    quote_count: int = 0
    sentiment: TweetSentimentInfo | None = None
    topic: TweetTopicInfo | None = None


class TweetListResponse(BaseModel):
    """Paginated list of tweets with analytical metadata."""

    items: list[TweetItem]
    total: int
    page: int
    page_size: int
    total_pages: int
