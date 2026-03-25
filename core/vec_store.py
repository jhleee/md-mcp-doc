from __future__ import annotations

import sqlite3
from pathlib import Path

import sqlite_vec

import config
from core.embedder import dimension

_conn: sqlite3.Connection | None = None


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(str(config.DB_PATH))
        _conn.enable_load_extension(True)
        sqlite_vec.load(_conn)
        _conn.enable_load_extension(False)
        _init_tables(_conn)
    return _conn


def _init_tables(conn: sqlite3.Connection) -> None:
    dim = dimension()
    conn.execute(
        f"""
        CREATE VIRTUAL TABLE IF NOT EXISTS wiki_vec
        USING vec0(
            key TEXT PRIMARY KEY,
            embedding float[{dim}]
        )
        """
    )
    # metadata table: stores mtime for diff-based reindexing
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS wiki_meta (
            key TEXT PRIMARY KEY,
            path TEXT NOT NULL,
            mtime REAL NOT NULL
        )
        """
    )
    conn.commit()


def upsert(key: str, path: str, mtime: float, embedding: bytes) -> None:
    conn = _get_conn()
    # sqlite-vec vec0 does not support ON CONFLICT, so delete then insert
    conn.execute("DELETE FROM wiki_vec WHERE key = ?", (key,))
    conn.execute(
        "INSERT INTO wiki_vec (key, embedding) VALUES (?, ?)",
        (key, embedding),
    )
    conn.execute(
        "INSERT OR REPLACE INTO wiki_meta (key, path, mtime) VALUES (?, ?, ?)",
        (key, path, mtime),
    )
    conn.commit()


def upsert_batch(
    items: list[tuple[str, str, float, bytes]],
) -> None:
    """Batch upsert. Each item is (key, path, mtime, embedding)."""
    if not items:
        return
    conn = _get_conn()
    for key, path, mtime, emb in items:
        conn.execute("DELETE FROM wiki_vec WHERE key = ?", (key,))
        conn.execute(
            "INSERT INTO wiki_vec (key, embedding) VALUES (?, ?)",
            (key, emb),
        )
        conn.execute(
            "INSERT OR REPLACE INTO wiki_meta (key, path, mtime) VALUES (?, ?, ?)",
            (key, path, mtime),
        )
    conn.commit()


def delete_by_path(path: str) -> None:
    """Delete all vectors associated with a file path."""
    conn = _get_conn()
    keys = [
        row[0]
        for row in conn.execute(
            "SELECT key FROM wiki_meta WHERE path = ?", (path,)
        ).fetchall()
    ]
    for key in keys:
        conn.execute("DELETE FROM wiki_vec WHERE key = ?", (key,))
    conn.execute("DELETE FROM wiki_meta WHERE path = ?", (path,))
    conn.commit()


def search(query_embedding: bytes, k: int = 10) -> list[tuple[str, float]]:
    """Return top-k (key, distance) pairs by cosine distance."""
    conn = _get_conn()
    rows = conn.execute(
        """
        SELECT key, distance
        FROM wiki_vec
        WHERE embedding MATCH ?
        ORDER BY distance
        LIMIT ?
        """,
        (query_embedding, k),
    ).fetchall()
    return [(row[0], row[1]) for row in rows]


def get_all_meta() -> list[tuple[str, str, float]]:
    """Return all (key, path, mtime) from metadata table."""
    conn = _get_conn()
    return conn.execute("SELECT key, path, mtime FROM wiki_meta").fetchall()
