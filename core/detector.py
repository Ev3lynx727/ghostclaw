"""Tech stack detection for codebases."""

from pathlib import Path
from typing import List, Set

# Directories to exclude from analysis (standard ignores)
EXCLUDE_DIRS = {
    '.venv', 'venv', '.env',
    '__pycache__', '.pytest_cache', '.coverage',
    '.git', '.hg', '.svn',
    'node_modules', 'dist', 'build', 'target',
    'vendor', '.deps',
    'tests', 'test', 'spec', 'specs',
    'docs', 'doc', 'example', 'examples',
    'scripts'  # Entry point scripts; not core modules
}

# Entry point directories that are allowed to have high efferent coupling (orchestrators)
ENTRY_POINT_DIRS = {'cli', 'scripts', 'bin', '__main__'}

def _should_exclude(path_parts: List[str]) -> bool:
    """Check if any component of the path is in exclude list."""
    return any(part in EXCLUDE_DIRS for part in path_parts)


def find_files(root: str, extensions: List[str]) -> List[str]:
    """Recursively find files with given extensions, excluding common non-source directories."""
    root_path = Path(root)
    files = []
    for ext in extensions:
        for filepath in root_path.rglob(f"*{ext}"):
            # Compute relative path parts to check exclusions
            try:
                rel_parts = filepath.relative_to(root_path).parts
            except ValueError:
                continue
            if _should_exclude(rel_parts):
                continue
            files.append(str(filepath))
    return files


def detect_stack(root: str) -> str:
    """Detect the primary tech stack of a repository."""
    root_path = Path(root)

    # Check for Python indicators first (more specific)
    python_indicators = ['pyproject.toml', 'requirements.txt', 'setup.py', 'Pipfile', 'poetry.lock']
    if any((root_path / f).exists() for f in python_indicators):
        return 'python'

    # Node.js / TypeScript / React
    node_indicators = ['package.json', 'tsconfig.json', 'vite.config.ts', 'next.config.js']
    if any((root_path / f).exists() for f in node_indicators):
        # Special case: if package.json exists with openclaw skill marker, it's not a Node codebase
        pkg_path = root_path / 'package.json'
        if pkg_path.exists():
            try:
                import json
                with open(pkg_path, 'r') as f:
                    pkg = json.load(f)
                if 'openclaw' in pkg:
                    # This is an OpenClaw skill, not a Node project; skip Node detection
                    return 'unknown'  # Will fall back to Python if pyproject.toml exists, or we can re-check below
            except Exception:
                pass
        return 'node'

    # Go
    if any((root_path / f).exists() for f in ['go.mod', 'go.sum']):
        return 'go'

    return 'unknown'

