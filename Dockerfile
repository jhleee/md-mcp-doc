FROM python:3.12-slim

# Install ripgrep
RUN apt-get update && \
    apt-get install -y --no-install-recommends ripgrep && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer cache)
COPY pyproject.toml ./
RUN pip install --no-cache-dir mcp sentence-transformers sqlite-vec python-frontmatter

# Copy source code
COPY config.py server.py ./
COPY core/ core/
COPY tools/ tools/

# Pre-download the embedding model at build time so startup is fast
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Default wiki path (mount your vault here)
ENV WIKI_PATH=/wiki
ENV WIKI_TRANSPORT=stdio
ENV WIKI_HOST=0.0.0.0
ENV WIKI_PORT=8000

VOLUME /wiki
EXPOSE 8000

ENTRYPOINT ["python", "server.py"]
