import argparse
import logging
import sys
from pathlib import Path

# Add backend dir to sys.path so we can import 'app'
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.analytics.sarcasm.analyzer import DatabaseSarcasmAnalyzer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Run Sarcasm detection over unanalyzed sentiment results.")
    parser.add_argument("--limit", type=int, default=100, help="Maximum number of records to process")
    args = parser.parse_args()

    logger.info(f"Connected to database. Fetching up to {args.limit} unanalyzed sentiment results...")

    
    analyzer = DatabaseSarcasmAnalyzer()
    
    results = analyzer.analyze_batch(limit=args.limit)
    
    logger.info("=== Analysis Summary ===")
    logger.info(f"Processed:     {results['processed']}")
    logger.info(f"Sarcastic:     {results['sarcastic']}")
    logger.info(f"Non-sarcastic: {results['non_sarcastic']}")
    logger.info(f"Failed:        {results['failed']}")

if __name__ == "__main__":
    main()
