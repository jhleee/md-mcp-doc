from __future__ import annotations

import re
from pathlib import Path

import config

_WIKI_LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")

# Cache of all .md files for link resolution (rebuilt on demand)
_md_cache: list[str] | None = None
_md_cache_mtime: float = 0.0


def _get_md_files() -> list[str]:
    """Return list of relative posix paths for all .md files in the vault."""
    global _md_cache, _md_cache_mtime
    # Simple cache: rebuild if vault directory mtime changed
    vault_mtime = config.WIKI_PATH.stat().st_mtime
    if _md_cache is None or vault_mtime != _md_cache_mtime:
        _md_cache = [
            p.relative_to(config.WIKI_PATH).as_posix()
            for p in config.WIKI_PATH.rglob("*.md")
        ]
        _md_cache_mtime = vault_mtime
    return _md_cache


def invalidate_cache() -> None:
    """Force rebuild of the file cache on next access."""
    global _md_cache
    _md_cache = None


def resolve_link(name: str) -> dict:
    """Resolve a [[link name]] to a file path using shortest-path matching.

    Matching rules:
    1. Exact match on filename (without .md extension)
    2. Exact match on relative path (without .md extension)
    3. Shortest path containing the name
    """
    md_files = _get_md_files()
    name_lower = name.lower().strip()

    # Normalize: if user passed "foo.md", strip extension
    if name_lower.endswith(".md"):
        name_lower = name_lower[:-3]

    candidates: list[str] = []

    for rel in md_files:
        stem = Path(rel).stem.lower()
        rel_no_ext = rel[:-3].lower() if rel.endswith(".md") else rel.lower()

        if stem == name_lower or rel_no_ext == name_lower:
            candidates.append(rel)

    if not candidates:
        # Fuzzy: check if name appears in the path
        for rel in md_files:
            if name_lower in rel.lower():
                candidates.append(rel)

    if not candidates:
        return {"path": None, "exists": False}

    # Pick shortest path
    best = min(candidates, key=len)
    return {"path": best, "exists": True}


def parse_links(content: str) -> list[str]:
    """Extract all [[link]] names from content."""
    return _WIKI_LINK_RE.findall(content)


def validate_links(content: str) -> list[dict]:
    """Check all [[links]] in content and return invalid ones."""
    names = parse_links(content)
    invalid: list[dict] = []
    for name in names:
        result = resolve_link(name)
        if not result["exists"]:
            entry: dict = {"name": name}
            # Suggest a close match
            md_files = _get_md_files()
            name_lower = name.lower()
            for rel in md_files:
                if name_lower in Path(rel).stem.lower():
                    entry["suggested"] = rel
                    break
            invalid.append(entry)
    return invalid


def get_file_links(path: Path) -> list[dict]:
    """Parse a file and return all [[links]] with resolution info."""
    content = path.read_text(encoding="utf-8")
    names = parse_links(content)
    results: list[dict] = []
    for name in names:
        resolved = resolve_link(name)
        results.append(
            {
                "name": name,
                "resolved_path": resolved["path"],
                "exists": resolved["exists"],
            }
        )
    return results
