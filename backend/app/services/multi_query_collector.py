"""Multi-query Twitter collection orchestrator with provenance tracking.

Reuses existing Phase 1 TwitterCollector and IngestionService without
duplicating collection or normalization logic.
"""

from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional, Tuple
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.collection import CollectionQuery, CollectionRun, TweetCollectionSource
from app.models.tweet import Tweet
from app.services.collection_config import CollectionConfigFile, CollectionQueryConfig
from app.services.ingestion import IngestionService
from app.services.twitter_collector import TwitterCollector

logger = logging.getLogger(__name__)


class MultiQueryCollector:
    """Coordinates executing configured search queries and persisting collection provenance."""

    def __init__(
        self,
        db: Session,
        collector: Optional[TwitterCollector] = None,
        ingestion: Optional[IngestionService] = None,
    ):
        self.db = db
        self.collector = collector or TwitterCollector()
        self.ingestion = ingestion or IngestionService(db)

    def sync_query_definitions(self, config: CollectionConfigFile) -> Dict[str, CollectionQuery]:
        """Ensure all queries defined in the YAML file exist in PostgreSQL collection_queries table."""
        key_to_model: Dict[str, CollectionQuery] = {}

        for q_cfg in config.queries:
            stmt = select(CollectionQuery).where(CollectionQuery.query_key == q_cfg.id)
            query_row = self.db.scalar(stmt)

            if not query_row:
                query_row = CollectionQuery(
                    query_key=q_cfg.id,
                    category=q_cfg.category,
                    query_text=q_cfg.query,
                    is_enabled=q_cfg.enabled,
                    default_limit=q_cfg.default_limit,
                )
                self.db.add(query_row)
            else:
                # Update existing definition if config changed
                query_row.category = q_cfg.category
                query_row.query_text = q_cfg.query
                query_row.is_enabled = q_cfg.enabled
                query_row.default_limit = q_cfg.default_limit

            key_to_model[q_cfg.id] = query_row

        self.db.commit()
        for k, v in key_to_model.items():
            self.db.refresh(v)
        return key_to_model

    async def execute_collection_cycle(
        self,
        config: CollectionConfigFile,
        query_ids: Optional[List[str]] = None,
        limit_override: Optional[int] = None,
    ) -> dict:
        """Run a collection cycle across enabled queries.

        Args:
            config: Validated CollectionConfigFile.
            query_ids: Optional list of query IDs to execute (subset execution).
            limit_override: Optional override for requested limit per query.

        Returns:
            dict: Safe summary of the collection cycle.
        """
        # Ensure twscrape session initialized
        await self.collector.initialize()

        # 1. Sync query metadata to DB
        query_models = self.sync_query_definitions(config)

        # 2. Select target queries
        target_queries = config.get_enabled_queries(filter_ids=query_ids)
        if not target_queries:
            logger.warning("No enabled queries matched the selection criteria.")
            return {
                "queries_attempted": 0,
                "queries_succeeded": 0,
                "queries_failed": 0,
                "total_retrieved": 0,
                "total_inserted": 0,
                "total_duplicates": 0,
                "per_query": {},
            }

        summary = {
            "queries_attempted": len(target_queries),
            "queries_succeeded": 0,
            "queries_failed": 0,
            "total_retrieved": 0,
            "total_inserted": 0,
            "total_duplicates": 0,
            "per_query": {},
        }

        # 3. Iterate queries with per-query failure isolation
        for q_cfg in target_queries:
            query_row = query_models[q_cfg.id]
            limit = limit_override or q_cfg.default_limit

            logger.info(f"Starting collection for [{q_cfg.id}] (limit: {limit}): '{q_cfg.query}'")

            # Initialize CollectionRun record with config version and effective query text
            run = CollectionRun(
                query_id=query_row.id,
                config_version=config.version,
                effective_query_text=q_cfg.query,
                requested_limit=limit,
                started_at=datetime.now(timezone.utc),
                status="running",
            )
            self.db.add(run)
            self.db.commit()
            self.db.refresh(run)

            q_retrieved = 0
            q_inserted = 0
            q_duplicates = 0

            try:
                # Perform live search via existing TwitterCollector
                raw_tweets = await self.collector.search_tweets(q_cfg.query, limit=limit)
                q_retrieved = len(raw_tweets)

                for raw_tweet in raw_tweets:
                    # Check if tweet is already in DB before ingestion to distinguish new vs duplicate
                    tweet_exists_stmt = select(Tweet).where(Tweet.twitter_tweet_id == str(raw_tweet.id))
                    existing_tweet = self.db.scalar(tweet_exists_stmt)

                    # Ingest tweet using existing IngestionService (idempotent, avoids duplicate tweet rows)
                    author, tweet_entity, _ = self.ingestion.ingest_raw_tweet(raw_tweet)

                    if existing_tweet is None:
                        q_inserted += 1
                    else:
                        q_duplicates += 1

                    # Record collection provenance link (many-to-many relationship)
                    # Unique constraint ensures no duplicate link within same run
                    source_stmt = select(TweetCollectionSource).where(
                        TweetCollectionSource.tweet_id == tweet_entity.id,
                        TweetCollectionSource.collection_run_id == run.id,
                    )
                    if not self.db.scalar(source_stmt):
                        source_link = TweetCollectionSource(
                            tweet_id=tweet_entity.id,
                            collection_run_id=run.id,
                        )
                        self.db.add(source_link)

                # Commit batch and mark run completed
                run.retrieved_count = q_retrieved
                run.inserted_count = q_inserted
                run.duplicate_count = q_duplicates
                run.status = "completed"
                run.completed_at = datetime.now(timezone.utc)
                self.db.commit()

                summary["queries_succeeded"] += 1
                summary["total_retrieved"] += q_retrieved
                summary["total_inserted"] += q_inserted
                summary["total_duplicates"] += q_duplicates
                summary["per_query"][q_cfg.id] = {
                    "category": q_cfg.category,
                    "retrieved": q_retrieved,
                    "inserted": q_inserted,
                    "duplicates": q_duplicates,
                    "status": "completed",
                }
                logger.info(f"Completed [{q_cfg.id}]: retrieved {q_retrieved}, new {q_inserted}, duplicates {q_duplicates}")

            except Exception as e:
                err_str = str(e)
                logger.error(f"Collection failed for query [{q_cfg.id}]: {err_str}")
                
                # Determine safe, non-sensitive error category
                if "403" in err_str or "unauthorized" in err_str.lower() or "login" in err_str.lower():
                    err_cat = "auth_failure"
                elif "429" in err_str or "rate" in err_str.lower():
                    err_cat = "rate_limit"
                elif "timeout" in err_str.lower() or "connect" in err_str.lower():
                    err_cat = "network_timeout"
                else:
                    err_cat = "unexpected_error"

                run.retrieved_count = q_retrieved
                run.inserted_count = q_inserted
                run.duplicate_count = q_duplicates
                run.status = "failed"
                run.error_category = err_cat
                run.completed_at = datetime.now(timezone.utc)
                self.db.commit()

                summary["queries_failed"] += 1
                summary["per_query"][q_cfg.id] = {
                    "category": q_cfg.category,
                    "retrieved": q_retrieved,
                    "inserted": q_inserted,
                    "duplicates": q_duplicates,
                    "status": "failed",
                    "error_category": err_cat,
                }

                # Authentication-wide failure: stop cleanly rather than spamming X
                if err_cat == "auth_failure":
                    logger.critical("Authentication failure encountered. Stopping collection cycle to prevent account lock.")
                    break

        return summary


