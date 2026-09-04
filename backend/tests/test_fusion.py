import pytest
from app.analytics.sentiment.fusion import fuse_sentiment_and_sarcasm, SARCASM_HIGH_THRESHOLD

def test_fusion_no_sarcasm():
    final_sent, final_conf, status = fuse_sentiment_and_sarcasm("positive", 0.9, "normal", 0.9)
    assert final_sent == "positive"
    assert final_conf == 0.9
    assert status == "NO_SARCASM"

def test_fusion_sarcasm_uncertain():
    # Sarcasm generated, but score < threshold
    final_sent, final_conf, status = fuse_sentiment_and_sarcasm("negative", 0.8, "derison", SARCASM_HIGH_THRESHOLD - 0.1)
    assert final_sent == "negative"
    assert final_conf == 0.8
    assert status == "SARCASM_UNCERTAIN"

def test_fusion_sarcasm_consistent():
    # High confidence sarcasm + negative base
    final_sent, final_conf, status = fuse_sentiment_and_sarcasm("negative", 0.7, "derison", SARCASM_HIGH_THRESHOLD + 0.1)
    assert final_sent == "negative"
    assert final_conf == 0.7
    assert status == "SARCASM_CONSISTENT"

def test_fusion_sarcasm_ambiguous_positive():
    # High confidence sarcasm + positive base
    final_sent, final_conf, status = fuse_sentiment_and_sarcasm("positive", 0.85, "derison", SARCASM_HIGH_THRESHOLD + 0.1)
    assert final_sent == "positive"
    assert final_conf == 0.85
    assert status == "SARCASM_AMBIGUOUS"

def test_fusion_sarcasm_ambiguous_neutral():
    # High confidence sarcasm + neutral base
    final_sent, final_conf, status = fuse_sentiment_and_sarcasm("neutral", 0.6, "derison", SARCASM_HIGH_THRESHOLD + 0.1)
    assert final_sent == "neutral"
    assert final_conf == 0.6
    assert status == "SARCASM_AMBIGUOUS"
