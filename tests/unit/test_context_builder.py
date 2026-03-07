import pytest
from ghostclaw.core.context_builder import ContextBuilder
import json

def test_context_builder():
    builder = ContextBuilder()
    prompt = builder.build_prompt(
        metrics={"vibe_score": 80},
        issues=["Bad layer"],
        ghosts=["AuthGhost"],
        flags=["Flag1"],
        coupling_metrics={"instability": 0.9},
        import_edges=[("A", "B")]
    )

    assert "<metrics>" in prompt
    assert '"vibe_score": 80' in prompt
    assert "<issues>" in prompt
    assert "- Bad layer" in prompt
    assert "<ghosts>" in prompt
    assert "- AuthGhost" in prompt
    assert "<flags>" in prompt
    assert "- Flag1" in prompt
    assert "<coupling_metrics>" in prompt
    assert '"instability": 0.9' in prompt
    assert "<import_edges>" in prompt
    assert "A -> B" in prompt
