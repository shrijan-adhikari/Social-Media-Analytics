"""Network Analysis & Influence Topology CLI script (Phase 4).

Computes PageRank, degree centrality, Louvain communities, betweenness bridges,
and observed cross-community interaction flows.
"""

import argparse
from datetime import datetime, timedelta, timezone
import logging
from pathlib import Path
import sys

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import func, select
from app.analytics.network import DatabaseNetworkAnalyzer
from app.db.session import SessionLocal
from app.models.network import (
    CommunityFlow,
    NetworkAnalysisRun,
    NetworkEdge,
    NetworkNode,
)
from app.models.topic import Topic
from app.models.user import User

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Phase 4 Network Analysis & Influence Topology CLI."
    )
    parser.add_argument(
        "--topic-id",
        type=int,
        default=None,
        help="Optional topic ID for topic-specific network analysis.",
    )
    parser.add_argument(
        "--hours",
        type=float,
        default=None,
        help="Optional time window filter (e.g. 24 for last 24 hours of data).",
    )
    parser.add_argument(
        "--pagerank-damping",
        type=float,
        default=0.85,
        help="PageRank damping factor (default: 0.85).",
    )
    parser.add_argument(
        "--louvain-resolution",
        type=float,
        default=1.0,
        help="Louvain modularity resolution parameter (default: 1.0).",
    )

    args = parser.parse_args()

    db = SessionLocal()
    try:
        start_at = None
        end_at = None

        if args.hours:
            end_at = datetime.now(timezone.utc)
            start_at = end_at - timedelta(hours=args.hours)

        analyzer = DatabaseNetworkAnalyzer(db)
        scope_type = "topic" if args.topic_id is not None else "global"

        run = analyzer.run_analysis(
            scope_type=scope_type,
            topic_id=args.topic_id,
            start_at=start_at,
            end_at=end_at,
            pagerank_damping=args.pagerank_damping,
            louvain_resolution=args.louvain_resolution,
        )

        topic_label = None
        if run.topic_id:
            top_row = db.get(Topic, run.topic_id)
            if top_row:
                topic_label = top_row.label

        # Query top PageRank nodes
        top_pr_stmt = (
            select(NetworkNode, User.username)
            .join(User, NetworkNode.user_id == User.id)
            .where(NetworkNode.run_id == run.id)
            .order_by(NetworkNode.pagerank_score.desc())
            .limit(5)
        )
        top_pr_nodes = db.execute(top_pr_stmt).all()

        # Query top Bridge nodes (by betweenness centrality)
        top_bridge_stmt = (
            select(NetworkNode, User.username)
            .join(User, NetworkNode.user_id == User.id)
            .where(NetworkNode.run_id == run.id)
            .order_by(NetworkNode.betweenness_centrality.desc(), NetworkNode.cross_community_edge_count.desc())
            .limit(5)
        )
        top_bridge_nodes = db.execute(top_bridge_stmt).all()

        # Query community size summary
        comm_summary_stmt = (
            select(NetworkNode.community_id, func.count(NetworkNode.id).label("user_count"))
            .where(NetworkNode.run_id == run.id)
            .group_by(NetworkNode.community_id)
            .order_by(func.count(NetworkNode.id).desc())
            .limit(5)
        )
        comm_summaries = db.execute(comm_summary_stmt).all()

        # Query top community flows
        flows_stmt = (
            select(CommunityFlow)
            .where(CommunityFlow.run_id == run.id)
            .order_by(CommunityFlow.interaction_count.desc())
            .limit(5)
        )
        top_flows = db.scalars(flows_stmt).all()

        # Print Safe Output Summary
        print("\n" + "=" * 70)
        print("NETWORK ANALYSIS COMPLETE")
        print("=" * 70)
        print(f"Run ID:      {run.id}")
        print(f"Scope:       {run.scope_type.upper()}" + (f" (Topic: '{topic_label}')" if topic_label else ""))
        print(f"Time Range:  {run.start_at or 'All time'} -> {run.end_at or 'All time'}")
        print("-" * 70)
        print("Graph Quality & Topology:")
        print(f"  Nodes (Connected Users):      {run.node_count}")
        print(f"  Edges (Interactions):         {run.edge_count}")
        print(f"  Density:                      {run.density:.6f}")
        print(f"  Weakly Connected Components:  {run.weak_component_count}")
        print(f"  Strongly Connected Components:{run.strong_component_count}")
        print(f"  Largest Component Size:       {run.largest_weak_component_size} users")
        print(f"  Isolated Users (0 edges):     {run.isolated_user_count}")
        print("-" * 70)
        print("Top Influential Accounts (by PageRank):")
        for idx, (node, username) in enumerate(top_pr_nodes, 1):
            print(
                f"  {idx}. @{username:<20} | PageRank: {node.pagerank_score:.5f} | "
                f"In-Degree: {node.in_degree:2d} (Vol: {node.weighted_in_degree:4.1f}) | "
                f"Community: {node.community_id}"
            )

        print("\nTop Bridge Accounts (by Betweenness Centrality):")
        for idx, (node, username) in enumerate(top_bridge_nodes, 1):
            print(
                f"  {idx}. @{username:<20} | Betweenness: {node.betweenness_centrality:.5f} | "
                f"Cross-Community Edges: {node.cross_community_edge_count:2d} | "
                f"Communities Reached: {node.communities_reached}"
            )

        print("\nLargest Louvain Communities:")
        for comm in comm_summaries:
            print(f"  Community {comm.community_id}: {comm.user_count} users")

        if top_flows:
            print("\nObserved Cross-Community Flows:")
            for fl in top_flows:
                print(
                    f"  Community {fl.source_community_id} -> Community {fl.target_community_id}: "
                    f"{fl.interaction_count} interaction(s)"
                )

        # Topic + Community Sentiment Breakdown (if applicable)
        if run.topic_id is not None:
            sentiment_breakdown = analyzer.get_topic_community_sentiment_breakdown(run.id)
            if sentiment_breakdown:
                print("\nCommunity Sentiment Breakdown for Topic:")
                for c_data in sentiment_breakdown:
                    print(
                        f"  Community {c_data['community_id']:2d} ({c_data['total']:2d} tweets) | "
                        f"Pos: {c_data['positive']:2d} | Neu: {c_data['neutral']:2d} | Neg: {c_data['negative']:2d}"
                    )
        print("=" * 70 + "\n")

    finally:
        db.close()


if __name__ == "__main__":
    main()
