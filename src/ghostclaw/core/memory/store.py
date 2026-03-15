"""
Core database logic for Ghostclaw Memory.
"""

import json
import sqlite3
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import aiosqlite
    HAS_AIOSQLITE = True
except ImportError:
    HAS_AIOSQLITE = False

logger = logging.getLogger("ghostclaw.memory.store")

class MemoryStore:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path.cwd() / ".ghostclaw" / "storage" / "ghostclaw.db"

    def _db_exists(self) -> bool:
        return self.db_path.exists()

    async def _ensure_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
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
                    repo_path TEXT
                )
            """)
            await db.commit()

    async def list_runs(self, limit: int = 20, repo_path: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self._db_exists(): return []
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            cols = "id, timestamp, vibe_score, stack, files_analyzed, total_lines, repo_path"
            if repo_path:
                query = f"SELECT {cols} FROM reports WHERE repo_path = ? ORDER BY timestamp DESC LIMIT ?"
                params = (repo_path, limit)
            else:
                query = f"SELECT {cols} FROM reports ORDER BY timestamp DESC LIMIT ?"
                params = (limit,)
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_run(self, run_id: int) -> Optional[Dict[str, Any]]:
        if not self._db_exists(): return None
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            async with db.execute("SELECT * FROM reports WHERE id = ?", (run_id,)) as cursor:
                row = await cursor.fetchone()
                if not row: return None
                row_dict = dict(row)
                try:
                    row_dict["report"] = json.loads(row_dict.pop("report_json", "{}"))
                except:
                    row_dict["report"] = {}
                return row_dict

    async def get_previous_run(self, repo_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if not self._db_exists(): return None
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            query = "SELECT * FROM reports" + (" WHERE repo_path = ?" if repo_path else "") + " ORDER BY timestamp DESC LIMIT 1"
            params = (repo_path,) if repo_path else ()
            async with db.execute(query, params) as cursor:
                row = await cursor.fetchone()
                if not row: return None
                row_dict = dict(row)
                try:
                    row_dict["report"] = json.loads(row_dict.pop("report_json", "{}"))
                except:
                    row_dict["report"] = {}
                return row_dict

    async def search(self, query: str, repo_path=None, stack=None, min_score=None, max_score=None, limit=10) -> List[Dict[str, Any]]:
        if not self._db_exists(): return []
        conditions, params = [], []
        if query:
            conditions.append("report_json LIKE ? ESCAPE '\\'")
            params.append(f"%{query.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')}%")
        if repo_path: conditions.append("repo_path = ?"); params.append(repo_path)
        if stack: conditions.append("stack = ?"); params.append(stack)
        if min_score is not None: conditions.append("vibe_score >= ?"); params.append(min_score)
        if max_score is not None: conditions.append("vibe_score <= ?"); params.append(max_score)
        where = " AND ".join(conditions) if conditions else "1=1"
        sql = f"SELECT id, timestamp, vibe_score, stack, files_analyzed, total_lines, repo_path, report_json FROM reports WHERE {where} ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            async with db.execute(sql, params) as cursor:
                rows = await cursor.fetchall()
        results = []
        for row in rows:
            rd = dict(row)
            rj = rd.pop("report_json", "{}")
            rd["matched_snippets"] = self._extract_snippets(rj, query)
            results.append(rd)
        return results

    @staticmethod
    def _extract_snippets(report_json_str: str, query: str, max_snippets: int = 5, context_chars: int = 120) -> List[str]:
        if not query: return []
        snippets = []
        lower_text, lower_query = report_json_str.lower(), query.lower()
        start = 0
        while len(snippets) < max_snippets:
            idx = lower_text.find(lower_query, start)
            if idx == -1: break
            s, e = max(0, idx - context_chars), min(len(report_json_str), idx + len(query) + context_chars)
            snippet = report_json_str[s:e].strip().replace("\\n", " ").replace('\\"', '"')
            snippets.append(f"...{snippet}...")
            start = idx + len(query)
        return snippets

    async def diff_runs(self, run_id_a: int, run_id_b: int) -> Optional[Dict[str, Any]]:
        run_a, run_b = await self.get_run(run_id_a), await self.get_run(run_id_b)
        if not run_a or not run_b: return None
        report_a, report_b = run_a.get("report", {}), run_b.get("report", {})
        def _m(items):
            res = {}
            for i in items:
                k = json.dumps(i, sort_keys=True) if isinstance(i, dict) else str(i)
                res[k] = i
            return res
        ia, ib = _m(report_a.get("issues", [])), _m(report_b.get("issues", []))
        ga, gb = _m(report_a.get("architectural_ghosts", [])), _m(report_b.get("architectural_ghosts", []))
        fa, fb = _m(report_a.get("red_flags", [])), _m(report_b.get("red_flags", []))

        return {
            "run_a": {"id": run_id_a, "timestamp": run_a.get("timestamp")},
            "run_b": {"id": run_id_b, "timestamp": run_b.get("timestamp")},
            "vibe_score_delta": (report_b.get("vibe_score", 0) - report_a.get("vibe_score", 0)),
            "new_issues": sorted([ib[k] for k in set(ib.keys())-set(ia.keys())], key=str),
            "resolved_issues": sorted([ia[k] for k in set(ia.keys())-set(ib.keys())], key=str),
            "new_ghosts": sorted([gb[k] for k in set(gb.keys())-set(ga.keys())], key=str),
            "resolved_ghosts": sorted([ga[k] for k in set(ga.keys())-set(gb.keys())], key=str),
            "new_flags": sorted([fb[k] for k in set(fb.keys())-set(fa.keys())], key=str),
            "resolved_flags": sorted([fa[k] for k in set(fa.keys())-set(fb.keys())], key=str),
            "metrics_comparison": {
                "files_analyzed": {"before": report_a.get("files_analyzed", 0), "after": report_b.get("files_analyzed", 0)},
                "total_lines": {"before": report_a.get("total_lines", 0), "after": report_b.get("total_lines", 0)},
                "vibe_score": {"before": report_a.get("vibe_score", 0), "after": report_b.get("vibe_score", 0)},
            }
        }

    async def get_knowledge_graph(self, **kwargs) -> Dict[str, Any]:
        from ghostclaw.core.memory.mcp import get_knowledge_graph
        return await get_knowledge_graph(self, **kwargs)
