"""GET /api/v1/network endpoints for global network topology, nodes, edges, and communities."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.network import (
    CommunityFlow,
    NetworkAnalysisRun,
    NetworkEdge,
    NetworkNode,
)
from app.models.user import User
from app.schemas.network import (
    CommunityFlowItem,
    CommunityItem,
    NetworkEdgeItem,
    NetworkNodeItem,
    NetworkSummaryResponse,
)

router = APIRouter(prefix="/network", tags=["network"])


def _resolve_run(db: Session, run_id: Optional[int] = None) -> NetworkAnalysisRun:
    """Helper to retrieve requested run or latest global network run."""
    if run_id is not None:
        run = db.get(NetworkAnalysisRun, run_id)
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Network run {run_id} not found",
            )
        return run

    run = db.scalars(
        select(NetworkAnalysisRun)
        .where(NetworkAnalysisRun.scope_type == "global")
        .order_by(NetworkAnalysisRun.id.desc())
        .limit(1)
    ).first()

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No completed network analysis run exists",
        )
    return run


@router.get(
    "/summary",
    response_model=NetworkSummaryResponse,
    summary="Get network graph quality and structural telemetry",
)
def get_network_summary(
    run_id: Optional[int] = Query(None, description="Optional run ID (defaults to latest global run)"),
    db: Session = Depends(get_db),
) -> NetworkSummaryResponse:
    """Return graph quality and component metrics for the interaction network."""
    run = _resolve_run(db, run_id)

    community_count = db.scalar(
        select(func.count(func.distinct(NetworkNode.community_id))).where(NetworkNode.run_id == run.id)
    ) or 0

    sparsity_warning = None
    if run.density < 0.05:
        sparsity_warning = (
            f"Graph density is {run.density:.4f} with {run.weak_component_count} disjoint components. "
            f"Results reflect sparse bootstrap sampling rather than dense real-world communities."
        )

    return NetworkSummaryResponse(
        run_id=run.id,
        scope_type=run.scope_type,
        topic_id=run.topic_id,
        node_count=run.node_count,
        edge_count=run.edge_count,
        density=round(float(run.density), 6),
        weak_component_count=run.weak_component_count,
        strong_component_count=run.strong_component_count,
        largest_weak_component_size=run.largest_weak_component_size,
        connected_user_count=run.connected_user_count,
        isolated_user_count=run.isolated_user_count,
        community_count=community_count,
        is_sparse=run.density < 0.05,
        sparsity_warning=sparsity_warning,
        algorithm_params=run.algorithm_params,
        created_at=run.created_at,
    )


@router.get(
    "/nodes",
    response_model=list[NetworkNodeItem],
    summary="Get user nodes with PageRank, degree, and betweenness scores",
)
def get_network_nodes(
    run_id: Optional[int] = Query(None, description="Optional run ID"),
    limit: int = Query(50, ge=1, le=500, description="Max nodes to return"),
    community_id: Optional[int] = Query(None, description="Filter by Louvain community ID"),
    db: Session = Depends(get_db),
) -> list[NetworkNodeItem]:
    """Return nodes ordered by PageRank descending, including uncollapsed centrality metrics."""
    run = _resolve_run(db, run_id)

    stmt = (
        select(NetworkNode, User.username)
        .join(User, NetworkNode.user_id == User.id)
        .where(NetworkNode.run_id == run.id)
    )

    if community_id is not None:
        stmt = stmt.where(NetworkNode.community_id == community_id)

    stmt = stmt.order_by(NetworkNode.pagerank_score.desc()).limit(limit)
    rows = db.execute(stmt).all()

    return [
        NetworkNodeItem(
            user_id=n.user_id,
            username=u or f"user_{n.user_id}",
            pagerank_score=round(float(n.pagerank_score), 6),
            in_degree=n.in_degree,
            out_degree=n.out_degree,
            weighted_in_degree=round(float(n.weighted_in_degree), 1),
            weighted_out_degree=round(float(n.weighted_out_degree), 1),
            betweenness_centrality=round(float(n.betweenness_centrality), 6),
            community_id=n.community_id,
            cross_community_edge_count=n.cross_community_edge_count,
            communities_reached=n.communities_reached,
        )
        for n, u in rows
    ]


@router.get(
    "/edges",
    response_model=list[NetworkEdgeItem],
    summary="Get directed interaction edges with interaction type volumes",
)
def get_network_edges(
    run_id: Optional[int] = Query(None, description="Optional run ID"),
    limit: int = Query(100, ge=1, le=500, description="Max edges to return"),
    db: Session = Depends(get_db),
) -> list[NetworkEdgeItem]:
    """Return pairwise directed interaction edges ordered by interaction weight descending."""
    run = _resolve_run(db, run_id)

    edge_stmt = (
        select(
            NetworkEdge,
            select(User.username).where(User.id == NetworkEdge.source_user_id).scalar_subquery().label("src_u"),
            select(User.username).where(User.id == NetworkEdge.target_user_id).scalar_subquery().label("tgt_u"),
        )
        .where(NetworkEdge.run_id == run.id)
        .order_by(NetworkEdge.total_weight.desc())
        .limit(limit)
    )
    rows = db.execute(edge_stmt).all()

    return [
        NetworkEdgeItem(
            source_user_id=e.source_user_id,
            source_username=src_u or f"user_{e.source_user_id}",
            target_user_id=e.target_user_id,
            target_username=tgt_u or f"user_{e.target_user_id}",
            total_weight=round(float(e.total_weight), 1),
            reply_count=e.reply_count,
            mention_count=e.mention_count,
            repost_count=e.repost_count,
            quote_count=e.quote_count,
            first_observed_at=e.first_observed_at,
            last_observed_at=e.last_observed_at,
        )
        for e, src_u, tgt_u in rows
    ]


@router.get(
    "/communities",
    response_model=list[CommunityItem],
    summary="Get detected Louvain communities and member distributions",
)
def get_network_communities(
    run_id: Optional[int] = Query(None, description="Optional run ID"),
    db: Session = Depends(get_db),
) -> list[CommunityItem]:
    """Return communities ordered by size descending, with top PageRank accounts in each."""
    run = _resolve_run(db, run_id)

    comm_counts = db.execute(
        select(NetworkNode.community_id, func.count(NetworkNode.id).label("cnt"))
        .where(NetworkNode.run_id == run.id)
        .group_by(NetworkNode.community_id)
        .order_by(func.count(NetworkNode.id).desc())
    ).all()

    # Pre-fetch top users per community
    top_user_rows = db.execute(
        select(NetworkNode, User.username)
        .join(User, NetworkNode.user_id == User.id)
        .where(NetworkNode.run_id == run.id)
        .order_by(NetworkNode.pagerank_score.desc())
    ).all()

    top_by_comm: dict[int, list[NetworkNodeItem]] = {}
    for n, u in top_user_rows:
        cid = n.community_id if n.community_id is not None else -1
        if cid not in top_by_comm:
            top_by_comm[cid] = []
        if len(top_by_comm[cid]) < 3:
            top_by_comm[cid].append(
                NetworkNodeItem(
                    user_id=n.user_id,
                    username=u or f"user_{n.user_id}",
                    pagerank_score=round(float(n.pagerank_score), 6),
                    in_degree=n.in_degree,
                    out_degree=n.out_degree,
                    weighted_in_degree=round(float(n.weighted_in_degree), 1),
                    weighted_out_degree=round(float(n.weighted_out_degree), 1),
                    betweenness_centrality=round(float(n.betweenness_centrality), 6),
                    community_id=n.community_id,
                    cross_community_edge_count=n.cross_community_edge_count,
                    communities_reached=n.communities_reached,
                )
            )

    communities: list[CommunityItem] = []
    for cid, cnt in comm_counts:
        c_val = cid if cid is not None else -1
        communities.append(
            CommunityItem(
                community_id=c_val,
                user_count=cnt,
                interaction_count=cnt,
                top_users=top_by_comm.get(c_val, []),
            )
        )

    return communities


@router.get(
    "/flows",
    response_model=list[CommunityFlowItem],
    summary="Get observed chronological interaction flows between communities",
)
def get_network_flows(
    run_id: Optional[int] = Query(None, description="Optional run ID"),
    db: Session = Depends(get_db),
) -> list[CommunityFlowItem]:
    """Return observed cross-community interaction flows (Correction 8)."""
    run = _resolve_run(db, run_id)

    flows = list(
        db.scalars(
            select(CommunityFlow)
            .where(CommunityFlow.run_id == run.id)
            .order_by(CommunityFlow.interaction_count.desc())
        ).all()
    )

    return [
        CommunityFlowItem(
            source_community_id=fl.source_community_id,
            target_community_id=fl.target_community_id,
            interaction_count=fl.interaction_count,
            first_observed_at=fl.first_observed_at,
            last_observed_at=fl.last_observed_at,
        )
        for fl in flows
    ]
