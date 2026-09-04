"""Unit tests for Phase 3A Trend & Topic detection metrics, lexical parsing, and labeling.

Strictly mocks ML model boundaries; does not download MiniLM.
"""

from datetime import datetime, timezone
import numpy as np
import pytest

from app.analytics.trends.metrics import (
    calculate_velocity,
    calculate_acceleration,
    aggregate_engagement,
)
from app.analytics.trends.lexical import (
    extract_hashtags,
    extract_keywords,
    get_window_bounds,
    generate_time_windows,
)
from app.analytics.trends.labeling import (
    clean_text_for_tfidf,
    extract_cluster_topic_labels,
)
from app.analytics.trends.clustering import cluster_embeddings


# ==========================================================
# 1. Lexical Extraction & Windowing Tests
# ==========================================================

def test_extract_hashtags():
    text = "Exploring #AI and #DataScience with #TechUpdates!"
    tags = extract_hashtags(text)
    assert tags == ["#ai", "#datascience", "#techupdates"]

    # No hashtags
    assert extract_hashtags("Just plain text without tags") == []
    # Empty text
    assert extract_hashtags("") == []


def test_extract_keywords_preserves_multilingual_and_hinglish():
    text = "AI revolution in Bharat! Kya baat hai #tech https://t.co/xyz @user"
    keywords = extract_keywords(text)
    assert "revolution" in keywords
    assert "bharat" in keywords
    assert "kya" in keywords
    assert "baat" in keywords
    assert "hai" in keywords
    # URLs and handles stripped
    assert "https" not in keywords
    assert "@user" not in keywords


def test_window_bounds_alignment():
    # 15-minute window alignment
    dt1 = datetime(2026, 9, 2, 14, 7, 23, tzinfo=timezone.utc)
    w_start, w_end = get_window_bounds(dt1, window_minutes=15)
    assert w_start == datetime(2026, 9, 2, 14, 0, 0, tzinfo=timezone.utc)
    assert w_end == datetime(2026, 9, 2, 14, 15, 0, tzinfo=timezone.utc)

    dt2 = datetime(2026, 9, 2, 14, 45, 0, tzinfo=timezone.utc)
    w_start2, w_end2 = get_window_bounds(dt2, window_minutes=15)
    assert w_start2 == datetime(2026, 9, 2, 14, 45, 0, tzinfo=timezone.utc)
    assert w_end2 == datetime(2026, 9, 2, 15, 0, 0, tzinfo=timezone.utc)


def test_generate_time_windows():
    start = datetime(2026, 9, 2, 10, 5, tzinfo=timezone.utc)
    end = datetime(2026, 9, 2, 10, 35, tzinfo=timezone.utc)
    windows = generate_time_windows(start, end, window_minutes=15)
    
    # Covers 10:00-10:15, 10:15-10:30, 10:30-10:45
    assert len(windows) == 3
    assert windows[0] == (
        datetime(2026, 9, 2, 10, 0, tzinfo=timezone.utc),
        datetime(2026, 9, 2, 10, 15, tzinfo=timezone.utc),
    )
    assert windows[-1] == (
        datetime(2026, 9, 2, 10, 30, tzinfo=timezone.utc),
        datetime(2026, 9, 2, 10, 45, tzinfo=timezone.utc),
    )


# ==========================================================
# 2. Velocity, Acceleration, and Smoothing Tests
# ==========================================================

def test_velocity_minimum_support_gate():
    # 0 -> 1 mention must yield 0.0 velocity (does not spike to infinity)
    vel = calculate_velocity(current_mentions=1, baseline_mentions=0.0, min_support=2)
    assert vel == 0.0

    # 0 mentions yields 0.0
    vel_zero = calculate_velocity(current_mentions=0, baseline_mentions=10.0, min_support=2)
    assert vel_zero == 0.0


