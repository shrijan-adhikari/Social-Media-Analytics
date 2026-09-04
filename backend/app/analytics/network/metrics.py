"""Graph metrics computation: PageRank, Degree centrality, Betweenness, and Graph Quality."""

from typing import Any, Dict
import networkx as nx

from app.analytics.network.config import (
    DEFAULT_PAGERANK_DAMPING,
    DEFAULT_PAGERANK_MAX_ITER,
    DEFAULT_PAGERANK_TOL,
)


def compute_pagerank(
    G: nx.DiGraph,
    damping: float = DEFAULT_PAGERANK_DAMPING,
    max_iter: int = DEFAULT_PAGERANK_MAX_ITER,
    tol: float = DEFAULT_PAGERANK_TOL,
) -> Dict[int, float]:
    """Compute weighted PageRank on directed graph.

    Incoming edges (in_degree) denote attention/influence received by target accounts.
    Uses canonical edge 'weight' (interaction strength).
    """
    if G.number_of_nodes() == 0:
        return {}
    if G.number_of_edges() == 0:
        # Uniform distribution if no edges exist
        n = G.number_of_nodes()
        return {node: 1.0 / n for node in G.nodes()}

    try:
        return nx.pagerank(
            G,
            alpha=damping,
            max_iter=max_iter,
            tol=tol,
            weight="weight",
        )
    except nx.PowerIterationFailedConvergence:
        # Fallback with higher iteration count if convergence is slow
        return nx.pagerank(
            G,
            alpha=damping,
            max_iter=max_iter * 2,
            tol=tol * 10,
            weight="weight",
        )


def compute_degree_metrics(G: nx.DiGraph) -> Dict[int, Dict[str, Any]]:
    """Compute in/out degrees and weighted in/out degrees for each node."""
    degree_metrics: Dict[int, Dict[str, Any]] = {}

    for node in G.nodes():
        in_deg = G.in_degree(node)
        out_deg = G.out_degree(node)
        w_in_deg = float(G.in_degree(node, weight="weight"))
        w_out_deg = float(G.out_degree(node, weight="weight"))

        degree_metrics[node] = {
            "in_degree": in_deg,
            "out_degree": out_deg,
            "weighted_in_degree": w_in_deg,
            "weighted_out_degree": w_out_deg,
        }

    return degree_metrics


def compute_betweenness_centrality(G: nx.DiGraph) -> Dict[int, float]:
    """Compute shortest-path betweenness centrality.

    CORRECTION 1: Uses edge attribute 'distance' (distance = 1.0 / weight),
    ensuring higher interaction strength corresponds to shorter path distance.
    Canonical 'weight' is preserved untouched for PageRank and persistence.
    """
    if G.number_of_nodes() == 0:
        return {}
    if G.number_of_edges() == 0:
        return {node: 0.0 for node in G.nodes()}

    return nx.betweenness_centrality(
        G,
        weight="distance",
        normalized=True,
    )


def compute_graph_quality(G: nx.DiGraph) -> Dict[str, Any]:
    """Compute graph quality, connectivity, and component statistics (Correction 3)."""
    node_count = G.number_of_nodes()
    edge_count = G.number_of_edges()

    if node_count == 0:
        return {
            "node_count": 0,
            "edge_count": 0,
            "density": 0.0,
            "weak_component_count": 0,
            "strong_component_count": 0,
            "largest_weak_component_size": 0,
        }

    density = float(nx.density(G))
    wcc = list(nx.weakly_connected_components(G))
    scc = list(nx.strongly_connected_components(G))

    weak_count = len(wcc)
    strong_count = len(scc)
    largest_wcc_size = max((len(c) for c in wcc), default=0)

    return {
        "node_count": node_count,
        "edge_count": edge_count,
        "density": density,
        "weak_component_count": weak_count,
        "strong_component_count": strong_count,
        "largest_weak_component_size": largest_wcc_size,
    }
