"""Unit tests for Phase 4 Network Analysis and Influence Topology.

Tests graph construction, PageRank, degree metrics, betweenness distance semantics,
explicit Louvain projection, bridge metrics, and database persistence.
"""

from datetime import datetime, timezone
import networkx as nx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.analytics.network.analyzer import DatabaseNetworkAnalyzer
from app.analytics.network.builder import GraphBuilder
from app.analytics.network.communities import (
    build_explicit_undirected_projection,
    compute_bridge_metrics,
    detect_communities_louvain,
)
from app.analytics.network.metrics import (
    compute_betweenness_centrality,
    compute_degree_metrics,
    compute_graph_quality,
    compute_pagerank,
)
from app.analytics.network.propagation import compute_community_flows
from app.models.interaction import Interaction, InteractionType
from app.models.network import (
    CommunityFlow,
    NetworkAnalysisRun,
    NetworkEdge,
    NetworkNode,
)
from app.models.topic import Topic, TweetTopic
from app.models.tweet import Base, Tweet
from app.models.user import User


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


# =====================================================================
# 1. Pure Algorithmic & Transformation Unit Tests
# =====================================================================

def test_explicit_undirected_louvain_projection():
    """Verify Correction 2: W{A,B} = W(A->B) + W(B->A)."""
    G = nx.DiGraph()
    G.add_edge(1, 2, weight=3.0)
    G.add_edge(2, 1, weight=2.0)
    G.add_edge(2, 3, weight=4.0)

    G_undirected = build_explicit_undirected_projection(G)

    assert not G_undirected.is_directed()
    assert G_undirected.number_of_nodes() == 3
    assert G_undirected.number_of_edges() == 2

    # Reciprocal weight must be summed: 3.0 + 2.0 = 5.0
    assert G_undirected[1][2]["weight"] == 5.0
    # Unidirectional edge preserved: 4.0
    assert G_undirected[2][3]["weight"] == 4.0

    # Original directed graph remains untouched
    assert G.is_directed()
    assert G[1][2]["weight"] == 3.0
    assert G[2][1]["weight"] == 2.0


def test_weighted_betweenness_distance_semantics():
    """Verify Correction 1: betweenness uses distance = 1.0 / weight."""
    G = nx.DiGraph()
    # Path 1: 1 -> 2 -> 3 with high interaction weight (low distance)
    # Path 2: 1 -> 4 -> 3 with low interaction weight (high distance)
    G.add_edge(1, 2, weight=10.0, distance=1.0 / 10.0)
    G.add_edge(2, 3, weight=10.0, distance=1.0 / 10.0)
    G.add_edge(1, 4, weight=1.0, distance=1.0 / 1.0)
    G.add_edge(4, 3, weight=1.0, distance=1.0 / 1.0)

    bw = compute_betweenness_centrality(G)

    # Node 2 sits on the shortest path (distance 0.2 vs distance 2.0 for node 4)
    # Therefore node 2 must have strictly higher betweenness than node 4
    assert bw[2] > bw[4]
    assert bw[4] == 0.0


def test_pagerank_and_degree_metrics():
    """Verify PageRank and in/out degree calculations."""
    G = nx.DiGraph()
    # Node 1 and Node 2 both interact with Node 3 (actor -> referenced)
    G.add_edge(1, 3, weight=2.0, distance=0.5)
    G.add_edge(2, 3, weight=5.0, distance=0.2)

    pr = compute_pagerank(G, damping=0.85)
    assert len(pr) == 3
    # Target node 3 receives all attention, so its PageRank must be highest
    assert pr[3] > pr[1]
    assert pr[3] > pr[2]

    degrees = compute_degree_metrics(G)
    assert degrees[3]["in_degree"] == 2
    assert degrees[3]["out_degree"] == 0
    assert degrees[3]["weighted_in_degree"] == 7.0
    assert degrees[1]["out_degree"] == 1
    assert degrees[1]["weighted_out_degree"] == 2.0


def test_louvain_communities_and_bridge_metrics():
    """Verify Louvain community detection and bridge metric counts."""
    G = nx.DiGraph()
    # Community A: 1, 2, 3 densely connected
    G.add_edge(1, 2, weight=5.0)
    G.add_edge(2, 1, weight=5.0)
    G.add_edge(2, 3, weight=5.0)
    G.add_edge(3, 1, weight=5.0)

    # Community B: 4, 5 densely connected
    G.add_edge(4, 5, weight=5.0)
    G.add_edge(5, 4, weight=5.0)

    # Bridge edge connecting Community A and B via node 3 and node 4
    G.add_edge(3, 4, weight=1.0)

    node_to_comm = detect_communities_louvain(G, seed=42)
    assert len(set(node_to_comm.values())) >= 2

    bridge_metrics = compute_bridge_metrics(G, node_to_comm)
    assert bridge_metrics[3]["cross_community_edge_count"] >= 1
    assert bridge_metrics[3]["communities_reached"] >= 1
    assert bridge_metrics[1]["cross_community_edge_count"] == 0


def test_community_flows():
    """Verify observed cross-community interaction flow calculation."""
    G = nx.DiGraph()
    t1 = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 9, 1, 11, 0, tzinfo=timezone.utc)

    G.add_edge(1, 2, weight=3.0, first_observed_at=t1, last_observed_at=t2)
    node_to_comm = {1: 0, 2: 1}

    flows = compute_community_flows(G, node_to_comm)
    assert len(flows) == 1
    assert flows[0]["source_community_id"] == 0
    assert flows[0]["target_community_id"] == 1
    assert flows[0]["interaction_count"] == 3
    assert flows[0]["first_observed_at"] == t1


