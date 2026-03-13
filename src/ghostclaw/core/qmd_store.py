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
from collections import defaultdict
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
                "SELECT * FROM reports WHERE id = ?",
                (run_id,)
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
                    # Combine searchable text from all report fields
                    text_parts = report.get("issues", []) + report.get("architectural_ghosts", []) + report.get("red_flags", [])
                    searchable = " ".join(str(t) for t in text_parts)
                    # Also search AI synthesis and other string fields
                    for field in ("ai_synthesis", "ai_reasoning"):
                        if report.get(field):
                            searchable += " " + str(report[field])
                    text = searchable.lower()
                    if query.lower() in text:
                        if repo_path and row["repo_path"] != repo_path:
                            continue
                        if stack and row["stack"] != stack:
                            continue
                        if min_score is not None and (row["vibe_score"] is None or row["vibe_score"] < min_score):
                            continue
                        if max_score is not None and (row["vibe_score"] is None or row["vibe_score"] > max_score):
                            continue
                        results.append({
                            "id": row["id"],
                            "timestamp": row["timestamp"],
                            "vibe_score": row["vibe_score"],
                            "stack": row["stack"],
                            "repo_path": row["repo_path"],
                        "matched_snippets": [query]  # TODO: extract actual snippets
                        })
                        if len(results) >= limit:
                            break
        return results

    # ------------------------------------------------------------------
    # Diff runs
    # ------------------------------------------------------------------

    async def diff_runs(self, run_id_a: int, run_id_b: int) -> Optional[Dict[str, Any]]:
        """
        Compare two analysis runs and highlight differences.
        """
        run_a = await self.get_run(run_id_a)
        run_b = await self.get_run(run_id_b)

        if not run_a or not run_b:
            return None

        report_a = run_a.get("report", {})
        report_b = run_b.get("report", {})

        # Normalize issues to hashable keys to handle dict and string forms
        def _make_mapping(items):
            mapping = {}
            for item in items:
                if isinstance(item, dict):
                    key = json.dumps(item, sort_keys=True)
                else:
                    key = str(item)
                mapping[key] = item
            return mapping

        issues_a_map = _make_mapping(report_a.get("issues", []))
        issues_b_map = _make_mapping(report_b.get("issues", []))
        ghosts_a_map = _make_mapping(report_a.get("architectural_ghosts", []))
        ghosts_b_map = _make_mapping(report_b.get("architectural_ghosts", []))
        flags_a_map = _make_mapping(report_a.get("red_flags", []))
        flags_b_map = _make_mapping(report_b.get("red_flags", []))

        new_issue_keys = set(issues_b_map.keys()) - set(issues_a_map.keys())
        resolved_issue_keys = set(issues_a_map.keys()) - set(issues_b_map.keys())
        new_ghost_keys = set(ghosts_b_map.keys()) - set(ghosts_a_map.keys())
        resolved_ghost_keys = set(ghosts_a_map.keys()) - set(ghosts_b_map.keys())
        new_flag_keys = set(flags_b_map.keys()) - set(flags_a_map.keys())
        resolved_flag_keys = set(flags_a_map.keys()) - set(flags_b_map.keys())

        new_issues = sorted([issues_b_map[k] for k in new_issue_keys], key=lambda x: str(x))
        resolved_issues = sorted([issues_a_map[k] for k in resolved_issue_keys], key=lambda x: str(x))
        new_ghosts = sorted([ghosts_b_map[k] for k in new_ghost_keys], key=lambda x: str(x))
        resolved_ghosts = sorted([ghosts_a_map[k] for k in resolved_ghost_keys], key=lambda x: str(x))
        new_flags = sorted([flags_b_map[k] for k in new_flag_keys], key=lambda x: str(x))
        resolved_flags = sorted([flags_a_map[k] for k in resolved_flag_keys], key=lambda x: str(x))

        return {
            "run_a": {"id": run_id_a, "timestamp": run_a.get("timestamp")},
            "run_b": {"id": run_id_b, "timestamp": run_b.get("timestamp")},
            "vibe_score_delta": (
                report_b.get("vibe_score", 0) - report_a.get("vibe_score", 0)
            ),
            "new_issues": new_issues,
            "resolved_issues": resolved_issues,
            "new_ghosts": new_ghosts,
            "resolved_ghosts": resolved_ghosts,
            "new_flags": new_flags,
            "resolved_flags": resolved_flags,
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
    # Knowledge graph (placeholder)
    # ------------------------------------------------------------------

    async def get_knowledge_graph(
        self,
        repo_path: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Build a knowledge graph from accumulated analysis history.

        Aggregates recurring issues, ghost patterns, coupling hotspots,
        and vibe score trends across past runs.
        """
        if not self._db_exists():
            return self._empty_knowledge_graph()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

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
                if isinstance(issue, dict):
                    key = issue.get("message", json.dumps(issue, sort_keys=True))
                else:
                    key = str(issue)
                issue_counts[key] += 1
            for ghost in report.get("architectural_ghosts", []):
                if isinstance(ghost, dict):
                    key = ghost.get("message", json.dumps(ghost, sort_keys=True))
                else:
                    key = str(ghost)
                ghost_counts[key] += 1
            for flag in report.get("red_flags", []):
                if isinstance(flag, dict):
                    key = flag.get("message", json.dumps(flag, sort_keys=True))
                else:
                    key = str(flag)
                flag_counts[key] += 1

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
