import asyncio
import os
import sys

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, backend_dir)

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.services.ingestion import IngestionService
from app.services.twitter_collector import TwitterCollector

TOPICS = ["politics", "gaming", "movies", "technology", "artificial intelligence"]
PER_TOPIC_LIMIT = 20

async def main():
    collector = TwitterCollector()
    await collector.initialize()

    db: Session = SessionLocal()
    ingestion = IngestionService(db)
    
    total_new_tweets = 0
    total_interactions = 0

    print(f"Starting multi-topic collection across: {TOPICS} (target: {PER_TOPIC_LIMIT} per topic)...")

    try:
        for topic in TOPICS:
            print(f"Searching tweets for '{topic}'...")
            try:
                raw_tweets = await collector.search_tweets(topic, limit=PER_TOPIC_LIMIT)
                topic_tweets = 0
                topic_interactions = 0
                for rt in raw_tweets:
                    author, tweet, interactions = ingestion.ingest_raw_tweet(rt)
                    topic_tweets += 1
                    topic_interactions += len(interactions)
                print(f"  -> Ingested {topic_tweets} tweets and {topic_interactions} interactions for '{topic}'.")
                total_new_tweets += topic_tweets
                total_interactions += topic_interactions
            except Exception as e:
                print(f"  -> Error collecting '{topic}': {e}")
                
        print(f"\nCompleted multi-topic collection! Total processed: {total_new_tweets} tweets, {total_interactions} interactions.")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
