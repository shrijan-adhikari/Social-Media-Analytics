"""Multi-query Twitter collection CLI script.

Executes configured search queries from collection_queries.yaml, tracks
provenance in PostgreSQL, and generates collection coverage summaries.
"""

import argparse
import asyncio
import logging
from pathlib import Path
import sys

# Ensure backend root is on sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from app.db.session import SessionLocal
from app.services.collection_config import load_collection_config
from app.services.multi_query_collector import (
    MultiQueryCollector,
    get_collection_coverage_report,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def print_coverage_report(db):
    """Print a clean ASCII summary table of collection coverage (§13)."""
    rows = get_collection_coverage_report(db)
    print("\n" + "=" * 95)
    print("=== COLLECTION COVERAGE & PROVENANCE REPORT ===")
    print("=" * 95)
    header = f"{'Category':<15} | {'Query Key':<25} | {'Runs':<5} | {'Retrieved':<10} | {'Unique Tweets':<14} | {'Last Collected'}"
    print(header)
    print("-" * 95)

    if not rows:
        print("No collection queries recorded yet.")
    else:
        for r in rows:
            last_ts = r["last_collected_at"].strftime("%Y-%m-%d %H:%M UTC") if r["last_collected_at"] else "Never"
            print(
                f"{r['category']:<15} | {r['query_key']:<25} | {r['total_runs']:<5} | "
                f"{r['total_retrieved']:<10} | {r['unique_tweets']:<14} | {last_ts}"
            )
    print("=" * 95 + "\n")


async def async_main():
    parser = argparse.ArgumentParser(description="Multi-query Twitter collection and provenance tracking CLI.")
    parser.add_argument(
        "--config",
        type=str,
        default=str(backend_root.parent / "config" / "collection_queries.yaml"),
        help="Path to collection_queries.yaml configuration file.",
    )
    parser.add_argument(
        "--limit-per-query",
        type=int,
        default=None,
        help="Optional override for tweet retrieval limit per query.",
    )
    parser.add_argument(
        "--query-id",
        action="append",
        dest="query_ids",
        help="Specific query ID to run. Can be specified multiple times (e.g. --query-id q1 --query-id q2).",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Display collection coverage and audit report without running collection.",
    )

    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.report:
            print_coverage_report(db)
            return

        config_path = Path(args.config)
        logger.info(f"Loading collection configuration from: {config_path}")
        config = load_collection_config(config_path)

        collector = MultiQueryCollector(db=db)
        summary = await collector.execute_collection_cycle(
            config=config,
            query_ids=args.query_ids,
            limit_override=args.limit_per_query,
        )

        # Print Safe Summary Output (no tokens, passwords, or cookies)
        print("\n" + "=" * 60)
        print("COLLECTION CYCLE SUMMARY")
        print("=" * 60)
        print(f"Queries attempted: {summary['queries_attempted']}")
        print(f"Queries succeeded: {summary['queries_succeeded']}")
        print(f"Queries failed:    {summary['queries_failed']}")
        print(f"Total retrieved:   {summary['total_retrieved']}")
        print(f"New tweets:        {summary['total_inserted']}")
        print(f"Duplicates:        {summary['total_duplicates']}")
        print("-" * 60)
        print("Per query breakdown:")
        for q_id, q_data in summary["per_query"].items():
            status_tag = q_data["status"].upper()
            err_info = f" [Error: {q_data.get('error_category')}]" if q_data["status"] != "completed" else ""
            print(
                f"  [{status_tag}] {q_id} ({q_data['category']}): "
                f"retrieved {q_data['retrieved']}, inserted {q_data['inserted']}, "
                f"duplicates {q_data['duplicates']}{err_info}"
            )
        print("=" * 60 + "\n")

    finally:
        db.close()


def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
