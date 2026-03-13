"""Shell script stack analyzer."""

from typing import Dict, List
from .base import StackAnalyzer


class ShellAnalyzer(StackAnalyzer):
    """Analyzes Shell scripts for architectural issues."""

    def get_extensions(self) -> List[str]:
        return ['.sh', '.bash', '.zsh']

    def get_large_file_threshold(self) -> int:
        return 150

    def analyze(self, root: str, files: List[str], metrics: Dict) -> Dict:
        """Run Shell-specific architectural checks."""
        # For now, we rely primarily on patterns.yaml rules for shell
        return {
            "stack": "shell",
            "issues": [],
            "architectural_ghosts": [],
            "red_flags": [],
            "coupling_metrics": {}
        }
