"""GET /api/v1/sentiment/summary and /timeline endpoints."""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.sentiment_result import SentimentResult
from app.models.topic import TweetTopic
from app.models.tweet import Tweet
from app.schemas.sentiment import (
    SarcasmBreakdown,
    SentimentCount,
    SentimentSummaryResponse,
    SentimentTimelinePoint,
    SentimentTimelineResponse,
)

router = APIRouter(prefix="/sentiment", tags=["sentiment"])


@router.get(
    "/summary",
    response_model=SentimentSummaryResponse,
    summary="Get overall or topic-filtered sentiment & sarcasm breakdown",
)
def get_sentiment_summary(
    topic_id: Optional[int] = Query(None, description="Optional topic ID filter"),
    start_at: Optional[datetime] = Query(None, description="Optional start timestamp filter"),
    end_at: Optional[datetime] = Query(None, description="Optional end timestamp filter"),
    db: Session = Depends(get_db),
) -> SentimentSummaryResponse:
    """Return aggregate sentiment proportions and sarcasm fusion status counts.

    Does NOT run ML inference; reads directly from persisted sentiment_results.
    """
    stmt = select(SentimentResult).join(Tweet, SentimentResult.tweet_id == Tweet.id)

    if topic_id is not None:
        stmt = stmt.join(TweetTopic, Tweet.id == TweetTopic.tweet_id).where(
            TweetTopic.topic_id == topic_id,
            TweetTopic.is_outlier == False,
        )

    if start_at is not None:
        stmt = stmt.where(Tweet.created_at_utc >= start_at)

    if end_at is not None:
        stmt = stmt.where(Tweet.created_at_utc <= end_at)

    results = list(db.scalars(stmt).all())
    total_analyzed = len(results)

    pos_count = 0
    neu_count = 0
    neg_count = 0

    sarcasm_evaluated = 0
    high_evidence_count = 0
    no_sarcasm_count = 0
    uncertain_count = 0
    consistent_count = 0
    ambiguous_count = 0
    total_sarcasm_score = 0.0

    model_name = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
    sarcasm_model = "mrm8488/t5-base-finetuned-sarcasm-twitter"

    for r in results:
        sentiment_label = str(r.final_sentiment).lower()
        if "pos" in sentiment_label:
            pos_count += 1
        elif "neg" in sentiment_label:
            neg_count += 1
        else:
            neu_count += 1

        if r.model_id:
            model_name = r.model_id

        if r.sarcasm_probability is not None:
            sarcasm_evaluated += 1
            total_sarcasm_score += float(r.sarcasm_probability)
            if float(r.sarcasm_probability) >= 0.85:
                high_evidence_count += 1

        status = str(r.fusion_status or "NO_SARCASM").upper()
        if "UNCERTAIN" in status:
            uncertain_count += 1
        elif "CONSISTENT" in status:
            consistent_count += 1
        elif "AMBIGUOUS" in status:
            ambiguous_count += 1
        else:
            no_sarcasm_count += 1

    pos_pct = round(pos_count / total_analyzed * 100, 1) if total_analyzed > 0 else 0.0
    neu_pct = round(neu_count / total_analyzed * 100, 1) if total_analyzed > 0 else 0.0
    neg_pct = round(neg_count / total_analyzed * 100, 1) if total_analyzed > 0 else 0.0

    avg_score = round(total_sarcasm_score / sarcasm_evaluated, 4) if sarcasm_evaluated > 0 else None

    return SentimentSummaryResponse(
        total_analyzed=total_analyzed,
        positive=SentimentCount(count=pos_count, percentage=pos_pct),
        neutral=SentimentCount(count=neu_count, percentage=neu_pct),
        negative=SentimentCount(count=neg_count, percentage=neg_pct),
        sarcasm=SarcasmBreakdown(
            analyzed=sarcasm_evaluated,
            high_evidence_count=high_evidence_count,
            no_sarcasm_count=no_sarcasm_count,
            sarcasm_uncertain_count=uncertain_count,
            sarcasm_consistent_count=consistent_count,
            sarcasm_ambiguous_count=ambiguous_count,
            average_sarcasm_score=avg_score,
        ),
        pipeline_metadata={
            "sentiment_model": model_name,
            "sarcasm_model": sarcasm_model,
            "fusion_rule": "confidence_aware_decision_tree_v1",
            "sarcasm_score_semantics": "uncalibrated_t5_generation_log_likelihood",
        },
    )


