"""Tests for Python import coupling analysis."""

import sys
import pytest
from pathlib import Path
from core.coupling import PythonImportAnalyzer

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def create_python_repo(tmp_path: Path, structure: dict):
    """Helper to create a Python repo from a dict of {relpath: content}."""
    for relpath, content in structure.items():
        p = tmp_path / relpath
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)


def test_no_imports(tmp_path):
    create_python_repo(tmp_path, {
        "module.py": "def foo():\n    return 1\n"
    })
    analyzer = PythonImportAnalyzer(str(tmp_path))
    report = analyzer.analyze()
    assert report["circular_dependencies"] == []
    assert len(report["issues"]) == 0
    # Should have one module with 0 afferent/efferent
    assert len(report["coupling_metrics"]) == 1


def test_simple_chain(tmp_path):
    create_python_repo(tmp_path, {
        "a.py": "from b import get\n",
        "b.py": "from c import value\n",
        "c.py": "CONST = 1\n"
    })
    analyzer = PythonImportAnalyzer(str(tmp_path))
    report = analyzer.analyze()
    # No cycles
    assert len(report["circular_dependencies"]) == 0
    metrics = report["coupling_metrics"]
    # a imports b -> a efferent=1, b afferent=1
    assert metrics["a"]["efferent"] == 1
    assert metrics["b"]["afferent"] == 1
    assert metrics["b"]["efferent"] == 1
    assert metrics["c"]["afferent"] == 1


def test_circular_dependency(tmp_path):
    create_python_repo(tmp_path, {
        "a.py": "from b import x\n",
        "b.py": "from a import y\n"
    })
    analyzer = PythonImportAnalyzer(str(tmp_path))
    report = analyzer.analyze()
    assert len(report["circular_dependencies"]) >= 1
    # Check that a cycle appears in issues/ghosts
    issues = " ".join(report["issues"])
    assert "Circular dependency" in issues
