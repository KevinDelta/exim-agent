"""Optimized FastAPI application with Mem0 memory system."""

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from exim_agent.application.chat_service.service import chat_service
from exim_agent.application.ingest_documents_service.service import ingest_service
from exim_agent.application.evaluation_service import evaluation_service
from exim_agent.application.compliance_service.service import compliance_service
from exim_agent.application.memory_service.mem0_client import mem0_client
from exim_agent.domain.exceptions import DocumentIngestionError
from exim_agent.infrastructure.db.chroma_client import chroma_client
from exim_agent.infrastructure.db.compliance_collections import compliance_collections
from exim_agent.infrastructure.llm_providers.langchain_provider import get_embeddings, get_llm
from exim_agent.infrastructure.http_client import shutdown_http_clients
from exim_agent.config import config

# Models
from .models import (
    ChatRequest,
    ChatResponse,
    EvalRequest,
    IngestDocumentsRequest,
    IngestDocumentsResponse,
    ResetMemoryRequest,
)

# Mem0 memory routes
from .routes.memory_routes import router as memory_router
# Compliance routes
from .routes.compliance_routes import router as compliance_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup and shutdown events."""
    # Startup
    logger.info("Starting Agent API (Mem0-powered)...")
    try:
        get_llm()
        get_embeddings()
        chroma_client.initialize()
        chat_service.initialize()
        compliance_service.initialize()
        compliance_collections.initialize()
        logger.info("Agent API startup complete")
    except Exception as e:
        logger.error(f"Failed to start Agent API: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Agent API...")
    try:
        await shutdown_http_clients()
        logger.info("HTTP clients shutdown complete")
    except Exception as e:
        logger.error(f"Error shutting down HTTP clients: {e}")


app = FastAPI(
    title="exim_agent",
    description="Mem0-powered exim Agent with LangGraph",
    docs_url="/docs",
    lifespan=lifespan,
)

# Allow development frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Mem0 memory routes
app.include_router(memory_router)
# Include Compliance routes
app.include_router(compliance_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Welcome to Agent API. Visit /docs for documentation"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Chat endpoint with RAG + Mem0 memory and compliance routing.
    
    Handles three routing paths:
    1. General RAG: Non-compliance questions use document retrieval
    2. Slot Filling: Compliance questions without required IDs prompt for missing information
    3. Compliance Delegation: Compliance questions with all IDs delegate to compliance graph
    
    - Retrieves conversational memory from Mem0
    - Queries document knowledge base (RAG)
    - Reranks and fuses context
    - Generates response with LLM
    - Stores conversation in Mem0
    """
    try:
        # Extract message text
        message_text = request.message if isinstance(request.message, str) else str(request.message)
        logger.info(f"Chat request: {message_text[:50]}...")
        
        # Ensure chat service is initialized
        if not chat_service.initialized:
            logger.warning("Chat service not initialized, attempting initialization...")
            try:
                chat_service.initialize()
            except Exception as init_error:
                logger.error(f"Failed to initialize chat service: {init_error}")
                return ChatResponse(
                    response="Chat service is not available. Please check server configuration.",
                    success=False,
                    error=f"Initialization failed: {str(init_error)}"
                )
        
        # Generate default user_id and session_id if not provided
        user_id = request.user_id or "default"
        session_id = request.session_id or f"session-{user_id}"
        
        # Call chat service with optional identifiers
        result = chat_service.chat(
            message=message_text,
            user_id=user_id,
            session_id=session_id,
            client_id=request.client_id,
            sku_id=request.sku_id,
            lane_id=request.lane_id
        )
        
        return ChatResponse(
            response=result["response"],
            success=result.get("success", True),
            error=result.get("error"),
            citations=result.get("citations", []),
            snapshot=result.get("snapshot"),
            routing_path=result.get("routing_path")
        )
        
    except Exception as e:
        logger.error(f"Chat request failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/evaluate")
