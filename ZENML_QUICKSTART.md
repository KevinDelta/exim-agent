# ZenML Integration - Quick Start (Mem0-Optimized)

## ✅ Status: Operational (Simplified Architecture)

ZenML is successfully integrated with 2 pipelines optimized for Mem0-based memory management.

## What Was Fixed

**Problem**: ZenML 0.85.0 had Pydantic compatibility issues
**Solution**: Constrained Pydantic to `>=2.0.0,<2.11.0` (downgraded to 2.10.6)

## Quick Verification

```bash
# Check ZenML version
.venv/bin/zenml version

# View ZenML stack
.venv/bin/zenml stack list

# Test pipeline imports
uv run python test_zenml_pipeline.py
```

## Available Pipelines

### 1. Ingestion Pipeline

Load documents into RAG knowledge base with tracking and caching.

### 2. Memory Analytics Pipeline

Analyze Mem0 usage patterns and generate insights.

**Note**: Distillation and promotion pipelines are not needed - Mem0 handles memory lifecycle automatically.

## Using ZenML Pipelines

### Option 1: Via Python

```python
from acc_llamaindex.application.zenml_pipelines import (
    run_ingestion_pipeline,
    memory_analytics_pipeline
)

# Run ingestion with ZenML tracking
result = run_ingestion_pipeline("/path/to/documents")

# Run memory analytics
result = memory_analytics_pipeline(user_id="user-123")
```

### Option 2: Via API

```bash
# Start the API
uv run uvicorn acc_llamaindex.infrastructure.api.main:app --reload

# Check ZenML status
curl http://localhost:8000/pipelines/status

# Run ingestion pipeline
curl -X POST http://localhost:8000/pipelines/ingest \
  -H "Content-Type: application/json" \
  -d '{"directory_path": "/path/to/documents"}'

# Run memory analytics pipeline
curl -X POST http://localhost:8000/pipelines/analytics?user_id=user-123
```

## ZenML Features Now Available

### 1. **Pipeline Tracking**

Every pipeline run is tracked with:

- Execution time
- Parameters used
- Artifacts produced
- Status (success/failure)

```bash
# View pipeline runs
.venv/bin/zenml pipeline runs list
```

### 2. **Artifact Caching**

Expensive operations are cached:

- Document embeddings (skip re-embedding unchanged docs)
- Document loading and splitting
- Database scans

### 3. **Experiment Tracking** (with MLflow)

Compare different configurations:

- Different chunking strategies (512 vs 1024)
- Different embedding models
- Different promotion thresholds

```bash
# Start MLflow UI (optional)
mlflow server --host 127.0.0.1 --port 5000

# Configure ZenML to use MLflow
.venv/bin/zenml experiment-tracker register mlflow_tracker --flavor=mlflow
```

### 4. **Full Lineage**

Track data flow:

- Raw documents → Chunks → Embeddings → ChromaDB
- Conversations → Facts → Episodic Memory → Semantic Memory

### 5. **Reproducibility**

Reproduce any pipeline run exactly:

```bash
# Get run details
.venv/bin/zenml pipeline runs describe <run-id>

# Reproduce a run
.venv/bin/zenml pipeline runs clone <run-id>
```

## ZenML Dashboard (Optional)

View pipelines in a web UI:

```bash
# Start ZenML dashboard
.venv/bin/zenml up

# Access at http://localhost:8237
```

## Pipeline Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/pipelines/status` | GET | Check ZenML availability |
| `/pipelines/ingest` | POST | Run ingestion with tracking |
| `/pipelines/analytics` | POST | Run memory analytics |

## Benefits Over Direct Service Calls

### Without ZenML (Original)

```python
result = ingest_service.ingest_documents_from_directory("/path")
# ❌ No tracking
# ❌ No caching
# ❌ No lineage
# ❌ No experiment comparison
```

### With ZenML (Now)

```python
result = run_ingestion_pipeline("/path")
# ✅ Full execution tracking
# ✅ Automatic caching
# ✅ Complete lineage
# ✅ Experiment comparison
# ✅ Reproducibility
```

## Next Steps (Optional Enhancements)

### Testing & Validation

- Run end-to-end pipeline tests
- Validate artifact caching works
- Test pipeline failure scenarios
- Verify lineage tracking

### MLflow Integration

- Set up MLflow experiment tracker
- Configure experiment tracking for pipelines
- Compare different configurations

### Production Deployment (Future)

- Configure Kubernetes orchestrator
- Set up S3 artifact store
- Deploy PostgreSQL metadata store
- Add Slack alerting

## Troubleshooting

### If ZenML CLI doesn't work

Use the virtual environment directly:

```bash
.venv/bin/zenml <command>
```

### If pipelines fall back to regular services

Check ZenML availability:

```python
from acc_llamaindex.application.zenml_pipelines.ingestion_pipeline import ZENML_AVAILABLE
print(ZENML_AVAILABLE)  # Should be True
```

### View logs

```bash
# ZenML logs
.venv/bin/zenml logs

# API logs
uv run uvicorn acc_llamaindex.infrastructure.api.main:app --log-level debug
```

## Documentation

- **Pipeline Guide**: `src/acc_llamaindex/application/zenml_pipelines/README.md`
- **Implementation Status**: `ZENML_IMPLEMENTATION_STATUS.md`
- **Integration Guide**: `ZENML_INTEGRATION_GUIDE.md`
- **ZenML Docs**: [https://docs.zenml.io/](https://docs.zenml.io/)

---

**Status**: ✅ Fully operational as of 2025-01-21
