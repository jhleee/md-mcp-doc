from __future__ import annotations

import numpy as np

from config import EMBED_MODEL

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(EMBED_MODEL)
    return _model


def embed(text: str) -> bytes:
    """Encode a single text string and return raw float32 bytes for sqlite-vec."""
    model = _get_model()
    vec = model.encode(text, normalize_embeddings=True)
    return np.asarray(vec, dtype=np.float32).tobytes()


def embed_batch(texts: list[str]) -> list[bytes]:
    """Encode multiple texts and return list of raw float32 bytes."""
    if not texts:
        return []
    model = _get_model()
    vecs = model.encode(texts, normalize_embeddings=True)
    return [np.asarray(v, dtype=np.float32).tobytes() for v in vecs]


def dimension() -> int:
    """Return the embedding dimension of the loaded model."""
    return _get_model().get_sentence_embedding_dimension()
