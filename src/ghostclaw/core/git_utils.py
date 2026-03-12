"""Git utilities for diff extraction and change detection.

Provides functions to obtain unified diffs between git references and
parse them into lists of changed files and line ranges.
"""

import subprocess
from dataclasses import dataclass
from typing import List, Optional, Tuple
from pathlib import Path


@dataclass
class DiffResult:
    """Represents a parsed git diff."""
    files_changed: List[str]
    raw_diff: str
    against: str  # the base ref we diffed against


def get_git_diff(base_ref: str = "HEAD~1", cwd: Optional[Path] = None) -> DiffResult:
    """
    Run `git diff` against a base reference and return the raw unified diff.

    Args:
        base_ref: Git reference to diff against (branch, tag, commit).
        cwd: Working directory (defaults to current).

    Returns:
        DiffResult with raw diff text and list of changed files.
    """
    cmd = ["git", "diff", base_ref]
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    raw = result.stdout
    files = _parse_changed_files(raw)
    return DiffResult(files_changed=files, raw_diff=raw, against=base_ref)


def get_staged_diff(cwd: Optional[Path] = None) -> DiffResult:
    """Get diff of staged changes (index vs HEAD)."""
    cmd = ["git", "diff", "--cached"]
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    raw = result.stdout
    files = _parse_changed_files(raw)
    return DiffResult(files_changed=files, raw_diff=raw, against="HEAD (staged)")


def get_unstaged_diff(cwd: Optional[Path] = None) -> DiffResult:
    """Get diff of unstaged changes (working tree vs index)."""
    cmd = ["git", "diff"]
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    raw = result.stdout
    files = _parse_changed_files(raw)
    return DiffResult(files_changed=files, raw_diff=raw, against="index (unstaged)")


def _parse_changed_files(diff_text: str) -> List[str]:
    """Extract file paths from a unified diff."""
    files = []
    for line in diff_text.splitlines():
        if line.startswith("--- a/") or line.startswith("+++ b/"):
            # Lines look like: --- a/path/to/file.py or +++ b/path/to/file.py
            prefix = "--- a/" if line.startswith("--- a/") else "+++ b/"
            path = line[len(prefix):]
            # Avoid duplicates and /dev/null
            if path != "/dev/null" and path not in files:
                files.append(path)
    return files


def has_uncommitted_changes(cwd: Optional[Path] = None) -> bool:
    """Quick check if there are any staged or unstaged changes."""
    subprocess.run(["git", "update-index", "-q", "--refresh"], cwd=cwd, check=False)
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    return bool(result.stdout.strip())


def get_current_branch(cwd: Optional[Path] = None) -> str:
    """Get the current branch name (or commit SHA if detached)."""
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    branch = result.stdout.strip()
    return branch if branch != "HEAD" else get_current_sha(cwd)[:8]


def get_current_sha(cwd: Optional[Path] = None) -> str:
    """Get full commit SHA of HEAD."""
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip()
