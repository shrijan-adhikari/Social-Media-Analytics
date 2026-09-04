"""GET /api/v1/tweets endpoint providing paginated tweets with analytical metadata."""

from datetime import datetime
import math
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.sentiment_result import SentimentResult
from app.models.topic import Topic, TweetTopic
from app.models.tweet import Tweet
from app.models.user import User
from app.schemas.tweet import (
    TweetItem,
    TweetListResponse,
    TweetSentimentInfo,
    TweetTopicInfo,
)

router = APIRouter(tags=["tweets"])


@router.get(
    "/tweets",
    response_model=TweetListResponse,
    summary="Get paginated tweets with sentiment and topic annotations",
)
def list_tweets(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    topic_id: Optional[int] = Query(None, description="Filter to tweets assigned to this topic"),
    user_id: Optional[int] = Query(None, description="Filter to tweets authored by internal user ID"),
    username: Optional[str] = Query(None, description="Filter to tweets authored by Twitter username"),
    sentiment: Optional[str] = Query(None, description="Filter by sentiment (positive, neutral, negative)"),
    fusion_status: Optional[str] = Query(None, description="Filter by fusion status (e.g. SARCASM_CONSISTENT)"),
    start_at: Optional[datetime] = Query(None, description="Filter by created_at_utc >= start_at"),
    end_at: Optional[datetime] = Query(None, description="Filter by created_at_utc <= end_at"),
    db: Session = Depends(get_db),
) -> TweetListResponse:
    """Return paginated tweet records with joined author usernames, sentiment classifications, and topic tags."""
    stmt = (
        select(
            Tweet,
            User.username,
            SentimentResult,
            Topic.id.label("topic_id"),
            Topic.label.label("topic_label"),
            Topic.topic_type.label("topic_type"),
        )
        .outerjoin(User, Tweet.author_id == User.id)
        .outerjoin(SentimentResult, Tweet.id == SentimentResult.tweet_id)
        .outerjoin(TweetTopic, Tweet.id == TweetTopic.tweet_id)
        .outerjoin(Topic, TweetTopic.topic_id == Topic.id)
    )

    if topic_id is not None:
        stmt = stmt.where(TweetTopic.topic_id == topic_id, TweetTopic.is_outlier == False)

    if user_id is not None:
        stmt = stmt.where(Tweet.author_id == user_id)

    if username is not None:
        stmt = stmt.where(User.username == username)

    if sentiment is not None:
        stmt = stmt.where(func.lower(SentimentResult.final_sentiment) == sentiment.lower())

    if fusion_status is not None:
        stmt = stmt.where(SentimentResult.fusion_status == fusion_status)

    if start_at is not None:
        stmt = stmt.where(Tweet.created_at_utc >= start_at)

    if end_at is not None:
        stmt = stmt.where(Tweet.created_at_utc <= end_at)

    # Count total matching rows
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.scalar(count_stmt) or 0

    # Paginate and order by tweet creation time desc
    offset = (page - 1) * page_size
    stmt = stmt.order_by(Tweet.created_at_utc.desc()).offset(offset).limit(page_size)
    rows = db.execute(stmt).all()

    items: list[TweetItem] = []
    for tweet, username, sent, tid, tlabel, ttype in rows:
        sent_info = None
        if sent is not None:
            # Sarcasm boolean: high_sarcasm_evidence derived from documented Phase 2 threshold (Correction 3)
            high_evidence = bool(sent.sarcasm_probability and sent.sarcasm_probability >= 0.85)
            sent_info = TweetSentimentInfo(
                final_sentiment=sent.final_sentiment,
                final_confidence=round(float(sent.final_confidence or 0.0), 3),
                sarcasm_score=round(float(sent.sarcasm_probability), 4) if sent.sarcasm_probability is not None else None,
                high_sarcasm_evidence=high_evidence,
                fusion_status=sent.fusion_status,
            )

        topic_info = None
        if tid is not None and tlabel is not None:
            topic_info = TweetTopicInfo(
                topic_id=tid,
                label=tlabel,
                topic_type=ttype or "semantic",
            )

        items.append(
            TweetItem(
                id=tweet.id,
                tweet_id=tweet.twitter_tweet_id,
                username=username or "unknown",
                text=tweet.text,
                created_at_utc=tweet.created_at_utc,
                ingested_at=tweet.ingested_at,
                like_count=tweet.like_count or 0,
                retweet_count=tweet.retweet_count or 0,
                reply_count=tweet.reply_count or 0,
                quote_count=tweet.quote_count or 0,
                sentiment=sent_info,
                topic=topic_info,
            )
        )

    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return TweetListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
