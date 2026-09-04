"""Trend metrics computation: velocity, acceleration, and engagement aggregation.

Implements Phase 3A explainable formulations with minimum support and zero-baseline smoothing.
"""

from typing import Any, Iterable


def calculate_velocity(
    current_mentions: int,
    baseline_mentions: float,
    min_support: int = 2,
    baseline_floor: float = 1.0,
) -> float:
    """Calculate temporal velocity with smoothing and minimum support.

    Formula:
        if current_mentions < min_support:
            velocity = 0.0
        else:
            velocity = current_mentions / max(baseline_mentions, baseline_floor)

    Args:
        current_mentions: Mention count in the current window W_t.
        baseline_mentions: Average mentions over preceding K baseline windows.
        min_support: Minimum current mentions required to prevent 0->1 spurious spikes.
        baseline_floor: Minimum baseline value to prevent zero division and infinite scores.

    Returns:
        float: Velocity relative to baseline (e.g. 2.5 means 2.5x normal volume).
    """
    if current_mentions < min_support:
        return 0.0

    effective_baseline = max(baseline_mentions, baseline_floor)
    return float(current_mentions / effective_baseline)


def calculate_acceleration(
    current_velocity: float,
    previous_velocity: float,
) -> float:
    """Calculate temporal acceleration between consecutive windows.

    Formula:
        acceleration = current_velocity - previous_velocity

    Args:
        current_velocity: Velocity in window W_t.
        previous_velocity: Velocity in window W_{t-1}.

    Returns:
        float: Rate of change of velocity (+ for speeding up, - for slowing down).
    """
    return float(current_velocity - previous_velocity)


def aggregate_engagement(tweets: Iterable[Any]) -> dict[str, int]:
    """Aggregate engagement metrics across a set of tweets in a window.

    Standardizes on `repost_count` while supporting models that store `retweet_count`.

    Returns:
        dict with keys: 'like_count', 'repost_count', 'reply_count', 'quote_count'
    """
    total_likes = 0
    total_reposts = 0
    total_replies = 0
    total_quotes = 0

    for t in tweets:
        total_likes += getattr(t, "like_count", 0) or 0
        
        # Support both repost_count and retweet_count
        reposts = getattr(t, "repost_count", None)
        if reposts is None:
            reposts = getattr(t, "retweet_count", 0)
        total_reposts += reposts or 0

        total_replies += getattr(t, "reply_count", 0) or 0
        total_quotes += getattr(t, "quote_count", 0) or 0

    return {
        "like_count": total_likes,
        "repost_count": total_reposts,
        "reply_count": total_replies,
        "quote_count": total_quotes,
    }