def test_graph_quality_statistics():
    """Verify weak/strong component count and density."""
    G = nx.DiGraph()
    G.add_edge(1, 2)
    G.add_edge(3, 4)

    quality = compute_graph_quality(G)
    assert quality["node_count"] == 4
    assert quality["edge_count"] == 2
    assert quality["weak_component_count"] == 2
    assert quality["strong_component_count"] == 4
    assert quality["largest_weak_component_size"] == 2


# =====================================================================
# 2. Database Orchestration & Persistence Unit Tests
# =====================================================================

def test_database_network_analyzer_global(in_memory_db: Session):
    """Verify end-to-end global network run persistence in database."""
    # Seed users
    u1 = User(twitter_user_id="101", username="alice")
    u2 = User(twitter_user_id="102", username="bob")
    u3 = User(twitter_user_id="103", username="carol")
    in_memory_db.add_all([u1, u2, u3])
    in_memory_db.commit()

    # Seed interactions
    i1 = Interaction(
        source_user_id=u1.id,
        target_user_id=u2.id,
        interaction_type=InteractionType.REPLY,
        weight=1.0,
        timestamp_utc=datetime.now(timezone.utc),
    )
    i2 = Interaction(
        source_user_id=u1.id,
        target_user_id=u2.id,
        interaction_type=InteractionType.MENTION,
        weight=1.0,
        timestamp_utc=datetime.now(timezone.utc),
    )
    i3 = Interaction(
        source_user_id=u3.id,
        target_user_id=u2.id,
        interaction_type=InteractionType.QUOTE,
        weight=1.0,
        timestamp_utc=datetime.now(timezone.utc),
    )
    in_memory_db.add_all([i1, i2, i3])
    in_memory_db.commit()

    analyzer = DatabaseNetworkAnalyzer(in_memory_db)
    run = analyzer.run_analysis(scope_type="global")

    assert run.id is not None
    assert run.node_count == 3
    assert run.edge_count == 2  # (u1->u2) aggregated + (u3->u2)
    assert run.scope_type == "global"
    assert run.connected_user_count == 3

    # Check edges
    edges = in_memory_db.scalars(select(NetworkEdge).where(NetworkEdge.run_id == run.id)).all()
    assert len(edges) == 2
    edge_u1_u2 = next(e for e in edges if e.source_user_id == u1.id and e.target_user_id == u2.id)
    assert edge_u1_u2.total_weight == 2.0
    assert edge_u1_u2.reply_count == 1
    assert edge_u1_u2.mention_count == 1

    # Check nodes
    nodes = in_memory_db.scalars(select(NetworkNode).where(NetworkNode.run_id == run.id)).all()
    assert len(nodes) == 3
    bob_node = next(n for n in nodes if n.user_id == u2.id)
    assert bob_node.in_degree == 2
    assert bob_node.weighted_in_degree == 3.0
    assert bob_node.pagerank_score > 0.0


def test_database_network_analyzer_topic_filter(in_memory_db: Session):
    """Verify topic-specific graph filtering."""
    u1 = User(twitter_user_id="201", username="user1")
    u2 = User(twitter_user_id="202", username="user2")
    u3 = User(twitter_user_id="203", username="user3")
    in_memory_db.add_all([u1, u2, u3])
    in_memory_db.commit()

    now = datetime.now(timezone.utc)
    t1 = Tweet(twitter_tweet_id="tweet_1", author_id=u1.id, text="AI news", created_at_utc=now)
    t2 = Tweet(twitter_tweet_id="tweet_2", author_id=u3.id, text="Sports news", created_at_utc=now)
    in_memory_db.add_all([t1, t2])
    in_memory_db.commit()

    # Topic 1 = AI
    topic1 = Topic(run_id=1, label="AI Topic", topic_type="semantic", representative_terms=["ai"])
    in_memory_db.add(topic1)
    in_memory_db.commit()

    tt1 = TweetTopic(run_id=1, tweet_id=t1.id, topic_id=topic1.id, cluster_id=0, is_outlier=False)
    in_memory_db.add(tt1)
    in_memory_db.commit()

    # Interaction on AI tweet (u1 -> u2)
    i1 = Interaction(
        source_user_id=u1.id,
        target_user_id=u2.id,
        tweet_id=t1.id,
        interaction_type=InteractionType.REPLY,
        weight=1.0,
        timestamp_utc=now,
    )
    # Interaction on Sports tweet (u3 -> u2)
    i2 = Interaction(
        source_user_id=u3.id,
        target_user_id=u2.id,
        tweet_id=t2.id,
        interaction_type=InteractionType.REPLY,
        weight=1.0,
        timestamp_utc=now,
    )
    in_memory_db.add_all([i1, i2])
    in_memory_db.commit()

    analyzer = DatabaseNetworkAnalyzer(in_memory_db)
    # Run analysis only for Topic 1
    run = analyzer.run_analysis(scope_type="topic", topic_id=topic1.id)

    assert run.scope_type == "topic"
    assert run.topic_id == topic1.id
    assert run.edge_count == 1  # Only the AI tweet interaction
    assert run.node_count == 2  # u1 and u2 only
