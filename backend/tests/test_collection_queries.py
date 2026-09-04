"""Unit tests for multi-query configuration, collection orchestration, and provenance tracking."""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.tweet import Base, Tweet
from app.models.collection import CollectionQuery, CollectionRun, TweetCollectionSource
from app.services.collection_config import (
    CollectionConfigFile,
    CollectionQueryConfig,
    load_collection_config,
)
from app.services.ingestion import IngestionService
from app.services.multi_query_collector import (
    MultiQueryCollector,
    get_collection_coverage_report,
)


@pytest.fixture
def in_memory_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionTesting = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionTesting()
    try:
        yield db
    finally:
        db.close()


def create_mock_tweet(tweet_id: int, text: str):
    mock_user = MagicMock()
    mock_user.id = 12345
    mock_user.username = "mockuser"
    mock_user.displayname = "Mock User"
    mock_user.description = "User bio"
    mock_user.profileImageUrl = "http://example.com/pic.jpg"
    mock_user.location = "Global"
    mock_user.followersCount = 50
    mock_user.friendsCount = 20
    mock_user.statusesCount = 100
    mock_user.favouritesCount = 30
    mock_user.verified = False
    mock_user.created = datetime.now(timezone.utc)
    mock_user.dict.return_value = {"id": 12345, "username": "mockuser"}

    mock_tweet = MagicMock()
    mock_tweet.id = tweet_id
    mock_tweet.rawContent = text
    mock_tweet.date = datetime.now(timezone.utc)
    mock_tweet.conversationId = tweet_id
    mock_tweet.inReplyToTweetId = None
    mock_tweet.inReplyToUser = None
    mock_tweet.retweetedTweet = None
    mock_tweet.quotedTweet = None
    mock_tweet.mentionedUsers = []
    mock_tweet.likeCount = 5
    mock_tweet.retweetCount = 2
    mock_tweet.replyCount = 1
    mock_tweet.quoteCount = 0
    mock_tweet.bookmarkCount = 0
    mock_tweet.user = mock_user
    mock_tweet.dict.return_value = {"id": tweet_id, "text": text}
    return mock_tweet


class MockTwitterCollector:
    def __init__(self, query_responses=None):
        # query_responses maps query string -> list of MockRawTweet
        self.query_responses = query_responses or {}
        self.initialized = False

    async def initialize(self):
        self.initialized = True

    async def search_tweets(self, query: str, limit: int = 30):
        if query in self.query_responses:
            res = self.query_responses[query]
            if isinstance(res, Exception):
                raise res
            return res[:limit]
        return []


# =====================================================================
# 1. Config Loader Tests
# =====================================================================

def test_load_valid_yaml_config(tmp_path: Path):
    yaml_content = """
version: 1
queries:
  - id: artificial_intelligence
    category: technology
    query: '"artificial intelligence" OR AI'
    enabled: true
    default_limit: 25
  - id: jobs
    category: economy
    query: 'jobs OR hiring'
    enabled: false
    default_limit: 10
"""
    cfg_file = tmp_path / "queries.yaml"
    cfg_file.write_text(yaml_content, encoding="utf-8")

    config = load_collection_config(cfg_file)
    assert config.version == 1
    assert len(config.queries) == 2
    assert config.queries[0].id == "artificial_intelligence"
    assert config.queries[0].default_limit == 25
    assert config.queries[0].enabled is True

    enabled = config.get_enabled_queries()
    assert len(enabled) == 1
    assert enabled[0].id == "artificial_intelligence"


def test_reject_duplicate_query_ids(tmp_path: Path):
    yaml_content = """
version: 1
queries:
  - id: dupe_id
    category: cat1
    query: 'q1'
  - id: dupe_id
    category: cat2
    query: 'q2'
"""
    cfg_file = tmp_path / "dupes.yaml"
    cfg_file.write_text(yaml_content, encoding="utf-8")

    with pytest.raises(ValueError, match="Duplicate query IDs found"):
        load_collection_config(cfg_file)


def test_reject_invalid_limit(tmp_path: Path):
    yaml_content = """
version: 1
queries:
  - id: bad_limit
    category: cat1
    query: 'test'
    default_limit: -5
"""
    cfg_file = tmp_path / "bad_limit.yaml"
    cfg_file.write_text(yaml_content, encoding="utf-8")

    with pytest.raises(ValueError):
        load_collection_config(cfg_file)


def test_reject_malformed_yaml(tmp_path: Path):
    cfg_file = tmp_path / "malformed.yaml"
    cfg_file.write_text("not: valid: yaml: [", encoding="utf-8")

    with pytest.raises(ValueError, match="Malformed YAML"):
        load_collection_config(cfg_file)


def test_filter_subset_query_ids():
    cfg = CollectionConfigFile(
        version=1,
        queries=[
            CollectionQueryConfig(id="q1", category="c", query="t1", enabled=True),
            CollectionQueryConfig(id="q2", category="c", query="t2", enabled=True),
            CollectionQueryConfig(id="q3", category="c", query="t3", enabled=False),
        ],
    )
    filtered = cfg.get_enabled_queries(filter_ids=["q2", "q3"])
    assert len(filtered) == 1
    assert filtered[0].id == "q2"


# =====================================================================
# 2. Multi-Query Collector & Provenance Tests
# =====================================================================

