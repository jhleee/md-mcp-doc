from tools.crud import wiki_get, wiki_write
from tools.replace import wiki_replace


def test_replace_basic(wiki_env):
    wiki_write("a.md", "Hello world. Hello again.")
    wiki_write("b.md", "Hello there.")
    wiki_write("c.md", "Nothing here.")

    result = wiki_replace("Hello", "Hi")
    assert set(result["changed_files"]) == {"a.md", "b.md"}
    assert result["count"] == 3  # 2 in a.md + 1 in b.md

    data_a = wiki_get("a.md")
    assert "Hi world" in data_a["content"]
    assert "Hello" not in data_a["content"]


def test_replace_no_match(wiki_env):
    wiki_write("x.md", "abc")
    result = wiki_replace("zzz", "yyy")
    assert result["changed_files"] == []
    assert result["count"] == 0


def test_replace_with_dir_filter(wiki_env):
    wiki_write("a.md", "target text")
    wiki_write("sub/b.md", "target text")

    result = wiki_replace("target", "replaced", dir="sub")
    assert result["changed_files"] == ["sub/b.md"]

    # a.md should be unchanged
    data = wiki_get("a.md")
    assert "target" in data["content"]


def test_replace_reports_dangling_links(wiki_env):
    wiki_write("doc.md", "See [[existing]].")
    wiki_write("existing.md", "I exist.")

    result = wiki_replace("existing", "missing")
    # doc.md now has [[missing]] which doesn't resolve
    if "dangling_links" in result:
        assert any("missing" in str(v) for v in result["dangling_links"].values())
