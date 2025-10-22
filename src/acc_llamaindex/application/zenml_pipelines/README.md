# ZenML Pipelines

This directory contains ZenML pipeline implementations for the memory-aware RAG system.

## Overview

The ZenML pipelines provide MLOps capabilities for:

- Document ingestion
- Conversation distillation  
- Memory promotion

## Architecture

```bash
┌──────────────────────────────────────────────┐
│           ZenML Orchestration                │
│                                              │
│  ┌────────────┐  ┌──────────┐  ┌──────────┐ │
│  │ Ingestion  │  │ Distill  │  │ Promote  │ │
│  │  Pipeline  │  │ Pipeline │  │ Pipeline │ │
│  └────────────┘  └──────────┘  └──────────┘ │
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

### 2. Distillation Pipeline (`distillation_pipeline.py`)

Converts conversation distillation into a tracked pipeline with:

**Steps:**

1. `fetch_recent_turns` - Get conversation history
2. `summarize_conversation` - LLM summarization
3. `extract_facts` - Extract atomic facts
4. `deduplicate_facts` - Remove duplicates
5. `store_episodic_facts` - Persist to EM

**Benefits:**

- Track which LLM generated which facts
- Compare different summarization prompts
- Measure fact extraction quality
- Full lineage from turns to facts

**Usage:**

```python
from acc_llamaindex.application.zenml_pipelines import run_distillation_pipeline

result = run_distillation_pipeline(
    session_id="user-123",
    n_turns=5
)
```

**API Endpoint:**

```bash
POST /pipelines/distill
{
  "session_id": "user-123",
  "force": false
}
```

### 3. Promotion Pipeline (`promotion_pipeline.py`)

Converts memory promotion into a tracked pipeline with:

**Steps:**

1. `scan_episodic_memory` - Find candidates
2. `filter_promotion_candidates` - Apply criteria
3. `transform_for_semantic_memory` - Prepare metadata
4. `promote_to_semantic_memory` - Copy to SM
5. `cleanup_promoted_facts` - Optional cleanup

**Benefits:**

- Experiment with different promotion thresholds
- Track promotion rates over time
- A/B test criteria changes
- Rollback if promotion degrades quality

**Usage:**

```python
from acc_llamaindex.application.zenml_pipelines import run_promotion_pipeline

result = run_promotion_pipeline(
    salience_threshold=0.8,
    citation_threshold=5,
    age_days=7
)
```

**API Endpoint:**
```bash
POST /pipelines/promote
{}
```

## Unified Runner

The `runner.py` module provides a unified interface:

```python
from acc_llamaindex.application.zenml_pipelines.runner import pipeline_runner

# Run individual pipelines
pipeline_runner.run_ingestion(directory_path="/path")
pipeline_runner.run_distillation(session_id="user-123")
pipeline_runner.run_promotion()

# Run all pipelines
pipeline_runner.run_all_pipelines(
    directory_path="/path",
    session_id="user-123"
)
```

## Graceful Degradation

All pipelines include fallback to existing services if ZenML is unavailable:

- `run_ingestion_pipeline` → `ingest_service.ingest_documents_from_directory()`
- `run_distillation_pipeline` → `conversation_summarizer.distill()`
- `run_promotion_pipeline` → `memory_promoter.run_promotion_cycle()`

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

✅ Pipeline structure implemented  
✅ Graceful fallback to existing services  
✅ API endpoints integrated  
⚠️ ZenML dependency compatibility issues (being resolved)  
⏳ Full ZenML orchestration (pending dependency fix)  

## Notes

- Pipelines follow existing design patterns (no unnecessary directories/files)
- Code reuses existing services (no duplication)
- Backward compatible with non-ZenML mode
- Ready for MLOps when ZenML is fully operational

## Integration Points

### FastAPI Routes

New routes added to `infrastructure/api/main.py`:
- `POST /pipelines/ingest` - ZenML ingestion
- `POST /pipelines/distill` - ZenML distillation
- `POST /pipelines/promote` - ZenML promotion
- `GET /pipelines/status` - Check availability

### Health Check

`GET /health` now includes `zenml_pipelines_enabled` field.

### Existing Routes

Original routes remain unchanged for compatibility:
- `POST /ingest-documents` - Direct ingestion
- `POST /memory/distill` - Direct distillation
- `POST /memory/promote` - Direct promotion
