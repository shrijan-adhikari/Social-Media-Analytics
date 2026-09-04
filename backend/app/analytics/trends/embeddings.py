"""Semantic embedding service using sentence-transformers/all-MiniLM-L6-v2.

PRIMARY / APPROVED model for semantic topic discovery and dense representation.

CRITICAL MULTILINGUAL LIMITATION NOTE:
all-MiniLM-L6-v2 is trained primarily on English sentence pairs (~1B+ pairs).
For Hindi (Devanagari script) and mixed Hinglish, its tokenization splits unfamiliar
characters into byte fallbacks, and semantic clustering performance degrades.
Per project constraints, we preserve this approved model for the MVP and explicitly
document this limitation rather than silently substituting unapproved checkpoints.
Multilingual alternatives (e.g. paraphrase-multilingual-MiniLM-L12-v2) remain
evaluation candidates for future phases.
"""

from typing import List, Optional, Tuple
import logging
import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer

from app.analytics.trends.config import DEFAULT_TREND_CONFIG

logger = logging.getLogger(__name__)


def mean_pooling(model_output: Any, attention_mask: torch.Tensor) -> torch.Tensor:
    """Perform mean pooling over token embeddings taking attention mask into account."""
    token_embeddings = model_output[0]  # First element contains hidden state tokens
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, dim=1)
    sum_mask = torch.clamp(input_mask_expanded.sum(dim=1), min=1e-9)
    return sum_embeddings / sum_mask


class MiniLMEmbeddingService:
    """Batch embedding service for sentence-transformers/all-MiniLM-L6-v2."""

    def __init__(self, model_id: str = DEFAULT_TREND_CONFIG.EMBEDDING_MODEL_ID):
        self.model_id = model_id
        
        # Hardware selection
        if torch.cuda.is_available():
            self.device = "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            self.device = "mps"
        else:
            self.device = "cpu"

        logger.info(f"Initializing MiniLMEmbeddingService with {self.model_id} on {self.device}")

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_id)
        self.model = AutoModel.from_pretrained(self.model_id).to(self.device)
        self.model.eval()

        # Resolve immutable revision hash if available
        self.model_revision: Optional[str] = getattr(self.model.config, "_commit_hash", None)

    def embed_texts(
        self,
        texts: List[str],
        batch_size: int = DEFAULT_TREND_CONFIG.EMBEDDING_BATCH_SIZE,
    ) -> np.ndarray:
        """Compute 384-dimensional normalized dense embeddings for a list of texts in batches.

        Args:
            texts: List of tweet text strings.
            batch_size: Number of sentences to encode per forward pass.

        Returns:
            np.ndarray: Array of shape (len(texts), 384), L2-normalized.
        """
        if not texts:
            return np.empty((0, 384), dtype=np.float32)

        all_embeddings: List[np.ndarray] = []

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i : i + batch_size]
            
            # Tokenize batch
            encoded_input = self.tokenizer(
                batch_texts,
                padding=True,
                truncation=True,
                max_length=256,
                return_tensors="pt",
            ).to(self.device)

            with torch.no_grad():
                model_output = self.model(**encoded_input)
                # Mean pooling
                sentence_embeddings = mean_pooling(model_output, encoded_input["attention_mask"])
                # L2 normalize so cosine distance equals euclidean distance
                sentence_embeddings = torch.nn.functional.normalize(sentence_embeddings, p=2, dim=1)

            all_embeddings.append(sentence_embeddings.cpu().numpy())

        return np.vstack(all_embeddings).astype(np.float32)
