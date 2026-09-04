"""GET /api/v1/trends endpoints for topic signals, timelines, and topic networks."""

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
from app.models.sentiment_result import SentimentResult
from app.models.topic import Topic, TrendAnalysisRun, TrendWindow, TweetTopic
from app.models.tweet import Tweet
from app.models.user import User
from app.schemas.network import (
    CommunityFlowItem,
    CommunityItem,
    NetworkEdgeItem,
    NetworkNodeItem,
    NetworkSummaryResponse,
    TopicNetworkResponse,
)
from app.schemas.trends import (
    TopicSentimentResponse,
    TrendDetailResponse,
    TrendItem,
    TrendListResponse,
    TrendTimelinePoint,
    TrendTimelineResponse,
)

router = APIRouter(prefix="/trends", tags=["trends"])


@router.get(
    "",
    response_model=TrendListResponse,
    summary="Get discovered topics and velocity metrics from latest trend run",
)
def list_trends(
    topic_type: Optional[str] = Query(None, description="Filter by 'semantic' or 'lexical'"),
    limit: int = Query(20, ge=1, le=100, description="Max topics to return"),
    db: Session = Depends(get_db),
) -> TrendListResponse:
    """Return discovered topics with real velocity and acceleration metrics from the latest analysis run."""
    # Find latest completed trend analysis run
    latest_run = db.scalars(
        select(TrendAnalysisRun)
        .order_by(TrendAnalysisRun.id.desc())
        .limit(1)
    ).first()

    if not latest_run:
        return TrendListResponse(
            run_id=0,
            pipeline_version="none",
            clustering_algorithm="none",
            topics=[],
        )

    # Query topics belonging to this run
    topic_stmt = select(Topic).where(Topic.run_id == latest_run.id)
    if topic_type:
        topic_stmt = topic_stmt.where(Topic.topic_type == topic_type)

    topics = list(db.scalars(topic_stmt).all())

    items: list[TrendItem] = []
    for top in topics:
        # Get latest window metrics for this topic in this run
        latest_window = db.scalars(
            select(TrendWindow)
            .where(TrendWindow.run_id == latest_run.id, TrendWindow.topic_id == top.id)
            .order_by(TrendWindow.window_end.desc())
            .limit(1)
        ).first()

        # Count total non-outlier tweets assigned
        tweet_count = db.scalar(
            select(func.count(TweetTopic.id)).where(
                TweetTopic.topic_id == top.id, TweetTopic.is_outlier == False
            )
        ) or 0

        vel = round(float(latest_window.velocity), 2) if latest_window else 1.0
        acc = round(float(latest_window.acceleration), 2) if latest_window else 0.0
        cur_m = latest_window.mention_count if latest_window else 0
        base_m = round(float(latest_window.baseline_mentions), 1) if latest_window else 0.0
        w_start = latest_window.window_start if latest_window else None
        w_end = latest_window.window_end if latest_window else None

        items.append(
            TrendItem(
                topic_id=top.id,
                topic_type=top.topic_type,
                label=top.label,
                representative_terms=top.representative_terms or [],
                tweet_count=tweet_count,
                current_mentions=cur_m,
                baseline_mentions=base_m,
                velocity=vel,
                acceleration=acc,
                latest_window_start=w_start,
                latest_window_end=w_end,
            )
        )

    # Sort by velocity descending, then tweet_count descending
    items.sort(key=lambda x: (x.velocity, x.tweet_count), reverse=True)
    items = items[:limit]

    alg = "HDBSCAN"
    if latest_run.clustering_params and isinstance(latest_run.clustering_params, dict):
        alg = latest_run.clustering_params.get("algorithm", "HDBSCAN")

    return TrendListResponse(
        run_id=latest_run.id,
        pipeline_version=latest_run.pipeline_version,
        clustering_algorithm=alg,
        topics=items,
    )


