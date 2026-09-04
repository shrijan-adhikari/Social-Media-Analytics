"""Configuration and default hyperparameters for Trend & Topic Detection (Phase 3A).

Centralizes all windowing thresholds, baseline heuristics, and HDBSCAN parameters.
"""

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass(frozen=True)
class TrendConfig:
    """Centralized configuration for lexical and semantic trend analysis."""

    # Windowing parameters
    TREND_WINDOW_MINUTES: int = 15
    BASELINE_WINDOW_COUNT: int = 8  # 8 * 15m = 2-hour baseline window span
    
    # Velocity & smoothing thresholds
    MIN_SUPPORT_MENTIONS: int = 2   # Minimum mentions in current window to be eligible for emergence
    BASELINE_FLOOR: float = 1.0     # Baseline floor to prevent zero-division and 0->1 infinity spikes
    
    # Semantic embedding model
    EMBEDDING_MODEL_ID: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_BATCH_SIZE: int = 32
    
    # HDBSCAN baseline hyperparameters (configurable, not claimed to be optimal)
    HDBSCAN_MIN_CLUSTER_SIZE: int = 3
    HDBSCAN_MIN_SAMPLES: int = 2
    HDBSCAN_METRIC: str = "cosine"
    
    # Labeling parameters
    TOPIC_TOP_TERMS_COUNT: int = 5
    
    # Pipeline metadata
    PIPELINE_VERSION: str = "v1"

    def get_hdbscan_params(self) -> Dict[str, Any]:
        """Return HDBSCAN parameters as serializable dict for provenance logging."""
        return {
            "min_cluster_size": self.HDBSCAN_MIN_CLUSTER_SIZE,
            "min_samples": self.HDBSCAN_MIN_SAMPLES,
            "metric": self.HDBSCAN_METRIC,
        }


DEFAULT_TREND_CONFIG = TrendConfig()
