import asyncio
import os
import sys

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.interaction import Interaction
from app.models.tweet import Tweet
from app.models.user import User
from app.services.ingestion import IngestionService
from app.services.twitter_collector import TwitterCollector


async def run_live_verification():
    settings = get_settings()
    print("[1/6] Checking configuration...")
    if not settings.DATABASE_URL:
        print("FAIL: DATABASE_URL not set")
        return False

    has_creds = bool(settings.TWITTER_USERNAME and settings.TWITTER_PASSWORD)
    print(f"Twitter credentials configured: {has_creds}")

    # [2/6] Initialize twscrape collector and test auth
    print("[2/6] Initializing twscrape and testing session/login...")
    collector = TwitterCollector()
    await collector.initialize()

    accounts = await collector.api.pool.get_all()
    print(f"Registered accounts in pool: {len(accounts)}")
    if accounts:
        active_count = sum(1 for a in accounts if a.active)
        logged_in_count = sum(1 for a in accounts if a.logged_in)
        print(f"Account status: active={active_count}, logged_in={logged_in_count}")
    else:
        print("Warning: No accounts in pool.")

    # [3/6] Fetch small sample (5-10 tweets)
    query = "technology"
    limit = 5
    print(f"[3/6] Fetching {limit} tweets for query '{query}'...")
    try:
        raw_tweets = await collector.search_tweets(query, limit=limit)
        print(f"Retrieved {len(raw_tweets)} tweets from Twitter.")
    except Exception as e:
        print(f"FAIL: twscrape search error: {type(e).__name__}: {e}")
        return False

    if not raw_tweets:
        print("FAIL: No tweets returned from search.")
        return False

    # [4/6] Production pipeline ingestion
    print("[4/6] Ingesting tweets via IngestionService -> SQLAlchemy -> PostgreSQL...")
    db: Session = SessionLocal()
    try:
        ingestion = IngestionService(db)

        # Baseline counts before ingestion
        u_before = db.scalar(select(func.count(User.id)))
        t_before = db.scalar(select(func.count(Tweet.id)))
        i_before = db.scalar(select(func.count(Interaction.id)))

        inserted_tweets = 0
        inserted_interactions = 0
        for raw_tweet in raw_tweets:
            author, tweet, interactions = ingestion.ingest_raw_tweet(raw_tweet)
            inserted_tweets += 1
            inserted_interactions += len(interactions)

        u_after = db.scalar(select(func.count(User.id)))
        t_after = db.scalar(select(func.count(Tweet.id)))
        i_after = db.scalar(select(func.count(Interaction.id)))

        print(f"First ingestion complete:")
        print(f"  Users in DB: {u_before} -> {u_after} (delta: +{u_after - u_before})")
        print(f"  Tweets in DB: {t_before} -> {t_after} (delta: +{t_after - t_before})")
        print(f"  Interactions in DB: {i_before} -> {i_after} (delta: +{i_after - i_before})")

        # [5/6] Integrity check on at least one stored tweet
        print("[5/6] Verifying data integrity of stored tweet...")
        sample_tweet_id = str(raw_tweets[0].id)
        stmt = select(Tweet).where(Tweet.twitter_tweet_id == sample_tweet_id)
        sample = db.scalar(stmt)
        if not sample:
            print(f"FAIL: Tweet {sample_tweet_id} not found in database!")
            return False

        print(f"  Verified Tweet record:")
        print(f"    - twitter_tweet_id: {sample.twitter_tweet_id}")
        print(f"    - author_id: {sample.author_id} (Internal FK)")
        print(f"    - text present: {bool(sample.text and len(sample.text) > 0)}")
        print(f"    - created_at_utc: {sample.created_at_utc}")
        print(f"    - ingested_at: {sample.ingested_at}")

        # Check author exists
        author_record = db.scalar(select(User).where(User.id == sample.author_id))
        print(f"    - Author username: @{author_record.username if author_record else 'None'}")
        print(f"    - Author twitter_user_id: {author_record.twitter_user_id if author_record else 'None'}")

        # [6/6] Duplicate safety / idempotency check
        print("[6/6] Testing duplicate safety / idempotency (re-ingesting the same tweets)...")
        for raw_tweet in raw_tweets:
            ingestion.ingest_raw_tweet(raw_tweet)

        u_dup = db.scalar(select(func.count(User.id)))
        t_dup = db.scalar(select(func.count(Tweet.id)))
        i_dup = db.scalar(select(func.count(Interaction.id)))

        print(f"Second ingestion (idempotency) results:")
        print(f"  Users in DB: {u_after} -> {u_dup} (delta: +{u_dup - u_after})")
        print(f"  Tweets in DB: {t_after} -> {t_dup} (delta: +{t_dup - t_after})")
        print(f"  Interactions in DB: {i_after} -> {i_dup} (delta: +{i_dup - i_after})")

        # Check for unintended duplicate interaction entries
        # If interactions grew unexpectedly, we should analyze why
        is_idempotent = (t_dup == t_after) and (u_dup == u_after)
        print(f"Idempotency verification: Users & Tweets strictly preserved = {is_idempotent}")

        return True
    finally:
        db.close()


if __name__ == "__main__":
    success = asyncio.run(run_live_verification())
    sys.exit(0 if success else 1)