async def evaluate(request: EvalRequest):
    """
    Evaluate a RAG response for quality metrics.
    
    Returns faithfulness, relevance, and context precision scores.
    """
    try:
        logger.info(f"Evaluation request: {request.query[:50]}...")
        
        if not evaluation_service.is_enabled():
            evaluation_service.initialize()
        
        results = await evaluation_service.evaluate_response(
            query=request.query,
            response=request.response,
            contexts=request.contexts,
            ground_truth=request.ground_truth,
            metrics=request.metrics
        )
        
        return {
            "success": True,
            "evaluation": results
        }
        
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/evaluation/metrics")
async def list_evaluation_metrics():
    """List available evaluation metrics."""
    return {
        "success": True,
        "metrics": evaluation_service.get_available_metrics() if evaluation_service.is_enabled() else [],
        "descriptions": {
            "faithfulness": "Measures if answer is grounded in retrieved context (0-1)",
            "answer_relevance": "Measures if answer addresses the question (0-1)",
            "context_precision": "Measures if retrieved documents are relevant (0-1)"
        }
    }


@app.post("/ingest-documents", response_model=IngestDocumentsResponse)
async def ingest_documents(request: IngestDocumentsRequest) -> IngestDocumentsResponse:
    """
    Ingest documents into RAG vector store.
    
    - Single file via file_path
    - Directory via directory_path
    - Uses default documents_path if neither provided
    """
    try:
        logger.info(f"Ingestion request: {request}")
        
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
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/reset-memory")
async def reset_memory(request: ResetMemoryRequest):
    """Reset the RAG vector store collection."""
    try:
        logger.warning("Resetting vector store collection...")
        chroma_client.reset_collection()
        stats = chroma_client.get_collection_stats()
        
        return {
            "success": True,
            "message": "Vector store collection reset successfully",
            "collection_stats": stats
        }
        
    except Exception as e:
        logger.error(f"Failed to reset collection: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reset collection: {str(e)}")


@app.get("/health")
async def health_check():
    """
    Health check endpoint that checks dependency status.
    
    Checks:
    - ChromaDB connection status
    - Mem0 availability (optional, doesn't fail if unavailable)
    - LLM provider connectivity
    
    Returns detailed status for each dependency.
    """
    dependencies = {}
    overall_status = "healthy"
    
    # Check ChromaDB
    try:
        rag_stats = chroma_client.get_collection_stats()
        dependencies["chromadb"] = {
            "status": "healthy",
            "document_count": rag_stats.get("count", 0),
            "collection_name": rag_stats.get("name", "unknown")
        }
    except Exception as e:
        logger.error(f"ChromaDB health check failed: {e}")
        dependencies["chromadb"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        overall_status = "degraded"
    
    # Check Mem0 (optional - doesn't affect overall status)
    try:
        if config.mem0_enabled:
            mem0_enabled = mem0_client.is_enabled()
            dependencies["mem0"] = {
                "status": "healthy" if mem0_enabled else "disabled",
                "enabled": mem0_enabled
            }
        else:
            dependencies["mem0"] = {
                "status": "disabled",
                "enabled": False
            }
    except Exception as e:
        logger.warning(f"Mem0 health check failed (non-critical): {e}")
        dependencies["mem0"] = {
            "status": "unavailable",
            "error": str(e),
            "note": "Mem0 is optional and system can function without it"
        }
    
    # Check LLM provider
    try:
        llm = get_llm()
        dependencies["llm_provider"] = {
            "status": "healthy",
            "provider": config.llm_provider,
            "model": getattr(llm, "model_name", "unknown")
        }
    except Exception as e:
        logger.error(f"LLM provider health check failed: {e}")
        dependencies["llm_provider"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        overall_status = "unhealthy"
    
    # Check compliance service
    try:
        compliance_initialized = compliance_service.graph is not None
        dependencies["compliance_service"] = {
            "status": "healthy" if compliance_initialized else "not_initialized",
            "initialized": compliance_initialized
        }
    except Exception as e:
        logger.error(f"Compliance service health check failed: {e}")
        dependencies["compliance_service"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        overall_status = "degraded"
    
    # Check chat service
    try:
        chat_initialized = chat_service.initialized
        dependencies["chat_service"] = {
            "status": "healthy" if chat_initialized else "not_initialized",
            "initialized": chat_initialized
        }
    except Exception as e:
        logger.error(f"Chat service health check failed: {e}")
        dependencies["chat_service"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        overall_status = "degraded"
    
    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "dependencies": dependencies,
        "configuration": {
            "langgraph": True,
            "mem0_enabled": config.mem0_enabled,
            "reranking_enabled": config.enable_reranking,
            "llm_provider": config.llm_provider
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
