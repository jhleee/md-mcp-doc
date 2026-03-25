# wiki-mcp

MCP server for a markdown-based personal wiki. Provides CRUD, full-text search (ripgrep), semantic search (sqlite-vec + sentence-transformers), and hybrid search via a single interface.

## Features

- **10 MCP tools**: read, batch read, write, append, delete, list, search, replace, link check, link resolve
- **Hybrid search**: combines ripgrep full-text and embedding-based semantic search using Reciprocal Rank Fusion (RRF)
- **Auto-indexing**: writes and deletes automatically update the vector index
- **`[[wiki links]]`**: parse, resolve (shortest-path matching), and validate links across the vault
- **Chunked embeddings**: files < 10KB get a single vector; larger files are split by H1/H2 headings

## Quick Start

### Docker (recommended)

```bash
docker build -t wiki-mcp .
```

MCP client configuration (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "wiki": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-v", "/path/to/your/wiki:/wiki",
        "-e", "WIKI_PATH=/wiki",
        "wiki-mcp"
      ]
    }
  }
}
```

### uvx (local install)

```bash
pip install mcp sentence-transformers sqlite-vec python-frontmatter
```

```json
{
  "mcpServers": {
    "wiki": {
      "command": "python",
      "args": ["/path/to/wiki-mcp/server.py"],
      "env": {
        "WIKI_PATH": "/path/to/your/wiki"
      }
    }
  }
}
```

## Tools

| Tool | Description |
|---|---|
| `wiki_get` | Read a file with optional line pagination |
| `wiki_get_batch` | Read multiple files at once |
| `wiki_write` | Create/overwrite a file (auto-indexes, validates links) |
| `wiki_append` | Append to an existing file |
| `wiki_delete` | Delete a file and remove from index |
| `wiki_list` | List `.md` files in a directory |
| `wiki_search` | Search by text, semantic, or hybrid mode |
| `wiki_replace` | Find-and-replace across all files |
| `wiki_links` | Parse `[[links]]` in a file and check targets |
| `wiki_resolve` | Resolve a link name to a file path |

## Search Modes

- **`text`** — ripgrep full-text search on filenames and content
- **`semantic`** — cosine similarity search using `all-MiniLM-L6-v2` embeddings stored in sqlite-vec
- **`hybrid`** (default) — runs both, merges results with RRF (`k=60`)

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `WIKI_PATH` | *(required)* | Path to the wiki vault root |
| `WIKI_DB_PATH` | `{WIKI_PATH}/.wiki.db` | sqlite-vec database location |
| `WIKI_EMBED_MODEL` | `all-MiniLM-L6-v2` | Sentence-transformers model name |
| `WIKI_RG_PATH` | `rg` | Path to ripgrep binary |
| `WIKI_CHUNK_THRESHOLD` | `10240` | File size threshold (bytes) for heading-based chunking |

## Development

```bash
# Install dev dependencies
pip install mcp sentence-transformers sqlite-vec python-frontmatter pytest

# Run tests
WIKI_PATH=/tmp/wiki python -m pytest -v

# Run tests in Docker
docker build -t wiki-mcp .
docker build -t wiki-mcp-test -f Dockerfile.test .
docker run --rm wiki-mcp-test
```

## Project Structure

```
wiki-mcp/
├── server.py           # MCP server entry point
├── config.py           # Environment variable configuration
├── core/
│   ├── embedder.py     # Sentence-transformers wrapper
│   ├── vec_store.py    # sqlite-vec CRUD
│   ├── rrf.py          # Reciprocal Rank Fusion
│   └── index.py        # Indexing logic with chunking
├── tools/
│   ├── crud.py         # Read/write/delete/list operations
│   ├── search.py       # Text/semantic/hybrid search
│   ├── replace.py      # Find-and-replace
│   └── links.py        # Wiki link parsing and resolution
├── tests/              # pytest test suite (55 tests)
├── Dockerfile
├── docker-compose.yml
└── .github/workflows/ci.yml
```

## License

MIT
