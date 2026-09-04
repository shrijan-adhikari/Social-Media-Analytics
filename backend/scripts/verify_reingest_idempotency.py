import asyncio
import os
import sys

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.interaction import Interaction
from app.models.tweet import Tweet
from app.models.user import User
from app.services.ingestion import IngestionService
from app.services.twitter_collector import TwitterCollector


async def verify():
    collector = TwitterCollector()
    await collector.initialize()

    # Retrieve live batch
    raw_tweets = (await collector.search_tweets("technology", limit=5))[:5]
    print(f"Retrieved {len(raw_tweets)} live tweets.")

    db: Session = SessionLocal()
    try:
        ingestion = IngestionService(db)

        # Baseline before batch
        u0 = db.scalar(select(func.count(User.id)))
        t0 = db.scalar(select(func.count(Tweet.id)))
        i0 = db.scalar(select(func.count(Interaction.id)))

        # First pass of this live batch
        for rt in raw_tweets:
            ingestion.ingest_raw_tweet(rt)

        u1 = db.scalar(select(func.count(User.id)))
        t1 = db.scalar(select(func.count(Tweet.id)))
        i1 = db.scalar(select(func.count(Interaction.id)))

        print("\n--- FIRST INGESTION OF LIVE BATCH ---")
        print(f"Users: {u0} -> {u1} (delta: +{u1 - u0})")
        print(f"Tweets: {t0} -> {t1} (delta: +{t1 - t0})")
        print(f"Interactions: {i0} -> {i1} (delta: +{i1 - i0})")

        # Second pass of the exact same live batch (Testing duplicate prevention)
        for rt in raw_tweets:
            ingestion.ingest_raw_tweet(rt)

        u2 = db.scalar(select(func.count(User.id)))
        t2 = db.scalar(select(func.count(Tweet.id)))
        i2 = db.scalar(select(func.count(Interaction.id)))

        print("\n--- SECOND INGESTION OF EXACT SAME BATCH (IDEMPOTENCY TEST) ---")
        print(f"Users: {u1} -> {u2} (delta: +{u2 - u1})")
        print(f"Tweets: {t1} -> {t2} (delta: +{t2 - t1})")
        print(f"Interactions: {i1} -> {i2} (delta: +{i2 - i1})")

        print("\nSUMMARY_COUNTS:")
        print(f"Before repeat pass: Users={u1}, Tweets={t1}, Interactions={i1}")
        print(f"After repeat pass:  Users={u2}, Tweets={t2}, Interactions={i2}")
        print(f"Duplicates added:   Users=+{u2 - u1}, Tweets=+{t2 - t1}, Interactions=+{i2 - i1}")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(verify())
