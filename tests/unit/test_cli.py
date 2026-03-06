import pytest
from unittest.mock import MagicMock, patch, ANY
from pathlib import Path
from ghostclaw.cli.ghostclaw import generate_markdown_report, detect_github_remote, main as cli_main
from ghostclaw.core.cache import LocalCache
import subprocess
import sys


def test_generate_markdown_report():
    report = {
        'vibe_score': 85,
        'stack': 'python',
        'files_analyzed': 10,
        'total_lines': 1000,
        'issues': ['Issue 1'],
        'architectural_ghosts': ['Ghost 1'],
        'red_flags': ['Flag 1'],
        'metadata': {'timestamp': '2026-02-24T22:00:00Z'}
    }
    md = generate_markdown_report(report)
    assert "# Architecture Report — 2026-02-24T22:00:00Z" in md
    assert "## 🟢 Vibe Score: 85/100" in md
    assert "- **Stack**: python" in md
    assert "## Issues Detected" in md
    assert "- Issue 1" in md
    assert "## 👻 Architectural Ghosts" in md
    assert "- Ghost 1" in md
    assert "## 🚨 Red Flags" in md
    assert "- Flag 1" in md


@patch("subprocess.run")
def test_detect_github_remote_success(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout="https://github.com/user/repo.git")
    url = detect_github_remote("/fake/path")
    assert url == "https://github.com/user/repo.git"


@patch("subprocess.run")
def test_detect_github_remote_not_github(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout="https://gitlab.com/user/repo.git")
    url = detect_github_remote("/fake/path")
    assert url is None


@patch("subprocess.run")
def test_detect_github_remote_fail(mock_run):
    mock_run.return_value = MagicMock(returncode=1)
    url = detect_github_remote("/fake/path")
    assert url is None


def test_cli_no_cache_flag(tmp_path, capsys):
    """Test --no-cache prevents cache usage."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname='test'")
    (repo / "module.py").write_text("def foo(): return 1\n")

    original_argv = sys.argv
    try:
        sys.argv = ["ghostclaw", str(repo), "--no-cache"]
        cli_main()  # Should not raise

        captured = capsys.readouterr()
        # Should not contain "Cache hit!" because cache is disabled
        assert "Cache hit!" not in captured.err
    finally:
        sys.argv = original_argv


def test_cli_cache_stats_flag(tmp_path, capsys):
    """Test --cache-stats prints cache info."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname='test'")
    (repo / "module.py").write_text("def foo(): return 1\n")

    original_argv = sys.argv
    try:
        sys.argv = ["ghostclaw", str(repo), "--cache-stats"]
        cli_main()  # Should not raise

        captured = capsys.readouterr()
        output = captured.out + captured.err
        # Look for cache stats line (contains "Cache:" and "entries")
        assert "Cache:" in output
        assert "entries" in output
    finally:
        sys.argv = original_argv


def test_cli_cache_dir_flag(tmp_path, capsys):
    """Test --cache-dir uses custom directory."""
    repo = tmp_path / "repo"
    custom_cache = tmp_path / "custom_cache"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname='test'")
    (repo / "module.py").write_text("def foo(): return 1\n")

    original_argv = sys.argv
    try:
        sys.argv = ["ghostclaw", str(repo), "--cache-dir", str(custom_cache), "--cache-stats"]
        cli_main()  # Should not raise

        captured = capsys.readouterr()
        output = captured.out + captured.err
        # Stats should show custom_cache path
        assert str(custom_cache) in output

        # Verify cache was created in custom location
        assert custom_cache.exists()
        assert any(custom_cache.glob("*.json"))
    finally:
        sys.argv = original_argv
