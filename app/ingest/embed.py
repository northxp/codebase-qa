"""Embed texts with a small general-purpose sentence-transformer.

Baseline model for variant A. Week 2's variant F swaps this for a
code-trained model (CodeRankEmbed or Jina Code V2).
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DIM = 384


@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)


def embed_texts(texts: list[str], *, batch_size: int = 32) -> np.ndarray:
    """Encode `texts` into a (n, DIM) float32 array of L2-normalised vectors."""
    if not texts:
        return np.empty((0, DIM), dtype=np.float32)
    model = get_model()
    return model.encode(
        texts,
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=False,
        convert_to_numpy=True,
    )
