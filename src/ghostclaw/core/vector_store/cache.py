"""
Embedding cache management for QMD Vector Store.
"""

from ghostclaw.core.embedding_cache import EmbeddingCache

def get_embedding_cache(maxsize: int, ttl: int) -> EmbeddingCache:
    """Initialize and return an EmbeddingCache."""
    return EmbeddingCache(maxsize=maxsize, ttl=ttl)