def get_collection_coverage_report(db: Session) -> List[dict]:
    """Generate a read-only audit report of collection coverage across queries (§13)."""
    # Subquery for run aggregates per query
    runs_subq = (
        select(
            CollectionRun.query_id,
            func.count(CollectionRun.id).label("total_runs"),
            func.coalesce(func.sum(CollectionRun.retrieved_count), 0).label("total_retrieved"),
            func.max(CollectionRun.completed_at).label("last_collected_at"),
        )
        .group_by(CollectionRun.query_id)
        .subquery()
    )

    # Subquery for distinct unique tweets per query
    tweets_subq = (
        select(
            CollectionRun.query_id,
            func.count(func.distinct(TweetCollectionSource.tweet_id)).label("unique_tweets"),
        )
        .join(TweetCollectionSource, CollectionRun.id == TweetCollectionSource.collection_run_id)
        .group_by(CollectionRun.query_id)
        .subquery()
    )

    stmt = (
        select(
            CollectionQuery.query_key,
            CollectionQuery.category,
            func.coalesce(runs_subq.c.total_runs, 0).label("total_runs"),
            func.coalesce(runs_subq.c.total_retrieved, 0).label("total_retrieved"),
            func.coalesce(tweets_subq.c.unique_tweets, 0).label("unique_tweets"),
            runs_subq.c.last_collected_at,
        )
        .outerjoin(runs_subq, CollectionQuery.id == runs_subq.c.query_id)
        .outerjoin(tweets_subq, CollectionQuery.id == tweets_subq.c.query_id)
        .order_by(CollectionQuery.category, CollectionQuery.query_key)
    )

    rows = db.execute(stmt).all()
    report = []
    for r in rows:
        report.append({
            "query_key": r.query_key,
            "category": r.category,
            "total_runs": r.total_runs,
            "total_retrieved": r.total_retrieved,
            "unique_tweets": r.unique_tweets,
            "last_collected_at": r.last_collected_at,
        })
    return report
