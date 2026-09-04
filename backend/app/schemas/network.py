"""Pydantic schemas for Phase 4 network topology and influence endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class NetworkSummaryResponse(BaseModel):
    """Network-level graph quality and structural telemetry."""

    run_id: int
    scope_type: str = Field(..., description="'global' or 'topic'")
    topic_id: int | None = None
    node_count: int = Field(..., description="Active interacting user accounts in graph")
    edge_count: int = Field(..., description="Pairwise aggregated directed interaction edges")
    density: float = Field(..., description="Graph density |E| / (|V|*(|V|-1))")
    weak_component_count: int = Field(..., description="Disjoint conversation clusters")
    strong_component_count: int = Field(..., description="Mutually reachable directed subgraphs")
    largest_weak_component_size: int = Field(..., description="User count in largest connected sub-network")
    connected_user_count: int = Field(..., description="Users participating in interactions")
    isolated_user_count: int = Field(..., description="Users with zero observed interactions")
    community_count: int = Field(..., description="Distinct Louvain communities identified")
    is_sparse: bool = Field(True, description="True if graph density is below 0.05")
    sparsity_warning: str | None = Field(
        None, description="Explains sparsity limitations when network has high disconnectedness"
    )
    algorithm_params: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class NetworkNodeItem(BaseModel):
    """User account centrality and influence metrics in a specific network run."""

    user_id: int
    username: str
    pagerank_score: float = Field(..., description="Weighted PageRank structural attention score")
    in_degree: int = Field(..., description="Count of distinct users interacting with this account")
    out_degree: int = Field(..., description="Count of distinct users this account interacted with")
    weighted_in_degree: float = Field(..., description="Total incoming interaction volume")
    weighted_out_degree: float = Field(..., description="Total outgoing interaction volume")
    betweenness_centrality: float = Field(
        ..., description="Normalized shortest-path betweenness using distance=1.0/weight"
    )
    community_id: int | None = Field(
        None, description="Run-local Louvain community identifier"
    )
    cross_community_edge_count: int = Field(
        0, description="Directed edges connecting this account to other communities"
    )
    communities_reached: int = Field(
        0, description="Number of distinct foreign communities interacted with"
    )


class NetworkEdgeItem(BaseModel):
    """Directed, pairwise aggregated interaction edge."""

    source_user_id: int
    source_username: str
    target_user_id: int
    target_username: str
    total_weight: float = Field(..., description="Total aggregated interaction strength")
    reply_count: int = 0
    mention_count: int = 0
    repost_count: int = 0
    quote_count: int = 0
    first_observed_at: datetime | None = None
    last_observed_at: datetime | None = None


class CommunityItem(BaseModel):
    """Summary of a detected Louvain community within a run."""

    community_id: int
    user_count: int
    interaction_count: int
    top_users: list[NetworkNodeItem] = Field(
        default_factory=list, description="Top PageRank accounts belonging to this community"
    )


class CommunityFlowItem(BaseModel):
    """Observed chronological interaction flow between Louvain communities."""

    source_community_id: int
    target_community_id: int
    interaction_count: int
    first_observed_at: datetime | None = None
    last_observed_at: datetime | None = None


class TopicNetworkResponse(BaseModel):
    """Topic-specific network intelligence or explicit unavailable status (Correction 8)."""

    available: bool
    reason: str | None = None
    run: NetworkSummaryResponse | None = None
    nodes: list[NetworkNodeItem] = Field(default_factory=list)
    edges: list[NetworkEdgeItem] = Field(default_factory=list)
    communities: list[CommunityItem] = Field(default_factory=list)
    flows: list[CommunityFlowItem] = Field(default_factory=list)
    top_pagerank_nodes: list[NetworkNodeItem] = Field(default_factory=list)
    top_bridge_nodes: list[NetworkNodeItem] = Field(default_factory=list)
