"""CLI tool to execute Trend & Topic Detection across stored tweets in PostgreSQL."""

import argparse
from datetime import datetime, timedelta, timezone
import logging
import os
from pathlib import Path
import sys

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import select, desc
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.analytics.trends.config import TrendConfig
from app.analytics.trends.analyzer import DatabaseTrendAnalyzer
from app.models.topic import Topic, TrendWindow, TweetTopic

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Run Trend & Topic Detection on stored tweets.")
    parser.add_argument("--hours", type=int, default=None, help="Filter to tweets within the last N hours.")
    parser.add_argument("--window-minutes", type=int, default=15, help="Time window size in minutes (default: 15).")
    parser.add_argument("--min-cluster-size", type=int, default=3, help="HDBSCAN min_cluster_size (default: 3).")
    parser.add_argument("--limit", type=int, default=None, help="Max tweets to analyze.")
    args = parser.parse_args()

    start_time = None
    if args.hours:
        start_time = datetime.now(timezone.utc) - timedelta(hours=args.hours)

    config = TrendConfig(
        TREND_WINDOW_MINUTES=args.window_minutes,
        HDBSCAN_MIN_CLUSTER_SIZE=args.min_cluster_size,
    )

    with SessionLocal() as session:
        analyzer = DatabaseTrendAnalyzer(session=session, config=config)
        
        logger.info(f"Executing trend analysis (window: {args.window_minutes}m, min_cluster_size: {args.min_cluster_size})...")
        run = analyzer.run_analysis(start_time=start_time, limit=args.limit)

        print("\n" + "=" * 70)
        print("=== TREND & TOPIC ANALYSIS RUN SUMMARY ===")
        print("=" * 70)
        print(f"Run ID:                  {run.id}")
        print(f"Pipeline Version:        {run.pipeline_version}")
        print(f"Analyzed Tweet Count:    {run.dataset_tweet_count}")
        print(f"Earliest Tweet UTC:      {run.earliest_tweet_at}")
        print(f"Latest Tweet UTC:        {run.latest_tweet_at}")
        print(f"Window Minutes:          {run.window_minutes}")
        print(f"Embedding Model:         {run.embedding_model_id}")
        print(f"Model Revision:          {run.embedding_model_revision}")
        print(f"Clustering Parameters:   {run.clustering_params}")

        # Fetch Topics
        topics = session.scalars(select(Topic).where(Topic.run_id == run.id)).all()
        print(f"\nDiscovered Topics ({len(topics)} total):")
        for tp in topics:
            tweet_count = len(tp.tweet_assignments)
            sentiment = analyzer.get_topic_sentiment_breakdown(run.id, tp.id)
            print(f"  [{tp.topic_type.upper()}] ID {tp.id:2d}: \"{tp.label}\" ({tweet_count} tweets)")
            print(f"       Terms:     {tp.representative_terms}")
            print(f"       Sentiment: Pos: {sentiment['positive']} | Neu: {sentiment['neutral']} | Neg: {sentiment['negative']}")

        # Fetch Top Emerging Windows (sorted by velocity)
        top_windows = session.scalars(
            select(TrendWindow)
            .where(TrendWindow.run_id == run.id)
            .order_by(desc(TrendWindow.velocity), desc(TrendWindow.mention_count))
            .limit(10)
        ).all()

        print("\nTop Emerging Trend Windows (by Velocity):")
        for tw in top_windows:
            if tw.velocity > 0 or tw.mention_count >= config.MIN_SUPPORT_MENTIONS:
                print(
                    f"  Topic {tw.topic_id} ('{tw.topic.label}') | "
                    f"Window: {tw.window_start.strftime('%Y-%m-%d %H:%M')} - {tw.window_end.strftime('%H:%M')} UTC | "
                    f"Mentions: {tw.mention_count:2d} (Baseline: {tw.baseline_mentions:.2f}) | "
                    f"Vel: {tw.velocity:5.2f}x | Accel: {tw.acceleration:+5.2f} | "
                    f"Engage: [Likes: {tw.like_count}, Reposts: {tw.repost_count}, Replies: {tw.reply_count}]"
                )
        print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
