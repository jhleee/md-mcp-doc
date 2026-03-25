import numpy as np

from core.embedder import dimension, embed, embed_batch


def test_embed_returns_bytes():
    result = embed("hello world")
    assert isinstance(result, bytes)
    # float32 bytes should be dim * 4
    dim = dimension()
    assert len(result) == dim * 4


def test_embed_batch():
    results = embed_batch(["hello", "world"])
    assert len(results) == 2
    assert all(isinstance(r, bytes) for r in results)


def test_embed_batch_empty():
    results = embed_batch([])
    assert results == []


def test_similar_texts_close():
    v1 = np.frombuffer(embed("fire magic"), dtype=np.float32)
    v2 = np.frombuffer(embed("flame sorcery"), dtype=np.float32)
    v3 = np.frombuffer(embed("database migration"), dtype=np.float32)
    # fire/flame should be more similar than fire/database
    sim_close = np.dot(v1, v2)
    sim_far = np.dot(v1, v3)
    assert sim_close > sim_far


def test_dimension():
    dim = dimension()
    assert dim == 384  # all-MiniLM-L6-v2 produces 384-dim vectors
