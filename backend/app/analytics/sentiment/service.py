"""Sentiment inference service.

Wraps the Hugging Face transformer model, tokenizer, and handles batching.
"""

import logging
from typing import Any, Dict, List, Optional

import torch
import torch.nn.functional as F
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from app.analytics.sentiment.preprocessing import preprocess_tweet

logger = logging.getLogger(__name__)

MODEL_ID = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
PIPELINE_VERSION = "1.0.0"


class SentimentService:
    """Primary sentiment inference wrapper."""

    def __init__(self, model_id: str = MODEL_ID):
        self.model_id = model_id
        
        # Select device safely: respect local VRAM limits, fallback to CPU
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Initializing SentimentService with {self.model_id} on {self.device}")
        
        # Load tokenizer and model.
        # This will download the weights automatically and cache them locally if needed.
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_id)
        self.model = AutoModelForSequenceClassification.from_pretrained(self.model_id)
        self.model.to(self.device)
        self.model.eval()
        
        self.config = self.model.config
        # Attempt to grab the commit hash if the config has it
        self.model_revision = getattr(self.config, "_commit_hash", None)

    def analyze_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """Run sentiment inference on a batch of raw tweet texts."""
        if not texts:
            return []

        # Preprocess
        clean_texts = [preprocess_tweet(t) for t in texts]

        # Tokenize
        inputs = self.tokenizer(
            clean_texts, return_tensors="pt", padding=True, truncation=True, max_length=512
        ).to(self.device)

        # Inference
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            # Softmax to get probabilities (0 to 1)
            probs = F.softmax(logits, dim=-1)

        results = []
        for i in range(len(texts)):
            prob_tensor = probs[i].cpu().numpy()
            
            # The model outputs probabilities matching its config's id2label.
            # We map the labels carefully. cardiffnlp uses:
            # 0: negative, 1: neutral, 2: positive (usually, but we verify via config)
            mapped_probs = {"negative": 0.0, "neutral": 0.0, "positive": 0.0}
            
            for label_idx, prob in enumerate(prob_tensor):
                label_str = self.config.id2label[label_idx].lower()
                # Map expected model label variants to our standard names
                if label_str in ("negative", "neg"):
                    mapped_probs["negative"] = float(prob)
                elif label_str in ("neutral", "neu"):
                    mapped_probs["neutral"] = float(prob)
                elif label_str in ("positive", "pos"):
                    mapped_probs["positive"] = float(prob)

            # Determine predicted label
            predicted_label = max(mapped_probs, key=mapped_probs.get)
            confidence = mapped_probs[predicted_label]

            results.append({
                "negative_probability": mapped_probs["negative"],
                "neutral_probability": mapped_probs["neutral"],
                "positive_probability": mapped_probs["positive"],
                "base_sentiment": predicted_label,
                "base_confidence": confidence,
                "model_id": self.model_id,
                "model_revision": self.model_revision,
                "pipeline_version": PIPELINE_VERSION,
            })

        return results

    def analyze_text(self, text: str) -> Dict[str, Any]:
        """Convenience method for a single text."""
        return self.analyze_batch([text])[0]
