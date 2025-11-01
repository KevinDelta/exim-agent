# Use
 # multi-stage build to avoid containerd issues
FROM python:3.11-slim as base

# Install system dependencies in a single layer
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# Install uv directly using pip to avoid multi-stage copy issues
RUN pip install uv

# Set the working directory
WORKDIR /app

# Copy dependency files
COPY uv.lock pyproject.toml README.md ./

# Install dependencies
RUN uv sync --frozen --no-cache

# Copy the application
COPY src/ ./src/

# Set environment variables
ENV DOCUMENTS_PATH=/app/data/documents
ENV CHROMA_DB_PATH=/app/data/chroma_db
ENV MEM0_HISTORY_DB_PATH=/app/data/mem0_history.db

# Use uv to run the application
CMD ["uv", "run", "fastapi", "run", "src/exim_agent/infrastructure/api/main.py", "--port", "8000", "--host", "0.0.0.0"]

