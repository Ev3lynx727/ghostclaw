import pytest
from unittest.mock import MagicMock, patch
from core.pyscn_wrapper import PySCNAnalyzer
from core.analyzer import CodebaseAnalyzer

def test_pyscn_not_available():
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError
        analyzer = PySCNAnalyzer("/fake/path")
        assert analyzer.is_available() is False

def test_pyscn_available():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        analyzer = PySCNAnalyzer("/fake/path")
        assert analyzer.is_available() is True

def test_pyscn_analyze_success():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"clones": [{"file": "a.py"}], "dead_code": ["func_b"]}'
        )
        # First call to is_available
        with patch.object(PySCNAnalyzer, "is_available", return_value=True):
            analyzer = PySCNAnalyzer("/fake/path")
            result = analyzer.analyze()
            assert "clones" in result
            assert len(result["clones"]) == 1
            assert "dead_code" in result
            assert len(result["dead_code"]) == 1

def test_analyzer_integration_with_pyscn(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname='test'")
    (repo / "a.py").write_text("def a(): pass")

    with patch("core.pyscn_wrapper.PySCNAnalyzer.is_available", return_value=True), \
         patch("core.pyscn_wrapper.PySCNAnalyzer.analyze", return_value={
             "clones": [{"file": "a.py"}],
             "dead_code": ["func_b"]
         }):
        analyzer = CodebaseAnalyzer()
        report = analyzer.analyze(str(repo), use_cache=False)

        assert any("Found 1 code clones via pyscn" in g for g in report["architectural_ghosts"])
        assert any("Detected 1 potential dead code spots via pyscn" in i for i in report["issues"])
