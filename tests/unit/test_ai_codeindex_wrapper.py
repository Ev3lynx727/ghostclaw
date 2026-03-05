import pytest
from unittest.mock import MagicMock, patch
from ghostclaw.core.ai_codeindex_wrapper import AICodeIndexWrapper
from ghostclaw.core.analyzer import CodebaseAnalyzer

def test_ai_codeindex_not_available():
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError
        wrapper = AICodeIndexWrapper("/fake/path")
        assert wrapper.is_available() is False

def test_ai_codeindex_available():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        wrapper = AICodeIndexWrapper("/fake/path")
        assert wrapper.is_available() is True

def test_ai_codeindex_build_graph_success():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0
        )
        with patch.object(AICodeIndexWrapper, "is_available", return_value=True):
            wrapper = AICodeIndexWrapper("/fake/path")
            result = wrapper.build_graph()
            assert result == {"status": "success", "engine": "symbols"}

def test_ai_codeindex_build_graph_failure():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="Graph generation failed midway"
        )
        with patch.object(AICodeIndexWrapper, "is_available", return_value=True):
            wrapper = AICodeIndexWrapper("/fake/path")
            result = wrapper.build_graph()
            assert "error" in result
            assert "Graph generation failed midway" in result["error"]

def test_analyzer_integration_with_ai_codeindex(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname='test'")
    (repo / "a.py").write_text("def a(): pass")

    with patch("ghostclaw.core.ai_codeindex_wrapper.AICodeIndexWrapper.is_available", return_value=True), \
         patch("ghostclaw.core.ai_codeindex_wrapper.AICodeIndexWrapper.build_graph", return_value={"nodes": [], "edges": []}), \
         patch("ghostclaw.core.ai_codeindex_wrapper.AICodeIndexWrapper.get_inheritance_depth", return_value={"DeepClass": 5}):
        analyzer = CodebaseAnalyzer()
        report = analyzer.analyze(str(repo), use_cache=False)

        assert any("Deep inheritance hierarchies detected via ai-codeindex: DeepClass" in g for g in report["architectural_ghosts"])
