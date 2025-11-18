from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request model for chat."""
    message: str | dict = Field(..., description="The user's message")
    user_id: Optional[str] = Field(None, description="The user's ID")
    session_id: Optional[str] = Field(None, description="The session's ID") # This is the session ID from the frontend
    stream: bool = Field(False, description="Whether to stream the response")
    # Optional identifiers for compliance routing
    client_id: Optional[str] = Field(None, description="Client identifier for compliance queries")
    sku_id: Optional[str] = Field(None, description="SKU identifier for compliance queries")
    lane_id: Optional[str] = Field(None, description="Lane identifier for compliance queries")

class ChatResponse(BaseModel):
    """Response model for chat."""
    response: str = Field(..., description="The assistant's response")
    success: bool = True
    error: Optional[str] = None
    citations: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Source citations")
    snapshot: Optional[Dict[str, Any]] = Field(None, description="Compliance snapshot if compliance delegation occurred")
    routing_path: Optional[str] = Field(None, description="Which path was taken: general_rag, slot_filling, or delegate_compliance")

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


class AddMemoryRequest(BaseModel):
    """Request model for adding memory."""
    messages: List[Dict[str, str]] = Field(
        ...,
        description="List of messages with 'role' and 'content' keys",
        example=[
            {"role": "user", "content": "What is LangChain?"},
            {"role": "assistant", "content": "LangChain is a framework..."},
        ],
    )
    user_id: Optional[str] = Field(None, description="User identifier")
    agent_id: Optional[str] = Field(None, description="Agent identifier")
    session_id: Optional[str] = Field(None, description="Session identifier")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class SearchMemoryRequest(BaseModel):
    """Request model for searching memories."""
    query: str = Field(..., description="Search query")
    user_id: Optional[str] = Field(None, description="Filter by user")
    agent_id: Optional[str] = Field(None, description="Filter by agent")
    session_id: Optional[str] = Field(None, description="Filter by session")
    limit: int = Field(10, ge=1, le=100, description="Maximum number of results")


class UpdateMemoryRequest(BaseModel):
    """Request model for updating memory."""
    data: str = Field(..., description="New memory content")


class ResetMemoryRequest(BaseModel):
    """Request model for resetting memories."""
    user_id: Optional[str] = Field(None, description="Reset for specific user")
    agent_id: Optional[str] = Field(None, description="Reset for specific agent")
    session_id: Optional[str] = Field(None, description="Reset for specific session")


class SnapshotRequest(BaseModel):
    """Request model for compliance snapshot."""
    client_id: str = Field(..., description="Client identifier")
    sku_id: str = Field(..., description="SKU identifier")
    lane_id: str = Field(..., description="Lane identifier (e.g., CNSHA-USLAX-ocean)")
    hts_code: Optional[str] = Field(None, description="Optional HTS code override")

    model_config = {
        "json_schema_extra": {
            "example": {
                "client_id": "client_ABC",
                "sku_id": "SKU-123",
                "lane_id": "CNSHA-USLAX-ocean",
                "hts_code": "8517.12.00",
            }
        }
    }

class SnapshotResponse(BaseModel):
    """Response model for compliance snapshot."""
    success: bool
    snapshot: Optional[Dict[str, Any]] = None
    citations: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AskRequest(BaseModel):
    """Request model for compliance Q&A."""
    client_id: str = Field(..., description="Client identifier")
    sku_id: str = Field(..., description="SKU identifier")
    lane_id: str = Field(..., description="Lane identifier (e.g., CNSHA-USLAX-ocean)")
    question: str = Field(..., description="Natural language compliance question")
    hts_code: Optional[str] = Field(None, description="Optional HTS code override")

    model_config = {
        "json_schema_extra": {
            "example": {
                "client_id": "client_ABC",
                "sku_id": "SKU-123",
                "lane_id": "CNSHA-USLAX-ocean",
                "question": "What are the special requirements for importing smartphones from China?",
                "hts_code": "8517.12.00",
            }
        }
    }


class AskResponse(BaseModel):
    """Response model for compliance Q&A."""
    success: bool
    answer: Optional[str] = None
    citations: Optional[List[Dict[str, Any]]] = None
    question: str
    error: Optional[str] = None


class WeeklyPulseResponse(BaseModel):
    """Response model for weekly compliance pulse."""
    success: bool
    client_id: str
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    summary: Optional[Dict[str, Any]] = None
    changes: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
