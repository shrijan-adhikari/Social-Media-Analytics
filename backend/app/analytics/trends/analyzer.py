"""Database orchestrator for Trend & Topic Detection (Phase 3A).

Coordinates:
- Tweet retrieval from PostgreSQL
- MiniLM dense semantic embedding
- HDBSCAN clustering with noise isolation
- Deterministic TF-IDF topic labeling
- Lexical hashtag trend discovery
- Time-window bucketing, velocity, and acceleration calculations
- Versioned analysis run persistence under `trend_analysis_runs`
- Read-only sentiment join for topic breakdown
"""

from collections import defaultdict
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics.trends.clustering import cluster_embeddings
from app.analytics.trends.config import DEFAULT_TREND_CONFIG, TrendConfig
from app.analytics.trends.embeddings import MiniLMEmbeddingService
from app.analytics.trends.labeling import extract_cluster_topic_labels
from app.analytics.trends.lexical import (
    extract_hashtags,
    generate_time_windows,
    compute_windowed_metrics_for_topic,
)
from app.models.sentiment_result import SentimentResult
from app.models.topic import Topic, TrendAnalysisRun, TrendWindow, TweetTopic
from app.models.tweet import Tweet

logger = logging.getLogger(__name__)


class DatabaseTrendAnalyzer:
    """Orchestrator for discovering topics and computing windowed trend metrics."""

    def __init__(
        self,
        session: Session,
        config: TrendConfig = DEFAULT_TREND_CONFIG,
        embedding_service: Optional[MiniLMEmbeddingService] = None,
    ):
        self.session = session
        self.config = config
        self._embedding_service = embedding_service

    def _get_embedding_service(self) -> MiniLMEmbeddingService:
        if self._embedding_service is None:
            self._embedding_service = MiniLMEmbeddingService(
                model_id=self.config.EMBEDDING_MODEL_ID
            )
        return self._embedding_service

    def run_analysis(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> TrendAnalysisRun:
        """Execute complete trend and topic analysis over stored tweets.

        Creates an explicit TrendAnalysisRun and persists topics, tweet-topic
        assignments, and trend windows.
        """
        # 1. Fetch tweets
        stmt = select(Tweet).order_by(Tweet.created_at_utc.asc())
        if start_time:
            stmt = stmt.where(Tweet.created_at_utc >= start_time)
        if end_time:
            stmt = stmt.where(Tweet.created_at_utc <= end_time)
        if limit:
            stmt = stmt.limit(limit)

        tweets: List[Tweet] = list(self.session.scalars(stmt).all())
        if not tweets:
            raise ValueError("No tweets found in specified range for trend analysis.")

        earliest_t = tweets[0].created_at_utc
        latest_t = tweets[-1].created_at_utc
        logger.info(
            f"Starting trend analysis over {len(tweets)} tweets "
            f"spanning {earliest_t} to {latest_t}."
        )

        embedding_svc = self._get_embedding_service()

        # 2. Initialize analysis run
        run = TrendAnalysisRun(
            pipeline_version=self.config.PIPELINE_VERSION,
            dataset_tweet_count=len(tweets),
            earliest_tweet_at=earliest_t,
            latest_tweet_at=latest_t,
            window_minutes=self.config.TREND_WINDOW_MINUTES,
            embedding_model_id=embedding_svc.model_id,
            embedding_model_revision=embedding_svc.model_revision,
            clustering_params=self.config.get_hdbscan_params(),
        )
        self.session.add(run)
        self.session.flush()  # Obtain run.id

        # 3. Generate all chronological windows across the dataset span
        all_windows = generate_time_windows(
            start_dt=earliest_t,
            end_dt=latest_t,
            window_minutes=self.config.TREND_WINDOW_MINUTES,
        )

        # ==========================================================
        # LAYER B: SEMANTIC TOPIC DISCOVERY (MiniLM + HDBSCAN)
        # ==========================================================
        tweet_texts = [t.text for t in tweets]
        embeddings = embedding_svc.embed_texts(
            tweet_texts, batch_size=self.config.EMBEDDING_BATCH_SIZE
        )

        cluster_labels, cluster_probs = cluster_embeddings(
            embeddings=embeddings,
            min_cluster_size=self.config.HDBSCAN_MIN_CLUSTER_SIZE,
            min_samples=self.config.HDBSCAN_MIN_SAMPLES,
            metric=self.config.HDBSCAN_METRIC,
        )

        # Group tweets by cluster
        cluster_to_tweets: Dict[int, List[Tweet]] = defaultdict(list)
        cluster_to_texts: Dict[int, List[str]] = defaultdict(list)
        for tweet, c_id in zip(tweets, cluster_labels):
            if c_id >= 0:
                cluster_to_tweets[c_id].append(tweet)
                cluster_to_texts[c_id].append(tweet.text)

        # Generate TF-IDF labels for clusters
        cluster_labels_dict = extract_cluster_topic_labels(
            cluster_texts=cluster_to_texts,
            top_n_terms=self.config.TOPIC_TOP_TERMS_COUNT,
        )

        # Persist Semantic Topics & Tweet Topics
        cluster_to_topic_obj: Dict[int, Topic] = {}
        for c_id, (label, rep_terms) in cluster_labels_dict.items():
            topic_obj = Topic(
                run_id=run.id,
                label=label,
                representative_terms=rep_terms,
                topic_type="semantic",
            )
            self.session.add(topic_obj)
            cluster_to_topic_obj[c_id] = topic_obj

        self.session.flush()

        # Persist TweetTopic memberships (including noise)
        for tweet, c_id, prob in zip(tweets, cluster_labels, cluster_probs):
            is_outlier = bool(c_id == -1)
            topic_ref = cluster_to_topic_obj.get(c_id) if not is_outlier else None
            
            tt_row = TweetTopic(
                run_id=run.id,
                tweet_id=tweet.id,
                topic_id=topic_ref.id if topic_ref else None,
                cluster_id=int(c_id),
                is_outlier=is_outlier,
                membership_probability=float(prob) if prob is not None else None,
            )
            self.session.add(tt_row)

        # Compute and persist Trend Windows for Semantic Topics
        for c_id, topic_obj in cluster_to_topic_obj.items():
            c_tweets = cluster_to_tweets[c_id]
            window_metrics = compute_windowed_metrics_for_topic(
                topic_tweets=c_tweets,
                all_windows=all_windows,
                baseline_window_count=self.config.BASELINE_WINDOW_COUNT,
                min_support=self.config.MIN_SUPPORT_MENTIONS,
                baseline_floor=self.config.BASELINE_FLOOR,
            )
            for wm in window_metrics:
                tw_row = TrendWindow(
                    run_id=run.id,
                    topic_id=topic_obj.id,
                    window_start=wm["window_start"],
                    window_end=wm["window_end"],
                    mention_count=wm["mention_count"],
                    baseline_mentions=wm["baseline_mentions"],
                    velocity=wm["velocity"],
                    acceleration=wm["acceleration"],
                    like_count=wm["like_count"],
                    repost_count=wm["repost_count"],
                    reply_count=wm["reply_count"],
                    quote_count=wm["quote_count"],
                )
                self.session.add(tw_row)

        # ==========================================================
        # LAYER A: LEXICAL HASHTAG TREND DETECTION
        # ==========================================================
        hashtag_to_tweets: Dict[str, List[Tweet]] = defaultdict(list)
        for tweet in tweets:
            for ht in set(extract_hashtags(tweet.text)):
                hashtag_to_tweets[ht].append(tweet)

        # Filter hashtags that meet minimum support across dataset
        for ht, ht_tweets in hashtag_to_tweets.items():
            if len(ht_tweets) >= self.config.MIN_SUPPORT_MENTIONS:
                lex_topic = Topic(
                    run_id=run.id,
                    label=ht,
                    representative_terms=[ht],
                    topic_type="lexical",
                )
                self.session.add(lex_topic)
                self.session.flush()

                for t in ht_tweets:
                    tt_row = TweetTopic(
                        run_id=run.id,
                        tweet_id=t.id,
                        topic_id=lex_topic.id,
                        cluster_id=0,  # 0 indicates matched lexical rule
                        is_outlier=False,
                        membership_probability=1.0,
                    )
                    self.session.add(tt_row)

                lex_window_metrics = compute_windowed_metrics_for_topic(
                    topic_tweets=ht_tweets,
                    all_windows=all_windows,
                    baseline_window_count=self.config.BASELINE_WINDOW_COUNT,
                    min_support=self.config.MIN_SUPPORT_MENTIONS,
                    baseline_floor=self.config.BASELINE_FLOOR,
                )
                for wm in lex_window_metrics:
                    tw_row = TrendWindow(
                        run_id=run.id,
                        topic_id=lex_topic.id,
                        window_start=wm["window_start"],
                        window_end=wm["window_end"],
                        mention_count=wm["mention_count"],
                        baseline_mentions=wm["baseline_mentions"],
                        velocity=wm["velocity"],
                        acceleration=wm["acceleration"],
                        like_count=wm["like_count"],
                        repost_count=wm["repost_count"],
                        reply_count=wm["reply_count"],
                        quote_count=wm["quote_count"],
                    )
                    self.session.add(tw_row)

        self.session.commit()
        logger.info(
            f"TrendAnalysisRun {run.id} complete: "
            f"{len(cluster_to_topic_obj)} semantic topics and "
            f"{len([h for h, ts in hashtag_to_tweets.items() if len(ts) >= self.config.MIN_SUPPORT_MENTIONS])} lexical topics saved."
        )
        return run

    def get_topic_sentiment_breakdown(self, run_id: int, topic_id: int) -> dict[str, int]:
        """Perform read-only aggregation of existing sentiment results for a topic.

        Strictly avoids rerunning sentiment inference models (§23).
        """
        stmt = (
            select(
                SentimentResult.final_sentiment,
                func.count(SentimentResult.id),
            )
            .join(TweetTopic, TweetTopic.tweet_id == SentimentResult.tweet_id)
            .where(TweetTopic.run_id == run_id, TweetTopic.topic_id == topic_id)
            .group_by(SentimentResult.final_sentiment)
        )
        counts = dict(self.session.execute(stmt).all())
        return {
            "positive": counts.get("positive", 0),
            "neutral": counts.get("neutral", 0),
            "negative": counts.get("negative", 0),
        }
