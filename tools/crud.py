from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import config
from core.index import index_file, remove_file
from tools.links import invalidate_cache, validate_links


def _resolve_path(path: str) -> Path:
    """Resolve a relative wiki path to an absolute path, ensuring it's inside the vault."""
    # Normalize and make relative
    clean = path.lstrip("/").lstrip("\\")
    if not clean.endswith(".md"):
        clean += ".md"
    full = (config.WIKI_PATH / clean).resolve()
    # Security: ensure it's within WIKI_PATH
    if not str(full).startswith(str(config.WIKI_PATH)):
        raise ValueError(f"Path escapes wiki vault: {path}")
    return full


def _file_meta(p: Path) -> dict:
    stat = p.stat()
    content = p.read_text(encoding="utf-8")
    return {
        "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        "size": stat.st_size,
        "line_count": content.count("\n") + 1,
    }


def wiki_get(path: str, offset: int | None = None, limit: int | None = None) -> dict:
    full = _resolve_path(path)
    if not full.exists():
        raise FileNotFoundError(f"File not found: {path}")

    content = full.read_text(encoding="utf-8")
    meta = _file_meta(full)
    truncated = False

    if offset is not None or limit is not None:
        lines = content.splitlines(keepends=True)
        start = offset or 0
        end = (start + limit) if limit else len(lines)
        content = "".join(lines[start:end])
        truncated = end < len(lines)

    return {"content": content, "meta": meta, "truncated": truncated}


def wiki_get_batch(paths: list[str]) -> list[dict]:
    results: list[dict] = []
    for p in paths:
        try:
            result = wiki_get(p)
            result["path"] = p
            results.append(result)
        except Exception as e:
            results.append({"path": p, "error": str(e)})
    return results


def wiki_write(path: str, content: str) -> dict:
    full = _resolve_path(path)
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")
    invalidate_cache()
    index_file(full)

    result: dict = {"ok": True}
    invalid = validate_links(content)
    if invalid:
        result["invalid_links"] = invalid
    return result


def wiki_append(path: str, content: str) -> dict:
    full = _resolve_path(path)
    if not full.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with open(full, "a", encoding="utf-8") as f:
        f.write(content)

    index_file(full)

    full_content = full.read_text(encoding="utf-8")
    result: dict = {"ok": True}
    invalid = validate_links(full_content)
    if invalid:
        result["invalid_links"] = invalid
    return result


def wiki_delete(path: str) -> dict:
    full = _resolve_path(path)
    if not full.exists():
        raise FileNotFoundError(f"File not found: {path}")

    remove_file(full)
    full.unlink()
    invalidate_cache()
    return {"ok": True}


def wiki_list(dir: str | None = None) -> list[dict]:
    base = config.WIKI_PATH
    if dir:
        base = (config.WIKI_PATH / dir.lstrip("/")).resolve()
        if not str(base).startswith(str(config.WIKI_PATH)):
            raise ValueError(f"Directory escapes wiki vault: {dir}")

    if not base.is_dir():
        raise FileNotFoundError(f"Directory not found: {dir}")

    results: list[dict] = []
    for md_file in sorted(base.rglob("*.md")):
        stat = md_file.stat()
        results.append(
            {
                "path": md_file.relative_to(config.WIKI_PATH).as_posix(),
                "modified": datetime.fromtimestamp(
                    stat.st_mtime, tz=timezone.utc
                ).isoformat(),
                "size": stat.st_size,
            }
        )
    return results
