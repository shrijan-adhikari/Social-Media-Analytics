"""GET /api/v1/analysis/status reporting actual backend pipeline readiness (Correction 10)."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.network import NetworkAnalysisRun
from app.models.sentiment_result import SentimentResult
from app.models.topic import TrendAnalysisRun
from app.models.tweet import Tweet
from app.schemas.status import (
    PipelineDimensionStatus,
    SystemAnalysisStatusResponse,
)

router = APIRouter(prefix="/analysis", tags=["status"])


@router.get(
    "/status",
    response_model=SystemAnalysisStatusResponse,
    summary="Get readiness and execution status across all roadmap capabilities",
)
def get_analysis_status(db: Session = Depends(get_db)) -> SystemAnalysisStatusResponse:
    """Report real pipeline state directly from PostgreSQL, with zero fabricated completion claims."""
    now_utc = datetime.now(timezone.utc)

    # 1. Collection
    tweet_count = db.scalar(select(func.count(Tweet.id))) or 0
    latest_ingested = db.scalar(select(func.max(Tweet.ingested_at)))
    collection_status = PipelineDimensionStatus(
        status="ready" if tweet_count > 0 else "none",
        is_available=tweet_count > 0,
        records_count=tweet_count,
        latest_run_at=latest_ingested,
        pipeline_version="1.0.0",
        notes="Twscrape ingestion with multi-query provenance active.",
    )

    # 2. Sentiment
    sentiment_count = db.scalar(select(func.count(SentimentResult.id))) or 0
    latest_sentiment = db.scalar(select(func.max(SentimentResult.analyzed_at)))
    sentiment_status = PipelineDimensionStatus(
        status="ready" if sentiment_count > 0 else "none",
        is_available=sentiment_count > 0,
        records_count=sentiment_count,
        latest_run_at=latest_sentiment,
        pipeline_version="1.0.0",
        notes="CardiffNLP Twitter XLM-RoBERTa sentiment analysis active.",
    )

    # 3. Sarcasm
    sarcasm_count = db.scalar(
        select(func.count(SentimentResult.id)).where(SentimentResult.sarcasm_probability.isnot(None))
    ) or 0
    sarcasm_status = PipelineDimensionStatus(
        status="ready" if sarcasm_count > 0 else "none",
        is_available=sarcasm_count > 0,
        records_count=sarcasm_count,
        latest_run_at=latest_sentiment,
        pipeline_version="1.0.0",
        notes="T5 Twitter sarcasm model with confidence-aware fusion active.",
    )

    # 4. Trends
    latest_trend_run = db.scalars(
        select(TrendAnalysisRun)
        .order_by(TrendAnalysisRun.id.desc())
        .limit(1)
    ).first()
    trends_status = PipelineDimensionStatus(
        status="ready" if latest_trend_run else "none",
        is_available=latest_trend_run is not None,
        records_count=latest_trend_run.dataset_tweet_count if latest_trend_run else 0,
        latest_run_at=latest_trend_run.created_at if latest_trend_run else None,
        pipeline_version=latest_trend_run.pipeline_version if latest_trend_run else None,
        notes="all-MiniLM-L6-v2 + HDBSCAN + 15m windowed velocity active.",
    )

    # 5. Network
    latest_net_run = db.scalars(
        select(NetworkAnalysisRun)
        .where(NetworkAnalysisRun.scope_type == "global")
        .order_by(NetworkAnalysisRun.id.desc())
        .limit(1)
    ).first()
    network_status = PipelineDimensionStatus(
        status="ready" if latest_net_run else "none",
        is_available=latest_net_run is not None,
        records_count=latest_net_run.node_count if latest_net_run else 0,
        latest_run_at=latest_net_run.created_at if latest_net_run else None,
        pipeline_version=latest_net_run.pipeline_version if latest_net_run else None,
        notes="NetworkX directed PageRank, Louvain communities, and betweenness active.",
    )

    # 6. Demographics (Scheduled for Phase 5)
    demographics_status = PipelineDimensionStatus(
        status="not_implemented",
        is_available=False,
        records_count=0,
        latest_run_at=None,
        pipeline_version=None,
        notes="M3-Inference aggregate demographic profiling scheduled for Phase 5.",
    )

    # 7. Emotion (Not yet selected)
    emotion_status = PipelineDimensionStatus(
        status="not_implemented",
        is_available=False,
        records_count=0,
        latest_run_at=None,
        pipeline_version=None,
        notes="Emotion classification model not yet selected per PROJECT_CONTEXT.md §24.4b.",
    )

    # 8. Stance (Not yet selected)
    stance_status = PipelineDimensionStatus(
        status="not_implemented",
        is_available=False,
        records_count=0,
        latest_run_at=None,
        pipeline_version=None,
        notes="Target-specific stance model not yet selected per PROJECT_CONTEXT.md §24.4c.",
    )

    return SystemAnalysisStatusResponse(
        generated_at=now_utc,
        collection=collection_status,
        sentiment=sentiment_status,
        sarcasm=sarcasm_status,
        trends=trends_status,
        network=network_status,
        demographics=demographics_status,
        emotion=emotion_status,
        stance=stance_status,
    )
