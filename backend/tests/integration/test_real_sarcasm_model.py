import pytest
from app.analytics.sarcasm.service import SarcasmService

@pytest.mark.integration
def test_real_sarcasm_model_inference():
    """Smoke test using the real T5 model."""
    service = SarcasmService()
    
    # Positive literal
    res1 = service.analyze_text("This update is genuinely excellent.")
    assert "label" in res1
    assert "score" in res1
    
    # Sarcastic
    res2 = service.analyze_text("Great, exactly what I needed today \U0001f644")
    assert res2["label"] in ["derison", "normal"] # Depending on model confidence
    
    # Test batch
    batch_res = service.analyze_batch([
        "This update is genuinely excellent.",
        "Great, exactly what I needed today \U0001f644"
    ])
    assert len(batch_res) == 2
    assert batch_res[0]["label"] == res1["label"]
