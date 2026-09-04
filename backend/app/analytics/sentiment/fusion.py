"""
Confidence-Aware Sarcasm Fusion Policy (Phase 2B MVP).
"""

from typing import Tuple

# Initial MVP heuristic threshold for uncalibrated generative sequence scores.
# Subject to future evaluation.
SARCASM_HIGH_THRESHOLD = 0.75

def fuse_sentiment_and_sarcasm(
    base_sentiment: str,
    base_confidence: float,
    sarcasm_label: str,
    sarcasm_score: float
) -> Tuple[str, float, str]:
    """
    Fuses base XLM-RoBERTa sentiment with T5 sarcasm detection.
    
    Returns:
        Tuple of (final_sentiment, final_confidence, fusion_status)
    """
    
    # Clean the generated label to handle variations like "derison", "derisonrison", etc.
    # The T5 model primarily generates "normal" or some form of "derison" when sarcasm is detected.
    is_sarcastic = "derison" in sarcasm_label.lower() or "sarcasm" in sarcasm_label.lower()
    
    if not is_sarcastic:
        # Generated label is normal (or at least not recognized as sarcasm)
        return base_sentiment, base_confidence, "NO_SARCASM"
        
    if sarcasm_score < SARCASM_HIGH_THRESHOLD:
        # Detected sarcasm, but score is below confidence threshold
        return base_sentiment, base_confidence, "SARCASM_UNCERTAIN"
        
    # High-confidence sarcasm detected
    if base_sentiment == "negative":
        # Sarcasm on top of negative base confirms negative intent
        return "negative", base_confidence, "SARCASM_CONSISTENT"
        
    else:
        # Sarcasm on top of positive/neutral base is ambiguous.
        # We preserve the original base polarity and confidence, but flag the ambiguity.
        return base_sentiment, base_confidence, "SARCASM_AMBIGUOUS"
