"""Observed interaction flow between Louvain communities (Correction 8).

Reconstructs chronological observed interaction flow between user communities.
Does NOT claim causal diffusion or narrative adoption.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import networkx as nx


def compute_community_flows(
    G: nx.DiGraph,
    node_to_community: Dict[int, int],
) -> List[Dict[str, Any]]:
    """Compute observed interaction flow between communities.

    Iterates directed interaction edges (source -> target).
    Aggregates pairwise community transitions (source_community -> target_community).

    Returns:
        List[Dict[str, Any]]: List of flow dictionaries ready for persistence.
    """
    flow_aggregates: Dict[Tuple[int, int], Dict[str, Any]] = {}

    for u, v, data in G.edges(data=True):
        c_src = node_to_community.get(u)
        c_tgt = node_to_community.get(v)

        # Only track cross-community or explicit between-community flows
        if c_src is None or c_tgt is None:
            continue

        pair = (c_src, c_tgt)
        weight = float(data.get("weight", 1.0))
        t_first = data.get("first_observed_at")
        t_last = data.get("last_observed_at")

        if pair not in flow_aggregates:
            flow_aggregates[pair] = {
                "source_community_id": c_src,
                "target_community_id": c_tgt,
                "interaction_count": 0,
                "first_observed_at": t_first,
                "last_observed_at": t_last,
            }

        rec = flow_aggregates[pair]
        rec["interaction_count"] += int(weight)

        if t_first:
            if rec["first_observed_at"] is None or t_first < rec["first_observed_at"]:
                rec["first_observed_at"] = t_first
        if t_last:
            if rec["last_observed_at"] is None or t_last > rec["last_observed_at"]:
                rec["last_observed_at"] = t_last

    return list(flow_aggregates.values())
