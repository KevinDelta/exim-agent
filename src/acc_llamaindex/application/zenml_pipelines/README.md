# ZenML Pipelines (Mem0-Optimized)

This directory contains ZenML pipeline implementations for the Mem0-powered RAG system.

## Overview

The ZenML pipelines provide MLOps capabilities for:

- **Document ingestion** - Load documents into RAG knowledge base
- **Memory analytics** - Analyze Mem0 usage patterns and generate insights

**Note**: This system uses Mem0 for conversational memory management. Mem0 handles memory distillation, storage, and lifecycle automatically, eliminating the need for separate distillation/promotion pipelines.

## Architecture

```bash
┌──────────────────────────────────────────────┐
│           ZenML Orchestration                │
│                                              │
│  ┌────────────┐  ┌──────────────────────┐   │
│  │ Ingestion  │  │ Memory Analytics     │   │
│  │  Pipeline  │  │ Pipeline (Mem0)      │   │
│  └────────────┘  └──────────────────────┘   │
│                                              │
│  Benefits:                                   │
│  • Artifact caching & lineage                │
│  • Experiment tracking (MLflow)              │
│  • Version control for runs                  │
│  • Reproducibility                           │
└──────────────────────────────────────────────┘
```

## Pipelines

### 1. Ingestion Pipeline (`ingestion_pipeline.py`)

Converts document ingestion into a tracked pipeline with:

**Steps:**

1. `discover_documents` - Find all supported files
2. `load_and_split_documents` - Load and chunk (cached)
3. `generate_embeddings` - Create embeddings (cached)
4. `store_in_chromadb` - Persist to vector DB

**Benefits:**

- Skip re-embedding unchanged documents via caching
- Track which embedding model was used
- Compare different chunking strategies
- Full lineage from raw docs to storage

**Usage:**

```python
from acc_llamaindex.application.zenml_pipelines import run_ingestion_pipeline

result = run_ingestion_pipeline(
    directory_path="/path/to/documents",
    chunk_size=1024,
    chunk_overlap=200
)
```

**API Endpoint:**

```bash
POST /pipelines/ingest
{
  "directory_path": "/path/to/documents"
}
```

### 2. Memory Analytics Pipeline (`memory_analytics_pipeline.py`)

Analyzes Mem0 memory usage patterns and generates actionable insights.

**Steps:**

1. `fetch_user_memories` - Retrieve all memories for a user from Mem0
2. `analyze_memory_patterns` - Compute statistics (count, types, avg length)
3. `generate_insights` - Generate recommendations based on patterns

**Benefits:**

- Track memory growth over time
- Identify memory quality issues
- Monitor Mem0 usage patterns
- Generate cleanup recommendations

**Usage:**

```python
from acc_llamaindex.application.zenml_pipelines import memory_analytics_pipeline

result = memory_analytics_pipeline(user_id="user-123")
# Returns: {stats, insights, recommendations}
```

**API Endpoint:**

```bash
POST /pipelines/analytics?user_id=user-123
```

**Why No Distillation/Promotion Pipelines?**

Mem0 handles these automatically:

- **Distillation**: Mem0 extracts and stores memories from conversations
- **Promotion**: Mem0 manages memory lifecycle and relevance scoring
- **Cleanup**: Mem0 handles memory retention policies

These pipelines are unnecessary with Mem0's built-in memory management.

## Unified Runner

The `runner.py` module provides a unified interface:

```python
from acc_llamaindex.application.zenml_pipelines.runner import pipeline_runner

# Run ingestion pipeline
pipeline_runner.run_ingestion(directory_path="/path")

# Run memory analytics pipeline
pipeline_runner.run_memory_analytics(user_id="user-123")
```

## Graceful Degradation

The ingestion pipeline includes fallback to existing services if ZenML is unavailable:

- `run_ingestion_pipeline` → `ingest_service.ingest_documents_from_directory()`

This ensures backward compatibility and allows the system to function even if ZenML dependencies have issues.

## ZenML Setup (Optional)

To enable full ZenML features:

1. **Install dependencies** (already in pyproject.toml):

   ```bash
   uv sync
   ```

2. **Initialize ZenML** (when dependency issues are resolved):

   ```bash
   zenml init
   zenml stack set default
   ```

3. **Start MLflow** (for experiment tracking):

   ```bash
   mlflow server --host 127.0.0.1 --port 5000
   ```

4. **Configure stack** (optional, for production):

   ```bash
   zenml stack create production \
     --orchestrator kubernetes \
     --artifact-store s3 \
     --experiment-tracker mlflow
   ```

## Current Status

✅ **Ingestion Pipeline**: Fully implemented and functional  
✅ **Memory Analytics Pipeline**: Fully implemented and functional  
✅ **Graceful fallback**: Falls back to existing services if ZenML unavailable  
✅ **API endpoints**: Integrated with FastAPI  
✅ **ZenML initialized**: Local stack configured and operational  
⏳ **Testing**: Pipelines need end-to-end testing  
⏳ **MLflow**: Experiment tracking not yet configured  

## Notes

- Pipelines follow existing design patterns (no unnecessary directories/files)
- Code reuses existing services (no duplication)
- Backward compatible with non-ZenML mode
- Ready for MLOps when ZenML is fully operational

## Integration Points

### FastAPI Routes

New routes added to `infrastructure/api/main.py`:

- `POST /pipelines/ingest` - ZenML ingestion pipeline
- `POST /pipelines/analytics` - Memory analytics pipeline
- `GET /pipelines/status` - Check ZenML availability

### Health Check

`GET /health` now includes `zenml` field showing ZenML availability.

### Existing Routes

Original routes remain unchanged for compatibility:

- `POST /ingest-documents` - Direct ingestion (non-ZenML)
- `POST /memory/*` - Mem0 memory management routes
