"""Tests for rule validator."""

import sys
import pytest
from pathlib import Path
from core.validator import RuleValidator

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_node_average_file_size_rule():
    validator = RuleValidator()
    report = {
        "stack": "node",
        "average_lines": 500,
        "large_file_count": 2,
        "coupling_metrics": {}
    }
    result = validator.validate("node", report)
    # Should add issues for average_lines > 200
    issues = result["issues"]
    assert any("Average file size" in i for i in issues)
    # Should add issue for large files
    assert any("files >400 lines" in i for i in issues)


def test_python_average_file_size_rule():
    validator = RuleValidator()
    report = {
        "stack": "python",
        "average_lines": 250,
        "large_file_count": 1,
        "coupling_metrics": {}
    }
    result = validator.validate("python", report)
    issues = result["issues"]
    assert any("Average file size" in i for i in issues)
    assert any("files >300 lines" in i for i in issues)


def test_instability_rule():
    validator = RuleValidator()
    report = {
        "stack": "node",
        "average_lines": 100,
        "large_file_count": 0,
        "coupling_metrics": {
            "unstableModule": {
                "instability": 0.95,
                "efferent": 10
            }
        }
    }
    result = validator.validate("node", report)
    issues = result["issues"]
    assert any("unstableModule" in i and "highly unstable" in i for i in issues)


def test_unknown_stack_passes_through():
    validator = RuleValidator()
    report = {
        "stack": "unknown",
        "average_lines": 100,
        "large_file_count": 0,
        "coupling_metrics": {},
        "issues": [],
        "architectural_ghosts": [],
        "red_flags": []
    }
    result = validator.validate("unknown", report)
    # Should not modify the report (no additional issues)
    assert result["issues"] == []
    assert result["architectural_ghosts"] == []

def test_import_dependency_rule():
    validator = RuleValidator()
    # Mock report for Node.js stack which has forbidden "repositories -> controllers"
    report = {
        "stack": "node",
        "import_edges": [
            ("src.repositories.UserRepo", "src.controllers.UserController")
        ],
        "issues": [],
        "architectural_ghosts": [],
        "red_flags": []
    }
    result = validator.validate("node", report)
    issues = result["issues"]
    assert any("Forbidden dependency" in i for i in issues)
    assert any("UserRepo" in i and "UserController" in i for i in issues)
