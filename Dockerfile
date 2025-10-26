FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set the working directory.
WORKDIR /app

# Install the application dependencies.
COPY uv.lock pyproject.toml README.md ./
RUN uv sync --frozen --no-cache

# Copy the application into the container.
COPY src/ ./src/

# Set environment variables for Docker paths (override .env if needed)
ENV DOCUMENTS_PATH=/app/data/documents
ENV CHROMA_DB_PATH=/app/data/chroma_db
ENV MEM0_HISTORY_DB_PATH=/app/data/mem0_history.db

CMD ["/app/.venv/bin/fastapi", "run", "src/exim_agent/infrastructure/api/main.py", "--port", "8000", "--host", "0.0.0.0"]

