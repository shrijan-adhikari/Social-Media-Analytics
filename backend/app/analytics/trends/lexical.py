"""Lexical signal extraction and time-window bucketing for Trend Detection.

Extracts hashtags and salient terms while strictly preserving multilingual,
Hindi/Hinglish, and case/entity nuances where appropriate.
"""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
import re
from typing import Any, Iterable, List, Sequence, Tuple

from app.analytics.trends.metrics import (
    calculate_acceleration,
    calculate_velocity,
    aggregate_engagement,
)

# Regex for Twitter hashtags (supports alphanumeric, unicode characters, and underscores)
HASHTAG_REGEX = re.compile(r"#\w+", re.UNICODE)

# Common stopwords to avoid trivial noise words in lexical analysis
EN_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "has", "he", "in", "is", "it", "its", "of", "on", "that", "the",
    "to", "was", "were", "will", "with", "this", "but", "they", "have",
    "had", "what", "when", "where", "who", "which", "why", "how", "all",
    "any", "both", "each", "few", "more", "most", "other", "some", "such",
    "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very",
    "can", "just", "should", "now", "or", "our", "my", "your", "their",
}


def extract_hashtags(text: str) -> list[str]:
    """Extract all hashtags from text in lowercased canonical form (e.g. ['#tech', '#ai'])."""
    if not text:
        return []
    return [h.lower() for h in HASHTAG_REGEX.findall(text)]


def extract_keywords(text: str) -> list[str]:
    """Extract meaningful unigrams/bigrams from tweet text.

    Preserves Hindi, Hinglish, named entities, and hashtags without aggressive destruction.
    Removes raw URLs and common stopwords.
    """
    if not text:
        return []

    # Strip URLs
    clean_text = re.sub(r"https?://\S+", "", text)
    # Strip user mentions
    clean_text = re.sub(r"@\w+", "", clean_text)
    
    # Tokenize words preserving unicode alphanumeric characters
    tokens = re.findall(r"\b[\w\u0900-\u097F]{3,}\b", clean_text, re.UNICODE)
    
    keywords = [
        tok.lower()
        for tok in tokens
        if tok.lower() not in EN_STOPWORDS and not tok.isdigit()
    ]
    return keywords


def get_window_bounds(dt: datetime, window_minutes: int) -> Tuple[datetime, datetime]:
    """Calculate the aligned chronological start and end for a timestamp.

    Aligns to fixed boundaries from UTC epoch (e.g. :00, :15, :30, :45 for 15m).
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    # Floor minutes to window boundary
    minute = (dt.minute // window_minutes) * window_minutes
    window_start = dt.replace(minute=minute, second=0, microsecond=0)
    window_end = window_start + timedelta(minutes=window_minutes)
    return window_start, window_end


def generate_time_windows(
    start_dt: datetime,
    end_dt: datetime,
    window_minutes: int,
) -> List[Tuple[datetime, datetime]]:
    """Generate all contiguous chronological windows covering start_dt to end_dt."""
    cur_start, _ = get_window_bounds(start_dt, window_minutes)
    _, final_end = get_window_bounds(end_dt, window_minutes)

    windows = []
    w_delta = timedelta(minutes=window_minutes)
    while cur_start < final_end:
        windows.append((cur_start, cur_start + w_delta))
        cur_start += w_delta
    return windows


def compute_windowed_metrics_for_topic(
    topic_tweets: Sequence[Any],
    all_windows: List[Tuple[datetime, datetime]],
    baseline_window_count: int = 8,
    min_support: int = 2,
    baseline_floor: float = 1.0,
) -> List[dict[str, Any]]:
    """Compute temporal mention frequency, velocity, acceleration, and engagement per window.

    Args:
        topic_tweets: Collection of tweet objects assigned to the topic.
        all_windows: Sorted list of (window_start, window_end) tuples.
        baseline_window_count: Number of preceding windows K for baseline average.
        min_support: Minimum mentions required to trigger emergence.
        baseline_floor: Minimum baseline to prevent division by zero.

    Returns:
        List of dicts ready to be persisted into `trend_windows`.
    """
    # Group tweets into windows
    window_tweets: dict[Tuple[datetime, datetime], list[Any]] = defaultdict(list)
    for tweet in topic_tweets:
        t_time = tweet.created_at_utc
        if t_time.tzinfo is None:
            t_time = t_time.replace(tzinfo=timezone.utc)
        else:
            t_time = t_time.astimezone(timezone.utc)
            
        w_bounds = get_window_bounds(t_time, (all_windows[0][1] - all_windows[0][0]).seconds // 60)
        window_tweets[w_bounds].append(tweet)

    results: List[dict[str, Any]] = []
    
    # Track historical velocities for acceleration calculation
    velocities: List[float] = []

    for i, (w_start, w_end) in enumerate(all_windows):
        current_tweets = window_tweets.get((w_start, w_end), [])
        current_mentions = len(current_tweets)

        # Baseline: average of preceding K windows
        start_idx = max(0, i - baseline_window_count)
        preceding_windows = all_windows[start_idx:i]
        
        if preceding_windows:
            preceding_counts = [len(window_tweets.get(w, [])) for w in preceding_windows]
            baseline_mentions = sum(preceding_counts) / len(preceding_counts)
        else:
            baseline_mentions = 0.0

        # Velocity
        vel = calculate_velocity(
            current_mentions=current_mentions,
            baseline_mentions=baseline_mentions,
            min_support=min_support,
            baseline_floor=baseline_floor,
        )

        # Acceleration
        prev_vel = velocities[-1] if velocities else 0.0
        accel = calculate_acceleration(current_velocity=vel, previous_velocity=prev_vel)
        velocities.append(vel)

        # Engagement
        engagement = aggregate_engagement(current_tweets)

        # Only store windows that have activity or are part of an active trend
        results.append({
            "window_start": w_start,
            "window_end": w_end,
            "mention_count": current_mentions,
            "baseline_mentions": baseline_mentions,
            "velocity": vel,
            "acceleration": accel,
            "like_count": engagement["like_count"],
            "repost_count": engagement["repost_count"],
            "reply_count": engagement["reply_count"],
            "quote_count": engagement["quote_count"],
            "tweets": current_tweets,
        })

    return results
