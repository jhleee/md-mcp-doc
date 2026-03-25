from __future__ import annotations

import re
from pathlib import Path

import config
from core import embedder, vec_store

_HEADING_RE = re.compile(r"^(#{1,2})\s+(.+)$", re.MULTILINE)


def _relative(path: Path) -> str:
    return path.relative_to(config.WIKI_PATH).as_posix()


def _chunk_file(path: Path) -> list[tuple[str, str]]:
    """Split a file into (key, text) chunks.

    Files < CHUNK_THRESHOLD bytes → single chunk keyed by relative path.
    Larger files → split by H1/H2 headings; fallback to single chunk.
    """
    content = path.read_text(encoding="utf-8")
    rel = _relative(path)
    size = path.stat().st_size

    if size < config.CHUNK_THRESHOLD:
        return [(rel, content)]

    sections = _split_by_headings(content)
    if len(sections) <= 1:
        return [(rel, content)]

    chunks: list[tuple[str, str]] = []
    for heading, text in sections:
        key = f"{rel}#{heading}" if heading else rel
        chunks.append((key, text))
    return chunks


def _split_by_headings(content: str) -> list[tuple[str | None, str]]:
    """Split content by H1/H2 headings. Returns (heading_text, section_content)."""
    matches = list(_HEADING_RE.finditer(content))
    if not matches:
        return [(None, content)]

    sections: list[tuple[str | None, str]] = []

    # Text before first heading
    if matches[0].start() > 0:
        preamble = content[: matches[0].start()].strip()
        if preamble:
            sections.append((None, preamble))

    for i, m in enumerate(matches):
        heading_text = m.group(2).strip()
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        section_content = content[start:end].strip()
        sections.append((heading_text, section_content))

    return sections


def index_file(path: Path) -> None:
    """Index (or re-index) a single file."""
    rel = _relative(path)
    # Remove old entries for this file
    vec_store.delete_by_path(rel)

    chunks = _chunk_file(path)
    if not chunks:
        return

    keys = [k for k, _ in chunks]
    texts = [t for _, t in chunks]
    embeddings = embedder.embed_batch(texts)
    mtime = path.stat().st_mtime

    items = [(key, rel, mtime, emb) for key, emb in zip(keys, embeddings)]
    vec_store.upsert_batch(items)


def remove_file(path: Path) -> None:
    """Remove a file's entries from the index."""
    rel = _relative(path)
    vec_store.delete_by_path(rel)


def reindex_all() -> dict[str, int]:
    """Diff-based reindex at startup. Returns stats."""
    existing_meta = vec_store.get_all_meta()
    indexed: dict[str, float] = {}  # path → mtime
    for _key, path, mtime in existing_meta:
        # Keep the latest mtime per path
        if path not in indexed or mtime > indexed[path]:
            indexed[path] = mtime

    # Scan filesystem
    fs_files: dict[str, Path] = {}
    for md_file in config.WIKI_PATH.rglob("*.md"):
        rel = _relative(md_file)
        fs_files[rel] = md_file

    added = 0
    updated = 0
    removed = 0

    # Files to add or update
    to_index: list[Path] = []
    for rel, md_file in fs_files.items():
        current_mtime = md_file.stat().st_mtime
        if rel not in indexed:
            to_index.append(md_file)
            added += 1
        elif current_mtime > indexed[rel]:
            to_index.append(md_file)
            updated += 1

    # Files to remove (in index but not on filesystem)
    for rel in indexed:
        if rel not in fs_files:
            vec_store.delete_by_path(rel)
            removed += 1

    # Index changed files
    for md_file in to_index:
        index_file(md_file)

    return {"added": added, "updated": updated, "removed": removed}
