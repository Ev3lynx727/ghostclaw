"""
Wrapper for ai-codeindex to replace/enhance core/graph.py with tree-sitter based analysis.
"""

import subprocess
import json
from pathlib import Path
from typing import Dict, List, Optional


class AICodeIndexWrapper:
    """Wrapper for the ai-codeindex command-line tool."""

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)

    def is_available(self) -> bool:
        """Check if ai-codeindex is installed and accessible."""
        try:
            subprocess.run(["ai-codeindex", "--version"], capture_output=True, check=False)
            return True
        except FileNotFoundError:
            return False

    def build_graph(self) -> Dict:
        """Run ai-codeindex to build a call graph and inheritance hierarchies."""
        if not self.is_available():
            return {"error": "ai-codeindex not installed"}

        try:
            # Assuming ai-codeindex has a command to export graph in JSON format
            result = subprocess.run(
                ["ai-codeindex", "graph", str(self.repo_path), "--format", "json"],
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode == 0:
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    return {"raw_output": result.stdout}
            else:
                return {"error": f"ai-codeindex failed with return code {result.returncode}", "stderr": result.stderr}

        except Exception as e:
            return {"error": str(e)}

    def get_inheritance_depth(self) -> Dict[str, int]:
        """Extract inheritance hierarchies from ai-codeindex output."""
        # Placeholder for real parsing logic
        return {}

    def get_complex_coupling(self) -> Dict:
        """Extract complex coupling metrics (e.g. cross-stack dependencies)."""
        # Placeholder for real parsing logic
        return {}
