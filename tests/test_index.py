from pathlib import Path

from core.index import index_file, reindex_all, remove_file
from core.vec_store import get_all_meta


def test_index_small_file(wiki_env):
    f = wiki_env / "small.md"
    f.write_text("# Small\n\nShort content.", encoding="utf-8")
    index_file(f)

    meta = get_all_meta()
    keys = {m[0] for m in meta}
    assert "small.md" in keys


def test_index_large_file_with_headings(wiki_env):
    # Create a file > 10KB with headings
    content = "# Title\n\n" + "x" * 5000 + "\n\n## Section A\n\n" + "y" * 5000 + "\n"
    f = wiki_env / "large.md"
    f.write_text(content, encoding="utf-8")

    import config
    original = config.CHUNK_THRESHOLD
    config.CHUNK_THRESHOLD = 100  # lower threshold for testing
    try:
        index_file(f)
    finally:
        config.CHUNK_THRESHOLD = original

    meta = get_all_meta()
    keys = {m[0] for m in meta}
    assert "large.md#Title" in keys
    assert "large.md#Section A" in keys


def test_remove_file(wiki_env):
    f = wiki_env / "removeme.md"
    f.write_text("# Remove\n\nContent.", encoding="utf-8")
    index_file(f)
    remove_file(f)

    meta = get_all_meta()
    paths = {m[1] for m in meta}
    assert "removeme.md" not in paths


def test_reindex_all(sample_files):
    stats = reindex_all()
    assert stats["added"] == 3
    assert stats["updated"] == 0
    assert stats["removed"] == 0

    # Reindex again — should be no changes
    stats2 = reindex_all()
    assert stats2["added"] == 0
    assert stats2["updated"] == 0
    assert stats2["removed"] == 0


def test_reindex_detects_removal(sample_files):
    reindex_all()
    (sample_files / "characters.md").unlink()
    stats = reindex_all()
    assert stats["removed"] >= 1
