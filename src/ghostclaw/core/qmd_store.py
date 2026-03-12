"""
QMD (Quantum Memory Database) backend for Ghostclaw.

Provides high-performance hybrid search (BM25 + vector) as an alternative
to the default SQLite MemoryStore.

This is a minimal implementation that uses SQLite with FTS5 for now,
providing the same interface as MemoryStore. Future versions may
integrate a true vector database or specialized QMD engine.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import aiosqlite
    HAS_AIOSQLITE = True
except ImportError:
    HAS_AIOSQLITE = False

logger = logging.getLogger("ghostclaw.qmd")


class QMDMemoryStore:
    """
    QMD-backed memory store with hybrid search capabilities.

    Storage location: .ghostclaw/storage/qmd/ghostclaw.db (separate from SQLite).
    Schema: Same as MemoryStore initially, but extensible for vectors.
    """

    def __init__(self, db_path: Optional[Path] = None):
        # Use .ghostclaw/storage/qmd/ instead of .ghostclaw/storage/
        self.db_path = db_path or Path.cwd() / ".ghostclaw" / "storage" / "qmd" / "ghostclaw.db"

    def _db_exists(self) -> bool:
        return self.db_path.exists()

    async def _ensure_db(self) -> None:
        """Create the database and tables if they don't exist yet."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        if not HAS_AIOSQLITE:
            raise ImportError("aiosqlite is required for QMDMemoryStore")

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    vibe_score INTEGER,
                    stack TEXT,
                    files_analyzed INTEGER,
                    total_lines INTEGER,
                    report_json TEXT,
                    repo_path TEXT,
                    vcs_commit TEXT,
                    vcs_branch TEXT
                )
            """)
            # Future: Add FTS virtual table for BM25 search
            await db.commit()

    # ------------------------------------------------------------------
    # List runs (same interface as MemoryStore)
    # ------------------------------------------------------------------

    async def list_runs(
        self,
        limit: int = 20,
        repo_path: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if not self._db_exists():
            return []

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
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
        if not self._db_exists():
            return None

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT report_json FROM reports WHERE id = ?",
                (run_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return json.loads(row["report_json"])
                return None

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
            db.row_factory = aiosqlite.Row
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
    # Search (placeholder: simple LIKE, will be BM25+vector)
    # ------------------------------------------------------------------

    async def search(
        self,
        query: str,
        limit: int = 10,
        repo_path: Optional[str] = None,
        stack: Optional[str] = None,
        min_score: Optional[int] = None,
        max_score: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search across saved reports for matching content.
        Currently does simple substring match on issues/ghosts.
        Future: BM25 + vector similarity.
        """
        if not self._db_exists():
            return []

        results = []
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            # For now, fetch recent runs and filter in Python (inefficient but works for prototype)
            async with db.execute(
                "SELECT id, timestamp, vibe_score, stack, report_json, repo_path FROM reports ORDER BY timestamp DESC LIMIT 100"
            ) as cursor:
                rows = await cursor.fetchall()
                for row in rows:
                    report = json.loads(row["report_json"])
                    # Combine searchable text
                    text_parts = report.get("issues", []) + report.get("architectural_ghosts", [])
                    text = " ".join(text_parts).lower()
                    if query.lower() in text:
                        if repo_path and row["repo_path"] != repo_path:
                            continue
                        results.append({
                            "id": row["id"],
                            "timestamp": row["timestamp"],
                            "vibe_score": row["vibe_score"],
                            "stack": row["stack"],
                            "repo_path": row["repo_path"],
                            "snippets": [query]  # TODO: extract actual snippets
                        })
                        if len(results) >= limit:
                            break
        return results

    # ------------------------------------------------------------------
    # Diff runs
    # ------------------------------------------------------------------

    async def diff_runs(self, run_id_a: int, run_id_b: int) -> Optional[Dict[str, Any]]:
        """
        Compare two analysis runs and return differences.
        """
        run_a = await self.get_run(run_id_a)
        run_b = await self.get_run(run_id_b)
        if not run_a or not run_b:
            return None

        return {
            "run_a": run_a,
            "run_b": run_b,
            "vibe_score_delta": run_b.get("vibe_score", 0) - run_a.get("vibe_score", 0),
            "issues_added": [i for i in run_b.get("issues", []) if i not in run_a.get("issues", [])],
            "issues_removed": [i for i in run_a.get("issues", []) if i not in run_b.get("issues", [])],
            "ghosts_added": [g for g in run_b.get("architectural_ghosts", []) if g not in run_a.get("architectural_ghosts", [])],
            "ghosts_removed": [g for g in run_a.get("architectural_ghosts", []) if g not in run_b.get("architectural_ghosts", [])],
        }

    # ------------------------------------------------------------------
    # Knowledge graph (placeholder)
    # ------------------------------------------------------------------

    async def get_knowledge_graph(
        self,
        repo_path: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Return an aggregated knowledge graph of recurring issues and trends.
        """
        runs = await self.list_runs(limit=100, repo_path=repo_path)
        if not runs:
            return {"nodes": [], "edges": []}

        # Simple aggregation: count issue frequencies
        issue_counts = {}
        ghost_counts = {}
        for run_summary in runs:
            run_id = run_summary["id"]
            full_run = await self.get_run(run_id)
            if not full_run:
                continue
            for issue in full_run.get("issues", []):
                issue_counts[issue] = issue_counts.get(issue, 0) + 1
            for ghost in full_run.get("architectural_ghosts", []):
                ghost_counts[ghost] = ghost_counts.get(ghost, 0) + 1

        # Build nodes
        nodes = []
        for issue, count in sorted(issue_counts.items(), key=lambda x: -x[1])[:limit]:
            nodes.append({"id": f"issue:{issue}", "type": "issue", "label": issue, "count": count})
        for ghost, count in sorted(ghost_counts.items(), key=lambda x: -x[1])[:limit]:
            nodes.append({"id": f"ghost:{ghost}", "type": "ghost", "label": ghost, "count": count})

        # Minimal edges (could be expanded later)
        edges = []
        return {"nodes": nodes, "edges": edges}

    # ------------------------------------------------------------------
    # Save a run
    # ------------------------------------------------------------------

    async def save_run(
        self,
        report: Dict[str, Any],
        repo_path: str,
        timestamp: Optional[str] = None,
    ) -> int:
        """
        Save an analysis run to the QMD store.

        Returns the run ID.
        """
        await self._ensure_db()
        timestamp = timestamp or report.get("metadata", {}).get("timestamp")
        if not timestamp:
            from datetime import datetime
            timestamp = datetime.now().isoformat()

        # Extract VCS info if present
        vcs = report.get("metadata", {}).get("vcs", {})

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                """
                INSERT INTO reports
                (timestamp, vibe_score, stack, files_analyzed, total_lines, report_json, repo_path, vcs_commit, vcs_branch)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    timestamp,
                    report.get("vibe_score"),
                    report.get("stack"),
                    report.get("files_analyzed"),
                    report.get("total_lines"),
                    json.dumps(report),
                    repo_path,
                    vcs.get("commit"),
                    vcs.get("branch"),
                ),
            ) as cursor:
                run_id = cursor.lastrowid
                await db.commit()
                return run_id
