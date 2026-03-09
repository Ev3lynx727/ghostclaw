import sys
from typing import Dict, Any
from ghostclaw.cli.formatters.base import BaseFormatter

class TerminalFormatter(BaseFormatter):
    """
    Format the architecture report for terminal output.
    """

    def format(self, report: Dict[str, Any]) -> str:
        # Note: In the CLI context, we typically print directly to sys.stdout rather than
        # returning a giant string. However, for consistency with the BaseFormatter interface,
        # we will build a string and return it, which the caller can then print.

        vibe_score = report.get('vibe_score', 0)
        stack = report.get('stack', 'unknown')
        files = report.get('files_analyzed', 0)
        total = report.get('total_lines', 0)

        # Color/emoji based on vibe
        if vibe_score >= 80:
            emoji = "🟢"
        elif vibe_score >= 60:
            emoji = "🟡"
        elif vibe_score >= 40:
            emoji = "🟠"
        else:
            emoji = "🔴"

        lines = [
            f"{emoji} Vibe Score: {vibe_score}/100",
            f"   Stack: {stack}",
            f"   Files: {files}, Lines: {total}"
        ]

        metrics = report.get('coupling_metrics', {})
        if metrics:
            avg_ccn = metrics.get('avg_ccn')
            avg_nd = metrics.get('avg_nd')
            if avg_ccn is not None or avg_nd is not None:
                lines.append(f"   Metrics: Avg CCN: {avg_ccn if avg_ccn is not None else 'N/A'}, Avg Nesting: {avg_nd if avg_nd is not None else 'N/A'}")

        lines.append("")

        issues = report.get('issues', [])
        if issues:
            lines.append("Issues detected:")
            for issue in issues:
                lines.append(f"  • {issue}")
            lines.append("")

        ghosts = report.get('architectural_ghosts', [])
        if ghosts:
            lines.append("👻 Architectural Ghosts:")
            for ghost in ghosts:
                lines.append(f"   {ghost}")
            lines.append("")

        flags = report.get('red_flags', [])
        if flags:
            lines.append("🚨 Red Flags:")
            for flag in flags:
                lines.append(f"   {flag}")
            lines.append("")

        errors = report.get('errors', [])
        if errors:
            lines.append("⚠️ Adapter Errors:")
            for err in errors:
                lines.append(f"   {err}")
            lines.append("")

        lines.append("💡 Tip: Run with '--patch' to generate refactor suggestions")

        # Print AI synthesis if present and not already streamed (e.g., from cache)
        if "ai_synthesis" in report and not report.get("_synthesis_streamed", False):
            lines.append("\n✨ AI Synthesis:")
            if report.get("metadata", {}).get("cache_hit"):
                lines.append("(cached)")
            lines.append(report["ai_synthesis"])

        return "\n".join(lines)

    def print_to_terminal(self, report: Dict[str, Any]) -> None:
        """Utility method to print directly."""
        print(self.format(report))
