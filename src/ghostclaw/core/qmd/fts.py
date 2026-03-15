"""BM25 full-text search using SQLite FTS5."""

import aiosqlite
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ghostclaw.qmd.fts")


def _extract_searchable_text_impl(report_json_str: str) -> str:
    """Extract searchable text from a JSON report string."""
    try:
        report = json.loads(report_json_str)
    except (json.JSONDecodeError, TypeError):
        return ""
    parts = []

    # Explicitly pull known searchable fields to avoid pollution
    searchable_fields = ["issues", "architectural_ghosts", "red_flags", "ai_synthesis", "ai_reasoning"]
    for field in searchable_fields:
        val = report.get(field)
        if not val: continue
        if isinstance(val, list):
            for item in val:
                if isinstance(item, dict):
                    parts.append(str(item.get("message", "")))
                    parts.append(str(item.get("file", "")))
                else:
                    parts.append(str(item))
        else:
            parts.append(str(val))

    # AI synthesis and reasoning
    for field in ("ai_synthesis", "ai_reasoning"):
        val = report.get(field)
        if val:
            parts.append(str(val))

    # Generic issues/ghosts as strings if not already added
    for issue in report.get("issues", []):
        if isinstance(issue, str) and issue not in parts:
            parts.append(issue)
    for ghost in report.get("architectural_ghosts", []):
        if isinstance(ghost, str) and ghost not in parts:
            parts.append(ghost)

    # Ensure some content exists even if empty, but try to be descriptive
    if not parts:
        parts.append("__EMPTY_REPORT__")

    full_text = " ".join(parts)
    return full_text


class BM25Search:
    """BM25 search implementation using SQLite FTS5."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._initialized = False

    def is_initialized(self) -> bool:
        return self._initialized

    async def ensure_initialized(self, db=None) -> None:
        """Create FTS5 table and triggers if they don't exist."""
        if self._initialized:
            return

        if db:
            await self._ensure_initialized_with_db(db)
        else:
            async with aiosqlite.connect(self.db_path) as db:
                await self._ensure_initialized_with_db(db)

    async def _ensure_initialized_with_db(self, db) -> None:
        await self._register_searchable_function(db)
        async with db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='reports_fts'"
        ) as cursor:
            exists = await cursor.fetchone()

        if not exists:
            # Check if reports table exists first
            async with db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='reports'"
            ) as cursor:
                reports_exist = await cursor.fetchone()
            if not reports_exist:
                return

            # Note: We use 'porter' tokenizer for stemming.
            await db.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS reports_fts
                USING fts5(
                    report_id UNINDEXED,
                    content,
                    tokenize = 'porter'
                )
            """)
            await db.execute("""
                INSERT INTO reports_fts(report_id, content)
                SELECT id, extract_searchable_text(report_json)
                FROM reports
            """)
            await db.executescript("""
                CREATE TRIGGER reports_ai AFTER INSERT ON reports BEGIN
                    INSERT INTO reports_fts(report_id, content)
                    VALUES (new.id, extract_searchable_text(new.report_json));
                END;
                CREATE TRIGGER reports_ad AFTER DELETE ON reports BEGIN
                    DELETE FROM reports_fts WHERE report_id = old.id;
                END;
                CREATE TRIGGER reports_au AFTER UPDATE ON reports BEGIN
                    UPDATE reports_fts SET content = extract_searchable_text(new.report_json)
                    WHERE report_id = new.id;
                END;
            """)
            logger.info("Created FTS5 table and triggers")
        self._initialized = True

    async def _register_searchable_function(self, db) -> None:
        """Register the extract_searchable_text SQL function."""
        await db.create_function("extract_searchable_text", 1, _extract_searchable_text_impl)

    async def search(
        self,
        query: str,
        limit: int = 10,
        repo_path: Optional[str] = None,
        stack: Optional[str] = None,
        min_score: Optional[int] = None,
        max_score: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Perform BM25 search."""
        if not self._initialized:
            await self.ensure_initialized()

        results = []
        async with aiosqlite.connect(self.db_path) as db:
            await self._register_searchable_function(db)
            db.row_factory = aiosqlite.Row
            sql = """
                SELECT r.id, r.timestamp, r.vibe_score, r.stack, r.repo_path, r.report_json,
                       bm25(reports_fts) as bm25_score
                FROM reports_fts f
                JOIN reports r ON f.report_id = r.id
                WHERE (reports_fts MATCH ?)
            """

            # Simple heuristic for keyword search in FTS5
            search_query = query
            if '"' not in query and " " in query:
                # Optional: convert to AND search if not quoted?
                # For now, let's trust the input or wrap in quotes if spaces present and not quoted
                search_query = f'"{query}"'

            params = [search_query]
            if repo_path:
                sql += " AND r.repo_path = ?"
                params.append(repo_path)
            if stack:
                sql += " AND r.stack = ?"
                params.append(stack)
            if min_score is not None:
                sql += " AND r.vibe_score >= ?"
                params.append(min_score)
            if max_score is not None:
                sql += " AND r.vibe_score <= ?"
                params.append(max_score)

            # Use a slightly higher limit for internal search to allow for better filtering overlap
            sql += " ORDER BY bm25(reports_fts) ASC LIMIT ?"
            params.append(max(limit * 2, 50))

            async with db.execute(sql, params) as cursor:
                rows = await cursor.fetchall()
                for row in rows:
                    report = json.loads(row["report_json"])
                    results.append({
                        "id": row["id"],
                        "timestamp": row["timestamp"],
                        "vibe_score": row["vibe_score"],
                        "stack": row["stack"],
                        "repo_path": row["repo_path"],
                        "report": report,
                        "score": -row["bm25_score"],  # invert so higher = better
                        "matched_snippets": [],  # to be filled by caller
                    })
        return results
