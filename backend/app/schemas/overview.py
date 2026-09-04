"""Pydantic schemas for the GET /api/v1/overview dashboard summary."""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class DatasetMetrics(BaseModel):
    """Raw ingestion volume metrics."""

    total_tweets: int = Field(..., description="Total tweets persisted in database")
    total_users: int = Field(..., description="Total unique user accounts stored")
    total_interactions: int = Field(..., description="Total directed interaction edges recorded")


class AnalysisCoverage(BaseModel):
    """Analytics completion status across pipeline dimensions."""

    sentiment_analyzed: int = Field(..., description="Number of tweets with XLM-RoBERTa sentiment records")
    sarcasm_analyzed: int = Field(..., description="Number of tweets with T5 sarcasm proxy scores")
    topic_assigned: int = Field(..., description="Number of tweets assigned to non-outlier topics")


class SentimentOverview(BaseModel):
    """High-level sentiment distribution."""

    positive_percentage: float = Field(..., description="Percentage of analyzed posts that are positive")
    neutral_percentage: float = Field(..., description="Percentage of analyzed posts that are neutral")
    negative_percentage: float = Field(..., description="Percentage of analyzed posts that are negative")
    positive_count: int
    neutral_count: int
    negative_count: int


class TopEmergingTopic(BaseModel):
    """Fastest accelerating narrative signal from latest trend run."""

    topic_id: int
    label: str
    topic_type: str = "semantic"
    velocity: float = Field(..., description="Current window velocity multiplier over baseline")
    acceleration: float = Field(..., description="First difference in velocity compared to prior window")
    mention_count: int = Field(..., description="Total mentions in latest evaluation window")


class NetworkOverview(BaseModel):
    """High-level interaction network topology metrics from latest global network run."""

    latest_run_id: int | None = None
    connected_users: int = Field(..., description="Users participating in at least one interaction")
    edges: int = Field(..., description="Pairwise aggregated directed interaction edges")
    communities: int = Field(..., description="Louvain communities detected")
    density: float = Field(..., description="Graph density of interaction network")
    weak_component_count: int = Field(..., description="Weakly connected components")
    largest_weak_component_size: int = Field(..., description="User count in largest connected sub-network")
    is_sparse: bool = Field(True, description="True if graph density is below 0.05")


class OverviewResponse(BaseModel):
    """Complete frontend-ready analytical summary for the dashboard overview."""

    generated_at: datetime = Field(..., description="UTC timestamp of response generation")
    pipeline_status: str = Field("ready", description="Backend analytics health status")
    dataset: DatasetMetrics
    analysis_coverage: AnalysisCoverage
    sentiment: SentimentOverview
    top_emerging_topic: TopEmergingTopic | None = None
    network: NetworkOverview
