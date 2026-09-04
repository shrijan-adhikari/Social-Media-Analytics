"""Graph builder extracting directed interactions from PostgreSQL into NetworkX."""

from datetime import datetime
from typing import Dict, List, Optional, Tuple
import networkx as nx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.interaction import Interaction, InteractionType
from app.models.topic import TweetTopic
from app.models.user import User


class GraphBuilder:
    """Builds a directed, weighted NetworkX graph from canonical interaction records."""

    def __init__(self, db: Session):
        self.db = db

    def build_graph(
        self,
        start_at: Optional[datetime] = None,
        end_at: Optional[datetime] = None,
        topic_id: Optional[int] = None,
    ) -> Tuple[nx.DiGraph, Dict[str, int]]:
        """Construct a NetworkX DiGraph from filtered interactions.

        Args:
            start_at: Optional start timestamp filter.
            end_at: Optional end timestamp filter.
            topic_id: Optional topic ID filter. If specified, only interactions
                      associated with tweets belonging to this topic are included.

        Returns:
            Tuple[nx.DiGraph, Dict[str, int]]:
                - Directed graph with node and edge attributes.
                - Metadata dict containing total_users, connected_users, and isolated_users.
        """
        # Base query for qualifying interactions
        stmt = select(Interaction)

        if start_at:
            stmt = stmt.where(Interaction.timestamp_utc >= start_at)
        if end_at:
            stmt = stmt.where(Interaction.timestamp_utc <= end_at)

        if topic_id is not None:
            # Topic-specific filtering: include interactions whose tweet_id belongs to the topic
            topic_tweet_ids = select(TweetTopic.tweet_id).where(
                TweetTopic.topic_id == topic_id,
                TweetTopic.is_outlier == False,  # Exclude HDBSCAN noise
            )
            stmt = stmt.where(Interaction.tweet_id.in_(topic_tweet_ids))

        interactions: List[Interaction] = list(self.db.scalars(stmt).all())

        G = nx.DiGraph()

        # Aggregate pairwise interactions: (source_user_id, target_user_id)
        # Direction: source (actor) -> target (referenced user)
        aggregated_edges: Dict[Tuple[int, int], Dict] = {}

        for inter in interactions:
            pair = (inter.source_user_id, inter.target_user_id)
            if pair not in aggregated_edges:
                aggregated_edges[pair] = {
                    "reply_count": 0,
                    "mention_count": 0,
                    "repost_count": 0,
                    "quote_count": 0,
                    "total_weight": 0.0,
                    "first_observed_at": inter.timestamp_utc,
                    "last_observed_at": inter.timestamp_utc,
                }

            data = aggregated_edges[pair]
            itype = str(inter.interaction_type).lower()
            if "reply" in itype:
                data["reply_count"] += 1
            elif "mention" in itype:
                data["mention_count"] += 1
            elif "repost" in itype:
                data["repost_count"] += 1
            elif "quote" in itype:
                data["quote_count"] += 1

            data["total_weight"] += float(inter.weight or 1.0)

            if inter.timestamp_utc:
                if data["first_observed_at"] is None or inter.timestamp_utc < data["first_observed_at"]:
                    data["first_observed_at"] = inter.timestamp_utc
                if data["last_observed_at"] is None or inter.timestamp_utc > data["last_observed_at"]:
                    data["last_observed_at"] = inter.timestamp_utc

        # Populate NetworkX DiGraph
        for (src, tgt), data in aggregated_edges.items():
            G.add_node(src, user_id=src)
            G.add_node(tgt, user_id=tgt)

            weight = data["total_weight"]
            # Correction 1: Derive separate distance attribute for shortest-path/betweenness
            # higher interaction weight -> stronger relationship -> shorter graph distance
            distance = 1.0 / weight if weight > 0 else 1.0

            G.add_edge(
                src,
                tgt,
                weight=weight,           # Canonical interaction strength for PageRank
                distance=distance,       # Shortest path distance for Betweenness
                reply_count=data["reply_count"],
                mention_count=data["mention_count"],
                repost_count=data["repost_count"],
                quote_count=data["quote_count"],
                first_observed_at=data["first_observed_at"],
                last_observed_at=data["last_observed_at"],
            )

        # Audit user coverage
        total_db_users = self.db.scalar(select(func.count(User.id))) or 0
        connected_users = G.number_of_nodes()
        isolated_users = max(0, total_db_users - connected_users)

        metadata = {
            "total_users": total_db_users,
            "connected_users": connected_users,
            "isolated_users": isolated_users,
            "interaction_count": len(interactions),
        }

        return G, metadata
