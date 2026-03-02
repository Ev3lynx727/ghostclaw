import pytest
import json
from unittest.mock import MagicMock, patch
from mcp.server import ghostclaw_analyze, ghostclaw_get_ghosts, ghostclaw_refactor_plan

def test_ghostclaw_analyze_invalid_path():
    result = ghostclaw_analyze("/invalid/path")
    data = json.loads(result)
    assert "error" in data

def test_ghostclaw_analyze_success(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname='test'")

    with patch("core.analyzer.CodebaseAnalyzer.analyze") as mock_analyze:
        mock_analyze.return_value = {"vibe_score": 100}
        result = ghostclaw_analyze(str(repo))
        data = json.loads(result)
        assert data["vibe_score"] == 100

def test_ghostclaw_get_ghosts_success(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname='test'")

    with patch("core.analyzer.CodebaseAnalyzer.analyze") as mock_analyze:
        mock_analyze.return_value = {"architectural_ghosts": ["Ghost1"]}
        result = ghostclaw_get_ghosts(str(repo))
        data = json.loads(result)
        assert "Ghost1" in data["architectural_ghosts"]

def test_ghostclaw_refactor_plan_success(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname='test'")

    with patch("core.analyzer.CodebaseAnalyzer.analyze") as mock_analyze:
        mock_analyze.return_value = {"issues": ["Issue1"], "architectural_ghosts": ["Ghost1"]}
        result = ghostclaw_refactor_plan(str(repo))
        assert "### Ghostclaw Refactor Blueprint" in result
        assert "Issue1" in result
        assert "Ghost1" in result
