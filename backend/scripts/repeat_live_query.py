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


async def repeat_search():
    query = "artificial intelligence"
    limit = 30

    collector = TwitterCollector()
    await collector.initialize()

    # Search live tweets
    raw_tweets = await collector.search_tweets(query, limit=limit)
    raw_tweets = raw_tweets[:limit]

    db: Session = SessionLocal()
    try:
        u_before = db.scalar(select(func.count(User.id)))
        t_before = db.scalar(select(func.count(Tweet.id)))
        i_before = db.scalar(select(func.count(Interaction.id)))

        ingestion = IngestionService(db)
        for rt in raw_tweets:
            ingestion.ingest_raw_tweet(rt)

        u_after = db.scalar(select(func.count(User.id)))
        t_after = db.scalar(select(func.count(Tweet.id)))
        i_after = db.scalar(select(func.count(Interaction.id)))

        print("COUNTS_REPORT:")
        print(f"  Users: {u_before} -> {u_after} (delta: +{u_after - u_before})")
        print(f"  Tweets: {t_before} -> {t_after} (delta: +{t_after - t_before})")
        print(f"  Interactions: {i_before} -> {i_after} (delta: +{i_after - i_before})")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(repeat_search())
