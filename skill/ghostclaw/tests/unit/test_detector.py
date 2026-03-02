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
