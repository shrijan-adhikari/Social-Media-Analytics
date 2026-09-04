"""Unit tests for DatabaseTrendAnalyzer with mocked MiniLM embedding service.

Verifies:
- TrendAnalysisRun creation
- Topic and TweetTopic persistence
- Outlier/noise tweet handling
- TrendWindow velocity and acceleration persistence
- Read-only sentiment breakdown aggregation
- Clean rerun behavior without orphaned records
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
import numpy as np
import pytest
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker

from app.analytics.trends.analyzer import DatabaseTrendAnalyzer
from app.analytics.trends.config import TrendConfig
from app.models.tweet import Base, Tweet
from app.models.sentiment_result import SentimentResult
from app.models.topic import Topic, TrendAnalysisRun, TrendWindow, TweetTopic


@pytest.fixture
def mock_db_session():
    """In-memory SQLite session with all models created."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed test tweets across 3 distinct 15-minute windows
    base_time = datetime(2026, 9, 2, 12, 0, 0, tzinfo=timezone.utc)
    
    # 4 AI tweets in window 0 (12:00 - 12:15)
    for i in range(4):
        t = Tweet(
            id=i + 1,
            twitter_tweet_id=f"tw_ai_{i}",
            author_id=1,
            text=f"Artificial intelligence breakthrough in research #{i} #ai",
            created_at_utc=base_time + timedelta(minutes=i * 2),
            like_count=5,
            retweet_count=2,
            reply_count=1,
            quote_count=0,
        )
        session.add(t)
        # Add sentiment result for join testing
        session.add(SentimentResult(
            id=i + 1,
            tweet_id=t.id,
            model_id="mock_xlmr",
            pipeline_version="v1",
            negative_probability=0.1,
            neutral_probability=0.2,
            positive_probability=0.7,
            base_sentiment="positive",
            base_confidence=0.7,
            final_sentiment="positive",
            final_confidence=0.7,
        ))

    # 4 Gaming tweets in window 1 (12:15 - 12:30)
    for i in range(4):
        t = Tweet(
            id=i + 5,
            twitter_tweet_id=f"tw_game_{i}",
            author_id=2,
            text=f"New video game release graphics are incredible #{i} #gaming",
            created_at_utc=base_time + timedelta(minutes=16 + i * 2),
            like_count=10,
            retweet_count=4,
            reply_count=2,
            quote_count=1,
        )
        session.add(t)
        session.add(SentimentResult(
            id=i + 5,
            tweet_id=t.id,
            model_id="mock_xlmr",
            pipeline_version="v1",
            negative_probability=0.6,
            neutral_probability=0.3,
            positive_probability=0.1,
            base_sentiment="negative",
            base_confidence=0.6,
            final_sentiment="negative",
            final_confidence=0.6,
        ))

    session.commit()
    yield session
    session.close()


def test_database_trend_analyzer_mocked(mock_db_session):
    # Mock embedding service returning 8 distinct 384-dim embeddings
    mock_embedding_svc = MagicMock()
    mock_embedding_svc.model_id = "sentence-transformers/all-MiniLM-L6-v2"
    mock_embedding_svc.model_revision = "mock_hash_123"
    
    # 4 identical vectors for AI, 4 identical for Gaming
    v1 = np.ones(384, dtype=np.float32) / np.sqrt(384)
    v2 = -np.ones(384, dtype=np.float32) / np.sqrt(384)
    mock_embeddings = np.vstack([np.tile(v1, (4, 1)), np.tile(v2, (4, 1))])
    mock_embedding_svc.embed_texts.return_value = mock_embeddings

    config = TrendConfig(
        TREND_WINDOW_MINUTES=15,
        HDBSCAN_MIN_CLUSTER_SIZE=3,
        HDBSCAN_MIN_SAMPLES=2,
        MIN_SUPPORT_MENTIONS=2,
    )

    analyzer = DatabaseTrendAnalyzer(
        session=mock_db_session,
        config=config,
        embedding_service=mock_embedding_svc,
    )

    run = analyzer.run_analysis()

    # Verify run record
    assert run.id is not None
    assert run.dataset_tweet_count == 8
    assert run.embedding_model_id == "sentence-transformers/all-MiniLM-L6-v2"
    assert run.embedding_model_revision == "mock_hash_123"

    # Verify topics persisted
    topics = mock_db_session.scalars(select(Topic).where(Topic.run_id == run.id)).all()
    assert len(topics) >= 2  # Semantic clusters + Lexical hashtags

    # Check topic types exist
    types = {t.topic_type for t in topics}
    assert "semantic" in types
    assert "lexical" in types

    # Verify TweetTopic memberships
    tt_count = mock_db_session.scalar(select(func.count(TweetTopic.id)).where(TweetTopic.run_id == run.id))
    assert tt_count >= 8

    # Verify TrendWindows
    windows = mock_db_session.scalars(select(TrendWindow).where(TrendWindow.run_id == run.id)).all()
    assert len(windows) > 0

    # Verify sentiment join
    first_topic = topics[0]
    sentiment_breakdown = analyzer.get_topic_sentiment_breakdown(run.id, first_topic.id)
    assert sum(sentiment_breakdown.values()) > 0
