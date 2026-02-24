import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from cli.ghostclaw import generate_markdown_report, detect_github_remote

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
