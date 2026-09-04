"""Pydantic schemas for sentiment and sarcasm fusion analytics endpoints."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class SentimentCount(BaseModel):
    """Count and percentage for a specific sentiment label."""

    count: int
    percentage: float


class SarcasmBreakdown(BaseModel):
    """Breakdown of sarcasm evidence and deterministic fusion outcomes.

    Note: sarcasm_score is an uncalibrated model-derived proxy score from T5,
    NOT an empirical statistical probability.
    """

    analyzed: int = Field(..., description="Tweets evaluated through sarcasm detection")
    high_evidence_count: int = Field(
        ..., description="Tweets with sarcasm_score >= 0.85 threshold"
    )
    # Stored fusion statuses (Correction 4)
    no_sarcasm_count: int = Field(..., description="Status NO_SARCASM")
    sarcasm_uncertain_count: int = Field(..., description="Status SARCASM_UNCERTAIN")
    sarcasm_consistent_count: int = Field(..., description="Status SARCASM_CONSISTENT")
    sarcasm_ambiguous_count: int = Field(..., description="Status SARCASM_AMBIGUOUS")
    average_sarcasm_score: float | None = Field(
        None, description="Average uncalibrated proxy score across evaluated tweets"
    )


class SentimentSummaryResponse(BaseModel):
    """Aggregate sentiment and sarcasm fusion intelligence."""

    total_analyzed: int
    positive: SentimentCount
    neutral: SentimentCount
    negative: SentimentCount
    sarcasm: SarcasmBreakdown
    pipeline_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Provenance of models, checkpoints, and thresholds used",
    )


class SentimentTimelinePoint(BaseModel):
    """Chronological sentiment breakdown point for trajectory charts."""

    timestamp: str = Field(..., description="ISO-8601 or formatted bucket label")
    positive: int = 0
    neutral: int = 0
    negative: int = 0
    total: int = 0
    positive_pct: float = 0.0
    neutral_pct: float = 0.0
    negative_pct: float = 0.0


class SentimentTimelineResponse(BaseModel):
    """Ordered chronological trajectory of sentiment shifts."""

    points: list[SentimentTimelinePoint]
    interval: str = Field("4h", description="Aggregation bucket window interval")
    topic_id: int | None = None
