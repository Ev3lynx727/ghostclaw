"""
MCP Server implementation for Ghostclaw.
Provides tools: ghostclaw_analyze, ghostclaw_get_ghosts, ghostclaw_refactor_plan.
"""

import sys
import json
import logging
from typing import Dict, List, Optional
from pathlib import Path

# Use try-import to handle optional dependencies for Phase 2
try:
    from mcp.server.fastmcp import FastMCP
    HAS_MCP = True
except ImportError:
    HAS_MCP = False

from core.analyzer import CodebaseAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ghostclaw-mcp")

# Initialize MCP server if available
mcp = FastMCP("Ghostclaw") if HAS_MCP else None


def get_analyzer() -> CodebaseAnalyzer:
    return CodebaseAnalyzer()


@mcp.tool() if HAS_MCP else lambda x: x
def ghostclaw_analyze(repo_path: str) -> str:
    """
    Perform a full architectural vibe analysis of a codebase.
    Returns a detailed JSON report including vibe score, issues, and ghosts.
    """
    if not Path(repo_path).is_dir():
        return json.dumps({"error": f"Path not found: {repo_path}"})

    analyzer = get_analyzer()
    report = analyzer.analyze(repo_path)
    return json.dumps(report, indent=2)


@mcp.tool() if HAS_MCP else lambda x: x
def ghostclaw_get_ghosts(repo_path: str) -> str:
    """
    Analyze architectural smells and 'ghosts' only.
    Returns a list of identified architectural issues.
    """
    if not Path(repo_path).is_dir():
        return json.dumps({"error": f"Path not found: {repo_path}"})

    analyzer = get_analyzer()
    report = analyzer.analyze(repo_path)
    ghosts = report.get("architectural_ghosts", [])
    return json.dumps({"architectural_ghosts": ghosts}, indent=2)


@mcp.tool() if HAS_MCP else lambda x: x
def ghostclaw_refactor_plan(repo_path: str) -> str:
    """
    Generate an automated refactor blueprint based on architectural analysis.
    Identifies the most critical areas for improvement.
    """
    if not Path(repo_path).is_dir():
        return json.dumps({"error": f"Path not found: {repo_path}"})

    analyzer = get_analyzer()
    report = analyzer.analyze(repo_path)

    # Placeholder for advanced refactor planning logic (Phase 2 enhancement)
    issues = report.get("issues", [])
    ghosts = report.get("architectural_ghosts", [])

    plan = [
        "### Ghostclaw Refactor Blueprint",
        "",
        "1. **Address Critical Issues**:",
        *[f"   - {issue}" for issue in issues[:3]],
        "",
        "2. **Mitigate Architectural Ghosts**:",
        *[f"   - {ghost}" for ghost in ghosts[:3]],
        "",
        "3. **Next Steps**:",
        "   - Review large files and apply SOLID principles.",
        "   - Implement missing unit tests for identified hotspots."
    ]

    return "\n".join(plan)


def main():
    """Entry point for the MCP server."""
    if not HAS_MCP:
        print("Error: mcp-sdk not installed. Install with 'pip install ghostclaw[mcp]'.", file=sys.stderr)
        sys.exit(1)

    mcp.run()


if __name__ == "__main__":
    main()
