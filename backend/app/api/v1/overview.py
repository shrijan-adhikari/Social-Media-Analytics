"""GET /api/v1/overview endpoint providing high-level dashboard metrics."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.interaction import Interaction
from app.models.network import NetworkAnalysisRun, NetworkNode
from app.models.sentiment_result import SentimentResult
from app.models.topic import Topic, TrendAnalysisRun, TrendWindow, TweetTopic
from app.models.tweet import Tweet
from app.models.user import User
from app.schemas.overview import (
    AnalysisCoverage,
    DatasetMetrics,
    NetworkOverview,
    OverviewResponse,
    SentimentOverview,
    TopEmergingTopic,
)

router = APIRouter(tags=["overview"])


@router.get(
    "/overview",
    response_model=OverviewResponse,
    summary="Get high-level dashboard analytical aggregates",
)
def get_overview(db: Session = Depends(get_db)) -> OverviewResponse:
    """Return consolidated, real-time aggregates from PostgreSQL across all completed analytics dimensions."""
    now_utc = datetime.now(timezone.utc)

    # 1. Dataset metrics
    total_tweets = db.scalar(select(func.count(Tweet.id))) or 0
    total_users = db.scalar(select(func.count(User.id))) or 0
    total_interactions = db.scalar(select(func.count(Interaction.id))) or 0

    dataset = DatasetMetrics(
        total_tweets=total_tweets,
        total_users=total_users,
        total_interactions=total_interactions,
    )

    # 2. Coverage
    sentiment_analyzed = db.scalar(select(func.count(SentimentResult.id))) or 0
    sarcasm_analyzed = db.scalar(
        select(func.count(SentimentResult.id)).where(SentimentResult.sarcasm_probability.isnot(None))
    ) or 0
    topic_assigned = db.scalar(
        select(func.count(TweetTopic.id)).where(TweetTopic.is_outlier == False)
    ) or 0

    coverage = AnalysisCoverage(
        sentiment_analyzed=sentiment_analyzed,
        sarcasm_analyzed=sarcasm_analyzed,
        topic_assigned=topic_assigned,
    )

    # 3. Sentiment breakdown
    sentiment_rows = db.execute(
        select(SentimentResult.final_sentiment, func.count(SentimentResult.id))
        .group_by(SentimentResult.final_sentiment)
    ).all()

    pos_count = 0
    neu_count = 0
    neg_count = 0
    for label, count in sentiment_rows:
        lbl = str(label).lower()
        if "pos" in lbl:
            pos_count += count
        elif "neg" in lbl:
            neg_count += count
        else:
            neu_count += count

    total_sent = pos_count + neu_count + neg_count
    pos_pct = round((pos_count / total_sent * 100), 1) if total_sent > 0 else 0.0
    neu_pct = round((neu_count / total_sent * 100), 1) if total_sent > 0 else 0.0
    neg_pct = round((neg_count / total_sent * 100), 1) if total_sent > 0 else 0.0

    sentiment = SentimentOverview(
        positive_percentage=pos_pct,
        neutral_percentage=neu_pct,
        negative_percentage=neg_pct,
        positive_count=pos_count,
        neutral_count=neu_count,
        negative_count=neg_count,
    )

    # 4. Top emerging topic (from latest completed trend analysis run)
    top_emerging: TopEmergingTopic | None = None
    latest_trend_run_id = db.scalar(select(func.max(TrendAnalysisRun.id)))
    if latest_trend_run_id is not None:
        top_window_stmt = (
            select(TrendWindow, Topic.label, Topic.topic_type)
            .join(Topic, TrendWindow.topic_id == Topic.id)
            .where(TrendWindow.run_id == latest_trend_run_id)
            .order_by(TrendWindow.velocity.desc(), TrendWindow.mention_count.desc())
            .limit(1)
        )
        row = db.execute(top_window_stmt).first()
        if row:
            tw, lbl, ttype = row
            top_emerging = TopEmergingTopic(
                topic_id=tw.topic_id,
                label=lbl,
                topic_type=ttype,
                velocity=round(float(tw.velocity), 2),
                acceleration=round(float(tw.acceleration), 2),
                mention_count=tw.mention_count,
            )

    # 5. Network metrics (latest global network run)
    latest_net_run = db.scalars(
        select(NetworkAnalysisRun)
        .where(NetworkAnalysisRun.scope_type == "global")
        .order_by(NetworkAnalysisRun.id.desc())
        .limit(1)
    ).first()

    if latest_net_run:
        community_count = db.scalar(
            select(func.count(func.distinct(NetworkNode.community_id)))
            .where(NetworkNode.run_id == latest_net_run.id)
        ) or 0
        network = NetworkOverview(
            latest_run_id=latest_net_run.id,
            connected_users=latest_net_run.node_count,
            edges=latest_net_run.edge_count,
            communities=community_count,
            density=round(float(latest_net_run.density), 6),
            weak_component_count=latest_net_run.weak_component_count,
            largest_weak_component_size=latest_net_run.largest_weak_component_size,
            is_sparse=latest_net_run.density < 0.05,
        )
    else:
        network = NetworkOverview(
            latest_run_id=None,
            connected_users=0,
            edges=0,
            communities=0,
            density=0.0,
            weak_component_count=0,
            largest_weak_component_size=0,
            is_sparse=True,
        )

    return OverviewResponse(
        generated_at=now_utc,
        pipeline_status="ready",
        dataset=dataset,
        analysis_coverage=coverage,
        sentiment=sentiment,
        top_emerging_topic=top_emerging,
        network=network,
    )
