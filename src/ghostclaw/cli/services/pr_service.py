"""
PR Service — Handles GitHub PR creation for architecture reports.
"""

import subprocess
import datetime
from pathlib import Path
from typing import Optional


class PRService:
    """Service for creating GitHub PRs with architecture reports."""

    def __init__(self, repo_path: str | Path):
        self.repo_path = Path(repo_path).resolve()

    async def create_pr(
        self,
        report_file: Path,
        title: Optional[str] = None,
        body: Optional[str] = None
    ) -> str:
        """
        Create a GitHub PR with the architecture report.

        Args:
            report_file: Path to the markdown report file
            title: Custom PR title (default: auto-generated)
            body: Custom PR body (default: auto-generated with vibe score)

        Returns:
            URL of the created PR

        Raises:
            subprocess.CalledProcessError: If any git/gh command fails
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
        branch_name = f"ghostclaw/arch-report-{timestamp}"

        # Convert to relative path from repo root
        try:
            rel_report_path = report_file.relative_to(self.repo_path)
        except ValueError:
            # Not relative, use absolute but that's odd
            rel_report_path = report_file

        # 1. Create branch
        subprocess.run(
            ["git", "checkout", "-b", branch_name],
            cwd=self.repo_path,
            check=True,
            capture_output=True,
            text=True
        )

        # 2. Add report (force to bypass gitignore if needed)
        subprocess.run(
            ["git", "add", "-f", str(rel_report_path)],
            cwd=self.repo_path,
            check=True,
            capture_output=True,
            text=True
        )

        # 3. Commit
        subprocess.run(
            ["git", "commit", "-m", f"Add architecture report: {report_file.name}"],
            cwd=self.repo_path,
            check=True,
            capture_output=True,
            text=True
        )

        # 4. Push
        subprocess.run(
            ["git", "push", "origin", branch_name],
            cwd=self.repo_path,
            check=True,
            capture_output=True,
            text=True
        )

        # 5. Create PR
        pr_cmd = ["gh", "pr", "create", "--title", title or f"🏰 Architecture Report - {datetime.datetime.now().strftime('%Y-%m-%d')}", "--body", body or f"Ghostclaw has completed an architectural review of the codebase.\n\n**Vibe Score: N/A**\n\nPlease review the attached report for details."]
        result = subprocess.run(
            pr_cmd,
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=True
        )

        pr_url = result.stdout.strip()
        print(f"🔗 PR created: {pr_url}")
        return pr_url
