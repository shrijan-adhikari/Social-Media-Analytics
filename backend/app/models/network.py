"""SQLAlchemy models for Phase 4 Network Analysis and Influence Topology.

Preserves run-scoped directed interaction graph topology, node metrics
(PageRank, degree, betweenness), Louvain communities, and cross-community flows.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.tweet import Base


class NetworkAnalysisRun(Base):
    """Execution instance of a network analysis run, maintaining complete graph provenance."""

    __tablename__ = "network_analysis_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pipeline_version: Mapped[str] = mapped_column(String(32), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(32), nullable=False)  # "global" or "topic"
    topic_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("topics.id", ondelete="SET NULL"), nullable=True, index=True
    )
    start_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    end_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Graph Quality & Component Metadata (Correction 3)
    node_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    edge_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    density: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    weak_component_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    strong_component_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    largest_weak_component_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    connected_user_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    isolated_user_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    algorithm_params: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    nodes: Mapped[List["NetworkNode"]] = relationship(
        "NetworkNode", back_populates="run", cascade="all, delete-orphan"
    )
    edges: Mapped[List["NetworkEdge"]] = relationship(
        "NetworkEdge", back_populates="run", cascade="all, delete-orphan"
    )
    flows: Mapped[List["CommunityFlow"]] = relationship(
        "CommunityFlow", back_populates="run", cascade="all, delete-orphan"
    )


class NetworkNode(Base):
    """User node metrics within a specific network analysis run."""

    __tablename__ = "network_nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("network_analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Separate, uncollapsed graph metrics (Correction 4)
    pagerank_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    in_degree: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    out_degree: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    weighted_in_degree: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    weighted_out_degree: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    betweenness_centrality: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Louvain Community assignment (Run-local ID, Correction 7)
    community_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)

    # Bridge metrics
    cross_community_edge_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    communities_reached: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    run: Mapped["NetworkAnalysisRun"] = relationship("NetworkAnalysisRun", back_populates="nodes")
    user: Mapped["User"] = relationship("User")  # type: ignore[name-defined]

    __table_args__ = (
        UniqueConstraint("run_id", "user_id", name="uq_network_nodes_run_user"),
    )


class NetworkEdge(Base):
    """Pairwise aggregated directed interaction edge within a network analysis run."""

    __tablename__ = "network_edges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("network_analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Interaction volume & type counts
    total_weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    reply_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mention_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    repost_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quote_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    first_observed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_observed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    run: Mapped["NetworkAnalysisRun"] = relationship("NetworkAnalysisRun", back_populates="edges")

    __table_args__ = (
        UniqueConstraint("run_id", "source_user_id", "target_user_id", name="uq_network_edges_run_source_target"),
    )


class CommunityFlow(Base):
    """Observed interaction flow between Louvain communities within a network analysis run."""

    __tablename__ = "community_flows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("network_analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_community_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    target_community_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    interaction_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    first_observed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_observed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    run: Mapped["NetworkAnalysisRun"] = relationship("NetworkAnalysisRun", back_populates="flows")

    __table_args__ = (
        UniqueConstraint("run_id", "source_community_id", "target_community_id", name="uq_community_flows_run_source_target"),
    )
