from __future__ import annotations

import json
import subprocess
from pathlib import Path

import config
from core import embedder, vec_store
from core.rrf import reciprocal_rank_fusion


def _text_search(query: str, dir: str | None, k: int) -> list[dict]:
    """Full-text search using ripgrep. Searches file names and content."""
    base = config.WIKI_PATH
    if dir:
        base = (config.WIKI_PATH / dir.lstrip("/")).resolve()

    args = [
        config.RG_PATH,
        "--json",
        "--max-count", str(k * 3),  # over-fetch for ranking
        "--glob", "*.md",
        "--ignore-case",
        query,
        str(base),
    ]

    try:
        result = subprocess.run(
            args, capture_output=True, text=True, timeout=10
        )
    except FileNotFoundError:
        raise RuntimeError(f"ripgrep not found at '{config.RG_PATH}'. Install ripgrep or set WIKI_config.RG_PATH.")
    except subprocess.TimeoutExpired:
        return []

    hits: dict[str, dict] = {}  # path → {snippet, line_number}

    for line in result.stdout.strip().splitlines():
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue

        if obj.get("type") != "match":
            continue

        data = obj["data"]
        abs_path = Path(data["path"]["text"]).resolve()

        try:
            rel = abs_path.relative_to(config.WIKI_PATH).as_posix()
        except ValueError:
            continue

        if rel not in hits:
            line_text = data["lines"]["text"].strip()
            hits[rel] = {
                "path": rel,
                "snippet": line_text[:200],
            }

    # Also search filenames
    for md_file in base.rglob("*.md"):
        rel = md_file.relative_to(config.WIKI_PATH).as_posix()
        if query.lower() in md_file.stem.lower() and rel not in hits:
            # Read first few lines as snippet
            try:
                content = md_file.read_text(encoding="utf-8")
                snippet = "\n".join(content.splitlines()[:3])
            except Exception:
                snippet = ""
            hits[rel] = {"path": rel, "snippet": snippet[:200]}

    return list(hits.values())[:k]


def _semantic_search(query: str, dir: str | None, k: int) -> list[dict]:
    """Semantic search using sqlite-vec cosine similarity."""
    query_emb = embedder.embed(query)
    results = vec_store.search(query_emb, k=k * 2)  # over-fetch for dir filter

    hits: list[dict] = []
    for key, distance in results:
        # Parse key: "path" or "path#heading"
        if "#" in key:
            path, anchor = key.split("#", 1)
        else:
            path, anchor = key, None

        # Filter by dir
        if dir and not path.startswith(dir.lstrip("/")):
            continue

        # cosine distance → similarity score (1 - distance for cosine)
        score = 1.0 - distance

        # Build snippet from the indexed content
        snippet = _get_snippet(path, anchor)

        entry: dict = {"path": path, "score": round(score, 4), "snippet": snippet}
        if anchor:
            entry["anchor"] = anchor
        hits.append(entry)

        if len(hits) >= k:
            break

    return hits


def _get_snippet(path: str, anchor: str | None) -> str:
    """Get a short snippet for a search result."""
    full = config.WIKI_PATH / path
    if not full.exists():
        return ""
    try:
        content = full.read_text(encoding="utf-8")
    except Exception:
        return ""

    if anchor:
        # Find the heading and return it + next 3 lines
        lines = content.splitlines()
        for i, line in enumerate(lines):
            stripped = line.lstrip("#").strip()
            if stripped == anchor:
                snippet_lines = lines[i : i + 4]
                return "\n".join(snippet_lines)[:300]
        return content[:200]
    else:
        return "\n".join(content.splitlines()[:3])[:300]


def wiki_search(
    query: str,
    mode: str = "hybrid",
    dir: str | None = None,
    k: int = 10,
) -> list[dict]:
    if mode == "text":
        return _text_search(query, dir, k)
    elif mode == "semantic":
        return _semantic_search(query, dir, k)
    elif mode == "hybrid":
        text_results = _text_search(query, dir, k)
        semantic_results = _semantic_search(query, dir, k)

        text_keys = [r["path"] for r in text_results]
        semantic_keys = [r["path"] for r in semantic_results]

        # Build lookup for result data
        all_results: dict[str, dict] = {}
        for r in text_results:
            all_results[r["path"]] = r
        for r in semantic_results:
            # Semantic results have score and possibly anchor
            if r["path"] not in all_results:
                all_results[r["path"]] = r
            else:
                # Merge anchor info from semantic
                if "anchor" in r:
                    all_results[r["path"]]["anchor"] = r["anchor"]

        rrf_ranked = reciprocal_rank_fusion(text_keys, semantic_keys)

        merged: list[dict] = []
        for path, rrf_score in rrf_ranked[:k]:
            entry = all_results.get(path, {"path": path, "snippet": ""})
            entry["score"] = round(rrf_score, 4)
            merged.append(entry)

        return merged
    else:
        raise ValueError(f"Invalid search mode: {mode}. Use 'text', 'semantic', or 'hybrid'.")
