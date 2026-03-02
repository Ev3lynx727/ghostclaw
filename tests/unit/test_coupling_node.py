"""Tests for Node.js import coupling analysis."""

import sys
import pytest
from pathlib import Path
from core.node_coupling import NodeImportAnalyzer

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def create_node_repo(tmp_path: Path, structure: dict):
    for relpath, content in structure.items():
        p = tmp_path / relpath
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)


def test_simple_imports(tmp_path):
    create_node_repo(tmp_path, {
        "a.js": "const b = require('./b');\n",
        "b.js": "const c = require('./c');\n",
        "c.js": "module.exports = 1;\n"
    })
    analyzer = NodeImportAnalyzer(str(tmp_path))
    report = analyzer.analyze()
    metrics = report["coupling_metrics"]
    assert "a" in metrics
    assert metrics["a"]["efferent"] == 1
    assert metrics["b"]["afferent"] == 1


def test_circular_dependency(tmp_path):
    create_node_repo(tmp_path, {
        "a.js": "const b = require('./b');\n",
        "b.js": "const a = require('./a');\n"
    })
    analyzer = NodeImportAnalyzer(str(tmp_path))
    report = analyzer.analyze()
    assert len(report["circular_dependencies"]) >= 1


def test_entry_point_not_flagged_as_unstable(tmp_path):
    """
    Modules in entry point directories (scripts, bin, cli) should not be flagged
    as 'highly unstable' even if they have high efferent coupling.
    """
    # Create many core modules
    structure = {
        **{f"core/{chr(97+i)}.js": "" for i in range(10)},  # a.js through j.js
        "scripts/main.js": "\n".join([f"const {m} = require('../core/{m}');" for m in "abcdefghij"]),
    }
    create_node_repo(tmp_path, structure)

    analyzer = NodeImportAnalyzer(str(tmp_path))
    report = analyzer.analyze()

    all_issues = " ".join(report["issues"] + report["architectural_ghosts"])
    # The scripts.main module should not be flagged as unstable
    assert "scripts.main" not in all_issues
