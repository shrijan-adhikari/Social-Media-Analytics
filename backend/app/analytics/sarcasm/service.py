import math
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import logging

from app.analytics.sarcasm.preprocessing import preprocess_sarcasm_text

logger = logging.getLogger(__name__)

class SarcasmService:
    """
    Sarcasm detection service wrapping the T5 sequence-to-sequence model.
    """
    
    def __init__(self, model_id: str = "mrm8488/t5-base-finetuned-sarcasm-twitter"):
        self.model_id = model_id
        # Prefer GPU if available, else CPU (as per Phase 1 resource constraints)
        if torch.cuda.is_available():
            self.device = "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            self.device = "mps"
        else:
            self.device = "cpu"
            
        logger.info(f"Initializing SarcasmService with {self.model_id} on {self.device}")
        
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_id)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_id).to(self.device)
        self.pipeline_version = "v1"
        self.model_revision = getattr(self.model.config, "_commit_hash", "unknown")

    def analyze_text(self, text: str) -> dict:
        """
        Analyze a single text for sarcasm.
        
        Returns a dictionary with:
        - label (str): 'derison' or 'normal' (as output by the model)
        - score (float): UNCALIBRATED proxy score derived from generated tokens
        - model_id, model_revision, pipeline_version
        """
        if not text.strip():
            return self._build_result("normal", 0.0)

        preprocessed = preprocess_sarcasm_text(text)
        
        # Testing indicates 'recognize sarcasm: ' yields the most stable outputs
        # for this checkpoint when used manually
        input_text = f"recognize sarcasm: {preprocessed}</s>"
        
        inputs = self.tokenizer(input_text, return_tensors="pt", max_length=512, truncation=True).to(self.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                inputs.input_ids,
                max_new_tokens=5,
                return_dict_in_generate=True,
                output_scores=True
            )
            
        # Decode the full label
        generated_sequence = outputs.sequences[0]
        label = self.tokenizer.decode(generated_sequence, skip_special_tokens=True).strip().lower()
        
        # Calculate proxy score from all generated tokens
        # transition_scores[0] contains log probabilities for each generated token
        transition_scores = self.model.compute_transition_scores(
            outputs.sequences, outputs.scores, normalize_logits=True
        )
        seq_log_prob = transition_scores[0].sum().item()
        proxy_score = math.exp(seq_log_prob)
        
        return self._build_result(label, proxy_score)

    def analyze_batch(self, texts: list[str]) -> list[dict]:
        """Process a batch of texts for sarcasm."""
        return [self.analyze_text(t) for t in texts]
        
    def _build_result(self, label: str, score: float) -> dict:
        return {
            "label": label,
            "score": score,
            "model_id": self.model_id,
            "model_revision": self.model_revision,
            "pipeline_version": self.pipeline_version
        }
