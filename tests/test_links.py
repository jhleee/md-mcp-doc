from pathlib import Path

from tools.links import get_file_links, parse_links, resolve_link, validate_links


def test_parse_links():
    text = "See [[magic]] and [[characters]] for more."
    result = parse_links(text)
    assert result == ["magic", "characters"]


def test_parse_links_empty():
    assert parse_links("No links here.") == []


def test_resolve_link(sample_files):
    result = resolve_link("magic")
    assert result["exists"] is True
    assert result["path"] == "worlds/magic.md"


def test_resolve_link_exact(sample_files):
    result = resolve_link("characters")
    assert result["exists"] is True
    assert result["path"] == "characters.md"


def test_resolve_link_not_found(sample_files):
    result = resolve_link("nonexistent")
    assert result["exists"] is False


def test_validate_links_all_valid(sample_files):
    content = "[[magic]] and [[characters]]"
    invalid = validate_links(content)
    assert invalid == []


def test_validate_links_with_invalid(sample_files):
    content = "[[magic]] and [[doesnotexist]]"
    invalid = validate_links(content)
    assert len(invalid) == 1
    assert invalid[0]["name"] == "doesnotexist"


def test_get_file_links(sample_files):
    path = sample_files / "index.md"
    links = get_file_links(path)
    assert len(links) == 2
    names = {l["name"] for l in links}
    assert "magic" in names
    assert "characters" in names
    assert all(l["exists"] for l in links)
