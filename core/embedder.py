from __future__ import annotations

import numpy as np

import config

_model = None


def _get_model():
    global _model
    if _model is None:
        import os

        from sentence_transformers import SentenceTransformer

        # Suppress BertModel LOAD REPORT (C-level stdout/stderr from safetensors)
        devnull = os.open(os.devnull, os.O_WRONLY)
        old_stdout = os.dup(1)
        old_stderr = os.dup(2)
        os.dup2(devnull, 1)
        os.dup2(devnull, 2)
        try:
            _model = SentenceTransformer(config.EMBED_MODEL)
        finally:
            os.dup2(old_stdout, 1)
            os.dup2(old_stderr, 2)
            os.close(devnull)
            os.close(old_stdout)
            os.close(old_stderr)
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
