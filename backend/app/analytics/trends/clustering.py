"""HDBSCAN clustering for semantic tweet topic discovery.

Clustering dense sentence embeddings into coherent narrative clusters without
requiring a predetermined topic count. Outliers/noise (-1) are preserved as valid
first-class states rather than forced into artificial clusters.
"""

from typing import Tuple
import logging
import numpy as np
from sklearn.cluster import HDBSCAN

from app.analytics.trends.config import DEFAULT_TREND_CONFIG

logger = logging.getLogger(__name__)


def cluster_embeddings(
    embeddings: np.ndarray,
    min_cluster_size: int = DEFAULT_TREND_CONFIG.HDBSCAN_MIN_CLUSTER_SIZE,
    min_samples: int = DEFAULT_TREND_CONFIG.HDBSCAN_MIN_SAMPLES,
    metric: str = DEFAULT_TREND_CONFIG.HDBSCAN_METRIC,
) -> Tuple[np.ndarray, np.ndarray]:
    """Execute HDBSCAN clustering on normalized sentence embeddings.

    Args:
        embeddings: Array of shape (N, 384) representing tweet embeddings.
        min_cluster_size: Minimum number of tweets to form a distinct topic.
        min_samples: Conservative core sample parameter for noise isolation.
        metric: Distance metric ('cosine' or 'euclidean').

    Returns:
        Tuple of:
            labels: 1D int array of length N (cluster IDs, or -1 for noise/outliers)
            probabilities: 1D float array of length N (membership confidence in [0, 1])
    """
    n_samples = len(embeddings)
    if n_samples < min_cluster_size:
        logger.warning(
            f"Insufficient samples ({n_samples}) for min_cluster_size ({min_cluster_size}). "
            "All tweets marked as noise outliers (-1)."
        )
        return (
            np.full(n_samples, -1, dtype=int),
            np.zeros(n_samples, dtype=float),
        )

    # Scikit-learn HDBSCAN execution
    clusterer = HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric=metric,
        copy=True,
    )
    
    labels = clusterer.fit_predict(embeddings)
    probabilities = getattr(clusterer, "probabilities_", np.ones(n_samples, dtype=float))

    unique_clusters = set(labels) - {-1}
    noise_count = int(np.sum(labels == -1))
    logger.info(
        f"HDBSCAN clustering completed: {len(unique_clusters)} semantic clusters formed, "
        f"{noise_count}/{n_samples} tweets classified as noise/outliers."
    )

    return labels, probabilities
