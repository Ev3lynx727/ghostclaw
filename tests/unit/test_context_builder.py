import pytest
from ghostclaw.core.context_builder import ContextBuilder

def test_build_prompt_with_symbols():
    builder = ContextBuilder()
    metrics = {"total_files": 1}
    issues = ["Test issue"]
    
    # Test with empty symbols
    prompt_flat = builder.build_prompt(metrics, issues, [], [], {}, [])
    assert "<symbols>" not in prompt_flat
    
    # Test with symbol index
    symbol_data = "Class: User\nMethod: login"
    prompt_rich = builder.build_prompt(metrics, issues, [], [], {}, [], symbol_index=symbol_data)
    
    assert "<symbols>" in prompt_rich
    assert symbol_data in prompt_rich
    assert "</symbols>" in prompt_rich
