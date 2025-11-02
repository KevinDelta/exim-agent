"""Optimized FastAPI application with Mem0 memory system."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from exim_agent.application.chat_service.service import chat_service
from exim_agent.application.ingest_documents_service.service import ingest_service
from exim_agent.application.evaluation_service import evaluation_service
from exim_agent.application.compliance_service.service import compliance_service
from exim_agent.domain.exceptions import DocumentIngestionError
from exim_agent.infrastructure.db.chroma_client import chroma_client
from exim_agent.infrastructure.db.compliance_collections import compliance_collections
from exim_agent.infrastructure.llm_providers.langchain_provider import get_embeddings, get_llm
from exim_agent.config import config

# ZenML pipelines
try:
    from exim_agent.application.zenml_pipelines.runner import pipeline_runner
    ZENML_PIPELINES_AVAILABLE = True
except ImportError:
    logger.warning("ZenML pipelines not available - /pipelines/* endpoints disabled")
    ZENML_PIPELINES_AVAILABLE = False
    pipeline_runner = None

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
# Admin routes
from .routes.admin_routes import router as admin_router


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
# Include Admin routes
app.include_router(admin_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Welcome to Agent API. Visit /docs for documentation"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Chat endpoint with RAG + Mem0 memory.
    
    - Retrieves conversational memory from Mem0
    - Queries document knowledge base (RAG)
    - Reranks and fuses context
    - Generates response with LLM
    - Stores conversation in Mem0
    """
    try:
        logger.info(f"Chat request: {request.message[:50]}...")
        
        result = chat_service.chat(
            message=request.message,
            conversation_history=request.conversation_history
        )
        
        return ChatResponse(
            response=result["response"],
            success=result.get("success", True),
            error=result.get("error")
        )
        
    except Exception as e:
        logger.error(f"Chat request failed: {e}")
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
    Health check endpoint.
    
    Returns system status and configuration.
    """
    try:
        rag_stats = chroma_client.get_collection_stats()
        
        return {
            "status": "healthy",
            "stack": {
                "langgraph": True,
                "mem0": config.mem0_enabled,
                "reranking": config.enable_reranking,
                "zenml": ZENML_PIPELINES_AVAILABLE,
                "compliance": True,
            },
            "rag_documents": rag_stats,
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


# ZenML Pipeline Endpoints

@app.post("/pipelines/ingest")
async def run_ingestion_pipeline(request: IngestDocumentsRequest):
    """
    Run document ingestion via ZenML pipeline.
    
    Provides MLOps benefits:
    - Artifact caching
    - Experiment tracking
    - Full lineage tracking
    - Versioning of pipeline runs
    """
    if not ZENML_PIPELINES_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="ZenML pipelines not available. Use /ingest-documents instead."
        )
    
    try:
        logger.info(f"Running ZenML ingestion pipeline: {request}")
        
        result = pipeline_runner.run_ingestion(
            directory_path=request.directory_path or request.file_path
        )
        
        return {
            "success": result.get("status") == "success",
            "result": result,
            "pipeline_type": "zenml"
        }
        
    except Exception as e:
        logger.error(f"ZenML ingestion pipeline failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/pipelines/analytics")
async def run_analytics_pipeline(user_id: str):
    """
    Run memory analytics pipeline.
    
    Analyzes Mem0 usage patterns and generates insights.
    """
    if not ZENML_PIPELINES_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="ZenML pipelines not available."
        )
    
    try:
        logger.info(f"Running memory analytics pipeline for user: {user_id}")
        
        result = pipeline_runner.run_memory_analytics(user_id=user_id)
        
        return {
            "success": result.get("status") == "success",
            "result": result,
            "pipeline_type": "zenml"
        }
        
    except Exception as e:
        logger.error(f"Memory analytics pipeline failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/pipelines/compliance-ingestion")
async def run_compliance_ingestion_pipeline(lookback_days: int = 7):
    """
    Run compliance data ingestion pipeline.
    
    Fetches and ingests updates from:
    - HTS codes and notes
    - Sanctions lists
    - Import refusals
    - CBP rulings
    """
    if not ZENML_PIPELINES_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="ZenML pipelines not available."
        )
    
    try:
        logger.info(f"Running compliance ingestion pipeline (lookback: {lookback_days} days)")
        
        result = pipeline_runner.run_compliance_ingestion(
            lookback_days=lookback_days
        )
        
        return {
            "success": result.get("status") == "success",
            "result": result,
            "pipeline_type": "zenml"
        }
        
    except Exception as e:
        logger.error(f"Compliance ingestion pipeline failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/pipelines/weekly-pulse")
async def run_weekly_pulse_pipeline(client_id: str, period_days: int = 7):
    """
    Run weekly compliance pulse generation pipeline.
    
    Generates comprehensive weekly digest with:
    - New requirements
    - Risk escalations
    - Delta analysis
    - Action items
    """
    if not ZENML_PIPELINES_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="ZenML pipelines not available."
        )
    
    try:
        logger.info(f"Running weekly pulse pipeline for client: {client_id}")
        
        result = pipeline_runner.run_weekly_pulse(
            client_id=client_id,
            period_days=period_days
        )
        
        return {
            "success": result.get("status") == "success",
            "result": result,
            "pipeline_type": "zenml"
        }
        
    except Exception as e:
        logger.error(f"Weekly pulse pipeline failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/pipelines/status")
async def get_pipelines_status():
    """Get status of ZenML pipelines integration."""
    return {
        "zenml_available": ZENML_PIPELINES_AVAILABLE,
        "pipelines": {
            "ingestion": ZENML_PIPELINES_AVAILABLE,
            "analytics": ZENML_PIPELINES_AVAILABLE,
            "compliance_ingestion": ZENML_PIPELINES_AVAILABLE,
            "weekly_pulse": ZENML_PIPELINES_AVAILABLE,
        },
        "endpoints": {
            "ingest": "/pipelines/ingest",
            "analytics": "/pipelines/analytics",
            "compliance_ingestion": "/pipelines/compliance-ingestion",
            "weekly_pulse": "/pipelines/weekly-pulse",
        } if ZENML_PIPELINES_AVAILABLE else {}
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
