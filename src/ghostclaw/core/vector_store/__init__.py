"""
Vector Store package for QMD hybrid search.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np

from .cache import EmbeddingCache
from .embedding import EmbeddingProvider
from .index import VectorIndex

logger = logging.getLogger("ghostclaw.vector_store")


class VectorStore:
    """
    Wrapper around LanceDB for storing and querying vector embeddings of report chunks.
    """

    def __init__(self, db_path: Optional[Path] = None, embedding_backend: str = "fastembed",
                 embedding_cache_size: int = 1000, embedding_cache_ttl: int = 3600,
                 embedding_cache_dir: Optional[str] = None):
        self.db_path = db_path or Path.cwd() / ".ghostclaw" / "storage" / "qmd" / "lancedb"
        self.embedding_backend = embedding_backend
        self._provider = EmbeddingProvider(backend=embedding_backend, cache_dir=embedding_cache_dir)
        self._index = VectorIndex(db_path=self.db_path)
        self._embedding_cache = EmbeddingCache(maxsize=embedding_cache_size, ttl=embedding_cache_ttl)

    async def initialize(self) -> None:
        """Initialize the vector store connection and embedder."""
        self._provider.initialize()
        self._index.connect()
        logger.info("VectorStore initialized at %s with backend %s", self.db_path, self.embedding_backend)

    async def ensure_table(self) -> None:
        """Create the embeddings table if it doesn't exist."""
        self._index.ensure_table()

    async def embed_text(self, text: str) -> np.ndarray:
        """Generate embedding for a single text string, with caching."""
        cached = self._embedding_cache.get(text)
        if cached is not None:
            return cached

        embeddings = await self._provider.embed_batch([text])
        embedding = embeddings[0]
        self._embedding_cache.set(text, embedding)
        return embedding

    async def embed_batch(self, texts: List[str]) -> List[np.ndarray]:
        """Generate embeddings for multiple texts (batched for efficiency) with caching."""
        cached_embeddings = []
        uncached_texts = []
        uncached_indices = []
        
        for idx, text in enumerate(texts):
            cached = self._embedding_cache.get(text)
            if cached is not None:
                cached_embeddings.append((idx, cached))
            else:
                uncached_texts.append(text)
                uncached_indices.append(idx)

        if not uncached_texts:
            return [emb for _, emb in sorted(cached_embeddings, key=lambda x: x[0])]

        new_embeddings = await self._provider.embed_batch(uncached_texts)

        for text, emb in zip(uncached_texts, new_embeddings):
            self._embedding_cache.set(text, emb)

        result_embeddings = [None] * len(texts)
        for idx, emb in cached_embeddings:
            result_embeddings[idx] = emb
        for idx, emb in zip(uncached_indices, new_embeddings):
            result_embeddings[idx] = emb

        return result_embeddings

    async def add_chunks(
        self,
        report_id: int,
        chunks: List[Dict[str, Any]],
        base_metadata: Dict[str, Any],
    ) -> None:
        """Add text chunks with their embeddings to the vector store."""
        await self.ensure_table()

        texts = [chunk["text"] for chunk in chunks]
        embeddings = await self.embed_batch(texts)

        records = []
        for chunk, embedding in zip(chunks, embeddings):
            record = {
                "report_id": report_id,
                "chunk_id": chunk["chunk_id"],
                "text": chunk["text"],
                "vector": embedding.tolist(),
                "repo_path": base_metadata.get("repo_path", ""),
                "timestamp": base_metadata.get("timestamp", ""),
                "vibe_score": base_metadata.get("vibe_score", 0),
                "stack": base_metadata.get("stack", ""),
            }
            records.append(record)

        self._index.add_records(records)
        logger.info("Added %d chunks for report_id=%d", len(chunks), report_id)

    async def search(
        self,
        query: str,
        limit: int = 10,
        repo_path: Optional[str] = None,
        stack: Optional[str] = None,
        min_score: Optional[int] = None,
        max_score: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Vector similarity search for the query."""
        query_embedding = await self.embed_text(query)

        where_clauses = []
        if repo_path: where_clauses.append(f"repo_path = '{repo_path.replace(chr(39), chr(39)+chr(39))}'")
        if stack: where_clauses.append(f"stack = '{stack.replace(chr(39), chr(39)+chr(39))}'")
        if min_score is not None: where_clauses.append(f"vibe_score >= {int(min_score)}")
        if max_score is not None: where_clauses.append(f"vibe_score <= {int(max_score)}")
        where_clause = " AND ".join(where_clauses) if where_clauses else None

        records = self._index.search(query_embedding.tolist(), limit, where_clause)
        if not records:
            return []

        records.sort(key=lambda r: r["_distance"])
        seen, final = set(), []
        for r in records:
            rid = r["report_id"]
            if rid in seen: continue
            seen.add(rid)
            final.append({
                "report_id": rid, "chunk_id": r["chunk_id"], "text": r["text"],
                "score": 1 - r["_distance"], "repo_path": r["repo_path"],
                "timestamp": r["timestamp"], "vibe_score": r["vibe_score"], "stack": r["stack"],
            })
            if len(final) >= limit: break

        return final

    async def delete_report(self, report_id: int) -> None:
        """Remove all chunks belonging to a report."""
        logger.warning("delete_report not fully implemented in LanceDB alpha")

    async def clear(self) -> None:
        """Drop the entire embeddings table."""
        self._index.clear()

    @property
    def _table(self):
        """Internal table reference for backward compatibility (tests)."""
        return self._index.table

    async def close(self) -> None:
        """Close connections."""
        pass
