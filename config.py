from __future__ import annotations

import os
from pathlib import Path

WIKI_PATH: Path = Path(os.environ.get("WIKI_PATH", "")).resolve()

DB_PATH: Path = Path(
    os.environ.get("WIKI_DB_PATH", str(WIKI_PATH / ".wiki.db"))
).resolve()

EMBED_MODEL: str = os.environ.get("WIKI_EMBED_MODEL", "all-MiniLM-L6-v2")

RG_PATH: str = os.environ.get("WIKI_RG_PATH", "rg")

CHUNK_THRESHOLD: int = int(os.environ.get("WIKI_CHUNK_THRESHOLD", str(10 * 1024)))

# Basic authentication credentials for SSE / streamable-http transports.
# Both must be set to enable auth; if either is empty, auth is disabled.
AUTH_USER: str = os.environ.get("WIKI_AUTH_USER", "")
AUTH_PASS: str = os.environ.get("WIKI_AUTH_PASS", "")


def validate() -> None:
    """Validate config at server startup. Call this from server.py main()."""
    if not WIKI_PATH.is_dir():
        raise RuntimeError(f"WIKI_PATH is not a valid directory: {WIKI_PATH}")
