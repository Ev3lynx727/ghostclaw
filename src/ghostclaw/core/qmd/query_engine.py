"""QueryEngine — read operations: list, get, search, diff, knowledge_graph."""

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
            r['_vector_sim'] = r['score']
            r['_bm25_norm'] = 0.0
            if r['id'] in results_by_id:
                results_by_id[r['id']]['_vector_sim'] = r['score']
            else:
                results_by_id[r['id']] = r

        combined = list(results_by_id.values())
        for r in combined:
            r['score'] = (1 - r['_bm25_norm']) * alpha + r['_vector_sim'] * (1 - alpha)

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

    async def diff_runs(self, run_id1: int, run_id2: int) -> Dict[str, Any]:
        """Compare two architecture reports."""
        if run_id1 == run_id2:
            raise ValueError("Cannot diff same run")
        r1 = await self.get_run(run_id1)
        r2 = await self.get_run(run_id2)
        if not r1 or not r2:
            raise ValueError("Run not found")
        diff = {
            "run1": r1,
            "run2": r2,
            "field_diffs": [],
            "issue_count_diff": len(r2.get("issues", [])) - len(r1.get("issues", [])),
            "ghost_count_diff": len(r2.get("architectural_ghosts", [])) - len(r1.get("architectural_ghosts", [])),
            "red_flag_count_diff": len(r2.get("red_flags", [])) - len(r1.get("red_flags", [])),
        }
        for field in ["vibe_score", "files_analyzed", "total_lines"]:
            if r1.get(field) != r2.get(field):
                diff["field_diffs"].append({"field": field, "old": r1.get(field), "new": r2.get(field)})
        return diff

    async def knowledge_graph(self, limit: int = 50) -> Dict[str, Any]:
        """Return a knowledge graph across recent runs."""
        recent = await self.list_runs(limit=limit)
        nodes = {}
        edges = {}
        for run in recent:
            stack = run.get("stack", "unknown")
            nodes[stack] = nodes.get(stack, 0) + 1
            # Co-occurrence edges within same repo
            for other in recent:
                if other["id"] != run["id"] and other.get("repo_path") == run.get("repo_path"):
                    other_stack = other.get("stack", "unknown")
                    if other_stack != stack:
                        edge_key = tuple(sorted([stack, other_stack]))
                        edges[edge_key] = edges.get(edge_key, 0) + 1
        node_list = [{"id": k, "type": "stack", "count": v} for k, v in nodes.items()]
        edge_list = [{"source": a, "target": b, "weight": w} for (a, b), w in edges.items()]
        return {"nodes": node_list, "edges": edge_list}
