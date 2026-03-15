"""QueryEngine — read operations: list, get, search, diff, knowledge_graph."""

import asyncio
import aiosqlite
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from .fts import BM25Search

logger = logging.getLogger("ghostclaw.qmd.query")


class QueryPlan:
    """Query execution plan (used by AI-Buff)."""
    def __init__(self, use_hybrid: bool, use_cache: bool, alpha: float):
        self.use_hybrid = use_hybrid
        self.use_cache = use_cache
        self.alpha = alpha


class QueryEngine:
    """Handles all read-only queries against the QMD store."""

    def __init__(self, db_path: Path, fts: BM25Search, vector_store=None):
        self.db_path = db_path
        self.fts = fts
        self.vector_store = vector_store

    async def list_runs(self, limit: int = 10, repo_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """List recent runs, optionally filtered by repo_path."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            sql = "SELECT id, timestamp, vibe_score, stack, repo_path FROM reports"
            params = []
            if repo_path:
                sql += " WHERE repo_path = ?"
                params.append(repo_path)
            sql += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            async with db.execute(sql, params) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_run(self, run_id: int) -> Optional[Dict[str, Any]]:
        """Get a single report by run_id."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM reports WHERE id = ?", (run_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    data = dict(row)
                    data["report"] = json.loads(data["report_json"])
                    del data["report_json"]
                    return data
                return None

    async def search(
        self,
        query: str,
        limit: int = 10,
        repo_path: Optional[str] = None,
        stack: Optional[str] = None,
        min_score: Optional[int] = None,
        max_score: Optional[int] = None,
        alpha: float = 0.6,
    ) -> List[Dict[str, Any]]:
        """Perform hybrid search (BM25 + vector) with fallback."""
        if not query:
            return []

        # Decide strategy
        use_hybrid = self.use_hybrid()
        if use_hybrid:
            results = await self._hybrid_search(query, limit, repo_path, stack, min_score, max_score, alpha)
        elif self.fts and self.fts.is_initialized():
            results = await self.fts.search(query, limit, repo_path, stack, min_score, max_score)
        else:
            results = await self._legacy_search(query, limit, repo_path, stack, min_score, max_score)

        # Apply snippets
        for r in results:
            r["matched_snippets"] = self._extract_snippets(r.get("report", {}), query)

        return results

    def use_hybrid(self) -> bool:
        return self.vector_store is not None and self.fts and self.fts.is_initialized()

    async def _hybrid_search(
        self,
        query: str,
        limit: int = 10,
        repo_path: Optional[str] = None,
        stack: Optional[str] = None,
        min_score: Optional[int] = None,
        max_score: Optional[int] = None,
        alpha: float = 0.6,
    ) -> List[Dict[str, Any]]:
        """Hybrid BM25 + vector similarity search."""
        bm25_task = self.fts.search(query, limit=limit*2, repo_path=repo_path, stack=stack, min_score=min_score, max_score=max_score)
        vector_task = self.vector_store.search(query, limit=limit*2, repo_path=repo_path, stack=stack, min_score=min_score, max_score=max_score)
        bm25_results, vector_results = await asyncio.gather(bm25_task, vector_task)

        # Merge and rerank (same as before)
        results_by_id: Dict[int, Dict] = {}

        if bm25_results:
            bm25_scores = [r['score'] for r in bm25_results]
            bm25_min, bm25_max = min(bm25_scores), max(bm25_scores)
            bm25_range = bm25_max - bm25_min or 1
            for r in bm25_results:
                norm = (r['score'] - bm25_min) / bm25_range
                r['_bm25_norm'] = norm
                r['_vector_sim'] = 0.0
                results_by_id[r['id']] = r

        for r in vector_results:
            rid = r.get('id') or r.get('report_id')
            r['_vector_sim'] = r['score']
            r['_bm25_norm'] = 0.0
            if rid in results_by_id:
                results_by_id[rid]['_vector_sim'] = r['score']
            else:
                r['id'] = rid  # Ensure 'id' is present for consistency
                results_by_id[rid] = r

        combined = list(results_by_id.values())
        for r in combined:
            r['score'] = r['_bm25_norm'] * alpha + r['_vector_sim'] * (1 - alpha)

        combined.sort(key=lambda x: x['score'], reverse=True)
        return combined[:limit]

    async def _legacy_search(
        self,
        query: str,
        limit: int = 10,
        repo_path: Optional[str] = None,
        stack: Optional[str] = None,
        min_score: Optional[int] = None,
        max_score: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Pure substring-based search (last resort)."""
        results = []
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            sql = """
                SELECT r.id, r.timestamp, r.vibe_score, r.stack, r.repo_path, r.report_json
                FROM reports r
                WHERE 1=1
            """
            params = []
            if repo_path:
                sql += " AND repo_path = ?"
                params.append(repo_path)
            if stack:
                sql += " AND stack = ?"
                params.append(stack)
            if min_score is not None:
                sql += " AND vibe_score >= ?"
                params.append(min_score)
            if max_score is not None:
                sql += " AND vibe_score <= ?"
                params.append(max_score)
            # Simple substring match on concatenated text
            sql += " AND report_json LIKE ? ORDER BY timestamp DESC LIMIT ?"
            params.append(f"%{query}%")
            params.append(limit)

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
                        "score": 0.0,
                    })
        return results

    def _extract_snippets(self, report: Dict[str, Any], query: str) -> List[str]:
        """Extract matched snippets from a report."""
        snippets = []
        # Simple: search in issues, ghosts, flags, synthesis
        text = self._extract_searchable_text(report)
        words = query.lower().split()
        for word in words:
            idx = text.lower().find(word)
            if idx >= 0:
                start = max(0, idx - 40)
                end = idx + 60
                snippet = text[start:end]
                snippets.append(snippet.strip())
                if len(snippets) >= 3:
                    break
        return snippets

    def _extract_searchable_text(self, report: Dict[str, Any]) -> str:
        """Extract plain text from report for snippet extraction."""
        parts = []
        for issue in report.get("issues", []):
            parts.append(str(issue))
        for ghost in report.get("architectural_ghosts", []):
            parts.append(str(ghost))
        for flag in report.get("red_flags", []):
            parts.append(str(flag))
        if report.get("ai_synthesis"):
            parts.append(str(report["ai_synthesis"]))
        return " ".join(parts)

    # AI-Buff: query planning (stub)
    def _plan_query(self, query: str, limit: int, filters: dict) -> QueryPlan:
        """Decide query execution strategy based on input."""
        token_count = len(query.split())
        if token_count <= 3:
            alpha = 0.9
        elif token_count >= 10:
            alpha = 0.3
        else:
            alpha = 0.6
        use_cache = limit <= 10
        return QueryPlan(use_hybrid=True, use_cache=use_cache, alpha=alpha)

    async def diff_runs(self, run_id_a: int, run_id_b: int) -> Dict[str, Any]:
        """Compare two architecture reports, returning a MemoryStore-compatible diff."""
        if run_id_a == run_id_b:
            raise ValueError("Cannot diff same run")
        r1 = await self.get_run(run_id_a)
        r2 = await self.get_run(run_id_b)
        if not r1 or not r2:
            raise ValueError("Run not found")

        report_a = r1.get("report", {})
        report_b = r2.get("report", {})

        new_issues = [i for i in report_b.get("issues", []) if i not in report_a.get("issues", [])]
        resolved_issues = [i for i in report_a.get("issues", []) if i not in report_b.get("issues", [])]
        new_ghosts = [g for g in report_b.get("architectural_ghosts", []) if g not in report_a.get("architectural_ghosts", [])]
        resolved_ghosts = [g for g in report_a.get("architectural_ghosts", []) if g not in report_b.get("architectural_ghosts", [])]
        new_flags = [f for f in report_b.get("red_flags", []) if f not in report_a.get("red_flags", [])]
        resolved_flags = [f for f in report_a.get("red_flags", []) if f not in report_b.get("red_flags", [])]

        diff = {
            "vibe_score_delta": report_b.get("vibe_score", 0) - report_a.get("vibe_score", 0),
            "new_issues": new_issues,
            "resolved_issues": resolved_issues,
            "new_ghosts": new_ghosts,
            "resolved_ghosts": resolved_ghosts,
            "new_flags": new_flags,
            "resolved_flags": resolved_flags,
            "metrics_comparison": {}, # Stub for now
            "run_a": r1,
            "run_b": r2,
        }
        return diff

    async def knowledge_graph(self, limit: int = 50) -> Dict[str, Any]:
        """Return a MemoryStore-compatible knowledge graph across recent runs."""
        recent_runs = []
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM reports ORDER BY timestamp DESC LIMIT ?", (limit,)) as cursor:
                rows = await cursor.fetchall()
                for row in rows:
                    data = dict(row)
                    data["report"] = json.loads(data["report_json"])
                    recent_runs.append(data)

        total_runs = len(recent_runs)
        stacks_seen = {}
        score_trend = []
        recurring_issues = {}
        recurring_ghosts = {}
        recurring_flags = {}

        for run in reversed(recent_runs): # chronological
            report = run["report"]
            stack = run.get("stack", "unknown")
            stacks_seen[stack] = stacks_seen.get(stack, 0) + 1
            score_trend.append({"timestamp": run["timestamp"], "vibe_score": run["vibe_score"]})
            
            for item in report.get("issues", []):
                recurring_issues[item] = recurring_issues.get(item, 0) + 1
            for item in report.get("architectural_ghosts", []):
                recurring_ghosts[item] = recurring_ghosts.get(item, 0) + 1
            for item in report.get("red_flags", []):
                recurring_flags[item] = recurring_flags.get(item, 0) + 1

        def to_recurring_list(d):
            return [{"item": k, "count": v} for k, v in d.items() if v > 1]

        return {
            "total_runs": total_runs,
            "stacks_seen": sorted(stacks_seen.keys()),
            "score_trend": score_trend,
            "recurring_issues": to_recurring_list(recurring_issues),
            "recurring_ghosts": to_recurring_list(recurring_ghosts),
            "recurring_flags": to_recurring_list(recurring_flags),
            "coupling_hotspots": [], # Stub
            "nodes": [], # Legacy QMD nodes
            "edges": [], # Legacy QMD edges
        }
