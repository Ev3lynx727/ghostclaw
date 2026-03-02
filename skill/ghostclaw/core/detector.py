"""Tech stack detection for codebases."""

from pathlib import Path
from typing import List


def detect_stack(root: str) -> str:
    """Detect the primary tech stack of a repository."""
    root_path = Path(root)

    # Node.js / TypeScript / React
    node_indicators = ['package.json', 'tsconfig.json', 'vite.config.ts', 'next.config.js']
    if any((root_path / f).exists() for f in node_indicators):
        return 'node'

    # Python (Django, FastAPI, plain)
    python_indicators = ['requirements.txt', 'pyproject.toml', 'setup.py', 'Pipfile', 'poetry.lock']
    if any((root_path / f).exists() for f in python_indicators):
        return 'python'

    # Go
    if any((root_path / f).exists() for f in ['go.mod', 'go.sum']):
        return 'go'

    return 'unknown'


def find_files(root: str, extensions: List[str]) -> List[str]:
    """Recursively find files with given extensions."""
    root_path = Path(root)
    files = []
    for ext in extensions:
        files.extend(root_path.rglob(f"*{ext}"))
    return [str(f) for f in files]
