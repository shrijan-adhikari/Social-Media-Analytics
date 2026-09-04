"""Deterministic topic labeling using class-based TF-IDF.

Extracts top representative terms and constructs explainable topic titles
without relying on non-deterministic LLM generation.
"""

from typing import Dict, List, Tuple
import re
from sklearn.feature_extraction.text import TfidfVectorizer

from app.analytics.trends.config import DEFAULT_TREND_CONFIG


def clean_text_for_tfidf(text: str) -> str:
    """Strip URLs and user mentions to leave pure topical content for TF-IDF."""
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"@\w+", "", text)
    return text.strip()


def extract_cluster_topic_labels(
    cluster_texts: Dict[int, List[str]],
    top_n_terms: int = DEFAULT_TREND_CONFIG.TOPIC_TOP_TERMS_COUNT,
) -> Dict[int, Tuple[str, List[str]]]:
    """Extract representative terms and construct human-readable labels for each cluster.

    Args:
        cluster_texts: Mapping from cluster_id (e.g. 0, 1, 2) to list of tweet text strings.
                       Noise cluster (-1) should typically be excluded before calling.
        top_n_terms: Number of representative keywords/phrases to retain per topic.

    Returns:
        Dict mapping cluster_id to (display_label, representative_terms_list)
        Example: {0: ("ai / artificial intelligence / data centers", ["ai", "artificial intelligence", ...])}
    """
    if not cluster_texts:
        return {}

    # Aggregate each cluster into a single document
    cluster_ids = sorted(cluster_texts.keys())
    documents = [
        " ".join([clean_text_for_tfidf(t) for t in cluster_texts[cid]])
        for cid in cluster_ids
    ]

    # Fit TF-IDF across the cluster documents
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        stop_words="english",
        max_features=5000,
        min_df=1,
        token_pattern=r"(?u)\b[\w#]{2,}\b",
    )

    try:
        tfidf_matrix = vectorizer.fit_transform(documents)
        feature_names = vectorizer.get_feature_names_out()
    except ValueError:
        # Fallback if vocabulary is empty or only stopwords
        return {
            cid: (f"Topic Cluster {cid}", [f"cluster_{cid}"])
            for cid in cluster_ids
        }

    results: Dict[int, Tuple[str, List[str]]] = {}

    for doc_idx, cid in enumerate(cluster_ids):
        row = tfidf_matrix.getrow(doc_idx).toarray().flatten()
        # Top indices with non-zero weights
        top_indices = row.argsort()[::-1][:top_n_terms]
        
        rep_terms = [
            feature_names[idx]
            for idx in top_indices
            if row[idx] > 0
        ]

        if not rep_terms:
            rep_terms = [f"cluster_{cid}"]

        # Human-readable title: top 3 terms joined by " / "
        display_label = " / ".join(rep_terms[:3])
        results[cid] = (display_label, rep_terms)

    return results
