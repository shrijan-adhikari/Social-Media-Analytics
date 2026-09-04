"""Database network analysis orchestrator and persistence service."""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import networkx as nx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics.network.builder import GraphBuilder
from app.analytics.network.communities import (
    compute_bridge_metrics,
    detect_communities_louvain,
)
from app.analytics.network.config import (
    DEFAULT_LOUVAIN_RESOLUTION,
    DEFAULT_LOUVAIN_SEED,
    DEFAULT_PAGERANK_DAMPING,
    DEFAULT_PAGERANK_MAX_ITER,
    DEFAULT_PAGERANK_TOL,
    NETWORK_PIPELINE_VERSION,
)
from app.analytics.network.metrics import (
    compute_betweenness_centrality,
    compute_degree_metrics,
    compute_graph_quality,
    compute_pagerank,
)
from app.analytics.network.propagation import compute_community_flows
from app.models.network import (
    CommunityFlow,
    NetworkAnalysisRun,
    NetworkEdge,
    NetworkNode,
)
from app.models.sentiment_result import SentimentResult
from app.models.topic import Topic, TweetTopic
from app.models.tweet import Tweet

logger = logging.getLogger(__name__)


class DatabaseNetworkAnalyzer:
    """Orchestrates network graph extraction, metric computation, and persistence."""

    def __init__(self, session: Session):
        self.session = session
        self.builder = GraphBuilder(session)

    def run_analysis(
        self,
        scope_type: str = "global",
        topic_id: Optional[int] = None,
        start_at: Optional[datetime] = None,
        end_at: Optional[datetime] = None,
        pagerank_damping: float = DEFAULT_PAGERANK_DAMPING,
        louvain_seed: int = DEFAULT_LOUVAIN_SEED,
        louvain_resolution: float = DEFAULT_LOUVAIN_RESOLUTION,
    ) -> NetworkAnalysisRun:
        """Execute a complete network analysis run and persist results.

        Args:
            scope_type: "global" or "topic"
            topic_id: Optional topic ID if scope_type is "topic"
            start_at: Optional start timestamp filter
            end_at: Optional end timestamp filter
            pagerank_damping: PageRank damping factor (default 0.85)
            louvain_seed: Louvain random seed for determinism (default 42)
            louvain_resolution: Louvain modularity resolution parameter (default 1.0)

        Returns:
            NetworkAnalysisRun: Persisted run record with full graph metrics.
        """
        if topic_id is not None:
            scope_type = "topic"

        logger.info(
            f"Starting Network Analysis run (scope={scope_type}, topic_id={topic_id}, "
            f"start_at={start_at}, end_at={end_at})"
        )

        # 1. Build NetworkX DiGraph from interactions
        G, user_meta = self.builder.build_graph(
            start_at=start_at,
            end_at=end_at,
            topic_id=topic_id,
        )

        # 2. Compute Graph Metrics
        graph_quality = compute_graph_quality(G)
        pagerank_scores = compute_pagerank(G, damping=pagerank_damping)
        degree_metrics = compute_degree_metrics(G)
        betweenness_scores = compute_betweenness_centrality(G)

        # 3. Community Detection & Bridge Metrics
        node_to_community = detect_communities_louvain(
            G,
            seed=louvain_seed,
            resolution=louvain_resolution,
        )
        bridge_metrics = compute_bridge_metrics(G, node_to_community)

        # 4. Observed Community Flows
        flows_data = compute_community_flows(G, node_to_community)

        # 5. Persist NetworkAnalysisRun
        algorithm_params = {
            "pagerank_damping": pagerank_damping,
            "pagerank_max_iter": DEFAULT_PAGERANK_MAX_ITER,
            "pagerank_tol": DEFAULT_PAGERANK_TOL,
            "louvain_seed": louvain_seed,
            "louvain_resolution": louvain_resolution,
            "distance_formula": "1.0 / weight",
            "louvain_projection": "W{A,B} = W(A->B) + W(B->A)",
        }

        run = NetworkAnalysisRun(
            pipeline_version=NETWORK_PIPELINE_VERSION,
            scope_type=scope_type,
            topic_id=topic_id,
            start_at=start_at,
            end_at=end_at,
            node_count=graph_quality["node_count"],
            edge_count=graph_quality["edge_count"],
            density=graph_quality["density"],
            weak_component_count=graph_quality["weak_component_count"],
            strong_component_count=graph_quality["strong_component_count"],
            largest_weak_component_size=graph_quality["largest_weak_component_size"],
            connected_user_count=user_meta["connected_users"],
            isolated_user_count=user_meta["isolated_users"],
            algorithm_params=algorithm_params,
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(run)
        self.session.flush()

        # 6. Persist NetworkNode records
        for node in G.nodes():
            deg = degree_metrics.get(node, {})
            br = bridge_metrics.get(node, {})

            node_row = NetworkNode(
                run_id=run.id,
                user_id=node,
                pagerank_score=float(pagerank_scores.get(node, 0.0)),
                in_degree=int(deg.get("in_degree", 0)),
                out_degree=int(deg.get("out_degree", 0)),
                weighted_in_degree=float(deg.get("weighted_in_degree", 0.0)),
                weighted_out_degree=float(deg.get("weighted_out_degree", 0.0)),
                betweenness_centrality=float(betweenness_scores.get(node, 0.0)),
                community_id=node_to_community.get(node),
                cross_community_edge_count=int(br.get("cross_community_edge_count", 0)),
                communities_reached=int(br.get("communities_reached", 0)),
            )
            self.session.add(node_row)

        # 7. Persist NetworkEdge records
        for u, v, data in G.edges(data=True):
            edge_row = NetworkEdge(
                run_id=run.id,
                source_user_id=u,
                target_user_id=v,
                total_weight=float(data.get("weight", 1.0)),
                reply_count=int(data.get("reply_count", 0)),
                mention_count=int(data.get("mention_count", 0)),
                repost_count=int(data.get("repost_count", 0)),
                quote_count=int(data.get("quote_count", 0)),
                first_observed_at=data.get("first_observed_at"),
                last_observed_at=data.get("last_observed_at"),
            )
            self.session.add(edge_row)

        # 8. Persist CommunityFlow records
        for flow in flows_data:
            flow_row = CommunityFlow(
                run_id=run.id,
                source_community_id=flow["source_community_id"],
                target_community_id=flow["target_community_id"],
                interaction_count=flow["interaction_count"],
                first_observed_at=flow["first_observed_at"],
                last_observed_at=flow["last_observed_at"],
            )
            self.session.add(flow_row)

        self.session.commit()
        self.session.refresh(run)

        logger.info(
            f"Completed Network Analysis run {run.id}: {run.node_count} nodes, "
            f"{run.edge_count} edges, {len(flows_data)} community flows."
        )
        return run

    def get_topic_community_sentiment_breakdown(
        self,
        run_id: int,
    ) -> List[Dict[str, Any]]:
        """Read-only join of topic, community, and sentiment (§14).

        Does NOT rerun sentiment models or topic clustering.
        Groups tweets by the author's community within the network run.
        """
        run = self.session.get(NetworkAnalysisRun, run_id)
        if not run:
            return []

        # Join NetworkNode -> Tweet -> SentimentResult
        stmt = (
            select(
                NetworkNode.community_id,
                SentimentResult.final_sentiment,
                func.count(SentimentResult.id).label("count"),
            )
            .join(Tweet, NetworkNode.user_id == Tweet.author_id)
            .join(SentimentResult, Tweet.id == SentimentResult.tweet_id)
            .where(NetworkNode.run_id == run_id)
        )

        if run.topic_id is not None:
            # Filter to tweets associated with this topic
            stmt = stmt.join(TweetTopic, Tweet.id == TweetTopic.tweet_id).where(
                TweetTopic.topic_id == run.topic_id,
                TweetTopic.is_outlier == False,
            )

        stmt = stmt.group_by(NetworkNode.community_id, SentimentResult.final_sentiment).order_by(
            NetworkNode.community_id, SentimentResult.final_sentiment
        )

        rows = self.session.execute(stmt).all()

        # Organize by community
        comm_map: Dict[int, Dict[str, Any]] = {}
        for r in rows:
            cid = r.community_id if r.community_id is not None else -1
            if cid not in comm_map:
                comm_map[cid] = {
                    "community_id": cid,
                    "positive": 0,
                    "neutral": 0,
                    "negative": 0,
                    "total": 0,
                }
            s = str(r.final_sentiment).lower()
            if "pos" in s:
                comm_map[cid]["positive"] += r.count
            elif "neg" in s:
                comm_map[cid]["negative"] += r.count
            else:
                comm_map[cid]["neutral"] += r.count
            comm_map[cid]["total"] += r.count

        return list(comm_map.values())