def test_velocity_zero_baseline_smoothing():
    # With min_support=2, going from 0 to 4 mentions uses baseline floor of 1.0 -> 4.0x
    vel = calculate_velocity(
        current_mentions=4,
        baseline_mentions=0.0,
        min_support=2,
        baseline_floor=1.0,
    )
    assert vel == 4.0


def test_velocity_regular_calculation():
    # Normal baseline: 20 mentions with baseline of 5 -> 4.0x
    vel = calculate_velocity(current_mentions=20, baseline_mentions=5.0, min_support=2)
    assert vel == 4.0

    # High volume, low growth: 100 mentions with baseline of 100 -> 1.0x
    vel_pop = calculate_velocity(current_mentions=100, baseline_mentions=100.0, min_support=2)
    assert vel_pop == 1.0


def test_acceleration_calculation():
    # Growth speeding up
    accel_up = calculate_acceleration(current_velocity=3.5, previous_velocity=1.5)
    assert accel_up == 2.0

    # Growth slowing down
    accel_down = calculate_acceleration(current_velocity=1.0, previous_velocity=2.5)
    assert accel_down == -1.5


def test_aggregate_engagement():
    class MockTweet:
        def __init__(self, likes, reposts, replies, quotes):
            self.like_count = likes
            self.retweet_count = reposts  # schema name
            self.reply_count = replies
            self.quote_count = quotes

    tweets = [
        MockTweet(10, 2, 1, 0),
        MockTweet(5, 3, 2, 1),
    ]
    eng = aggregate_engagement(tweets)
    assert eng["like_count"] == 15
    assert eng["repost_count"] == 5
    assert eng["reply_count"] == 3
    assert eng["quote_count"] == 1


# ==========================================================
# 3. Labeling and Clustering Unit Tests
# ==========================================================

def test_clean_text_for_tfidf():
    raw = "Breaking news https://t.co/abc @CNN artificial intelligence is booming"
    cleaned = clean_text_for_tfidf(raw)
    assert "https" not in cleaned
    assert "@CNN" not in cleaned
    assert "artificial intelligence is booming" in cleaned


def test_extract_cluster_topic_labels_deterministic():
    cluster_texts = {
        0: [
            "artificial intelligence and machine learning advancements",
            "future of artificial intelligence models and intelligence chips",
            "cutting edge machine learning and intelligence systems",
        ],
        1: [
            "premier league football championship victory and sports match",
            "football match highlights and sports goals in the league",
        ],
    }

    labels = extract_cluster_topic_labels(cluster_texts, top_n_terms=3)
    
    assert 0 in labels
    assert 1 in labels
    
    label_0, terms_0 = labels[0]
    label_1, terms_1 = labels[1]
    
    # Label should be deterministic top terms joined by ' / '
    assert "intelligence" in label_0 or "artificial" in label_0 or "machine" in label_0
    assert "football" in label_1 or "league" in label_1 or "sports" in label_1
    assert len(terms_0) <= 3
    assert len(terms_1) <= 3


def test_cluster_embeddings_insufficient_samples():
    # When fewer samples than min_cluster_size, all should be marked as noise (-1)
    fake_embeddings = np.random.randn(2, 384).astype(np.float32)
    labels, probs = cluster_embeddings(fake_embeddings, min_cluster_size=5)
    
    assert len(labels) == 2
    assert (labels == -1).all()
    assert (probs == 0.0).all()


def test_cluster_embeddings_mock_clusters():
    # 3 points tightly clustered at origin, 3 tightly clustered at (10, 10)
    np.random.seed(42)
    c1 = np.random.normal(loc=0.0, scale=0.01, size=(5, 10))
    c2 = np.random.normal(loc=1.0, scale=0.01, size=(5, 10))
    outlier = np.array([[5.0] * 10])
    
    data = np.vstack([c1, c2, outlier])
    labels, probs = cluster_embeddings(data, min_cluster_size=3, min_samples=2, metric="euclidean")
    
    assert len(labels) == 11
    # Check that at least 2 distinct clusters were detected
    non_noise = [lbl for lbl in labels if lbl != -1]
    assert len(set(non_noise)) >= 2
