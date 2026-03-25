from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure the project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(autouse=True)
def wiki_env(tmp_path, monkeypatch):
    """Set up a temporary wiki vault for every test."""
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    db_path = tmp_path / ".wiki.db"

    # Patch config module attributes directly
    import config

    monkeypatch.setattr(config, "WIKI_PATH", wiki_dir)
    monkeypatch.setattr(config, "DB_PATH", db_path)
    monkeypatch.setattr(config, "CHUNK_THRESHOLD", 10 * 1024)

    # Reset vec_store connection so each test gets a fresh DB
    import core.vec_store as vs

    vs._conn = None

    # Reset link cache
    import tools.links as tl

    tl._md_cache = None

    yield wiki_dir


@pytest.fixture
def sample_files(wiki_env):
    """Create sample wiki files."""
    (wiki_env / "index.md").write_text(
        "# Index\n\nWelcome.\n\n- [[magic]]\n- [[characters]]\n",
        encoding="utf-8",
    )
    worlds = wiki_env / "worlds"
    worlds.mkdir()
    (worlds / "magic.md").write_text(
        "# Magic System\n\nElemental forces.\n\n## Fire Magic\n\nVolcanic energy.\n\n## Ice Magic\n\nGlacial formations.\n",
        encoding="utf-8",
    )
    (wiki_env / "characters.md").write_text(
        "# Characters\n\n## Alice\n\nA fire mage. See [[magic]].\n\n## Bob\n\nAn ice mage.\n",
        encoding="utf-8",
    )
    return wiki_env
