"""
QMD (Quantum Memory Database) backend for Ghostclaw.

Provides high-performance hybrid search (BM25 + vector) as an alternative
to the default SQLite MemoryStore.

This is a minimal implementation that uses SQLite with FTS5 for now,
providing the same interface as MemoryStore. Future versions may
integrate a true vector database or specialized QMD engine.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ghostclaw.qmd")


class QMDMemoryStore:
    """
    QMD-backed memory store with hybrid search capabilities.

    Storage location: .ghostclaw/storage/qmd/ghostclaw.db (separate from SQLite).
    Schema: Same as MemoryStore initially, but extensible for vectors.
    """

    def __init__(
        self,
        db_path: Optional[Path] = None,
        use_enhanced: bool = False,
        embedding_backend: str = "fastembed",
        ai_buff_enabled: bool = False,
    ):
        # Use .ghostclaw/storage/qmd/ instead of .ghostclaw/storage/
        self.db_path = db_path or Path.cwd() / ".ghostclaw" / "storage" / "qmd" / "ghostclaw.db"
        self.use_enhanced = use_enhanced
        self.embedding_backend = embedding_backend
        self.ai_buff_enabled = ai_buff_enabled

        # Subsystems
        # Using late imports to avoid circular dependencies
        from .qmd.fts import BM25Search
        from .qmd.indexer import ReportIndexer
        from .qmd.query_engine import QueryEngine
        from .vector_store import VectorStore
        from .qmd.embeddings import EmbeddingManager

        self.fts = BM25Search(self.db_path)

        if self.use_enhanced:
            # VectorStore defaults its db_path to .ghostclaw/storage/qmd/lancedb
            # We explicitly set it to be adjacent to the sqlite db for consistency
            lancedb_path = self.db_path.parent / "lancedb"
            self.vector_store = VectorStore(
                db_path=lancedb_path,
                embedding_backend=self.embedding_backend
            )
            self.embedding_mgr = EmbeddingManager(self.vector_store, self.embedding_backend)
        else:
            self.vector_store = None
            self.embedding_mgr = None

        self.indexer = ReportIndexer(self.db_path, self.fts, self.embedding_mgr)
        self.query_engine = QueryEngine(self.db_path, self.fts, self.vector_store)

    def get_stats(self) -> Dict[str, Any]:
        """Return statistics for the memory store."""
        stats = {
            "db_path": str(self.db_path),
            "use_enhanced": self.use_enhanced,
            "embedding_backend": self.embedding_backend,
            "ai_buff_enabled": self.ai_buff_enabled,
        }
        if self.vector_store:
            # Access underlying cache stats from VectorStore
            if hasattr(self.vector_store, "_embedding_cache"):
                stats["embedding_cache"] = self.vector_store._embedding_cache.stats()
            else:
                stats["embedding_cache"] = None
            
            stats["search_cache"] = None
        else:
            stats["embedding_cache"] = None
            stats["search_cache"] = None

        return stats

    async def list_runs(
        self,
        limit: int = 20,
        repo_path: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List recent runs."""
        if not self._db_exists():
            return []
        return await self.query_engine.list_runs(limit=limit, repo_path=repo_path)

    async def get_run(self, run_id: int) -> Optional[Dict[str, Any]]:
        """Get a single report by run_id."""
        if not self._db_exists():
            return None
        return await self.query_engine.get_run(run_id)

    async def get_previous_run(
        self, repo_path: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get the most recent analysis run, optionally filtered by repo path."""
        if not self._db_exists():
            return None
        runs = await self.query_engine.list_runs(limit=1, repo_path=repo_path)
        if not runs:
            return None
        return await self.query_engine.get_run(runs[0]["id"])

    async def search(
        self,
        query: str,
        limit: int = 10,
        repo_path: Optional[str] = None,
        stack: Optional[str] = None,
        min_score: Optional[int] = None,
        max_score: Optional[int] = None,
        alpha: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """Search across saved reports using hybrid BM25 + vector search."""
        if not self._db_exists():
            return []
        if alpha is None:
            # Default weighting: AI-Buff might prefer vector results
            alpha = 0.4 if self.ai_buff_enabled else 0.6

        return await self.query_engine.search(
            query=query,
            limit=limit,
            repo_path=repo_path,
            stack=stack,
            min_score=min_score,
            max_score=max_score,
            alpha=alpha
        )

    async def diff_runs(self, run_id_a: int, run_id_b: int) -> Optional[Dict[str, Any]]:
        """Compare two analysis runs."""
        if not self._db_exists():
            return None
        try:
            return await self.query_engine.diff_runs(run_id_a, run_id_b)
        except (ValueError, Exception) as e:
            logger.error("Error diffing runs %d and %d: %s", run_id_a, run_id_b, e)
            return None

    async def get_knowledge_graph(
        self,
        repo_path: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Build a knowledge graph from accumulated analysis history."""
        if not self._db_exists():
            return {
                "total_runs": 0,
                "stacks_seen": [],
                "score_trend": [],
                "recurring_issues": [],
                "recurring_ghosts": [],
                "recurring_flags": [],
                "coupling_hotspots": [],
                "nodes": [],
                "edges": []
            }
        # QueryEngine.knowledge_graph accepts limit
        return await self.query_engine.knowledge_graph(limit=limit)

    async def save_run(
        self,
        report: Dict[str, Any],
        repo_path: str,
        timestamp: Optional[str] = None,
    ) -> int:
        """Save an analysis run and handle FTS/embeddings indexing."""
        return await self.indexer.save(report, repo_path, timestamp)

    def _db_exists(self) -> bool:
        """Internal check for database existence."""
        return self.db_path.exists()
