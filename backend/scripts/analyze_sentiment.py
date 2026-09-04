"""CLI tool to analyze sentiment of unanalyzed tweets in the database."""

import argparse
import logging
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure backend root is in sys.path
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings
from app.analytics.sentiment.analyzer import DatabaseSentimentAnalyzer

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Run sentiment analysis on stored tweets.")
    parser.add_argument("--limit", type=int, default=10, help="Max number of tweets to analyze.")
    args = parser.parse_args()

    settings = get_settings()
    engine = create_engine(str(settings.DATABASE_URL))
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    with SessionLocal() as session:
        logger.info(f"Connected to database. Fetching up to {args.limit} unanalyzed tweets...")
        analyzer = DatabaseSentimentAnalyzer(session)
        
        results = analyzer.analyze_batch(limit=args.limit)
        
        logger.info("=== Analysis Summary ===")
        logger.info(f"Analyzed: {results['analyzed']}")
        logger.info(f"Positive: {results['positive']}")
        logger.info(f"Neutral:  {results['neutral']}")
        logger.info(f"Negative: {results['negative']}")
        logger.info(f"Failed:   {results['failed']}")


if __name__ == "__main__":
    main()
