"""Real model integration tests.

These tests actually download/load the Hugging Face model and perform inference.
They are marked with @pytest.mark.integration so they don't run in the fast unit test suite.
"""

import math
import pytest
from sqlalchemy.orm import Session

from app.analytics.sentiment.service import SentimentService, PIPELINE_VERSION
from app.analytics.sentiment.analyzer import DatabaseSentimentAnalyzer
from app.models.tweet import Tweet
from app.models.user import User
from app.models.sentiment_result import SentimentResult


from datetime import datetime, timezone

@pytest.mark.integration
def test_real_model_inference_and_persistence(db_session: Session):
    """Smoke test using the real model.
    
    Verifies:
    - Checkpoint downloads/loads.
    - Tokenizer works.
    - Inference executes.
    - Probabilities are valid and sum to ~1.
    - DB persistence succeeds with constraints.
    """
    # 1. Setup real service
    service = SentimentService()
    
    # 2. Setup DB test data
    user = User(twitter_user_id="integration_user", username="int_user")
    db_session.add(user)
    db_session.commit()
    
    t1 = Tweet(
        twitter_tweet_id="int_t1",
        author_id=user.id,
        text="I absolutely love this new feature! It is amazing! 😂",
        created_at_utc=datetime(2026, 1, 1, tzinfo=timezone.utc)
    )
    t2 = Tweet(
        twitter_tweet_id="int_t2",
        author_id=user.id,
        text="This is terrible and completely broken. I hate it.",
        created_at_utc=datetime(2026, 1, 2, tzinfo=timezone.utc)
    )
    db_session.add_all([t1, t2])
    db_session.commit()
    
    # 3. Analyze
    analyzer = DatabaseSentimentAnalyzer(db_session, service)
    summary = analyzer.analyze_batch(limit=10)
    
    assert summary["analyzed"] == 2
    assert summary["failed"] == 0
    
    # 4. Verify DB records and constraints
    results = db_session.query(SentimentResult).all()
    assert len(results) == 2
    
    for r in results:
        # Check sum of probabilities ≈ 1
        prob_sum = r.negative_probability + r.neutral_probability + r.positive_probability
        assert math.isclose(prob_sum, 1.0, rel_tol=1e-5)
        
        # Check ranges
        assert 0.0 <= r.negative_probability <= 1.0
        assert 0.0 <= r.neutral_probability <= 1.0
        assert 0.0 <= r.positive_probability <= 1.0
        assert 0.0 <= r.base_confidence <= 1.0
        
        # Check nullable revision
        # It should be either a string or None, not "latest" or "unknown"
        assert r.model_revision is None or (isinstance(r.model_revision, str) and r.model_revision not in ("latest", "unknown"))

    # Specific assertions based on expected sentiment
    r1 = db_session.query(SentimentResult).filter_by(tweet_id=t1.id).one()
    assert r1.base_sentiment == "positive"
    
    r2 = db_session.query(SentimentResult).filter_by(tweet_id=t2.id).one()
    assert r2.base_sentiment == "negative"
    
    # 5. Idempotency Check
    summary2 = analyzer.analyze_batch(limit=10)
    assert summary2["analyzed"] == 0  # No new tweets to analyze
    assert len(db_session.query(SentimentResult).all()) == 2  # Still 2 records
