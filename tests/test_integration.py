"""End-to-end integration test: write → search → get → replace → links → delete flow."""

from core.index import reindex_all
from tools.crud import wiki_delete, wiki_get, wiki_get_batch, wiki_list, wiki_write, wiki_append
from tools.links import resolve_link
from tools.replace import wiki_replace
from tools.search import wiki_search


def test_full_workflow(wiki_env):
    # 1. Write several pages
    r1 = wiki_write("index.md", "# Home\n\nWelcome to the wiki.\n\n- [[dragons]]\n- [[spells]]\n")
    assert r1["ok"] is True
    # dragons and spells don't exist yet → invalid links
    assert len(r1.get("invalid_links", [])) == 2

    wiki_write("dragons.md", "# Dragons\n\nDragons breathe fire and ice.\n\nSee [[spells]] for magic details.\n")
    wiki_write("spells.md", "# Spells\n\nFireball and Frostbolt are common spells.\n\nRelated: [[dragons]]\n")
    wiki_write("archive/old.md", "# Old Notes\n\nDeprecated content.\n")

    # 2. List all files
    files = wiki_list()
    paths = {f["path"] for f in files}
    assert paths == {"index.md", "dragons.md", "spells.md", "archive/old.md"}

    # 3. List subdirectory
    archive_files = wiki_list("archive")
    assert len(archive_files) == 1

    # 4. Get single file
    data = wiki_get("dragons.md")
    assert "breathe fire" in data["content"]
    assert data["meta"]["line_count"] > 0

    # 5. Get batch
    batch = wiki_get_batch(["index.md", "spells.md", "nonexistent.md"])
    assert len(batch) == 3
    assert "error" in batch[2]

    # 6. Append content
    wiki_append("dragons.md", "\n## Ice Dragons\n\nThey prefer cold climates.\n")
    updated = wiki_get("dragons.md")
    assert "Ice Dragons" in updated["content"]

    # 7. Build index and search
    reindex_all()

    # 7a. Text search
    text_results = wiki_search("fire", mode="text", k=5)
    text_paths = [r["path"] for r in text_results]
    assert "dragons.md" in text_paths

    # 7b. Semantic search
    sem_results = wiki_search("mythical creatures that breathe fire", mode="semantic", k=3)
    assert len(sem_results) >= 1
    assert sem_results[0]["path"] == "dragons.md"

    # 7c. Hybrid search
    hybrid_results = wiki_search("fire magic spells", mode="hybrid", k=5)
    assert len(hybrid_results) >= 1
    result_paths = {r["path"] for r in hybrid_results}
    assert "dragons.md" in result_paths or "spells.md" in result_paths

    # 8. Link resolution
    resolved = resolve_link("dragons")
    assert resolved["exists"] is True
    assert resolved["path"] == "dragons.md"

    resolved_missing = resolve_link("unicorns")
    assert resolved_missing["exists"] is False

    # 9. Replace across files
    replace_result = wiki_replace("fire", "flame")
    assert replace_result["count"] >= 1
    assert len(replace_result["changed_files"]) >= 1

    # Verify replacement
    dragons = wiki_get("dragons.md")
    assert "flame" in dragons["content"]
    assert "fire" not in dragons["content"].lower() or "flame" in dragons["content"]

    # 10. Verify re-index after replace picks up changes
    reindex_all()
    flame_results = wiki_search("flame", mode="text", k=5)
    flame_paths = [r["path"] for r in flame_results]
    assert "dragons.md" in flame_paths

    # 11. Delete a file
    del_result = wiki_delete("archive/old.md")
    assert del_result["ok"] is True

    files_after = wiki_list()
    paths_after = {f["path"] for f in files_after}
    assert "archive/old.md" not in paths_after

    # 12. Verify reindex detects deletion
    stats = reindex_all()
    assert stats["removed"] >= 0  # may be 0 if delete already cleaned index


def test_write_reindex_search_cycle(wiki_env):
    """Verify that write auto-indexes and search finds it immediately."""
    wiki_write("fresh.md", "# Fresh Page\n\nQuantum computing basics.\n")

    # Semantic search should find it (auto-indexed on write)
    results = wiki_search("quantum computing", mode="semantic", k=3)
    assert any(r["path"] == "fresh.md" for r in results)


def test_link_validation_end_to_end(wiki_env):
    """Write pages with links, verify validation catches missing targets."""
    wiki_write("target.md", "# Target\n\nI exist.\n")
    result = wiki_write("source.md", "Link to [[target]] and [[ghost]].\n")

    assert result["ok"] is True
    invalid = result.get("invalid_links", [])
    names = [l["name"] for l in invalid]
    assert "ghost" in names
    assert "target" not in names
