"""
Agent-facing memory store for Ghostclaw.

Provides search, retrieval, and knowledge graph capabilities
over past analysis runs stored in .ghostclaw/storage/ghostclaw.db.
"""

import json
import sqlite3
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import aiosqlite
    HAS_AIOSQLITE = True
except ImportError:
    HAS_AIOSQLITE = False

logger = logging.getLogger("ghostclaw.memory")


class MemoryStore:
    """
    Agent-facing memory interface over Ghostclaw's SQLite history.

    Enables AI agents to search past analysis runs, retrieve specific reports,
    and query a knowledge graph built from accumulated architectural data.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path.cwd() / ".ghostclaw" / "storage" / "ghostclaw.db"

    def _db_exists(self) -> bool:
        return self.db_path.exists()

    async def _ensure_db(self) -> None:
        """Create the database and tables if they don't exist yet."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    vibe_score INTEGER,
                    stack TEXT,
                    files_analyzed INTEGER,
                    total_lines INTEGER,
                    report_json TEXT,
                    repo_path TEXT
                )
            """)
            await db.commit()

    # ------------------------------------------------------------------
    # List runs
    # ------------------------------------------------------------------

    async def list_runs(
        self,
        limit: int = 20,
        repo_path: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List recent analysis runs with summary metadata.

        Args:
            limit: Maximum number of runs to return.
            repo_path: Optional filter by repository path.

        Returns:
            List of run summaries (id, timestamp, vibe_score, stack,
            files_analyzed, total_lines, repo_path).
        """
        if not self._db_exists():
            return []

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            if repo_path:
                query = (
                    "SELECT id, timestamp, vibe_score, stack, files_analyzed, "
                    "total_lines, repo_path FROM reports "
                    "WHERE repo_path = ? ORDER BY timestamp DESC LIMIT ?"
                )
                params = (repo_path, limit)
            else:
                query = (
                    "SELECT id, timestamp, vibe_score, stack, files_analyzed, "
                    "total_lines, repo_path FROM reports "
                    "ORDER BY timestamp DESC LIMIT ?"
                )
                params = (limit,)

            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    # ------------------------------------------------------------------
    # Get a single run
    # ------------------------------------------------------------------

    async def get_run(self, run_id: int) -> Optional[Dict[str, Any]]:
        """
        Get the full report for a specific run by its ID.

        Args:
            run_id: The integer ID of the run.

        Returns:
            Full report dict, or None if not found.
        """
        if not self._db_exists():
            return None

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            async with db.execute(
                "SELECT * FROM reports WHERE id = ?", (run_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None
                row_dict = dict(row)
                # Parse the full report JSON
                try:
                    row_dict["report"] = json.loads(row_dict.pop("report_json", "{}"))
                except (json.JSONDecodeError, TypeError):
                    row_dict["report"] = {}
                return row_dict

    # ------------------------------------------------------------------
    # Get previous run (most recent for a repo)
    # ------------------------------------------------------------------

    async def get_previous_run(
        self, repo_path: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get the most recent analysis run, optionally filtered by repo path.

        Args:
            repo_path: Optional repo path filter. Defaults to all repos.

        Returns:
            Full report dict of the most recent run, or None.
        """
        if not self._db_exists():
            return None

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            if repo_path:
                query = "SELECT * FROM reports WHERE repo_path = ? ORDER BY timestamp DESC LIMIT 1"
                params = (repo_path,)
            else:
                query = "SELECT * FROM reports ORDER BY timestamp DESC LIMIT 1"
                params = ()

            async with db.execute(query, params) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None
                row_dict = dict(row)
                try:
                    row_dict["report"] = json.loads(row_dict.pop("report_json", "{}"))
                except (json.JSONDecodeError, TypeError):
                    row_dict["report"] = {}
                return row_dict

    # ------------------------------------------------------------------
    # Memory search
    # ------------------------------------------------------------------

    async def search(
        self,
        query: str,
        repo_path: Optional[str] = None,
        stack: Optional[str] = None,
        min_score: Optional[int] = None,
        max_score: Optional[int] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search across past analysis reports by keyword and optional filters.

        The search scans the full report JSON for the query string
        (issues, ghosts, flags, AI synthesis, etc.) and applies
        optional filters on stack, vibe score range, and repo path.

        Args:
            query: Text to search for in report content.
            repo_path: Optional filter by repository path.
            stack: Optional filter by tech stack (e.g. 'python', 'node').
            min_score: Optional minimum vibe score filter.
            max_score: Optional maximum vibe score filter.
            limit: Maximum results to return.

        Returns:
            List of matching run summaries with matched context snippets.
        """
        if not self._db_exists():
            return []

        conditions = []
        params: list = []

        # Always search in report_json for the query text
        if query:
            conditions.append("report_json LIKE ?")
            params.append(f"%{query}%")

        if repo_path:
            conditions.append("repo_path = ?")
            params.append(repo_path)

        if stack:
            conditions.append("stack = ?")
            params.append(stack)

        if min_score is not None:
            conditions.append("vibe_score >= ?")
            params.append(min_score)

        if max_score is not None:
            conditions.append("vibe_score <= ?")
            params.append(max_score)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        sql = (
            f"SELECT id, timestamp, vibe_score, stack, files_analyzed, "
            f"total_lines, repo_path, report_json FROM reports "
            f"WHERE {where_clause} ORDER BY timestamp DESC LIMIT ?"
        )
        params.append(limit)

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            async with db.execute(sql, params) as cursor:
                rows = await cursor.fetchall()

        results = []
        for row in rows:
            row_dict = dict(row)
            report_json_str = row_dict.pop("report_json", "{}")

            # Extract matched context snippets from the report
            snippets = self._extract_snippets(report_json_str, query)

            row_dict["matched_snippets"] = snippets
            results.append(row_dict)

        return results

    @staticmethod
    def _extract_snippets(
        report_json_str: str, query: str, max_snippets: int = 5, context_chars: int = 120
    ) -> List[str]:
        """Extract text snippets around query matches in the report JSON."""
        if not query:
            return []

        snippets = []
        lower_text = report_json_str.lower()
        lower_query = query.lower()
        search_start = 0

        while len(snippets) < max_snippets:
            idx = lower_text.find(lower_query, search_start)
            if idx == -1:
                break
            start = max(0, idx - context_chars)
            end = min(len(report_json_str), idx + len(query) + context_chars)
            snippet = report_json_str[start:end].strip()
            # Clean up JSON artifacts for readability
            snippet = snippet.replace("\\n", " ").replace('\\"', '"')
            snippets.append(f"...{snippet}...")
            search_start = idx + len(query)

        return snippets

    # ------------------------------------------------------------------
    # Diff two runs
    # ------------------------------------------------------------------

    async def diff_runs(
        self, run_id_a: int, run_id_b: int
    ) -> Optional[Dict[str, Any]]:
        """
        Compare two analysis runs and highlight differences.

        Args:
            run_id_a: First run ID (typically older).
            run_id_b: Second run ID (typically newer).

        Returns:
            Dict with score delta, new/resolved issues, new/resolved ghosts,
            and metrics comparison. None if either run not found.
        """
        run_a = await self.get_run(run_id_a)
        run_b = await self.get_run(run_id_b)

        if not run_a or not run_b:
            return None

        report_a = run_a.get("report", {})
        report_b = run_b.get("report", {})

        issues_a = set(report_a.get("issues", []))
        issues_b = set(report_b.get("issues", []))
        ghosts_a = set(report_a.get("architectural_ghosts", []))
        ghosts_b = set(report_b.get("architectural_ghosts", []))
        flags_a = set(report_a.get("red_flags", []))
        flags_b = set(report_b.get("red_flags", []))

        return {
            "run_a": {"id": run_id_a, "timestamp": run_a.get("timestamp")},
            "run_b": {"id": run_id_b, "timestamp": run_b.get("timestamp")},
            "vibe_score_delta": (
                report_b.get("vibe_score", 0) - report_a.get("vibe_score", 0)
            ),
            "new_issues": sorted(issues_b - issues_a),
            "resolved_issues": sorted(issues_a - issues_b),
            "new_ghosts": sorted(ghosts_b - ghosts_a),
            "resolved_ghosts": sorted(ghosts_a - ghosts_b),
            "new_flags": sorted(flags_b - flags_a),
            "resolved_flags": sorted(flags_a - flags_b),
            "metrics_comparison": {
                "files_analyzed": {
                    "before": report_a.get("files_analyzed", 0),
                    "after": report_b.get("files_analyzed", 0),
                },
                "total_lines": {
                    "before": report_a.get("total_lines", 0),
                    "after": report_b.get("total_lines", 0),
                },
                "vibe_score": {
                    "before": report_a.get("vibe_score", 0),
                    "after": report_b.get("vibe_score", 0),
                },
            },
        }

    # ------------------------------------------------------------------
    # Knowledge graph
    # ------------------------------------------------------------------

    async def get_knowledge_graph(
        self,
        repo_path: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Build a knowledge graph from accumulated analysis history.

        Aggregates recurring issues, ghost patterns, coupling hotspots,
        and vibe score trends across past runs to provide agents with
        a high-level architectural memory of the codebase.

        Args:
            repo_path: Optional filter by repository path.
            limit: Maximum runs to include in the graph.

        Returns:
            Dict with:
              - recurring_issues: issues seen across multiple runs with counts
              - recurring_ghosts: architectural ghosts with frequency
              - recurring_flags: red flags with frequency
              - score_trend: chronological list of (timestamp, vibe_score)
              - coupling_hotspots: modules with consistently high instability
              - stacks_seen: set of detected stacks
              - total_runs: number of runs in the graph
        """
        if not self._db_exists():
            return self._empty_knowledge_graph()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row

            if repo_path:
                query = (
                    "SELECT report_json, timestamp, vibe_score, stack "
                    "FROM reports WHERE repo_path = ? "
                    "ORDER BY timestamp ASC LIMIT ?"
                )
                params = (repo_path, limit)
            else:
                query = (
                    "SELECT report_json, timestamp, vibe_score, stack "
                    "FROM reports ORDER BY timestamp ASC LIMIT ?"
                )
                params = (limit,)

            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()

        if not rows:
            return self._empty_knowledge_graph()

        issue_counts: Dict[str, int] = defaultdict(int)
        ghost_counts: Dict[str, int] = defaultdict(int)
        flag_counts: Dict[str, int] = defaultdict(int)
        coupling_instability: Dict[str, List[float]] = defaultdict(list)
        score_trend: List[Dict[str, Any]] = []
        stacks_seen: set = set()

        for row in rows:
            row_dict = dict(row)
            score_trend.append({
                "timestamp": row_dict["timestamp"],
                "vibe_score": row_dict["vibe_score"],
            })
            if row_dict.get("stack"):
                stacks_seen.add(row_dict["stack"])

            try:
                report = json.loads(row_dict.get("report_json", "{}"))
            except (json.JSONDecodeError, TypeError):
                continue

            for issue in report.get("issues", []):
                issue_counts[issue] += 1
            for ghost in report.get("architectural_ghosts", []):
                ghost_counts[ghost] += 1
            for flag in report.get("red_flags", []):
                flag_counts[flag] += 1

            # Aggregate coupling metrics
            coupling = report.get("coupling_metrics", {})
            for module, metrics in coupling.items():
                if isinstance(metrics, dict):
                    instability = metrics.get("instability")
                    if instability is not None:
                        coupling_instability[module].append(instability)

        # Build coupling hotspots: modules with average instability > 0.7
        coupling_hotspots = []
        for module, instabilities in coupling_instability.items():
            avg = sum(instabilities) / len(instabilities)
            if avg > 0.7:
                coupling_hotspots.append({
                    "module": module,
                    "avg_instability": round(avg, 3),
                    "occurrences": len(instabilities),
                })
        coupling_hotspots.sort(key=lambda x: x["avg_instability"], reverse=True)

        # Sort recurring items by frequency (descending)
        def _top_items(counts: Dict[str, int], top_n: int = 20) -> List[Dict[str, Any]]:
            sorted_items = sorted(counts.items(), key=lambda x: x[1], reverse=True)
            return [
                {"item": item, "count": count}
                for item, count in sorted_items[:top_n]
            ]

        return {
            "total_runs": len(rows),
            "stacks_seen": sorted(stacks_seen),
            "score_trend": score_trend,
            "recurring_issues": _top_items(issue_counts),
            "recurring_ghosts": _top_items(ghost_counts),
            "recurring_flags": _top_items(flag_counts),
            "coupling_hotspots": coupling_hotspots[:20],
        }

    @staticmethod
    def _empty_knowledge_graph() -> Dict[str, Any]:
        return {
            "total_runs": 0,
            "stacks_seen": [],
            "score_trend": [],
            "recurring_issues": [],
            "recurring_ghosts": [],
            "recurring_flags": [],
            "coupling_hotspots": [],
        }
