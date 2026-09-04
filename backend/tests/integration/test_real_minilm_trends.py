"""Integration and smoke test for real sentence-transformers/all-MiniLM-L6-v2 checkpoint.

Verifies:
- Checkpoint loads from HuggingFace
- Produces valid 384-dimensional dense embeddings
- No NaN or Inf values
- Embeddings are unit-normalized
- HDBSCAN clustering executes on real embeddings
- Topic labeling functions on real clusters
"""

import numpy as np
import pytest

from app.analytics.trends.embeddings import MiniLMEmbeddingService
from app.analytics.trends.clustering import cluster_embeddings
from app.analytics.trends.labeling import extract_cluster_topic_labels


@pytest.mark.integration
def test_real_minilm_embedding_and_clustering_smoke():
    """Smoke test running real MiniLM embedding and HDBSCAN clustering."""
    service = MiniLMEmbeddingService()

    # Small controlled sample of tweets
    sample_texts = [
        "Artificial intelligence and deep learning models are advancing rapidly in 2026.",
        "New breakthroughs in generative AI and large language model architectures.",
        "State of the art machine learning chips and AI hardware infrastructure.",
        "The football match was thrilling with a last minute goal victory.",
        "Premier league soccer highlights and outstanding sports championship performance.",
        "Completely random standalone sentence with no relation to the others.",
    ]

    # 1. Verify embedding generation
    embeddings = service.embed_texts(sample_texts, batch_size=2)
    
    assert embeddings is not None
    assert embeddings.shape == (len(sample_texts), 384)
    assert not np.isnan(embeddings).any(), "Embeddings contain NaN values"
    assert not np.isinf(embeddings).any(), "Embeddings contain Inf values"

    # 2. Verify L2 normalization
    norms = np.linalg.norm(embeddings, axis=1)
    np.testing.assert_allclose(norms, 1.0, atol=1e-5)

    # 3. Verify HDBSCAN clustering
    labels, probs = cluster_embeddings(embeddings, min_cluster_size=2, min_samples=1, metric="cosine")
    
    assert len(labels) == len(sample_texts)
    assert len(probs) == len(sample_texts)

    # 4. Verify topic labeling
    cluster_texts = {}
    for text, c_id in zip(sample_texts, labels):
        if c_id >= 0:
            cluster_texts.setdefault(c_id, []).append(text)

    if cluster_texts:
        topic_labels = extract_cluster_topic_labels(cluster_texts, top_n_terms=3)
        assert len(topic_labels) == len(cluster_texts)
        for c_id, (label, terms) in topic_labels.items():
            assert isinstance(label, str)
            assert len(label) > 0
            assert isinstance(terms, list)
            assert len(terms) > 0