@router.get(
    "/timeline",
    response_model=SentimentTimelineResponse,
    summary="Get chronological sentiment trajectory for charting",
)
def get_sentiment_timeline(
    topic_id: Optional[int] = Query(None, description="Optional topic ID filter"),
    interval: str = Query("4h", description="Bucket window interval ('1h', '4h', '1d')"),
    start_at: Optional[datetime] = Query(None, description="Optional start timestamp filter"),
    end_at: Optional[datetime] = Query(None, description="Optional end timestamp filter"),
    db: Session = Depends(get_db),
) -> SentimentTimelineResponse:
    """Return time-bucketed sentiment counts and percentages.

    Powers the 24h Sentiment Trajectory LineChart on the frontend.
    """
    stmt = (
        select(Tweet.created_at_utc, SentimentResult.final_sentiment)
        .join(SentimentResult, Tweet.id == SentimentResult.tweet_id)
        .order_by(Tweet.created_at_utc.asc())
    )

    if topic_id is not None:
        stmt = stmt.join(TweetTopic, Tweet.id == TweetTopic.tweet_id).where(
            TweetTopic.topic_id == topic_id,
            TweetTopic.is_outlier == False,
        )

    if start_at is not None:
        stmt = stmt.where(Tweet.created_at_utc >= start_at)

    if end_at is not None:
        stmt = stmt.where(Tweet.created_at_utc <= end_at)

    rows = db.execute(stmt).all()

    if not rows:
        return SentimentTimelineResponse(points=[], interval=interval, topic_id=topic_id)

    # Determine bucket size
    bucket_hours = 4
    if interval == "1h":
        bucket_hours = 1
    elif interval == "1d":
        bucket_hours = 24

    min_time = rows[0][0]
    max_time = rows[-1][0]

    # Normalize bucket start to hour boundary
    cur_bucket_start = min_time.replace(minute=0, second=0, microsecond=0)
    step = timedelta(hours=bucket_hours)

    buckets: list[dict] = []
    bucket_data: dict = {"pos": 0, "neu": 0, "neg": 0, "total": 0}

    row_idx = 0
    n_rows = len(rows)

    while cur_bucket_start <= max_time + step and row_idx < n_rows:
        bucket_end = cur_bucket_start + step
        pos = 0
        neu = 0
        neg = 0

        while row_idx < n_rows and rows[row_idx][0] < bucket_end:
            s = str(rows[row_idx][1]).lower()
            if "pos" in s:
                pos += 1
            elif "neg" in s:
                neg += 1
            else:
                neu += 1
            row_idx += 1

        total = pos + neu + neg
        if total > 0:
            pos_pct = round(pos / total * 100, 1)
            neu_pct = round(neu / total * 100, 1)
            neg_pct = round(neg / total * 100, 1)
            label = cur_bucket_start.strftime("%H:%M" if bucket_hours < 24 else "%b %d")
            buckets.append(
                SentimentTimelinePoint(
                    timestamp=label,
                    positive=pos,
                    neutral=neu,
                    negative=neg,
                    total=total,
                    positive_pct=pos_pct,
                    neutral_pct=neu_pct,
                    negative_pct=neg_pct,
                )
            )

        cur_bucket_start = bucket_end

    return SentimentTimelineResponse(points=buckets, interval=interval, topic_id=topic_id)
