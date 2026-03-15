"""
Vector Store module for QMD hybrid search.

Provides an abstraction over LanceDB for storing and querying report embeddings.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import lancedb
from ghostclaw.core.embedding_cache import EmbeddingCache

logger = logging.getLogger("ghostclaw.vector_store")


class VectorStore:
    """
    Wrapper around LanceDB for storing and querying vector embeddings of report chunks.

    Storage location: .ghostclaw/storage/qmd/lancedb/
    Table: embeddings
    """

    def __init__(self, db_path: Optional[Path] = None, embedding_backend: str = "fastembed",
                 embedding_cache_size: int = 1000, embedding_cache_ttl: int = 3600):
        self.db_path = db_path or Path.cwd() / ".ghostclaw" / "storage" / "qmd" / "lancedb"
        self.embedding_backend = embedding_backend
        self._table = None
        self._embedder = None
        self._initialized = False
        # Embedding cache for repeated queries
        self._embedding_cache = EmbeddingCache(maxsize=embedding_cache_size, ttl=embedding_cache_ttl)

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

        # Initialize embedding model based on backend
        if self.embedding_backend == "sentence-transformers":
            try:
                import sentence_transformers
            except ImportError as e:
                raise ImportError(
                    "sentence_transformers is required for embedding_backend='sentence-transformers'. "
                    "Install with: pip install 'ghostclaw[qmd]'"
                ) from e
            self._embedder = sentence_transformers.SentenceTransformer("all-MiniLM-L6-v2")
        elif self.embedding_backend == "fastembed":
            try:
                from fastembed import TextEmbedding
            except ImportError as e:
                raise ImportError(
                    "fastembed is required for embedding_backend='fastembed'. "
                    "Install with: pip install fastembed"
                ) from e
            # Use a supported ONNX model (full HF ID)
            self._embedder = TextEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
        elif self.embedding_backend == "openai":
            try:
                import openai
            except ImportError as e:
                raise ImportError(
                    "openai is required for embedding_backend='openai'. "
                    "Install with: pip install openai"
                ) from e
            # OpenAI embedder will be a callable; we'll set API key from env
            self._embedder = openai.OpenAI()
        else:
            raise ValueError(f"Unsupported embedding_backend: {self.embedding_backend}")

        self._initialized = True
        logger.info("VectorStore initialized at %s with backend %s", self.db_path, self.embedding_backend)

    async def ensure_table(self) -> None:
        """Create the embeddings table if it doesn't exist."""
        await self.initialize()
        if self._table is None:
            import pyarrow as pa

            schema = pa.schema([
                ("report_id", pa.int64()),
                ("chunk_id", pa.string()),
                ("text", pa.string()),
                ("vector", lancedb.vector(384)),  # vector type from lancedb
                ("repo_path", pa.string()),
                ("timestamp", pa.string()),
                ("vibe_score", pa.int32()),
                ("stack", pa.string()),
            ])
            self._table = self._conn.create_table("embeddings", schema=schema, mode="overwrite")
            # Create IVF-PQ index for fast search (disabled for lancedb 0.29 compatibility; TODO: adapt)
            # self._table.create_index(
            #     "vector",  # column name as positional
            #     metric="cosine",  # lancedb 0.29 uses `metric`
            #     num_partitions=256,
            #     num_subvectors=96,
            #     replace=True,
            # )
            logger.info("Created embeddings table (index creation skipped for compatibility)")

    async def embed_text(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text string, with caching.

        Args:
            text: Input text to embed

        Returns:
            numpy array of shape (384,) or appropriate dimension
        """
        # Check cache first
        cached = self._embedding_cache.get(text)
        if cached is not None:
            return cached

        await self.initialize()
        backend = self.embedding_backend

        if backend in ("sentence-transformers", "fastembed"):
            if backend == "fastembed":
                # fastembed.embed returns a generator; convert to list and get first
                embeddings = list(self._embedder.embed([text]))
                embedding = embeddings[0]
            else:
                # sentence-transformers
                embedding = self._embedder.encode(text, convert_to_numpy=True, normalize_embeddings=True)
        elif backend == "openai":
            # OpenAI: use embeddings endpoint
            response = self._embedder.embeddings.create(input=text, model="text-embedding-ada-002")
            embedding = np.array(response.data[0].embedding, dtype=np.float32)
            # Normalize for cosine similarity
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
        else:
            raise ValueError(f"Unsupported embedding_backend: {backend}")

        # Cache the result
        self._embedding_cache.set(text, embedding)
        return embedding

    async def embed_batch(self, texts: List[str]) -> List[np.ndarray]:
        """
        Generate embeddings for multiple texts (batched for efficiency) with caching.

        Args:
            texts: List of input texts

        Returns:
            List of numpy arrays
        """
        # Check cache for each text
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
            # All cached
            embeddings = [emb for _, emb in sorted(cached_embeddings, key=lambda x: x[0])]
            return embeddings

        # Generate embeddings for uncached texts
        await self.initialize()
        backend = self.embedding_backend

        if backend in ("sentence-transformers", "fastembed"):
            if backend == "fastembed":
                # fastembed.embed returns a generator; convert to list
                new_embeddings = list(self._embedder.embed(uncached_texts))
            else:
                emb_array = self._embedder.encode(uncached_texts, convert_to_numpy=True, normalize_embeddings=True, batch_size=32)
                new_embeddings = [emb for emb in emb_array]
        elif backend == "openai":
            response = self._embedder.embeddings.create(input=uncached_texts, model="text-embedding-ada-002")
            new_embeddings = []
            for data in response.data:
                emb = np.array(data.embedding, dtype=np.float32)
                norm = np.linalg.norm(emb)
                if norm > 0:
                    emb = emb / norm
                new_embeddings.append(emb)
        else:
            raise ValueError(f"Unsupported embedding_backend: {backend}")

        # Cache the new embeddings
        for text, emb in zip(uncached_texts, new_embeddings):
            self._embedding_cache.set(text, emb)

        # Merge cached and new in original order
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
        """
        Add text chunks with their embeddings to the vector store.

        Args:
            report_id: ID of the report (from SQLite)
            chunks: List of dicts with keys:
                - chunk_id: Unique identifier within report (e.g., "issue-0")
                - text: The text content to embed and store
            base_metadata: Common metadata (repo_path, timestamp, vibe_score, stack)
        """
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

        # LanceDB uses pyarrow Table; convert records
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
        """
        Vector similarity search for the query.

        Args:
            query: Search query text
            limit: Maximum number of unique report_ids to return (chunks reranked later)
            repo_path: Optional filter by repository path
            stack: Optional filter by tech stack
            min_score: Optional minimum vibe score filter
            max_score: Optional maximum vibe score filter

        Returns:
            List of dicts with keys:
                - report_id: int
                - chunk_id: str
                - text: str (matched chunk)
                - score: float (cosine similarity)
                - repo_path, timestamp, vibe_score, stack
            Results are ordered by similarity.
        """
        await self.initialize()
        if self._table is None:
            return []

        query_embedding = await self.embed_text(query)

        # Build where clause for LanceDB
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

        # LanceDB search (returns LanceTable)
        results = self._table.search(
            query=query_embedding.tolist(),
            vector_column_name="vector",
        ).limit(limit * 3)  # oversample to deduplicate report_ids

        if where_clause:
            results = results.where(where_clause, prefilter=True)

        # Convert to Arrow Table then to list of dicts (no pandas required)
        arrow_table = results.to_arrow()
        records = arrow_table.to_pylist()
        if not records:
            return []

        # Deduplicate by report_id, keeping highest scoring chunk (lowest distance)
        records.sort(key=lambda r: r["_distance"])
        seen = set()
        final = []
        for r in records:
            rid = r["report_id"]
            if rid in seen:
                continue
            seen.add(rid)
            final.append({
                "report_id": rid,
                "chunk_id": r["chunk_id"],
                "text": r["text"],
                "score": 1 - r["_distance"],  # cosine similarity
                "repo_path": r["repo_path"],
                "timestamp": r["timestamp"],
                "vibe_score": r["vibe_score"],
                "stack": r["stack"],
            })
            if len(final) >= limit:
                break

        return final

    async def delete_report(self, report_id: int) -> None:
        """
        Remove all chunks belonging to a report.

        Args:
            report_id: Report ID to delete
        """
        await self.initialize()
        if self._table is None:
            return
        # LanceDB doesn't have direct delete yet; we rewrite the table (inefficient for now)
        # For alpha, we can skip deletion and just not query it (or implement via filter exclusion)
        logger.warning("delete_report not fully implemented in LanceDB alpha; consider full rebuild")

    async def clear(self) -> None:
        """Drop the entire embeddings table (for testing/migration)."""
        await self.initialize()
        if self._table:
            self._conn.drop_table("embeddings")
            self._table = None
            logger.info("Cleared embeddings table")

    async def close(self) -> None:
        """Close connections (if needed)."""
        # LanceDB doesn't require explicit close, but placeholder for future
        pass
