import pytest

from core.index import reindex_all
from tools.search import wiki_search


@pytest.fixture
def indexed_wiki(sample_files):
    """Sample files with completed indexing."""
    reindex_all()
    return sample_files


def test_text_search(indexed_wiki):
    results = wiki_search("fire", mode="text", k=5)
    paths = [r["path"] for r in results]
    assert "worlds/magic.md" in paths


def test_semantic_search(indexed_wiki):
    results = wiki_search("volcanic energy", mode="semantic", k=5)
    assert len(results) >= 1
    assert results[0]["path"] == "worlds/magic.md"


def test_hybrid_search(indexed_wiki):
    results = wiki_search("fire magic", mode="hybrid", k=5)
    assert len(results) >= 1
    assert results[0]["path"] == "worlds/magic.md"


def test_search_with_dir_filter(indexed_wiki):
    results = wiki_search("magic", mode="text", dir="worlds", k=5)
    for r in results:
        assert r["path"].startswith("worlds/")


def test_search_no_results(indexed_wiki):
    results = wiki_search("xyznonexistent123", mode="text", k=5)
    assert len(results) == 0


def test_search_invalid_mode(indexed_wiki):
    with pytest.raises(ValueError, match="Invalid search mode"):
        wiki_search("test", mode="invalid")


def test_hybrid_returns_scores(indexed_wiki):
    results = wiki_search("magic system", mode="hybrid", k=3)
    for r in results:
        assert "score" in r
        assert isinstance(r["score"], float)
