"""Tests for SentimentService and DatabaseSentimentAnalyzer.

These tests mock the Hugging Face transformer components to avoid downloading
the model and avoid requiring heavy dependencies in the CI unit-test run.
"""

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.analytics.sentiment.service import SentimentService, PIPELINE_VERSION
from app.analytics.sentiment.analyzer import DatabaseSentimentAnalyzer
from app.models.tweet import Tweet
from app.models.sentiment_result import SentimentResult
from app.models.user import User


@pytest.fixture
def mock_transformers():
    with patch("app.analytics.sentiment.service.AutoTokenizer") as mock_tokenizer, \
         patch("app.analytics.sentiment.service.AutoModelForSequenceClassification") as mock_model, \
         patch("app.analytics.sentiment.service.torch") as mock_torch, \
         patch("app.analytics.sentiment.service.F.softmax") as mock_softmax:
         
        # Setup mock config
        mock_config = MagicMock()
        mock_config.id2label = {0: "negative", 1: "neutral", 2: "positive"}
        mock_config._commit_hash = "mock_hash_123"
        
        mock_model_instance = MagicMock()
        mock_model_instance.config = mock_config
        mock_model.from_pretrained.return_value = mock_model_instance
        
        mock_softmax.return_value = MagicMock()  # We will mock the output later
        
        yield {
            "tokenizer": mock_tokenizer,
            "model": mock_model,
            "model_instance": mock_model_instance,
            "torch": mock_torch,
            "softmax": mock_softmax,
        }


def test_sentiment_service_init(mock_transformers):
    service = SentimentService()
    assert service.model_id == "cardiffnlp/twitter-xlm-roberta-base-sentiment"
    assert service.model_revision == "mock_hash_123"
    assert service.tokenizer is not None
    assert service.model is not None


def test_analyze_batch_mapping(mock_transformers):
    # Mock the softmax output
    # Let's say batch size 2, 3 labels (neg, neu, pos)
    # Output 1: mostly positive [0.1, 0.2, 0.7]
    # Output 2: mostly negative [0.8, 0.1, 0.1]
    
    mock_tensor1 = MagicMock()
    mock_tensor1.cpu().numpy.return_value = [0.1, 0.2, 0.7]
    mock_tensor2 = MagicMock()
    mock_tensor2.cpu().numpy.return_value = [0.8, 0.1, 0.1]
    
    mock_transformers["softmax"].return_value = [mock_tensor1, mock_tensor2]
    
    service = SentimentService()
    results = service.analyze_batch(["test 1", "test 2"])
    
    assert len(results) == 2
    
    # Check first result (positive)
    r1 = results[0]
    assert r1["negative_probability"] == 0.1
    assert r1["neutral_probability"] == 0.2
    assert r1["positive_probability"] == 0.7
    assert r1["base_sentiment"] == "positive"
    assert r1["base_confidence"] == 0.7
    assert r1["model_revision"] == "mock_hash_123"
    
    # Check second result (negative)
    r2 = results[1]
    assert r2["negative_probability"] == 0.8
    assert r2["base_sentiment"] == "negative"
    assert r2["base_confidence"] == 0.8


from datetime import datetime, timezone

def test_analyzer_unanalyzed_tweets(db_session: Session, mock_transformers):
    # Create user
    user = User(twitter_user_id="111", username="test")
    db_session.add(user)
    db_session.commit()
    
    # Create two tweets
    t1 = Tweet(twitter_tweet_id="t1", author_id=user.id, text="t1 text", created_at_utc=datetime(2026, 1, 1, tzinfo=timezone.utc))
    t2 = Tweet(twitter_tweet_id="t2", author_id=user.id, text="t2 text", created_at_utc=datetime(2026, 1, 2, tzinfo=timezone.utc))
    db_session.add_all([t1, t2])
    db_session.commit()
    
    # Add sentiment for t1 only
    sr = SentimentResult(
        tweet_id=t1.id,
        model_id="cardiffnlp/twitter-xlm-roberta-base-sentiment",
        model_revision="hash",
        pipeline_version=PIPELINE_VERSION,
        negative_probability=0.1,
        neutral_probability=0.1,
        positive_probability=0.8,
        base_sentiment="positive",
        base_confidence=0.8,
        final_sentiment="positive",
        final_confidence=0.8,
    )
    db_session.add(sr)
    db_session.commit()
    
    service = SentimentService()
    analyzer = DatabaseSentimentAnalyzer(db_session, service)
    
    # t1 is analyzed, t2 is not. Should only return t2
    tweets = analyzer.get_unanalyzed_tweets(limit=10)
    assert len(tweets) == 1
    assert tweets[0].id == t2.id


def test_analyzer_persistence(db_session: Session, mock_transformers):
    user = User(twitter_user_id="222", username="test2")
    db_session.add(user)
    db_session.commit()
    
    t1 = Tweet(twitter_tweet_id="t10", author_id=user.id, text="hello", created_at_utc=datetime(2026, 1, 1, tzinfo=timezone.utc))
    db_session.add(t1)
    db_session.commit()
    
    # Mock inference result
    mock_tensor = MagicMock()
    mock_tensor.cpu().numpy.return_value = [0.1, 0.8, 0.1]
    mock_transformers["softmax"].return_value = [mock_tensor]
    
    analyzer = DatabaseSentimentAnalyzer(db_session)
    summary = analyzer.analyze_batch(limit=1)
    
    assert summary["analyzed"] == 1
    assert summary["neutral"] == 1
    
    # Verify in DB
    sr = db_session.query(SentimentResult).filter_by(tweet_id=t1.id).first()
    assert sr is not None
    assert sr.base_sentiment == "neutral"
    assert sr.neutral_probability == 0.8
    assert sr.sarcasm_probability is None