@router.get(
    "/{topic_id}",
    response_model=TrendDetailResponse,
    summary="Get single topic metadata and latest metrics",
)
def get_trend_detail(topic_id: int, db: Session = Depends(get_db)) -> TrendDetailResponse:
    """Return detailed topic metadata and term importance."""
    top = db.get(Topic, topic_id)
    if not top:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Topic {topic_id} does not exist",
        )

    latest_window = db.scalars(
        select(TrendWindow)
        .where(TrendWindow.topic_id == top.id)
        .order_by(TrendWindow.window_end.desc())
        .limit(1)
    ).first()

    tweet_count = db.scalar(
        select(func.count(TweetTopic.id)).where(
            TweetTopic.topic_id == top.id, TweetTopic.is_outlier == False
        )
    ) or 0

    return TrendDetailResponse(
        topic_id=top.id,
        run_id=top.run_id,
        label=top.label,
        topic_type=top.topic_type,
        representative_terms=top.representative_terms or [],
        tweet_count=tweet_count,
        current_mentions=latest_window.mention_count if latest_window else 0,
        baseline_mentions=round(float(latest_window.baseline_mentions), 1) if latest_window else 0.0,
        velocity=round(float(latest_window.velocity), 2) if latest_window else 1.0,
        acceleration=round(float(latest_window.acceleration), 2) if latest_window else 0.0,
        created_at=top.created_at,
    )


@router.get(
    "/{topic_id}/timeline",
    response_model=TrendTimelineResponse,
    summary="Get chronological windowed velocity progression for topic",
)
def get_trend_timeline(topic_id: int, db: Session = Depends(get_db)) -> TrendTimelineResponse:
    """Return chronological 15-minute windowed evaluations for trend charts."""
    top = db.get(Topic, topic_id)
    if not top:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Topic {topic_id} does not exist",
        )

    windows = list(
        db.scalars(
            select(TrendWindow)
            .where(TrendWindow.topic_id == top.id)
            .order_by(TrendWindow.window_start.asc())
        ).all()
    )

    points = [
        TrendTimelinePoint(
            window_start=w.window_start,
            window_end=w.window_end,
            mention_count=w.mention_count,
            baseline_mentions=round(float(w.baseline_mentions), 1),
            velocity=round(float(w.velocity), 2),
            acceleration=round(float(w.acceleration), 2),
            like_count=w.like_count,
            repost_count=w.repost_count,
            reply_count=w.reply_count,
            quote_count=w.quote_count,
        )
        for w in windows
    ]

    return TrendTimelineResponse(topic_id=top.id, label=top.label, points=points)


@router.get(
    "/{topic_id}/sentiment",
    response_model=TopicSentimentResponse,
    summary="Read-only join of topic tweets with sentiment and sarcasm",
)
def get_topic_sentiment(topic_id: int, db: Session = Depends(get_db)) -> TopicSentimentResponse:
    """Return sentiment and sarcasm fusion distribution for a specific topic without rerunning ML models."""
    top = db.get(Topic, topic_id)
    if not top:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Topic {topic_id} does not exist",
        )

    stmt = (
        select(SentimentResult.final_sentiment, SentimentResult.sarcasm_probability, SentimentResult.fusion_status)
        .join(Tweet, SentimentResult.tweet_id == Tweet.id)
        .join(TweetTopic, Tweet.id == TweetTopic.tweet_id)
        .where(TweetTopic.topic_id == topic_id, TweetTopic.is_outlier == False)
    )
    rows = db.execute(stmt).all()

    pos = 0
    neu = 0
    neg = 0
    high_sarcasm = 0
    fusion_statuses: dict[str, int] = {}

    for s_label, s_score, f_status in rows:
        lbl = str(s_label).lower()
        if "pos" in lbl:
            pos += 1
        elif "neg" in lbl:
            neg += 1
        else:
            neu += 1

        if s_score is not None and float(s_score) >= 0.85:
            high_sarcasm += 1

        fst = str(f_status or "NO_SARCASM").upper()
        fusion_statuses[fst] = fusion_statuses.get(fst, 0) + 1

    return TopicSentimentResponse(
        topic_id=top.id,
        label=top.label,
        tweet_count=len(rows),
        positive=pos,
        neutral=neu,
        negative=neg,
        high_sarcasm_evidence=high_sarcasm,
        fusion_statuses=fusion_statuses,
    )


