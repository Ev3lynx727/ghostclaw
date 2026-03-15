"""
LanceDB index management for Ghostclaw vector store.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import pyarrow as pa
import lancedb

logger = logging.getLogger("ghostclaw.vector_store.index")


class VectorIndex:
    """Handles LanceDB table operations and similarity search."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._conn = None
        self._table = None

    def connect(self) -> None:
        """Establish connection to LanceDB."""
        if self._conn is not None:
            return
        self.db_path.mkdir(parents=True, exist_ok=True)
        self._conn = lancedb.connect(str(self.db_path))
        if "embeddings" in self._conn.list_tables():
            self._table = self._conn.open_table("embeddings")

    def ensure_table(self) -> None:
        """Create the embeddings table if it doesn't exist."""
        self.connect()
        if self._table is None:
            schema = pa.schema([
                ("report_id", pa.int64()),
                ("chunk_id", pa.string()),
                ("text", pa.string()),
                ("vector", lancedb.vector(384)),
                ("repo_path", pa.string()),
                ("timestamp", pa.string()),
                ("vibe_score", pa.int32()),
                ("stack", pa.string()),
            ])
            self._table = self._conn.create_table("embeddings", schema=schema, mode="overwrite")
            logger.info("Created embeddings table")

    def add_records(self, records: List[Dict[str, Any]]) -> None:
        """Add records to the embeddings table."""
        self.ensure_table()
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

    def search(self, query_vector: List[float], limit: int, where_clause: Optional[str] = None) -> List[Dict[str, Any]]:
        """Perform vector similarity search."""
        self.connect()
        if self._table is None:
            return []

        results = self._table.search(
            query=query_vector,
            vector_column_name="vector",
        ).metric("cosine").limit(limit * 3)

        if where_clause:
            results = results.where(where_clause, prefilter=True)

        arrow_table = results.to_arrow()
        return arrow_table.to_pylist()

    def clear(self) -> None:
        """Drop the embeddings table."""
        self.connect()
        if self._table:
            self._conn.drop_table("embeddings")
            self._table = None

    @property
    def table(self):
        return self._table
