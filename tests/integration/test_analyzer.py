"""Integration tests for CodebaseAnalyzer."""

import sys
import pytest
from pathlib import Path
from ghostclaw.core.analyzer import CodebaseAnalyzer

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_analyze_node_repo(tmp_path):
    # Setup Node repo with large files
    (tmp_path / "package.json").write_text('{"name": "test"}')
    # Create a file with 500 lines (each line "x")
    (tmp_path / "index.js").write_text("\n".join(["x"] * 500))

    analyzer = CodebaseAnalyzer()
    report = analyzer.analyze(str(tmp_path))

    assert report["stack"] == "node"
    assert report["files_analyzed"] >= 1
    assert report["vibe_score"] < 100  # Should penalize large file
    assert any("files >400 lines" in i for i in report["issues"])


def test_analyze_python_repo_with_circular_imports(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='test'")
    (tmp_path / "a.py").write_text("from b import x\n")
    (tmp_path / "b.py").write_text("from a import y\n")

    analyzer = CodebaseAnalyzer()
    report = analyzer.analyze(str(tmp_path))

    assert report["stack"] == "python"
    assert any("Circular dependency" in i for i in report["issues"])


def test_analyze_unknown_stack(tmp_path):
    # Empty dir
    analyzer = CodebaseAnalyzer()
    report = analyzer.analyze(str(tmp_path))
    assert report["stack"] == "unknown"
    assert "Standard stack detection failed" in report["issues"][0]
