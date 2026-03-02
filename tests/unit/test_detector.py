"""Tests for core stack detector."""

import sys
import os
import pytest
from pathlib import Path
from core.detector import detect_stack, find_files

# Add repo root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_detect_node_by_package_json(tmp_path):
    p = tmp_path / "package.json"
    p.write_text('{"name": "test"}')
    assert detect_stack(str(tmp_path)) == "node"

def test_detect_node_by_tsconfig(tmp_path):
    p = tmp_path / "tsconfig.json"
    p.write_text('{"compilerOptions": {}}')
    assert detect_stack(str(tmp_path)) == "node"

def test_detect_python_by_requirements(tmp_path):
    p = tmp_path / "requirements.txt"
    p.write_text("flask==2.0")
    assert detect_stack(str(tmp_path)) == "python"

def test_detect_python_by_pyproject(tmp_path):
    p = tmp_path / "pyproject.toml"
    p.write_text("[project]\nname = 'test'")
    assert detect_stack(str(tmp_path)) == "python"

def test_detect_go_by_go_mod(tmp_path):
    p = tmp_path / "go.mod"
    p.write_text("module test\n\ngo 1.21")
    assert detect_stack(str(tmp_path)) == "go"

def test_detect_unknown(tmp_path):
    assert detect_stack(str(tmp_path)) == "unknown"


def test_find_files_ts(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.ts").write_text("console.log('hi')")
    (tmp_path / "src" / "test.js").write_text("test")
    files = find_files(str(tmp_path), ['.ts', '.js'])
    assert len(files) == 2
    assert any(f.endswith('.ts') for f in files)
    assert any(f.endswith('.js') for f in files)


def test_find_files_excludes_venv(tmp_path):
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "lib.py").write_text("")
    (tmp_path / "app.py").write_text("")
    files = find_files(str(tmp_path), ['.py'])
    assert all('.venv' not in f for f in files)
    assert len(files) == 1


def test_find_files_excludes_tests(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test.py").write_text("")
    (tmp_path / "app.py").write_text("")
    files = find_files(str(tmp_path), ['.py'])
    # Excluding tests/ means the only file should be app.py
    assert len(files) == 1
    # Check that the returned file is app.py (no tests component in relative path)
    relpath = Path(files[0]).relative_to(tmp_path)
    assert relpath.parts[0] == "app.py"


def test_find_files_excludes_node_modules(tmp_path):
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "pkg.js").write_text("")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.js").write_text("")
    files = find_files(str(tmp_path), ['.js'])
    assert all('node_modules' not in f for f in files)
    assert len(files) == 1


def test_detect_python_over_node_with_openclaw_skill(tmp_path):
    # Both package.json with openclaw key and pyproject.toml exist
    pkg = tmp_path / "package.json"
    pkg.write_text('{"name": "test", "openclaw": {"skill": true}}')
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[project]\nname = 'test'")
    # Should detect as python (OpenClaw skill, not a Node project)
    assert detect_stack(str(tmp_path)) == "python"


def test_detect_node_without_openclaw(tmp_path):
    # package.json without openclaw key
    pkg = tmp_path / "package.json"
    pkg.write_text('{"name": "test"}')
    assert detect_stack(str(tmp_path)) == "node"