@router.get(
    "/{topic_id}/network",
    response_model=TopicNetworkResponse,
    summary="Get topic-specific network topology and influence metrics",
)
def get_topic_network(topic_id: int, db: Session = Depends(get_db)) -> TopicNetworkResponse:
    """Return topic-scoped network run records, or explicit unavailable status (Correction 8)."""
    top = db.get(Topic, topic_id)
    if not top:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Topic {topic_id} does not exist",
        )

    # Find latest completed network run for this topic
    net_run = db.scalars(
        select(NetworkAnalysisRun)
        .where(NetworkAnalysisRun.scope_type == "topic", NetworkAnalysisRun.topic_id == topic_id)
        .order_by(NetworkAnalysisRun.id.desc())
        .limit(1)
    ).first()

    if not net_run:
        return TopicNetworkResponse(
            available=False,
            reason="NO_TOPIC_NETWORK_ANALYSIS",
            run=None,
            nodes=[],
            edges=[],
            communities=[],
            flows=[],
            top_pagerank_nodes=[],
            top_bridge_nodes=[],
        )

    # Query nodes with usernames
    node_rows = db.execute(
        select(NetworkNode, User.username)
        .join(User, NetworkNode.user_id == User.id)
        .where(NetworkNode.run_id == net_run.id)
        .order_by(NetworkNode.pagerank_score.desc())
    ).all()

    nodes: list[NetworkNodeItem] = [
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
        for n, u in node_rows
    ]

    # Query edges with usernames
    u1 = User
    u2 = User
    edge_rows = db.execute(
        select(
            NetworkEdge,
            select(User.username).where(User.id == NetworkEdge.source_user_id).scalar_subquery().label("src_u"),
            select(User.username).where(User.id == NetworkEdge.target_user_id).scalar_subquery().label("tgt_u"),
        ).where(NetworkEdge.run_id == net_run.id)
    ).all()

    edges: list[NetworkEdgeItem] = [
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
        for e, src_u, tgt_u in edge_rows
    ]

    # Communities
    comm_counts = db.execute(
        select(NetworkNode.community_id, func.count(NetworkNode.id).label("cnt"))
        .where(NetworkNode.run_id == net_run.id)
        .group_by(NetworkNode.community_id)
        .order_by(func.count(NetworkNode.id).desc())
    ).all()

    communities: list[CommunityItem] = []
    for cid, cnt in comm_counts:
        top_u = [n for n in nodes if n.community_id == cid][:3]
        communities.append(
            CommunityItem(
                community_id=cid if cid is not None else -1,
                user_count=cnt,
                interaction_count=cnt,
                top_users=top_u,
            )
        )

    # Flows
    flows = list(
        db.scalars(
            select(CommunityFlow)
            .where(CommunityFlow.run_id == net_run.id)
            .order_by(CommunityFlow.interaction_count.desc())
        ).all()
    )

    flow_items = [
        CommunityFlowItem(
            source_community_id=fl.source_community_id,
            target_community_id=fl.target_community_id,
            interaction_count=fl.interaction_count,
            first_observed_at=fl.first_observed_at,
            last_observed_at=fl.last_observed_at,
        )
        for fl in flows
    ]

    top_pr = nodes[:5]
    top_br = sorted(nodes, key=lambda x: (x.betweenness_centrality, x.cross_community_edge_count), reverse=True)[:5]

    run_summary = NetworkSummaryResponse(
        run_id=net_run.id,
        scope_type=net_run.scope_type,
        topic_id=net_run.topic_id,
        node_count=net_run.node_count,
        edge_count=net_run.edge_count,
        density=round(float(net_run.density), 6),
        weak_component_count=net_run.weak_component_count,
        strong_component_count=net_run.strong_component_count,
        largest_weak_component_size=net_run.largest_weak_component_size,
        connected_user_count=net_run.connected_user_count,
        isolated_user_count=net_run.isolated_user_count,
        community_count=len(communities),
        is_sparse=net_run.density < 0.05,
        sparsity_warning="Interaction topology is sparse; metrics reflect observed direct engagements." if net_run.density < 0.05 else None,
        algorithm_params=net_run.algorithm_params,
        created_at=net_run.created_at,
    )

    return TopicNetworkResponse(
        available=True,
        reason=None,
        run=run_summary,
        nodes=nodes,
        edges=edges,
        communities=communities,
        flows=flow_items,
        top_pagerank_nodes=top_pr,
        top_bridge_nodes=top_br,
    )
