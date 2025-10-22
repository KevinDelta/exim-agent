from typing import Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request model for chat."""
    message: str | dict = Field(..., description="The user's message")
    conversation_history: Optional[list[dict]] = Field(
        default_factory=list, example=[],
        description="Optional conversation history (list of message dicts with 'role' and 'content')"
    )
    stream: bool = Field(False, description="Whether to stream the response")


class ChatResponse(BaseModel):
    """Response model for chat."""
    response: str
    success: bool = True
    error: Optional[str] = None


class EvalRequest(BaseModel):
    """Request model for evaluation."""
    query: str = Field(..., description="The user's question")
    response: str = Field(..., description="The generated answer")
    contexts: list[str] = Field(..., description="Retrieved context documents")
    ground_truth: Optional[str] = Field(None, description="Optional ground truth answer")
    metrics: Optional[list[str]] = Field(
        None,
        description="List of metrics to compute (default: all). Options: faithfulness, answer_relevance, context_precision"
    )


class EvalResponse(BaseModel):
    """Response model for evaluation."""
    success: bool
    evaluation: dict
    error: Optional[str] = None


class IngestDocumentsRequest(BaseModel):
    """Request model for document ingestion."""
    directory_path: Optional[str] = Field(
        None,
        description="Path to directory containing documents. If not provided, uses default from settings."
    )
    file_path: Optional[str] = Field(
        None,
        description="Path to a single file to ingest. Takes precedence over directory_path."
    )


class IngestDocumentsResponse(BaseModel):
    """Response model for document ingestion."""
    success: bool
    documents_processed: int
    documents_failed: int
    failed_documents: list[str] = Field(default_factory=list)
    message: str
    collection_stats: Optional[dict] = None


class ResetMemoryRequest(BaseModel):
    pass


# Memory API Models

class MemoryRecallRequest(BaseModel):
    """Request model for memory recall."""
    query: str = Field(..., description="User query text")
    session_id: str = Field(..., description="Session identifier")
    intent: Optional[str] = Field(None, description="Optional intent (auto-detected if not provided)")
    k: Optional[int] = Field(10, description="Number of results to retrieve")


class MemoryRecallResponse(BaseModel):
    """Response model for memory recall."""
    success: bool
    results: list[dict]
    query_metadata: dict
    error: Optional[str] = None


class MemoryDistillRequest(BaseModel):
    """Request model for conversation distillation."""
    session_id: str = Field(..., description="Session identifier")
    force: bool = Field(False, description="Force distillation even if not at threshold")


class MemoryDistillResponse(BaseModel):
    """Response model for distillation."""
    success: bool
    facts_created: int
    duplicates_merged: int
    error: Optional[str] = None


class SessionInfoResponse(BaseModel):
    """Response model for session info."""
    success: bool
    session_id: str
    wm_turns: int
    em_facts: int
    last_distilled: Optional[str]
    error: Optional[str] = None


class MemoryPromoteRequest(BaseModel):
    """Request model for manual promotion."""
    fact_id: Optional[str] = Field(None, description="Specific fact ID to promote (optional)")


class MemoryPromoteResponse(BaseModel):
    """Response model for promotion."""
    success: bool
    promoted: int
    found: int
    error: Optional[str] = None


class MetricsResponse(BaseModel):
    """Response model for metrics."""
    success: bool
    metrics: dict
    error: Optional[str] = None
