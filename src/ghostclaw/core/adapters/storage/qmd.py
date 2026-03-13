"""Storage adapter using QMD (Quantum Memory Database) backend."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import aiosqlite
    HAS_AIOSQLITE = True
except ImportError:
    HAS_AIOSQLITE = False

from ghostclaw.core.adapters.base import StorageAdapter, AdapterMetadata
from ghostclaw.core.adapters.hooks import hookimpl

logger = logging.getLogger("ghostclaw.qmd")


class QMDStorageAdapter(StorageAdapter):
    """
    Persists ArchitectureReports to a QMD backend.

    Currently uses SQLite with a separate storage path from the default
    SQLiteStorageAdapter, enabling hybrid operation (both can be active).
    Future: Replace SQLite with a true vector-capable database.
    """

    def __init__(self):
        # QMD uses its own directory under .ghostclaw/storage/qmd/
        self.db_path = Path.cwd() / ".ghostclaw" / "storage" / "qmd" / "ghostclaw.db"
        self._initialized = False

    async def _ensure_db(self):
        if self._initialized:
            return
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
                    repo_path TEXT,
                    vcs_commit TEXT,
                    vcs_branch TEXT
                )
            """)
            await db.commit()
        self._initialized = True

    def get_metadata(self) -> AdapterMetadata:
        return AdapterMetadata(
            name="qmd",
            version="0.1.0",
            description="QMD (Quantum Memory Database) backend for high-performance architectural memory.",
            dependencies=["aiosqlite"],
        )

    async def is_available(self) -> bool:
        """QMD is available if aiosqlite is installed."""
        return HAS_AIOSQLITE

    # ------------------------------------------------------------------
    # StorageAdapter required methods
    # ------------------------------------------------------------------

    async def save_report(self, report: Any) -> str:
        """Save report to QMD store and return its ID."""
        await self._ensure_db()

        if hasattr(report, "model_dump"):
            data = report.model_dump()
        else:
            data = report

        vcs = data.get("metadata", {}).get("vcs", {})

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO reports
                (vibe_score, stack, files_analyzed, total_lines, report_json, repo_path, vcs_commit, vcs_branch)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data.get("vibe_score", 0),
                    data.get("stack", "unknown"),
                    data.get("files_analyzed", 0),
                    data.get("total_lines", 0),
                    json.dumps(data),
                    str(Path.cwd()),
                    vcs.get("commit"),
                    vcs.get("branch"),
                ),
            )
            await db.commit()
            return str(cursor.lastrowid)

    async def get_history(self, limit: int = 10) -> List[Any]:
        """Retrieve recent reports from QMD store."""
        await self._ensure_db()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM reports ORDER BY id DESC LIMIT ?", (limit,)
            ) as cursor:
                rows = await cursor.fetchall()
                results = []
                for row in rows:
                    data = json.loads(row["report_json"])
                    data["_db_id"] = row["id"]
                    data["_db_timestamp"] = row["timestamp"]
                    results.append(data)
                return results

    # ------------------------------------------------------------------
    # Hook implementations
    # ------------------------------------------------------------------

    @hookimpl
    async def ghost_save_report(self, report: Any) -> Optional[str]:
        """Hook implementation for saving report."""
        return await self.save_report(report)

    @hookimpl
    def ghost_get_metadata(self) -> Dict[str, Any]:
        """Expose metadata to the plugin manager."""
        meta = self.get_metadata()
        return {
            "name": meta.name,
            "version": meta.version,
            "description": meta.description,
            "available": True,
        }
