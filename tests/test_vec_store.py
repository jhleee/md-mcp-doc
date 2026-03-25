from core.embedder import embed
from core.vec_store import (
    delete_by_path,
    get_all_meta,
    search,
    upsert,
    upsert_batch,
)


def test_upsert_and_search():
    emb = embed("hello world")
    upsert("test.md", "test.md", 1000.0, emb)

    results = search(emb, k=5)
    assert len(results) >= 1
    assert results[0][0] == "test.md"


def test_upsert_batch_and_meta():
    emb1 = embed("first document")
    emb2 = embed("second document")
    upsert_batch([
        ("a.md", "a.md", 100.0, emb1),
        ("b.md", "b.md", 200.0, emb2),
    ])

    meta = get_all_meta()
    paths = {m[1] for m in meta}
    assert "a.md" in paths
    assert "b.md" in paths


def test_delete_by_path():
    emb = embed("to be deleted")
    upsert("del.md", "del.md", 100.0, emb)
    delete_by_path("del.md")

    meta = get_all_meta()
    paths = {m[1] for m in meta}
    assert "del.md" not in paths


def test_upsert_overwrite():
    emb1 = embed("version one")
    emb2 = embed("version two")
    upsert("ow.md", "ow.md", 100.0, emb1)
    upsert("ow.md", "ow.md", 200.0, emb2)

    meta = get_all_meta()
    for key, path, mtime in meta:
        if path == "ow.md":
            assert mtime == 200.0
            break
