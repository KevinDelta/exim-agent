from typing import Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    pass


class EvalRequest(BaseModel):
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
