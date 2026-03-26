from __future__ import annotations

import argparse
import logging
import os

from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("wiki-mcp")

mcp = FastMCP(
    "wiki",
    host=os.environ.get("WIKI_HOST", "0.0.0.0"),
    port=int(os.environ.get("WIKI_PORT", "8000")),
)


# ── CRUD tools ──────────────────────────────────────────────


@mcp.tool()
def wiki_get(path: str, offset: int | None = None, limit: int | None = None) -> dict:
    """Read a wiki page. Supports line-based pagination with offset/limit for large files.

    Args:
        path: Relative path to the markdown file (e.g. "notes/idea.md")
        offset: Start reading from this line number (0-based)
        limit: Maximum number of lines to return
    """
    from tools.crud import wiki_get as _impl

    return _impl(path, offset, limit)


@mcp.tool()
def wiki_get_batch(paths: list[str]) -> list[dict]:
    """Read multiple wiki pages at once. Missing files return an error entry instead of failing.

    Args:
        paths: List of relative paths to read
    """
    from tools.crud import wiki_get_batch as _impl

    return _impl(paths)


@mcp.tool()
def wiki_write(path: str, content: str) -> dict:
    """Create or overwrite a wiki page. Parent directories are created automatically.
    The file is automatically indexed for semantic search after writing.
    Returns invalid [[links]] as warnings (the write still succeeds).

    Args:
        path: Relative path for the file
        content: Full markdown content
    """
    from tools.crud import wiki_write as _impl

    return _impl(path, content)


@mcp.tool()
def wiki_append(path: str, content: str) -> dict:
    """Append content to an existing wiki page. Triggers re-indexing.

    Args:
        path: Relative path to the existing file
        content: Content to append at the end
    """
    from tools.crud import wiki_append as _impl

    return _impl(path, content)


@mcp.tool()
def wiki_delete(path: str) -> dict:
    """Delete a wiki page and remove it from the search index.

    Args:
        path: Relative path to the file to delete
    """
    from tools.crud import wiki_delete as _impl

    return _impl(path)


@mcp.tool()
def wiki_list(dir: str | None = None) -> list[dict]:
    """List all markdown files under a directory (default: vault root).

    Args:
        dir: Optional subdirectory to list (relative path)
    """
    from tools.crud import wiki_list as _impl

    return _impl(dir)


# ── Search tools ────────────────────────────────────────────


@mcp.tool()
def wiki_search(
    query: str,
    mode: str = "hybrid",
    dir: str | None = None,
    k: int = 10,
) -> list[dict]:
    """Search wiki pages by text, semantic similarity, or hybrid (default).

    - text: ripgrep full-text search on file names and content
    - semantic: embedding-based cosine similarity search
    - hybrid: combines text + semantic results using Reciprocal Rank Fusion

    Args:
        query: Search query string
        mode: Search mode — "text", "semantic", or "hybrid"
        dir: Restrict search to a subdirectory
        k: Maximum number of results to return
    """
    from tools.search import wiki_search as _impl

    return _impl(query, mode, dir, k)


# ── Replace tool ────────────────────────────────────────────


@mcp.tool()
def wiki_replace(old: str, new: str, dir: str | None = None) -> dict:
    """Find and replace text across all wiki files. Changed files are re-indexed.
    Returns the list of changed files and dangling [[links]] if any.

    Args:
        old: Text to find
        new: Replacement text
        dir: Restrict to a subdirectory
    """
    from tools.replace import wiki_replace as _impl

    return _impl(old, new, dir)


# ── Link tools ──────────────────────────────────────────────


@mcp.tool()
def wiki_links(path: str) -> list[dict]:
    """Parse [[wiki links]] in a file and check whether each target exists.

    Args:
        path: Relative path to the markdown file
    """
    import config
    from tools.links import get_file_links

    full = (config.WIKI_PATH / path.lstrip("/")).resolve()
    if not full.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return get_file_links(full)


@mcp.tool()
def wiki_resolve(name: str) -> dict:
    """Resolve a [[link name]] to its actual file path (shortest-path matching).

    Args:
        name: The wiki link name to resolve
    """
    from tools.links import resolve_link

    return resolve_link(name)


# ── Startup ─────────────────────────────────────────────────


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="wiki-mcp server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default=os.environ.get("WIKI_TRANSPORT", "stdio"),
        help="MCP transport mode (default: stdio, env: WIKI_TRANSPORT)",
    )
    parser.add_argument(
        "--host",
        default=None,
        help="Bind host for sse/streamable-http (env: WIKI_HOST, default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Bind port for sse/streamable-http (env: WIKI_PORT, default: 8000)",
    )
    return parser.parse_args()


def main() -> None:
    import config
    config.validate()

    args = _parse_args()

    # Override host/port if provided via CLI
    if args.host:
        mcp.settings.host = args.host
    if args.port:
        mcp.settings.port = args.port

    from core.index import reindex_all

    logger.info("Starting wiki-mcp server...")
    stats = reindex_all()
    logger.info(
        "Reindex complete: %d added, %d updated, %d removed",
        stats["added"],
        stats["updated"],
        stats["removed"],
    )

    transport = args.transport
    if transport in ("sse", "streamable-http"):
        logger.info(
            "Listening on %s:%d (%s)",
            mcp.settings.host,
            mcp.settings.port,
            transport,
        )
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
