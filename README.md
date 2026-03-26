# wiki-mcp

MCP server for a markdown-based personal wiki. Provides CRUD, full-text search (ripgrep), semantic search (sqlite-vec + sentence-transformers), and hybrid search via a single interface.

## Features

- **10 MCP tools**: read, batch read, write, append, delete, list, search, replace, link check, link resolve
- **Hybrid search**: combines ripgrep full-text and embedding-based semantic search using Reciprocal Rank Fusion (RRF)
- **Auto-indexing**: writes and deletes automatically update the vector index
- **`[[wiki links]]`**: parse, resolve (shortest-path matching), and validate links across the vault
- **Chunked embeddings**: files < 10KB get a single vector; larger files are split by H1/H2 headings
- **3 transport modes**: stdio (default), SSE, streamable-http — run as a local process or a network server

## Quick Start

### Docker — stdio mode (default)

```bash
docker pull ghcr.io/jhleee/md-mcp-doc:latest
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
        "ghcr.io/jhleee/md-mcp-doc:latest"
      ]
    }
  }
}
```

### Docker — SSE server mode

Run as a persistent HTTP server, connect from any MCP client via SSE:

```bash
docker run -d --name wiki-mcp \
  -v /path/to/your/wiki:/wiki \
  -e WIKI_PATH=/wiki \
  -e WIKI_TRANSPORT=sse \
  -p 8000:8000 \
  ghcr.io/jhleee/md-mcp-doc:latest
```

MCP client configuration (SSE):

```json
{
  "mcpServers": {
    "wiki": {
      "url": "http://localhost:8000/sse"
    }
  }
}
```

### Docker — Streamable HTTP mode

```bash
docker run -d --name wiki-mcp \
  -v /path/to/your/wiki:/wiki \
  -e WIKI_PATH=/wiki \
  -e WIKI_TRANSPORT=streamable-http \
  -p 8000:8000 \
  ghcr.io/jhleee/md-mcp-doc:latest
```

```json
{
  "mcpServers": {
    "wiki": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

### Docker Compose

```bash
# SSE server mode
docker compose up wiki-mcp-sse

# Streamable HTTP mode
docker compose up wiki-mcp-http
```

### Local install (stdio)

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

### CLI options

```
python server.py [--transport stdio|sse|streamable-http] [--host 0.0.0.0] [--port 8000]
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

## Basic Authentication

Basic Auth is available for SSE and streamable-http transports. Set both `WIKI_AUTH_USER` and `WIKI_AUTH_PASS` to enable it. stdio mode is unaffected.

### Docker run

```bash
docker run -d --name wiki-mcp \
  -v /path/to/your/wiki:/wiki \
  -e WIKI_PATH=/wiki \
  -e WIKI_TRANSPORT=sse \
  -e WIKI_AUTH_USER=admin \
  -e WIKI_AUTH_PASS=changeme \
  -p 8000:8000 \
  ghcr.io/jhleee/md-mcp-doc:latest
```

### Docker Compose

```bash
WIKI_AUTH_USER=admin WIKI_AUTH_PASS=changeme docker compose up wiki-mcp-sse-auth
# or
WIKI_AUTH_USER=admin WIKI_AUTH_PASS=changeme docker compose up wiki-mcp-http-auth
```

Or use a `.env` file:

```bash
# .env
WIKI_AUTH_USER=admin
WIKI_AUTH_PASS=changeme
```

```bash
docker compose up wiki-mcp-sse-auth
```

### MCP client configuration with Basic Auth

Encode `user:password` in base64 and pass it in the `Authorization` header:

```bash
echo -n "admin:changeme" | base64
# → YWRtaW46Y2hhbmdlbWU=
```

```json
{
  "mcpServers": {
    "wiki": {
      "url": "http://localhost:8000/sse",
      "headers": {
        "Authorization": "Basic YWRtaW46Y2hhbmdlbWU="
      }
    }
  }
}
```

> **Note**: Basic Auth transmits credentials in base64 (not encrypted). Use HTTPS (e.g. via a reverse proxy such as nginx or Caddy) when exposing the server over a network.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `WIKI_PATH` | *(required)* | Path to the wiki vault root |
| `WIKI_DB_PATH` | `{WIKI_PATH}/.wiki.db` | sqlite-vec database location |
| `WIKI_EMBED_MODEL` | `all-MiniLM-L6-v2` | Sentence-transformers model name |
| `WIKI_RG_PATH` | `rg` | Path to ripgrep binary |
| `WIKI_CHUNK_THRESHOLD` | `10240` | File size threshold (bytes) for heading-based chunking |
| `WIKI_TRANSPORT` | `stdio` | Transport mode: `stdio`, `sse`, or `streamable-http` |
| `WIKI_HOST` | `0.0.0.0` | Bind host for SSE/HTTP modes |
| `WIKI_PORT` | `8000` | Bind port for SSE/HTTP modes |
| `WIKI_AUTH_USER` | *(disabled)* | Basic Auth username (requires `WIKI_AUTH_PASS`) |
| `WIKI_AUTH_PASS` | *(disabled)* | Basic Auth password (requires `WIKI_AUTH_USER`) |

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
├── auth.py             # Basic Auth ASGI middleware
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
