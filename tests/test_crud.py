import pytest

from tools.crud import (
    wiki_append,
    wiki_delete,
    wiki_get,
    wiki_get_batch,
    wiki_list,
    wiki_write,
)


def test_wiki_write_and_get(wiki_env):
    result = wiki_write("note.md", "# Note\n\nHello.")
    assert result["ok"] is True

    data = wiki_get("note.md")
    assert "# Note" in data["content"]
    assert data["meta"]["line_count"] == 3
    assert data["truncated"] is False


def test_wiki_write_creates_dirs(wiki_env):
    wiki_write("deep/nested/file.md", "content")
    data = wiki_get("deep/nested/file.md")
    assert data["content"] == "content"


def test_wiki_write_invalid_links(wiki_env):
    result = wiki_write("test.md", "See [[nonexistent]]")
    assert result["ok"] is True
    assert len(result.get("invalid_links", [])) == 1


def test_wiki_get_pagination(wiki_env):
    content = "\n".join(f"Line {i}" for i in range(100))
    wiki_write("big.md", content)

    data = wiki_get("big.md", offset=10, limit=5)
    lines = data["content"].strip().splitlines()
    assert lines[0] == "Line 10"
    assert len(lines) == 5
    assert data["truncated"] is True


def test_wiki_get_not_found(wiki_env):
    with pytest.raises(FileNotFoundError):
        wiki_get("nonexistent.md")


def test_wiki_get_batch(wiki_env):
    wiki_write("a.md", "A")
    wiki_write("b.md", "B")
    results = wiki_get_batch(["a.md", "b.md", "missing.md"])
    assert len(results) == 3
    assert results[0]["content"] == "A"
    assert results[1]["content"] == "B"
    assert "error" in results[2]


def test_wiki_append(wiki_env):
    wiki_write("app.md", "Start\n")
    result = wiki_append("app.md", "\nEnd\n")
    assert result["ok"] is True

    data = wiki_get("app.md")
    assert "End" in data["content"]


def test_wiki_append_not_found(wiki_env):
    with pytest.raises(FileNotFoundError):
        wiki_append("missing.md", "text")


def test_wiki_delete(wiki_env):
    wiki_write("todelete.md", "bye")
    result = wiki_delete("todelete.md")
    assert result["ok"] is True

    with pytest.raises(FileNotFoundError):
        wiki_get("todelete.md")


def test_wiki_delete_not_found(wiki_env):
    with pytest.raises(FileNotFoundError):
        wiki_delete("nope.md")


def test_wiki_list(wiki_env):
    wiki_write("a.md", "A")
    wiki_write("sub/b.md", "B")
    files = wiki_list()
    paths = {f["path"] for f in files}
    assert "a.md" in paths
    assert "sub/b.md" in paths


def test_wiki_list_subdir(wiki_env):
    wiki_write("x/one.md", "1")
    wiki_write("y/two.md", "2")
    files = wiki_list("x")
    assert len(files) == 1
    assert files[0]["path"] == "x/one.md"


def test_wiki_write_auto_md_extension(wiki_env):
    wiki_write("noext", "content")
    data = wiki_get("noext")
    assert data["content"] == "content"


def test_path_traversal_blocked(wiki_env):
    with pytest.raises(ValueError, match="escapes"):
        wiki_write("../../etc/passwd", "hack")
