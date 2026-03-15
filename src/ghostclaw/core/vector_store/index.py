"""
LanceDB table management and search operations for QMD Vector Store.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ghostclaw.vector_store.index")

async def ensure_embeddings_table(conn):
    """Create the embeddings table if it doesn't exist."""
    import lancedb
    import pyarrow as pa

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
    table = conn.create_table("embeddings", schema=schema, mode="overwrite")
    return table

async def perform_search(table, query_embedding: List[float], limit: int, where_clause: Optional[str] = None) -> List[Dict[str, Any]]:
    """Execute search on the LanceDB table."""
    results = table.search(
        query=query_embedding,
        vector_column_name="vector",
    )

    if where_clause:
        results = results.where(where_clause, prefilter=True)

    results = results.limit(limit * 3)

    arrow_table = results.to_arrow()
    records = arrow_table.to_pylist()

    if not records:
        return []

    records.sort(key=lambda r: r["_distance"])
    seen = set()
    final = []
    for r in records:
        rid = r["report_id"]
        if rid in seen:
            continue
        seen.add(rid)
        final.append({
            "id": rid,
            "report_id": rid,
            "chunk_id": r["chunk_id"],
            "text": r["text"],
            "score": 1 - r["_distance"],
            "repo_path": r["repo_path"],
            "timestamp": r["timestamp"],
            "vibe_score": r["vibe_score"],
            "stack": r["stack"],
        })
        if len(final) >= limit:
            break

    return final
