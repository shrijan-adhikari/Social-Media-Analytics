import logging
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.tweet import Tweet
from app.models.sentiment_result import SentimentResult
from app.analytics.sarcasm.service import SarcasmService
from app.analytics.sentiment.fusion import fuse_sentiment_and_sarcasm

logger = logging.getLogger(__name__)

class DatabaseSarcasmAnalyzer:
    """Orchestrates pulling unanalyzed sentiment results, processing sarcasm, and updating them."""

    def __init__(self):
        self._sarcasm_service = None

    def _get_service(self) -> SarcasmService:
        if self._sarcasm_service is None:
            self._sarcasm_service = SarcasmService()
        return self._sarcasm_service

    def analyze_batch(self, limit: int = 100) -> dict:
        """
        Analyze a batch of sentiment results that haven't had sarcasm processed yet.
        """
        summary = {
            "processed": 0,
            "sarcastic": 0,
            "non_sarcastic": 0,
            "failed": 0
        }

        with SessionLocal() as session:
            # Find sentiment results that have NO sarcasm pipeline version
            stmt = (
                select(SentimentResult, Tweet)
                .join(Tweet, SentimentResult.tweet_id == Tweet.id)
                .where(SentimentResult.sarcasm_pipeline_version.is_(None))
                .limit(limit)
            )
            
            results = session.execute(stmt).all()
            
            if not results:
                logger.info("No unanalyzed sentiment results found for sarcasm processing.")
                return summary

            service = self._get_service()

            for sentiment_res, tweet in results:
                try:
                    with session.begin_nested():
                        sarcasm_output = service.analyze_text(tweet.text)
                        
                        sarcasm_label = sarcasm_output["label"]
                        sarcasm_score = sarcasm_output["score"]
                        
                        final_sent, final_conf, fusion_status = fuse_sentiment_and_sarcasm(
                            base_sentiment=sentiment_res.base_sentiment,
                            base_confidence=sentiment_res.base_confidence,
                            sarcasm_label=sarcasm_label,
                            sarcasm_score=sarcasm_score
                        )
                        
                        # Update the result record
                        sentiment_res.sarcasm_probability = sarcasm_score
                        sentiment_res.sarcasm_model_id = sarcasm_output["model_id"]
                        sentiment_res.sarcasm_model_revision = sarcasm_output["model_revision"]
                        sentiment_res.sarcasm_pipeline_version = sarcasm_output["pipeline_version"]
                        
                        sentiment_res.final_sentiment = final_sent
                        sentiment_res.final_confidence = final_conf
                        sentiment_res.fusion_status = fusion_status

                        if fusion_status and "SARCASM" in fusion_status.upper() and fusion_status != "NO_SARCASM":
                            summary["sarcastic"] += 1
                        else:
                            summary["non_sarcastic"] += 1
                            
                        summary["processed"] += 1
                        
                except Exception as e:
                    logger.error(f"Failed to process sarcasm for sentiment_result {sentiment_res.id}: {e}")
                    summary["failed"] += 1
                    
            session.commit()

        return summary
