"""ZenML pipelines for document ingestion and memory analytics (Mem0-optimized)."""

from acc_llamaindex.application.zenml_pipelines.ingestion_pipeline import (
    ingestion_pipeline,
    run_ingestion_pipeline,
)
from acc_llamaindex.application.zenml_pipelines.memory_analytics_pipeline import (
    memory_analytics_pipeline,
)

__all__ = [
    "ingestion_pipeline",
    "run_ingestion_pipeline",
    "memory_analytics_pipeline",
]
