import argparse
import asyncio
import os
import sys

# Ensure backend directory is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.ingestion import IngestionService
from app.services.twitter_collector import TwitterCollector


async def main():
    parser = argparse.ArgumentParser(description="Ingest Twitter data into PostgreSQL")
    parser.add_argument("--query", type=str, help="Search query or hashtag (e.g. #tech)")
    parser.add_argument("--user", type=str, help="Twitter username to ingest")
    parser.add_argument(
        "--limit", type=int, default=10, help="Max tweets to fetch (default: 10, limit 10-20)"
    )
    args = parser.parse_args()

    if not args.query and not args.user:
        print("Error: must provide either --query or --user")
        sys.exit(1)

    settings = get_settings()

    if not SessionLocal:
        print("Error: DATABASE_URL not configured.")
        sys.exit(1)

    collector = TwitterCollector()
    await collector.initialize()

    raw_tweets = []
    if args.query:
        print(f"Searching tweets for query: '{args.query}' (limit: {args.limit})...")
        raw_tweets = await collector.search_tweets(args.query, limit=args.limit)
    elif args.user:
        print(f"Fetching user profile for: @{args.user}...")
        raw_user = await collector.get_user_by_login(args.user)
        if not raw_user:
            print(f"Error: User @{args.user} not found.")
            sys.exit(1)
        print(f"Fetching up to {args.limit} tweets for user ID {raw_user.id}...")
        raw_tweets = await collector.get_user_tweets(raw_user.id, limit=args.limit)

    if not raw_tweets:
        print("No tweets returned.")
        return

    print(f"Fetched {len(raw_tweets)} tweets. Ingesting into PostgreSQL...")
    db: Session = SessionLocal()
    try:
        ingestion = IngestionService(db)
        total_tweets = 0
        total_interactions = 0

        for raw_tweet in raw_tweets:
            author, tweet, interactions = ingestion.ingest_raw_tweet(raw_tweet)
            total_tweets += 1
            total_interactions += len(interactions)

        print(
            f"Successfully ingested {total_tweets} tweets and {total_interactions} interactions into PostgreSQL."
        )
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
