"""Community detection via explicit undirected Louvain projection and bridge account analysis."""

from typing import Any, Dict, List, Set, Tuple
import networkx as nx
from networkx.algorithms.community import louvain_communities

from app.analytics.network.config import DEFAULT_LOUVAIN_RESOLUTION, DEFAULT_LOUVAIN_SEED


def build_explicit_undirected_projection(G: nx.DiGraph) -> nx.Graph:
    """Explicitly construct an undirected weighted projection (Correction 2).

    Formally aggregates reciprocal directed interaction weights:
        W{A, B} = W(A -> B) + W(B -> A)
    Preserves the canonical directed graph G unchanged.
    """
    G_undirected = nx.Graph()

    # Add all nodes from directed graph
    for node, data in G.nodes(data=True):
        G_undirected.add_node(node, **data)

    # Accumulate edge weights for unordered pairs {u, v}
    edge_weights: Dict[Tuple[int, int], float] = {}

    for u, v, data in G.edges(data=True):
        if u == v:
            continue  # Exclude self-loops from community projection
        pair = (min(u, v), max(u, v))
        w = float(data.get("weight", 1.0))
        edge_weights[pair] = edge_weights.get(pair, 0.0) + w

    # Add undirected edges with summed reciprocal weights
    for (u, v), total_w in edge_weights.items():
        G_undirected.add_edge(u, v, weight=total_w)

    return G_undirected


def detect_communities_louvain(
    G: nx.DiGraph,
    seed: int = DEFAULT_LOUVAIN_SEED,
    resolution: float = DEFAULT_LOUVAIN_RESOLUTION,
) -> Dict[int, int]:
    """Execute Louvain community detection on the explicit undirected projection.

    Returns:
        Dict[int, int]: Mapping of user_id -> community_id (0-indexed, run-local).
    """
    if G.number_of_nodes() == 0:
        return {}

    G_undirected = build_explicit_undirected_projection(G)

    # Handle disjoint graph where some nodes have no edges
    # louvain_communities supports disconnected components natively
    communities_sets: List[Set[int]] = louvain_communities(
        G_undirected,
        weight="weight",
        resolution=resolution,
        seed=seed,
    )

    # Sort communities by size descending for deterministic, intuitive numbering
    communities_sorted = sorted(communities_sets, key=lambda c: len(c), reverse=True)

    node_to_community: Dict[int, int] = {}
    for comm_idx, comm_nodes in enumerate(communities_sorted):
        for node in comm_nodes:
            node_to_community[node] = comm_idx

    # Ensure any isolated nodes also receive a community ID
    for node in G.nodes():
        if node not in node_to_community:
            node_to_community[node] = len(communities_sorted)

    return node_to_community


def compute_bridge_metrics(
    G: nx.DiGraph,
    node_to_community: Dict[int, int],
) -> Dict[int, Dict[str, int]]:
    """Compute explainable bridge metrics for each node (Correction 4).

    Identifies users connecting otherwise separate communities:
    - cross_community_edge_count: number of directed edges connected to users in other communities
    - communities_reached: number of distinct other communities reached
    """
    bridge_metrics: Dict[int, Dict[str, int]] = {}

    for node in G.nodes():
        c_node = node_to_community.get(node)
        cross_count = 0
        reached_communities: Set[int] = set()

        if c_node is not None:
            # Check outgoing edges: node -> target
            for _, target in G.out_edges(node):
                c_target = node_to_community.get(target)
                if c_target is not None and c_target != c_node:
                    cross_count += 1
                    reached_communities.add(c_target)

            # Check incoming edges: source -> node
            for source, _ in G.in_edges(node):
                c_source = node_to_community.get(source)
                if c_source is not None and c_source != c_node:
                    cross_count += 1
                    reached_communities.add(c_source)

        bridge_metrics[node] = {
            "cross_community_edge_count": cross_count,
            "communities_reached": len(reached_communities),
        }

    return bridge_metrics
