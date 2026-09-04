"""Unit and integration tests for FastAPI v1 read endpoints."""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import get_db
from app.main import create_app
from app.models.interaction import Interaction, InteractionType
from app.models.network import (
    CommunityFlow,
    NetworkAnalysisRun,
    NetworkEdge,
    NetworkNode,
)
from app.models.sentiment_result import SentimentResult
from app.models.topic import Topic, TrendAnalysisRun, TrendWindow, TweetTopic
from app.models.tweet import Base, Tweet
from app.models.user import User


@pytest.fixture
def test_db():
    """Create an isolated in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(test_db: Session):
    """FastAPI TestClient with overridden get_db dependency."""
    app = create_app()

    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def populated_db(test_db: Session):
    """Seed sample data across all analytical pipeline tables."""
    now = datetime.now(timezone.utc)

    # 1. Users
    u1 = User(twitter_user_id="1001", username="alice", display_name="Alice")
    u2 = User(twitter_user_id="1002", username="bob", display_name="Bob")
    test_db.add_all([u1, u2])
    test_db.commit()

    # 2. Tweets
    t1 = Tweet(
        twitter_tweet_id="2001",
        author_id=u1.id,
        text="Loving this new AI development!",
        created_at_utc=now,
        like_count=10,
        retweet_count=2,
    )
    t2 = Tweet(
        twitter_tweet_id="2002",
        author_id=u2.id,
        text="Oh wonderful, another hiring freeze.",
        created_at_utc=now,
        like_count=5,
        retweet_count=1,
    )
    test_db.add_all([t1, t2])
    test_db.commit()

    # 3. Interactions
    i1 = Interaction(
        source_user_id=u1.id,
        target_user_id=u2.id,
        tweet_id=t1.id,
        interaction_type=InteractionType.REPLY,
        weight=1.0,
        timestamp_utc=now,
    )
    test_db.add(i1)
    test_db.commit()

    # 4. Sentiment Results
    s1 = SentimentResult(
        tweet_id=t1.id,
        model_id="cardiffnlp/twitter-xlm-roberta-base-sentiment",
        pipeline_version="1.0.0",
        negative_probability=0.03,
        neutral_probability=0.02,
        positive_probability=0.95,
        base_sentiment="positive",
        base_confidence=0.95,
        final_sentiment="positive",
        final_confidence=0.95,
        sarcasm_probability=0.12,
        fusion_status="NO_SARCASM",
        analyzed_at=now,
    )
    s2 = SentimentResult(
        tweet_id=t2.id,
        model_id="cardiffnlp/twitter-xlm-roberta-base-sentiment",
        pipeline_version="1.0.0",
        negative_probability=0.08,
        neutral_probability=0.10,
        positive_probability=0.82,
        base_sentiment="positive",
        base_confidence=0.82,
        final_sentiment="negative",
        final_confidence=0.74,
        sarcasm_probability=0.91,
        fusion_status="SARCASM_CONSISTENT",
        analyzed_at=now,
    )
    test_db.add_all([s1, s2])
    test_db.commit()

    # 5. Trend Analysis Run & Topics
    tr1 = TrendAnalysisRun(
        pipeline_version="1.0.0",
        dataset_tweet_count=2,
        window_minutes=15,
        embedding_model_id="sentence-transformers/all-MiniLM-L6-v2",
        clustering_params={"algorithm": "HDBSCAN"},
        created_at=now,
    )
    test_db.add(tr1)
    test_db.commit()

    top1 = Topic(
        run_id=tr1.id,
        label="ai / intelligence",
        topic_type="semantic",
        representative_terms=["ai", "intelligence", "models"],
        created_at=now,
    )
    test_db.add(top1)
    test_db.commit()

    tt1 = TweetTopic(
        run_id=tr1.id,
        tweet_id=t1.id,
        topic_id=top1.id,
        cluster_id=0,
        is_outlier=False,
        assigned_at=now,
    )
    test_db.add(tt1)
    test_db.commit()

    tw1 = TrendWindow(
        run_id=tr1.id,
        topic_id=top1.id,
        window_start=now,
        window_end=now,
        mention_count=15,
        baseline_mentions=3.2,
        velocity=4.69,
        acceleration=1.2,
        like_count=20,
        repost_count=5,
        reply_count=2,
    )
    test_db.add(tw1)
    test_db.commit()

    # 6. Network Analysis Runs (Global and Topic)
    nr_global = NetworkAnalysisRun(
        pipeline_version="1.0.0",
        scope_type="global",
        topic_id=None,
        node_count=2,
        edge_count=1,
        density=0.5,
        weak_component_count=1,
        strong_component_count=2,
        largest_weak_component_size=2,
        connected_user_count=2,
        isolated_user_count=0,
        algorithm_params={"pagerank_damping": 0.85},
        created_at=now,
    )
    nr_topic = NetworkAnalysisRun(
        pipeline_version="1.0.0",
        scope_type="topic",
        topic_id=top1.id,
        node_count=2,
        edge_count=1,
        density=0.5,
        weak_component_count=1,
        strong_component_count=2,
        largest_weak_component_size=2,
        connected_user_count=2,
        isolated_user_count=0,
        algorithm_params={"pagerank_damping": 0.85},
        created_at=now,
    )
    test_db.add_all([nr_global, nr_topic])
    test_db.commit()

    # Global Nodes & Edges
    nn1 = NetworkNode(
        run_id=nr_global.id,
        user_id=u1.id,
        pagerank_score=0.45,
        in_degree=0,
        out_degree=1,
        weighted_in_degree=0.0,
        weighted_out_degree=1.0,
        betweenness_centrality=0.0,
        community_id=0,
        cross_community_edge_count=0,
        communities_reached=0,
    )
    nn2 = NetworkNode(
        run_id=nr_global.id,
        user_id=u2.id,
        pagerank_score=0.55,
        in_degree=1,
        out_degree=0,
        weighted_in_degree=1.0,
        weighted_out_degree=0.0,
        betweenness_centrality=0.0,
        community_id=0,
        cross_community_edge_count=0,
        communities_reached=0,
    )
    ne1 = NetworkEdge(
        run_id=nr_global.id,
        source_user_id=u1.id,
        target_user_id=u2.id,
        total_weight=1.0,
        reply_count=1,
    )
    test_db.add_all([nn1, nn2, ne1])

    # Topic Nodes & Edges
    tn1 = NetworkNode(
        run_id=nr_topic.id,
        user_id=u1.id,
        pagerank_score=0.45,
        in_degree=0,
        out_degree=1,
        weighted_in_degree=0.0,
        weighted_out_degree=1.0,
        betweenness_centrality=0.0,
        community_id=0,
    )
    tn2 = NetworkNode(
        run_id=nr_topic.id,
        user_id=u2.id,
        pagerank_score=0.55,
        in_degree=1,
        out_degree=0,
        weighted_in_degree=1.0,
        weighted_out_degree=0.0,
        betweenness_centrality=0.0,
        community_id=0,
    )
    te1 = NetworkEdge(
        run_id=nr_topic.id,
        source_user_id=u1.id,
        target_user_id=u2.id,
        total_weight=1.0,
        reply_count=1,
    )
    test_db.add_all([tn1, tn2, te1])
    test_db.commit()

    return {
        "user1": u1,
        "user2": u2,
        "tweet1": t1,
        "tweet2": t2,
        "topic": top1,
        "trend_run": tr1,
        "net_global": nr_global,
        "net_topic": nr_topic,
    }


# =====================================================================
# Tests for Endpoints
# =====================================================================

def test_overview_endpoint(client: TestClient, populated_db: dict):
    """Verify GET /api/v1/overview returns accurate aggregates."""
    res = client.get("/api/v1/overview")
    assert res.status_code == 200
    data = res.json()

    assert data["dataset"]["total_tweets"] == 2
    assert data["dataset"]["total_users"] == 2
    assert data["dataset"]["total_interactions"] == 1
    assert data["analysis_coverage"]["sentiment_analyzed"] == 2
    assert data["analysis_coverage"]["topic_assigned"] == 1

    # Sentiment percentages: 1 pos (50%), 1 neg (50%), 0 neu
    assert data["sentiment"]["positive_percentage"] == 50.0
    assert data["sentiment"]["negative_percentage"] == 50.0
    assert data["sentiment"]["neutral_percentage"] == 0.0

    # Top emerging topic
    assert data["top_emerging_topic"]["label"] == "ai / intelligence"
    assert data["top_emerging_topic"]["velocity"] == 4.69

    # Network overview
    assert data["network"]["connected_users"] == 2
    assert data["network"]["edges"] == 1


def test_tweets_endpoint_pagination_and_filtering(client: TestClient, populated_db: dict):
    """Verify GET /api/v1/tweets pagination, topic filtering, and sentiment filtering."""
    # 1. All tweets
    res = client.get("/api/v1/tweets?page=1&page_size=10")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2

    # Verify tweet item structure
    item = data["items"][0]
    assert "username" in item
    assert "sentiment" in item
    assert item["sentiment"]["final_sentiment"] in ["positive", "negative"]

    # 2. Topic filter
    top_id = populated_db["topic"].id
    res_topic = client.get(f"/api/v1/tweets?topic_id={top_id}")
    assert res_topic.status_code == 200
    assert res_topic.json()["total"] == 1
    assert res_topic.json()["items"][0]["topic"]["topic_id"] == top_id

    # 3. Sentiment filter
    res_sent = client.get("/api/v1/tweets?sentiment=negative")
    assert res_sent.status_code == 200
    assert res_sent.json()["total"] == 1
    assert res_sent.json()["items"][0]["sentiment"]["final_sentiment"] == "negative"

    # 4. User filter (Related Tweets feature)
    u1_id = populated_db["user1"].id
    res_user = client.get(f"/api/v1/tweets?user_id={u1_id}")
    assert res_user.status_code == 200
    assert res_user.json()["total"] == 1
    assert res_user.json()["items"][0]["username"] == "alice"


def test_sentiment_summary_and_timeline(client: TestClient, populated_db: dict):
    """Verify GET /api/v1/sentiment/summary and /timeline endpoints."""
    # Summary
    res_sum = client.get("/api/v1/sentiment/summary")
    assert res_sum.status_code == 200
    sum_data = res_sum.json()
    assert sum_data["total_analyzed"] == 2
    assert sum_data["positive"]["count"] == 1
    assert sum_data["negative"]["count"] == 1
    assert sum_data["sarcasm"]["high_evidence_count"] == 1
    assert sum_data["sarcasm"]["sarcasm_consistent_count"] == 1

    # Timeline
    res_time = client.get("/api/v1/sentiment/timeline?interval=4h")
    assert res_time.status_code == 200
    time_data = res_time.json()
    assert len(time_data["points"]) >= 1
    assert time_data["points"][0]["total"] == 2


def test_trends_endpoints(client: TestClient, populated_db: dict):
    """Verify GET /api/v1/trends, detail, timeline, and sentiment."""
    top_id = populated_db["topic"].id

    # 1. Trends list
    res_list = client.get("/api/v1/trends")
    assert res_list.status_code == 200
    list_data = res_list.json()
    assert len(list_data["topics"]) == 1
    top_item = list_data["topics"][0]
    assert top_item["label"] == "ai / intelligence"
    assert top_item["velocity"] == 4.69
    assert "models" in top_item["representative_terms"]

    # 2. Detail
    res_det = client.get(f"/api/v1/trends/{top_id}")
    assert res_det.status_code == 200
    assert res_det.json()["label"] == "ai / intelligence"

    # 3. Timeline
    res_tl = client.get(f"/api/v1/trends/{top_id}/timeline")
    assert res_tl.status_code == 200
    assert len(res_tl.json()["points"]) == 1
    assert res_tl.json()["points"][0]["mention_count"] == 15

    # 4. Sentiment join
    res_ts = client.get(f"/api/v1/trends/{top_id}/sentiment")
    assert res_ts.status_code == 200
    assert res_ts.json()["positive"] == 1
    assert res_ts.json()["negative"] == 0

    # 5. Non-existent topic
    res_404 = client.get("/api/v1/trends/99999")
    assert res_404.status_code == 404


def test_network_endpoints_global_and_topic(client: TestClient, populated_db: dict):
    """Verify GET /api/v1/network/* endpoints and topic network fallback."""
    # 1. Global summary
    res_sum = client.get("/api/v1/network/summary")
    assert res_sum.status_code == 200
    assert res_sum.json()["node_count"] == 2
    assert res_sum.json()["edge_count"] == 1

    # 2. Nodes
    res_nodes = client.get("/api/v1/network/nodes?limit=10")
    assert res_nodes.status_code == 200
    nodes = res_nodes.json()
    assert len(nodes) == 2
    assert nodes[0]["pagerank_score"] >= nodes[1]["pagerank_score"]

    # 3. Edges
    res_edges = client.get("/api/v1/network/edges?limit=10")
    assert res_edges.status_code == 200
    edges = res_edges.json()
    assert len(edges) == 1
    assert edges[0]["source_username"] == "alice"
    assert edges[0]["target_username"] == "bob"

    # 4. Topic network (available)
    top_id = populated_db["topic"].id
    res_tnet = client.get(f"/api/v1/trends/{top_id}/network")
    assert res_tnet.status_code == 200
    tnet_data = res_tnet.json()
    assert tnet_data["available"] is True
    assert len(tnet_data["nodes"]) == 2

    # 5. Topic network fallback (topic with no network run)
    new_top = Topic(
        run_id=populated_db["trend_run"].id,
        label="empty topic",
        topic_type="semantic",
        representative_terms=["empty"],
    )
    populated_db["trend_run"]  # keep session active
    session = Session.object_session(populated_db["topic"])
    session.add(new_top)
    session.commit()

    res_empty_tnet = client.get(f"/api/v1/trends/{new_top.id}/network")
    assert res_empty_tnet.status_code == 200
    assert res_empty_tnet.json()["available"] is False
    assert res_empty_tnet.json()["reason"] == "NO_TOPIC_NETWORK_ANALYSIS"


def test_analysis_status_endpoint(client: TestClient, populated_db: dict):
    """Verify GET /api/v1/analysis/status reports real readiness across all 8 dimensions."""
    res = client.get("/api/v1/analysis/status")
    assert res.status_code == 200
    data = res.json()

    assert data["collection"]["status"] == "ready"
    assert data["collection"]["records_count"] == 2
    assert data["sentiment"]["status"] == "ready"
    assert data["sentiment"]["records_count"] == 2
    assert data["sarcasm"]["status"] == "ready"
    assert data["trends"]["status"] == "ready"
    assert data["network"]["status"] == "ready"

    # Unimplemented dimensions explicitly marked
    assert data["demographics"]["status"] == "not_implemented"
    assert data["demographics"]["is_available"] is False
    assert data["emotion"]["status"] == "not_implemented"
    assert data["stance"]["status"] == "not_implemented"
