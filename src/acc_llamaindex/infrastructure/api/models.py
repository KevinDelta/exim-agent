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
    pass


class EvalResponse(BaseModel):
    """Response model for evaluation."""
    pass


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
