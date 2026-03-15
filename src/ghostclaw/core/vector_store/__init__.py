"""
Vector Store module for QMD hybrid search.

Provides an abstraction over LanceDB for storing and querying report embeddings.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from ghostclaw.core.vector_store.cache import get_embedding_cache
from ghostclaw.core.vector_store.embedding import generate_embeddings
from ghostclaw.core.vector_store.index import ensure_embeddings_table, perform_search

logger = logging.getLogger("ghostclaw.vector_store")


class VectorStore:
    """
    Wrapper around LanceDB for storing and querying vector embeddings of report chunks.
    """

    def __init__(self, db_path: Optional[Path] = None, embedding_backend: str = "fastembed",
                 embedding_cache_size: int = 1000, embedding_cache_ttl: int = 3600):
        self.db_path = db_path or Path.cwd() / ".ghostclaw" / "storage" / "qmd" / "lancedb"
        self.embedding_backend = embedding_backend
        self._table = None
        self._embedder = None
        self._initialized = False
        self._embedding_cache = get_embedding_cache(maxsize=embedding_cache_size, ttl=embedding_cache_ttl)

    async def initialize(self) -> None:
        """Initialize the vector store connection and embedder."""
        if self._initialized:
            return

        try:
            import lancedb
        except ImportError as e:
            raise ImportError(
                "lancedb is required for VectorStore. Install with: pip install 'ghostclaw[qmd]'"
            ) from e

        self.db_path.mkdir(parents=True, exist_ok=True)
        self._conn = lancedb.connect(str(self.db_path))
        self._table = self._conn.open_table("embeddings") if "embeddings" in self._conn.table_names() else None

        if self.embedding_backend == "sentence-transformers":
            try:
                import sentence_transformers
            except ImportError as e:
                raise ImportError(
                    "sentence_transformers is required for embedding_backend='sentence-transformers'."
                ) from e
            self._embedder = sentence_transformers.SentenceTransformer("all-MiniLM-L6-v2")
        elif self.embedding_backend == "fastembed":
            try:
                from fastembed import TextEmbedding
            except ImportError as e:
                raise ImportError("fastembed is required. Install with: pip install fastembed") from e
            self._embedder = TextEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
        elif self.embedding_backend == "openai":
            try:
                import openai
            except ImportError as e:
                raise ImportError("openai is required. Install with: pip install openai") from e
            self._embedder = openai.OpenAI()
        else:
            raise ValueError(f"Unsupported embedding_backend: {self.embedding_backend}")

        self._initialized = True

    async def ensure_table(self) -> None:
        """Create the embeddings table if it doesn't exist."""
        await self.initialize()
        if self._table is None:
            self._table = await ensure_embeddings_table(self._conn)

    async def embed_text(self, text: str) -> np.ndarray:
        """Generate embedding for a single text string, with caching."""
        cached = self._embedding_cache.get(text)
        if cached is not None:
            return cached

        await self.initialize()
        embeddings = await generate_embeddings(self._embedder, [text], self.embedding_backend)
        embedding = embeddings[0]

        self._embedding_cache.set(text, embedding)
        return embedding

    async def embed_batch(self, texts: List[str]) -> List[np.ndarray]:
        """Generate embeddings for multiple texts, with caching."""
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
            embeddings = [emb for _, emb in sorted(cached_embeddings, key=lambda x: x[0])]
            return embeddings

        await self.initialize()
        new_embeddings = await generate_embeddings(self._embedder, uncached_texts, self.embedding_backend)

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

        import pyarrow as pa
        table = pa.Table.from_pydict({
            "report_id": [r["report_id"] for r in records],
            "chunk_id": [r["chunk_id"] for r in records],
            "text": [r["text"] for r in records],
            "vector": [r["vector"] for r in records],
            "repo_path": [r["repo_path"] for r in records],
            "timestamp": [r["timestamp"] for r in records],
            "vibe_score": [r["vibe_score"] for r in records],
            "stack": [r["stack"] for r in records],
        })

        self._table.add(table)

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
        await self.initialize()
        if self._table is None:
            return []

        query_embedding = await self.embed_text(query)

        where_clauses = []
        if repo_path:
            where_clauses.append(f"repo_path = '{repo_path}'")
        if stack:
            where_clauses.append(f"stack = '{stack}'")
        if min_score is not None:
            where_clauses.append(f"vibe_score >= {min_score}")
        if max_score is not None:
            where_clauses.append(f"vibe_score <= {max_score}")
        where_clause = " AND ".join(where_clauses) if where_clauses else None

        return await perform_search(self._table, query_embedding.tolist(), limit, where_clause)

    async def delete_report(self, report_id: int) -> None:
        """Remove all chunks belonging to a report."""
        pass

    async def clear(self) -> None:
        """Drop the entire embeddings table."""
        await self.initialize()
        if self._table:
            self._conn.drop_table("embeddings")
            self._table = None

    async def close(self) -> None:
        """Close connections."""
        pass
