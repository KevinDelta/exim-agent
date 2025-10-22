from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from loguru import logger

from acc_llamaindex.application.chat_service.service import chat_service
from acc_llamaindex.application.chat_service.session_manager import session_manager
from acc_llamaindex.application.ingest_documents_service.service import ingest_service
from acc_llamaindex.application.evaluation_service import evaluation_service
from acc_llamaindex.application.memory_service import (
    memory_service,
    conversation_summarizer,
    memory_promoter,
    background_jobs,
)
from acc_llamaindex.application.memory_service.metrics import memory_metrics
from acc_llamaindex.domain.exceptions import DocumentIngestionError
from acc_llamaindex.infrastructure.db.chroma_client import chroma_client
from acc_llamaindex.infrastructure.llm_providers.langchain_provider import get_embeddings, get_llm
from acc_llamaindex.config import config

# ZenML pipelines (optional)
try:
    from acc_llamaindex.application.zenml_pipelines.runner import pipeline_runner
    ZENML_PIPELINES_AVAILABLE = True
except ImportError:
    logger.warning("ZenML pipelines not available - /pipelines/* endpoints will be disabled")
    ZENML_PIPELINES_AVAILABLE = False
    pipeline_runner = None

from .models import (
    ChatRequest,
    ChatResponse,
    EvalRequest,
    IngestDocumentsRequest,
    IngestDocumentsResponse,
    ResetMemoryRequest,
    MemoryRecallRequest,
    MemoryRecallResponse,
    MemoryDistillRequest,
    MemoryDistillResponse,
    SessionInfoResponse,
    MemoryPromoteRequest,
    MemoryPromoteResponse,
    MetricsResponse,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup and shutdown events for the API."""
    # Startup: Initialize LLM providers and ChromaDB
    logger.info("Starting up Agent API...")
    try:
        # Initialize LangChain providers
        get_llm()
        get_embeddings()
        # Initialize ChromaDB
        chroma_client.initialize()
        # Initialize chat service
        chat_service.initialize()
        
        # Start background jobs if memory system enabled
        if config.enable_memory_system:
            background_jobs.start()
            logger.info("Memory background jobs started")
        
        logger.info("Agent API startup complete")
    except Exception as e:
        logger.error(f"Failed to start Agent API: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Agent API...")
    
    # Stop background jobs
    if config.enable_memory_system:
        background_jobs.stop()
        logger.info("Memory background jobs stopped")


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


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Chat endpoint with RAG capabilities.
    
    - Accepts a message and optional conversation history
    - Uses vector store to retrieve relevant context
    - Returns AI-generated response based on retrieved knowledge
    """
    try:
        logger.info(f"Received chat request: {request.message[:50]}...")
        
        # Process chat request
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
    
    - Accepts query, response, and contexts
    - Returns faithfulness, relevance, and context precision scores
    - Optional: specify which metrics to compute
    """
    try:
        logger.info(f"Received evaluation request for query: {request.query[:50]}...")
        
        # Initialize evaluation service if not already done
        if not evaluation_service.is_enabled():
            evaluation_service.initialize()
        
        # Evaluate the response
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
        logger.error(f"Evaluation request failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/evaluation/metrics")
async def list_evaluation_metrics():
    """
    List available evaluation metrics.
    
    Returns descriptions of all available metrics.
    """
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
    Reset the vector store collection, deleting all stored documents.
    """
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


# Memory API Endpoints

@app.post("/memory/recall", response_model=MemoryRecallResponse)
async def memory_recall(request: MemoryRecallRequest) -> MemoryRecallResponse:
    """
    Recall relevant memories from all tiers (WM, EM, SM).
    
    - Queries episodic memory (session-specific facts)
    - Queries semantic memory (long-term knowledge)
    - Filters by intent and entities
    - Returns ranked results with provenance
    """
    try:
        if not config.enable_memory_system:
            raise HTTPException(status_code=503, detail="Memory system is disabled")
        
        logger.info(f"Memory recall request: session={request.session_id}, query={request.query[:50]}")
        
        # Recall memories
        result = memory_service.recall(
            query=request.query,
            session_id=request.session_id,
            intent=request.intent or "general",
            entities=[],
            k_em=request.k // 2 if request.k else config.em_k_default,
            k_sm=request.k // 2 if request.k else config.sm_k_default
        )
        
        return MemoryRecallResponse(
            success=True,
            results=result["combined_results"],
            query_metadata=result["metadata"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Memory recall failed: {e}")
        return MemoryRecallResponse(
            success=False,
            results=[],
            query_metadata={},
            error=str(e)
        )


@app.post("/memory/distill", response_model=MemoryDistillResponse)
async def memory_distill(request: MemoryDistillRequest) -> MemoryDistillResponse:
    """
    Manually trigger conversation distillation.
    
    - Summarizes recent conversation turns
    - Extracts atomic facts
    - Writes to episodic memory
    """
    try:
        if not config.enable_memory_system:
            raise HTTPException(status_code=503, detail="Memory system is disabled")
        
        logger.info(f"Manual distillation request for session: {request.session_id}")
        
        # Get recent turns
        turns = session_manager.get_recent_turns(
            request.session_id,
            n=config.em_distill_every_n_turns if not request.force else config.wm_max_turns
        )
        
        if not turns:
            return MemoryDistillResponse(
                success=True,
                facts_created=0,
                duplicates_merged=0,
                error="No turns to distill"
            )
        
        # Distill
        result = conversation_summarizer.distill(
            session_id=request.session_id,
            turns=turns
        )
        
        return MemoryDistillResponse(
            success=True,
            facts_created=result.get("facts_created", 0),
            duplicates_merged=0,  # TODO: Track from deduplication
            error=result.get("error")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Distillation failed: {e}")
        return MemoryDistillResponse(
            success=False,
            facts_created=0,
            duplicates_merged=0,
            error=str(e)
        )


@app.get("/memory/session/{session_id}", response_model=SessionInfoResponse)
async def get_session_info(session_id: str) -> SessionInfoResponse:
    """
    Get information about a session.
    
    - Working memory turns count
    - Episodic memory facts count
    - Last distillation time
    """
    try:
        if not config.enable_memory_system:
            raise HTTPException(status_code=503, detail="Memory system is disabled")
        
        # Get session
        session = session_manager.get_session(session_id)
        
        if not session:
            return SessionInfoResponse(
                success=True,
                session_id=session_id,
                wm_turns=0,
                em_facts=0,
                last_distilled=None,
                error="Session not found"
            )
        
        # Count EM facts for this session
        try:
            em_results = chroma_client.query_episodic(session_id, "facts", k=1000)
            em_count = len(em_results)
        except:
            em_count = 0
        
        return SessionInfoResponse(
            success=True,
            session_id=session_id,
            wm_turns=session["turn_count"],
            em_facts=em_count,
            last_distilled=session.get("last_distilled")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session info: {e}")
        return SessionInfoResponse(
            success=False,
            session_id=session_id,
            wm_turns=0,
            em_facts=0,
            last_distilled=None,
            error=str(e)
        )


@app.post("/memory/promote", response_model=MemoryPromoteResponse)
async def memory_promote(request: MemoryPromoteRequest) -> MemoryPromoteResponse:
    """
    Manually trigger memory promotion (EM → SM).
    
    - Finds high-value episodic facts
    - Promotes them to semantic memory
    - Returns promotion statistics
    """
    try:
        if not config.enable_memory_system or not config.enable_sm_promotion:
            raise HTTPException(status_code=503, detail="Memory promotion is disabled")
        
        logger.info("Manual promotion triggered")
        
        # Run promotion cycle
        result = memory_promoter.run_promotion_cycle()
        
        return MemoryPromoteResponse(
            success=result.get("status") == "success",
            promoted=result.get("promoted", 0),
            found=result.get("found", 0),
            error=result.get("error")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Promotion failed: {e}")
        return MemoryPromoteResponse(
            success=False,
            promoted=0,
            found=0,
            error=str(e)
        )


@app.delete("/memory/session/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a session and its working memory.
    
    - Removes session from WM
    - Does not affect EM facts (they expire via TTL)
    """
    try:
        deleted = session_manager.delete_session(session_id)
        
        return {
            "success": True,
            "deleted": deleted,
            "message": f"Session {session_id} deleted" if deleted else "Session not found"
        }
        
    except Exception as e:
        logger.error(f"Failed to delete session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics", response_model=MetricsResponse)
async def get_metrics() -> MetricsResponse:
    """
    Get memory system metrics.
    
    - Retrieval metrics (latency, cache hit rate, over-fetch)
    - Memory metrics (item counts, promotion rate, deduplication)
    - Quality metrics (citation rate, precision)
    """
    try:
        metrics = memory_metrics.get_all_metrics()
        
        return MetricsResponse(
            success=True,
            metrics=metrics
        )
        
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        return MetricsResponse(
            success=False,
            metrics={},
            error=str(e)
        )


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns system status and configuration.
    """
    try:
        # Get collection stats
        sm_stats = chroma_client.get_collection_stats()
        
        # Get session stats
        session_stats = session_manager.get_stats()
        
        # Get background jobs status
        jobs_status = background_jobs.get_status() if config.enable_memory_system else {"running": False}
        
        return {
            "status": "healthy",
            "memory_system_enabled": config.enable_memory_system,
            "zenml_pipelines_enabled": ZENML_PIPELINES_AVAILABLE,
            "semantic_memory": sm_stats,
            "sessions": session_stats,
            "background_jobs": jobs_status
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


# ZenML Pipeline Endpoints (optional MLOps integration)

@app.post("/pipelines/ingest")
async def run_ingestion_pipeline_endpoint(request: IngestDocumentsRequest):
    """
    Run document ingestion via ZenML pipeline.
    
    Provides MLOps benefits:
    - Artifact caching (skip re-embedding unchanged docs)
    - Experiment tracking (compare chunking strategies)
    - Full lineage tracking (doc → chunks → embeddings → storage)
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


@app.post("/pipelines/distill")
async def run_distillation_pipeline_endpoint(request: MemoryDistillRequest):
    """
    Run conversation distillation via ZenML pipeline.
    
    Provides MLOps benefits:
    - Track which LLM generated which facts
    - Compare different summarization prompts
    - Measure fact extraction quality
    - Full lineage tracking (turns → summary → facts → storage)
    """
    if not ZENML_PIPELINES_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="ZenML pipelines not available. Use /memory/distill instead."
        )
    
    if not config.enable_memory_system:
        raise HTTPException(status_code=503, detail="Memory system is disabled")
    
    try:
        logger.info(f"Running ZenML distillation pipeline for session: {request.session_id}")
        
        n_turns = config.wm_max_turns if request.force else config.em_distill_every_n_turns
        
        result = pipeline_runner.run_distillation(
            session_id=request.session_id,
            n_turns=n_turns
        )
        
        return {
            "success": result.get("status") == "success",
            "facts_created": result.get("facts_stored", 0),
            "result": result,
            "pipeline_type": "zenml"
        }
        
    except Exception as e:
        logger.error(f"ZenML distillation pipeline failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/pipelines/promote")
async def run_promotion_pipeline_endpoint(request: MemoryPromoteRequest):
    """
    Run memory promotion via ZenML pipeline.
    
    Provides MLOps benefits:
    - Experiment with different promotion thresholds
    - Track promotion rates over time
    - A/B test criteria changes
    - Full lineage tracking (EM scan → filter → promote → SM)
    """
    if not ZENML_PIPELINES_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="ZenML pipelines not available. Use /memory/promote instead."
        )
    
    if not config.enable_memory_system or not config.enable_sm_promotion:
        raise HTTPException(status_code=503, detail="Memory promotion is disabled")
    
    try:
        logger.info("Running ZenML promotion pipeline")
        
        result = pipeline_runner.run_promotion()
        
        return {
            "success": result.get("status") == "success",
            "promoted": result.get("promoted", 0),
            "found": result.get("found_candidates", 0),
            "result": result,
            "pipeline_type": "zenml"
        }
        
    except Exception as e:
        logger.error(f"ZenML promotion pipeline failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/pipelines/status")
async def get_pipelines_status():
    """
    Get status of ZenML pipelines integration.
    
    Returns whether ZenML is available and configured.
    """
    return {
        "zenml_available": ZENML_PIPELINES_AVAILABLE,
        "pipelines": {
            "ingestion": ZENML_PIPELINES_AVAILABLE,
            "distillation": ZENML_PIPELINES_AVAILABLE,
            "promotion": ZENML_PIPELINES_AVAILABLE
        },
        "endpoints": {
            "ingest": "/pipelines/ingest",
            "distill": "/pipelines/distill",
            "promote": "/pipelines/promote"
        } if ZENML_PIPELINES_AVAILABLE else {}
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
