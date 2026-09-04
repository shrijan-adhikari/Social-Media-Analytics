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


async def run_live_search_and_ingest():
    query = "technology"
    limit = 5

    print(f"Starting LIVE collection for query '{query}' (limit: {limit})...")
    collector = TwitterCollector()
    await collector.initialize()

    # Perform live search via twscrape
    raw_tweets = await collector.search_tweets(query, limit=limit)
    raw_tweets = raw_tweets[:limit]
    num_retrieved = len(raw_tweets)
    print(f"LIVE tweets retrieved: {num_retrieved}")

    if not raw_tweets:
        print("ERROR: Zero live tweets retrieved from X.")
        return {
            "retrieval_mode": "LIVE",
            "query": query,
            "retrieved_count": 0,
            "users_persisted": 0,
            "tweets_persisted": 0,
            "interactions_persisted": 0,
            "error": "No tweets returned from X search query.",
        }

    # Ingest into PostgreSQL
    db: Session = SessionLocal()
    try:
        u_before = db.scalar(select(func.count(User.id)))
        t_before = db.scalar(select(func.count(Tweet.id)))
        i_before = db.scalar(select(func.count(Interaction.id)))

        ingestion = IngestionService(db)
        total_interactions = 0

        for rt in raw_tweets:
            author, tweet, interactions = ingestion.ingest_raw_tweet(rt)
            total_interactions += len(interactions)

        u_after = db.scalar(select(func.count(User.id)))
        t_after = db.scalar(select(func.count(Tweet.id)))
        i_after = db.scalar(select(func.count(Interaction.id)))

        users_persisted = u_after - u_before
        tweets_persisted = t_after - t_before
        interactions_persisted = i_after - i_before

        print(f"Users delta in DB: +{users_persisted} (Total in DB: {u_after})")
        print(f"Tweets delta in DB: +{tweets_persisted} (Total in DB: {t_after})")
        print(f"Interactions delta in DB: +{interactions_persisted} (Total in DB: {i_after})")

        return {
            "retrieval_mode": "LIVE",
            "query": query,
            "retrieved_count": num_retrieved,
            "users_persisted": users_persisted,
            "tweets_persisted": tweets_persisted,
            "interactions_persisted": interactions_persisted,
            "total_users_in_db": u_after,
            "total_tweets_in_db": t_after,
            "total_interactions_in_db": i_after,
            "error": None,
        }
    finally:
        db.close()


if __name__ == "__main__":
    result = asyncio.run(run_live_search_and_ingest())
    print("\nSUMMARY_RESULT:")
    for k, v in result.items():
        print(f"  {k}: {v}")
