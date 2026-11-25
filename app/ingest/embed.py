from __future__ import annotations
from functools import lru_cache
import numpy as np
from sentence_transformers import SentenceTransformer

# Fallback code-trained model (no custom remote code required)
MODEL_NAME = "flax-sentence-embeddings/st-codesearch-distilroberta-base"
DIM = 768

@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)

def embed_texts(texts: list[str], *, batch_size: int = 32) -> np.ndarray:
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
