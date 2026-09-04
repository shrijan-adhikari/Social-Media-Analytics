"""Database Sentiment Analyzer.

Orchestrates fetching unanalyzed tweets from PostgreSQL, passing them
to the SentimentService, and safely persisting the results.
"""

import logging
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.tweet import Tweet
from app.models.sentiment_result import SentimentResult
from app.analytics.sentiment.service import SentimentService, PIPELINE_VERSION

logger = logging.getLogger(__name__)


class DatabaseSentimentAnalyzer:
    """Service to analyze tweets already in the database."""

    def __init__(self, session: Session, sentiment_service: Optional[SentimentService] = None):
        self.session = session
        self.sentiment_service = sentiment_service

    def _get_service(self) -> SentimentService:
        # Lazy load to avoid instantiating the model if no tweets need analysis
        if not self.sentiment_service:
            self.sentiment_service = SentimentService()
        return self.sentiment_service

    def get_unanalyzed_tweets(self, limit: int = 10, model_id: Optional[str] = None) -> list[Tweet]:
        """Fetch tweets that haven't been analyzed by the current pipeline."""
        if not model_id:
             model_id = self._get_service().model_id

        # Subquery to find tweets that already have a result for this model+version
        subq = (
            select(SentimentResult.tweet_id)
            .where(
                SentimentResult.model_id == model_id,
                SentimentResult.pipeline_version == PIPELINE_VERSION,
            )
            .subquery()
        )

        # Select tweets whose ID is not in the subquery
        stmt = (
            select(Tweet)
            .outerjoin(subq, Tweet.id == subq.c.tweet_id)
            .where(subq.c.tweet_id.is_(None))
            .order_by(Tweet.created_at_utc.desc())
            .limit(limit)
        )
        
        return list(self.session.scalars(stmt).all())

    def analyze_batch(self, limit: int = 10) -> dict:
        """Run the analysis pipeline on up to `limit` tweets.
        
        Returns a summary dict with counts.
        """
        service = self._get_service()
        tweets = self.get_unanalyzed_tweets(limit=limit, model_id=service.model_id)

        if not tweets:
            logger.info("No unanalyzed tweets found.")
            return {"analyzed": 0, "positive": 0, "neutral": 0, "negative": 0, "failed": 0}

        texts = [t.text for t in tweets]
        try:
            inference_results = service.analyze_batch(texts)
        except Exception as e:
            logger.error(f"Inference batch failed: {e}")
            return {"analyzed": 0, "positive": 0, "neutral": 0, "negative": 0, "failed": len(tweets)}

        success_count = 0
        failed_count = 0
        pos_count = 0
        neu_count = 0
        neg_count = 0

        for tweet, res in zip(tweets, inference_results):
            tweet_id = tweet.id
            try:
                with self.session.begin_nested():
                    # final_sentiment initially equals base_sentiment because sarcasm fusion is not implemented yet
                    db_result = SentimentResult(
                        tweet_id=tweet_id,
                        model_id=res["model_id"],
                        model_revision=res["model_revision"],
                        pipeline_version=res["pipeline_version"],
                        negative_probability=res["negative_probability"],
                        neutral_probability=res["neutral_probability"],
                        positive_probability=res["positive_probability"],
                        base_sentiment=res["base_sentiment"],
                        base_confidence=res["base_confidence"],
                        final_sentiment=res["base_sentiment"],
                        final_confidence=res["base_confidence"],
                        sarcasm_probability=None,
                    )
                    self.session.add(db_result)
                
                # If we get here, the nested transaction committed successfully
                success_count += 1
                if res["base_sentiment"] == "positive":
                    pos_count += 1
                elif res["base_sentiment"] == "neutral":
                    neu_count += 1
                else:
                    neg_count += 1
            except IntegrityError:
                # The nested transaction automatically rolled back the SAVEPOINT
                logger.warning(f"Duplicate sentiment result skipped for tweet {tweet_id}")
                # Don't count as success or fail, it was already there (idempotency check)
            except Exception as e:
                logger.error(f"Failed to persist sentiment for tweet {tweet_id}: {e}")
                failed_count += 1

        self.session.commit()

        return {
            "analyzed": success_count,
            "positive": pos_count,
            "neutral": neu_count,
            "negative": neg_count,
            "failed": failed_count,
        }
