from __future__ import annotations

import subprocess
from pathlib import Path

import config
from core.index import index_file
from tools.links import invalidate_cache, validate_links


def wiki_replace(old: str, new: str, dir: str | None = None) -> dict:
    """Find and replace across wiki files. Returns changed files and count."""
    base = config.WIKI_PATH
    if dir:
        base = (config.WIKI_PATH / dir.lstrip("/")).resolve()
        if not str(base).startswith(str(config.WIKI_PATH)):
            raise ValueError(f"Directory escapes wiki vault: {dir}")

    # Use ripgrep to find matching files
    args = [
        config.RG_PATH,
        "--files-with-matches",
        "--glob", "*.md",
        old,
        str(base),
    ]

    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=10)
    except FileNotFoundError:
        raise RuntimeError(f"ripgrep not found at '{config.RG_PATH}'.")

    if result.returncode not in (0, 1):  # 1 means no matches
        raise RuntimeError(f"ripgrep error: {result.stderr}")

    matching_files = [
        Path(line.strip()).resolve()
        for line in result.stdout.strip().splitlines()
        if line.strip()
    ]

    changed_files: list[str] = []
    total_count = 0
    all_dangling: dict[str, list[dict]] = {}

    for file_path in matching_files:
        try:
            rel = file_path.relative_to(config.WIKI_PATH).as_posix()
        except ValueError:
            continue

        content = file_path.read_text(encoding="utf-8")
        count = content.count(old)
        if count == 0:
            continue

        new_content = content.replace(old, new)
        file_path.write_text(new_content, encoding="utf-8")

        changed_files.append(rel)
        total_count += count

        # Re-index
        index_file(file_path)

        # Link validation
        invalid = validate_links(new_content)
        if invalid:
            all_dangling[rel] = invalid

    invalidate_cache()

    result_dict: dict = {
        "changed_files": changed_files,
        "count": total_count,
    }
    if all_dangling:
        result_dict["dangling_links"] = all_dangling

    return result_dict
