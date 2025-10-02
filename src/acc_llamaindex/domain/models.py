from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class DocumentStatus(str, Enum):
    """Status of document processing."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Document(BaseModel):
    """Domain model for a document."""
    file_path: Path
    file_name: str
    file_type: str
    size_bytes: int
    status: DocumentStatus = DocumentStatus.PENDING
    error_message: Optional[str] = None
    
    class Config:
        use_enum_values = True


class IngestionResult(BaseModel):
    """Result of document ingestion operation."""
    success: bool
    documents_processed: int
    documents_failed: int
    failed_documents: list[str] = Field(default_factory=list)
    message: str
    collection_stats: Optional[dict] = None
