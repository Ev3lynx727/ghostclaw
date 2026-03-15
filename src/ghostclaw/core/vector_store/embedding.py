"""
Embedding generation logic for QMD Vector Store.
"""

import numpy as np
from typing import List

async def generate_embeddings(embedder, texts: List[str], backend: str) -> List[np.ndarray]:
    """
    Generate embeddings for multiple texts using the specified backend.
    """
    if backend in ("sentence-transformers", "fastembed"):
        if backend == "fastembed":
            return list(embedder.embed(texts))
        else:
            emb_array = embedder.encode(texts, convert_to_numpy=True, normalize_embeddings=True, batch_size=32)
            return [emb for emb in emb_array]
    elif backend == "openai":
        response = embedder.embeddings.create(input=texts, model="text-embedding-ada-002")
        new_embeddings = []
        for data in response.data:
            emb = np.array(data.embedding, dtype=np.float32)
            norm = np.linalg.norm(emb)
            if norm > 0:
                emb = emb / norm
            new_embeddings.append(emb)
        return new_embeddings
    else:
        raise ValueError(f"Unsupported embedding_backend: {backend}")
