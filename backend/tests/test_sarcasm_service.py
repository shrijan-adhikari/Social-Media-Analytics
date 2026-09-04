import pytest
from unittest.mock import patch, MagicMock

from app.analytics.sarcasm.preprocessing import preprocess_sarcasm_text
from app.analytics.sarcasm.service import SarcasmService

def test_preprocess_sarcasm_text():
    # Replace users
    assert preprocess_sarcasm_text("Hello @john_doe!") == "Hello @USER!"
    # Replace URLs
    assert preprocess_sarcasm_text("Check out http://t.co/xyz") == "Check out URL"
    # Both
    assert preprocess_sarcasm_text("@alice see https://example.com") == "@USER see URL"

@pytest.fixture
def mock_transformers():
    with patch("app.analytics.sarcasm.service.AutoTokenizer") as mock_tokenizer, \
         patch("app.analytics.sarcasm.service.AutoModelForSeq2SeqLM") as mock_model:
        
        # Setup mock model
        model_instance = mock_model.from_pretrained.return_value.to.return_value
        model_instance.config._commit_hash = "fake-commit-123"
        
        # Setup mock output
        mock_output = MagicMock()
        mock_output.sequences = [[0, 1, 2]]
        mock_output.scores = (torch_mock_scores(),) # Fake scores
        
        model_instance.generate.return_value = mock_output
        model_instance.compute_transition_scores.return_value = [torch_mock_transition_scores()]
        
        # Setup mock tokenizer
        tokenizer_instance = mock_tokenizer.from_pretrained.return_value
        tokenizer_instance.decode.return_value = "derison"
        
        yield tokenizer_instance, model_instance

def torch_mock_scores():
    import torch
    return torch.tensor([[0.1, 0.9, 0.0]])

def torch_mock_transition_scores():
    import torch
    import math
    # log prob of 0.8
    return torch.tensor([math.log(0.8)])

def test_sarcasm_service_inference(mock_transformers):
    tokenizer, model = mock_transformers
    service = SarcasmService()
    
    result = service.analyze_text("Some text")
    
    assert result["label"] == "derison"
    # math.exp(math.log(0.8)) should be approx 0.8
    assert abs(result["score"] - 0.8) < 1e-5
    assert result["model_revision"] == "fake-commit-123"
