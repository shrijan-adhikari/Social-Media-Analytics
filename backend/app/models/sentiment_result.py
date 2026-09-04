"""Sentiment Result ORM model.

Stores granular probabilities, base sentiment, and confidence values
for tweets analyzed by the sentiment pipeline.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class SentimentResult(Base):
    """Represents sentiment analysis inference results for a tweet."""

    __tablename__ = "sentiment_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # FK to our internal tweets.id
    tweet_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tweets.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Model provenance
    model_id: Mapped[str] = mapped_column(String(255), nullable=False)
    # Nullable model revision to avoid inventing "latest" or "unknown" if unresolved
    model_revision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pipeline_version: Mapped[str] = mapped_column(String(64), nullable=False)

    # Base inference probabilities from the model
    negative_probability: Mapped[float] = mapped_column(Float, nullable=False)
    neutral_probability: Mapped[float] = mapped_column(Float, nullable=False)
    positive_probability: Mapped[float] = mapped_column(Float, nullable=False)

    # Base label and confidence
    base_sentiment: Mapped[str] = mapped_column(String(32), nullable=False)
    base_confidence: Mapped[float] = mapped_column(Float, nullable=False)

    # Final label and confidence after potential sarcasm/fusion adjustments (Phase 3)
    final_sentiment: Mapped[str] = mapped_column(String(32), nullable=False)
    final_confidence: Mapped[float] = mapped_column(Float, nullable=False)

    # Sarcasm probability (Phase 3 -> Phase 2B MVP uses this for the uncalibrated proxy score)
    # Note: This is an UNCALIBRATED PROXY SCORE derived from the T5 generative sequence log-probabilities,
    # NOT a calibrated softmax probability.
    sarcasm_probability: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Sarcasm provenance
    sarcasm_model_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sarcasm_model_revision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sarcasm_pipeline_version: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Fusion interpretation status (e.g. NO_SARCASM, SARCASM_CONSISTENT, SARCASM_AMBIGUOUS, SARCASM_UNCERTAIN)
    fusion_status: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Row insertion timestamp
    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
    )

    # Relationships
    tweet: Mapped["Tweet"] = relationship(  # noqa: F821
        "Tweet", backref="sentiment_result"
    )

    __table_args__ = (
        # Idempotency constraint: 1 analysis per tweet + model + pipeline
        UniqueConstraint(
            "tweet_id", "model_id", "pipeline_version", name="uq_sentiment_tweet_model"
        ),
        # CHECK constraints for probabilities
        CheckConstraint(
            "negative_probability >= 0.0 AND negative_probability <= 1.0",
            name="chk_neg_prob_range",
        ),
        CheckConstraint(
            "neutral_probability >= 0.0 AND neutral_probability <= 1.0",
            name="chk_neu_prob_range",
        ),
        CheckConstraint(
            "positive_probability >= 0.0 AND positive_probability <= 1.0",
            name="chk_pos_prob_range",
        ),
        CheckConstraint(
            "base_confidence >= 0.0 AND base_confidence <= 1.0",
            name="chk_base_conf_range",
        ),
        CheckConstraint(
            "final_confidence >= 0.0 AND final_confidence <= 1.0",
            name="chk_final_conf_range",
        ),
        CheckConstraint(
            "sarcasm_probability >= 0.0 AND sarcasm_probability <= 1.0",
            name="chk_sarcasm_prob_range",
        ),
        Index("ix_sentiment_results_analyzed_at", "analyzed_at"),
    )

    def __repr__(self) -> str:
        return f"<SentimentResult id={self.id} tweet_id={self.tweet_id} base={self.base_sentiment}>"