@pytest.mark.asyncio
async def test_multi_query_collection_execution(in_memory_db: Session):
    config = CollectionConfigFile(
        version=1,
        queries=[
            CollectionQueryConfig(id="tech", category="technology", query="AI", enabled=True, default_limit=10),
            CollectionQueryConfig(id="econ", category="economy", query="jobs", enabled=True, default_limit=10),
        ],
    )

    t1 = create_mock_tweet(101, "AI progress is accelerating")
    t2 = create_mock_tweet(102, "New jobs report released")

    mock_collector = MockTwitterCollector({
        "AI": [t1],
        "jobs": [t2],
    })

    orchestrator = MultiQueryCollector(db=in_memory_db, collector=mock_collector)
    summary = await orchestrator.execute_collection_cycle(config)

    assert summary["queries_attempted"] == 2
    assert summary["queries_succeeded"] == 2
    assert summary["queries_failed"] == 0
    assert summary["total_retrieved"] == 2
    assert summary["total_inserted"] == 2
    assert summary["total_duplicates"] == 0

    # Verify PostgreSQL models
    queries_in_db = in_memory_db.scalars(select(CollectionQuery)).all()
    assert len(queries_in_db) == 2

    runs_in_db = in_memory_db.scalars(select(CollectionRun)).all()
    assert len(runs_in_db) == 2
    for r in runs_in_db:
        assert r.status == "completed"
        assert r.config_version == 1
        assert r.effective_query_text in ["AI", "jobs"]
        assert r.retrieved_count == 1
        assert r.inserted_count == 1
        assert r.duplicate_count == 0


@pytest.mark.asyncio
async def test_duplicate_tweet_across_multiple_queries(in_memory_db: Session):
    """Verify that a tweet retrieved by 2 queries creates 1 Tweet row but 2 provenance links."""
    config = CollectionConfigFile(
        version=1,
        queries=[
            CollectionQueryConfig(id="ai_query", category="technology", query="AI", enabled=True),
            CollectionQueryConfig(id="jobs_query", category="economy", query="jobs", enabled=True),
        ],
    )

    # Shared tweet about AI jobs
    shared_tweet = create_mock_tweet(999, "AI will transform software engineering jobs")

    mock_collector = MockTwitterCollector({
        "AI": [shared_tweet],
        "jobs": [shared_tweet],
    })

    orchestrator = MultiQueryCollector(db=in_memory_db, collector=mock_collector)
    summary = await orchestrator.execute_collection_cycle(config)

    assert summary["total_retrieved"] == 2
    assert summary["total_inserted"] == 1
    assert summary["total_duplicates"] == 1

    # Exactly ONE tweet in the database
    tweets = in_memory_db.scalars(select(Tweet)).all()
    assert len(tweets) == 1
    assert tweets[0].twitter_tweet_id == "999"

    # TWO provenance links in tweet_collection_sources
    sources = in_memory_db.scalars(select(TweetCollectionSource)).all()
    assert len(sources) == 2
    run_ids = {s.collection_run_id for s in sources}
    assert len(run_ids) == 2  # Linked to both distinct runs


@pytest.mark.asyncio
async def test_failure_isolation_per_query(in_memory_db: Session):
    """Verify that one failing query does not prevent subsequent queries from running."""
    config = CollectionConfigFile(
        version=1,
        queries=[
            CollectionQueryConfig(id="failing_query", category="cat1", query="error_query", enabled=True),
            CollectionQueryConfig(id="healthy_query", category="cat2", query="healthy_query", enabled=True),
        ],
    )

    t_healthy = create_mock_tweet(202, "Healthy tweet content")

    mock_collector = MockTwitterCollector({
        "error_query": RuntimeError("Simulated network timeout connecting to X"),
        "healthy_query": [t_healthy],
    })

    orchestrator = MultiQueryCollector(db=in_memory_db, collector=mock_collector)
    summary = await orchestrator.execute_collection_cycle(config)

    assert summary["queries_attempted"] == 2
    assert summary["queries_succeeded"] == 1
    assert summary["queries_failed"] == 1
    assert summary["total_inserted"] == 1

    # Check statuses in database
    runs = in_memory_db.scalars(select(CollectionRun).order_by(CollectionRun.id)).all()
    assert len(runs) == 2
    assert runs[0].status == "failed"
    assert runs[0].error_category in ["network_timeout", "unexpected_error"]
    assert runs[1].status == "completed"
    assert runs[1].inserted_count == 1


def test_coverage_report(in_memory_db: Session):
    """Verify read-only coverage summary generation (§13)."""
    q1 = CollectionQuery(query_key="q1", category="tech", query_text="txt1", is_enabled=True, default_limit=10)
    in_memory_db.add(q1)
    in_memory_db.commit()

    run = CollectionRun(
        query_id=q1.id,
        config_version=1,
        effective_query_text="txt1",
        requested_limit=10,
        retrieved_count=5,
        inserted_count=5,
        status="completed",
        completed_at=datetime.now(timezone.utc),
    )
    in_memory_db.add(run)
    in_memory_db.commit()

    report = get_collection_coverage_report(in_memory_db)
    assert len(report) == 1
    assert report[0]["query_key"] == "q1"
    assert report[0]["category"] == "tech"
    assert report[0]["total_runs"] == 1
    assert report[0]["total_retrieved"] == 5
