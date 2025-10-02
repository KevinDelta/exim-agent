from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from loguru import logger

from acc_llamaindex.application.ingest_documents_service.service import ingest_service
from acc_llamaindex.domain.exceptions import DocumentIngestionError
from acc_llamaindex.infrastructure.db.chroma_client import chroma_client
from acc_llamaindex.infrastructure.llm_providers.openai_provider import initialize_llm_providers

from .models import (
    ChatRequest,
    EvalRequest,
    IngestDocumentsRequest,
    IngestDocumentsResponse,
    ResetMemoryRequest,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup and shutdown events for the API."""
    # Startup: Initialize LLM providers and ChromaDB
    logger.info("Starting up Agent API...")
    try:
        initialize_llm_providers()
        chroma_client.initialize()
        logger.info("Agent API startup complete")
    except Exception as e:
        logger.error(f"Failed to start Agent API: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Agent API...")


app = FastAPI(
    title=" Agent API ",
    description=" This is a template for creating powerful Agent APIs. ",
    docs_url="/docs",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    """
    Root endpoint that redirects to API documentation
    """
    return {"message": "Welcome to Agent API. Visit /docs for documentation"}


@app.post("/chat")
async def chat(request: ChatRequest):
    """
    Uses the Chat Service from application layer
    """
    return {"message": "Chat request received"}


@app.post("/eval")
async def eval(request: EvalRequest):
    """
    Uses the Chat Service from application layer
    """
    return {"message": "Eval request received"}


@app.post("/ingest-documents", response_model=IngestDocumentsResponse)
async def ingest_documents(request: IngestDocumentsRequest) -> IngestDocumentsResponse:
    """
    Ingest documents into the vector store.
    
    - If file_path is provided, ingests a single file
    - If directory_path is provided, ingests all supported files from directory
    - If neither is provided, uses default documents directory from settings
    """
    try:
        logger.info(f"Received ingestion request: {request}")
        
        # Single file ingestion takes precedence
        if request.file_path:
            result = ingest_service.ingest_single_file(request.file_path)
        else:
            result = ingest_service.ingest_documents_from_directory(request.directory_path)
        
        return IngestDocumentsResponse(**result.model_dump())
        
    except DocumentIngestionError as e:
        logger.error(f"Document ingestion failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during ingestion: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during document ingestion")


@app.post("/reset-memory")
async def reset_memory(request: ResetMemoryRequest):
    """
    Uses the Chat Service from application layer
    """
    return {"message": "Reset memory request received"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
