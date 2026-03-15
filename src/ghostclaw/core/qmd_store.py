"""
QMD (Quantum Memory Database) backend for Ghostclaw.

Provides high-performance hybrid search (BM25 + vector) as an alternative
to the default SQLite MemoryStore.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from ghostclaw.core.qmd.fts import BM25Search
from ghostclaw.core.qmd.embeddings import EmbeddingManager
from ghostclaw.core.qmd.indexer import ReportIndexer
from ghostclaw.core.qmd.query_engine import QueryEngine
from ghostclaw.core.vector_store import VectorStore

logger = logging.getLogger("ghostclaw.qmd")

try:
    import aiosqlite
    HAS_AIOSQLITE = True
except ImportError:
    HAS_AIOSQLITE = False


class QMDMemoryStore:
    """
    QMD-backed memory store with hybrid search capabilities.
    """

    def __init__(self, db_path: Optional[Path] = None, use_enhanced: bool = False,
                 embedding_backend: str = "fastembed", ai_buff_enabled: bool = False):
        self.db_path = db_path or Path.cwd() / ".ghostclaw" / "storage" / "qmd" / "ghostclaw.db"
        self.use_enhanced = use_enhanced
        self.embedding_backend = embedding_backend
        self.ai_buff_enabled = ai_buff_enabled

        self.fts = BM25Search(self.db_path)

        self.vector_store = None
        self.embedding_mgr = None
        if use_enhanced:
            self.vector_store = VectorStore(embedding_backend=embedding_backend)
            self.embedding_mgr = EmbeddingManager(self.vector_store, embedding_backend)

        self.indexer = ReportIndexer(self.db_path, self.fts, self.embedding_mgr)
        self.query_engine = QueryEngine(self.db_path, self.fts, self.vector_store)
        self.query_engine.use_hybrid_mode = use_enhanced

    def _db_exists(self) -> bool:
        return self.db_path.exists()

    async def _ensure_db(self) -> None:
        if not HAS_AIOSQLITE:
            raise ImportError("aiosqlite is required for QMDMemoryStore")
        await self.indexer._ensure_db()

    async def list_runs(self, limit: int = 20, repo_path: Optional[str] = None) -> List[Dict[str, Any]]:
        return await self.query_engine.list_runs(limit, repo_path)

    async def get_run(self, run_id: int) -> Optional[Dict[str, Any]]:
        return await self.query_engine.get_run(run_id)

    async def get_previous_run(self, repo_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
        runs = await self.query_engine.list_runs(limit=1, repo_path=repo_path)
        if not runs:
            return None
        return await self.get_run(runs[0]["id"])

    async def search(self, query: str, limit: int = 10, repo_path: Optional[str] = None,
                     stack: Optional[str] = None, min_score: Optional[int] = None,
                     max_score: Optional[int] = None, alpha: float = 0.6) -> List[Dict[str, Any]]:
        return await self.query_engine.search(query, limit, repo_path, stack, min_score, max_score, alpha)

    async def diff_runs(self, run_id_a: int, run_id_b: int) -> Optional[Dict[str, Any]]:
        return await self.query_engine.diff_runs(run_id_a, run_id_b)

    async def get_knowledge_graph(self, repo_path: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
        return await self.query_engine.knowledge_graph(limit)

    async def save_run(self, report: Dict[str, Any], repo_path: str, timestamp: Optional[str] = None) -> int:
        return await self.indexer.save(report, repo_path, timestamp)
