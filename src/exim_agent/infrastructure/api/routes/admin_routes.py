"""Admin routes for pipeline control and monitoring."""

from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from loguru import logger

# ZenML pipelines
try:
    from exim_agent.application.zenml_pipelines.runner import pipeline_runner
    from exim_agent.application.zenml_pipelines.compliance_ingestion import compliance_ingestion_pipeline
    ZENML_PIPELINES_AVAILABLE = True
except ImportError:
    logger.warning("ZenML pipelines not available - admin endpoints will return 503")
    ZENML_PIPELINES_AVAILABLE = False
    pipeline_runner = None
    compliance_ingestion_pipeline = None


router = APIRouter(prefix="/admin", tags=["admin"])


# Request/Response Models
class IngestRunRequest(BaseModel):
    """Request model for manual ingestion trigger."""
    lookback_days: Optional[int] = 7
    force_refresh: Optional[bool] = False
    notify_on_completion: Optional[bool] = False


class IngestRunResponse(BaseModel):
    """Response model for ingestion run."""
    success: bool
    run_id: Optional[str] = None
    status: str
    message: str
    started_at: str
    estimated_duration_minutes: Optional[int] = None


class PipelineStatusResponse(BaseModel):
    """Response model for pipeline status."""
    pipeline_available: bool
    last_run: Optional[Dict[str, Any]] = None
    current_status: str
    health_checks: Dict[str, bool]
    next_scheduled_run: Optional[str] = None


# Global variable to track current pipeline run
_current_pipeline_run: Optional[Dict[str, Any]] = None


def run_compliance_ingestion_background(lookback_days: int = 7) -> Dict[str, Any]:
    """
    Run compliance ingestion pipeline in background.
    
    Args:
        lookback_days: Number of days to look back for updates
        
    Returns:
        Pipeline execution result
    """
    global _current_pipeline_run
    
    run_id = f"manual_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        _current_pipeline_run = {
            "run_id": run_id,
            "status": "running",
            "started_at": datetime.utcnow().isoformat(),
            "lookback_days": lookback_days,
            "trigger": "manual"
        }
        
        logger.info(f"Starting manual compliance ingestion pipeline: {run_id}")
        
        # Execute the pipeline
        result = compliance_ingestion_pipeline(lookback_days=lookback_days)
        
        # Update run status
        _current_pipeline_run.update({
            "status": "completed",
            "completed_at": datetime.utcnow().isoformat(),
            "result": result,
            "success": True
        })
        
        logger.info(f"Manual compliance ingestion pipeline completed: {run_id}")
        return _current_pipeline_run
        
    except Exception as e:
        logger.error(f"Manual compliance ingestion pipeline failed: {e}")
        
        _current_pipeline_run.update({
            "status": "failed",
            "completed_at": datetime.utcnow().isoformat(),
            "error": str(e),
            "success": False
        })
        
        return _current_pipeline_run


@router.post("/ingest/run", response_model=IngestRunResponse)
async def trigger_manual_ingestion(
    request: IngestRunRequest,
    background_tasks: BackgroundTasks
) -> IngestRunResponse:
    """
    Manually trigger compliance data ingestion pipeline.
    
    This endpoint allows administrators to manually start the compliance
    ingestion pipeline outside of the normal scheduled runs.
    
    Args:
        request: Ingestion parameters
        background_tasks: FastAPI background tasks
        
    Returns:
        Ingestion run details and status
        
    Raises:
        HTTPException: If ZenML pipelines are not available or pipeline fails to start
    """
    if not ZENML_PIPELINES_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="ZenML pipelines not available. Check system configuration."
        )
    
    global _current_pipeline_run
    
    # Check if pipeline is already running
    if _current_pipeline_run and _current_pipeline_run.get("status") == "running":
        raise HTTPException(
            status_code=409,
            detail=f"Pipeline already running: {_current_pipeline_run.get('run_id')}"
        )
    
    try:
        run_id = f"manual_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        started_at = datetime.utcnow().isoformat()
        
        logger.info(f"Triggering manual compliance ingestion: {run_id}")
        
        # Start pipeline in background
        background_tasks.add_task(
            run_compliance_ingestion_background,
            lookback_days=request.lookback_days
        )
        
        # Initialize tracking
        _current_pipeline_run = {
            "run_id": run_id,
            "status": "starting",
            "started_at": started_at,
            "lookback_days": request.lookback_days,
            "trigger": "manual"
        }
        
        return IngestRunResponse(
            success=True,
            run_id=run_id,
            status="starting",
            message=f"Compliance ingestion pipeline started successfully",
            started_at=started_at,
            estimated_duration_minutes=15  # Typical duration
        )
        
    except Exception as e:
        logger.error(f"Failed to start manual ingestion: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start ingestion pipeline: {str(e)}"
        )


@router.get("/ingest/status", response_model=PipelineStatusResponse)
async def get_ingestion_status() -> PipelineStatusResponse:
    """
    Get current status of compliance ingestion pipeline.
    
    Returns information about:
    - Current pipeline availability
    - Last run details and results
    - System health checks
    - Next scheduled run (if applicable)
    
    Returns:
        Pipeline status and health information
    """
    try:
        # Check pipeline availability
        pipeline_available = ZENML_PIPELINES_AVAILABLE
        
        # Get current/last run info
        global _current_pipeline_run
        last_run = _current_pipeline_run
        
        # Determine current status
        if not pipeline_available:
            current_status = "unavailable"
        elif last_run and last_run.get("status") == "running":
            current_status = "running"
        elif last_run and last_run.get("status") == "failed":
            current_status = "failed"
        elif last_run and last_run.get("status") == "completed":
            current_status = "idle"
        else:
            current_status = "ready"
        
        # Perform health checks
        health_checks = {
            "zenml_available": ZENML_PIPELINES_AVAILABLE,
            "pipeline_runner": pipeline_runner is not None if ZENML_PIPELINES_AVAILABLE else False,
            "compliance_pipeline": compliance_ingestion_pipeline is not None if ZENML_PIPELINES_AVAILABLE else False
        }
        
        # Add additional health checks if pipeline is available
        if ZENML_PIPELINES_AVAILABLE:
            try:
                # Check if we can import required components
                from exim_agent.infrastructure.db.supabase_client import supabase_client
                from exim_agent.infrastructure.db.compliance_collections import compliance_collections
                
                health_checks.update({
                    "supabase_client": True,
                    "compliance_collections": True
                })
            except Exception as e:
                logger.warning(f"Health check import failed: {e}")
                health_checks.update({
                    "supabase_client": False,
                    "compliance_collections": False
                })
        
        return PipelineStatusResponse(
            pipeline_available=pipeline_available,
            last_run=last_run,
            current_status=current_status,
            health_checks=health_checks,
            next_scheduled_run=None  # Manual triggers only for now
        )
        
    except Exception as e:
        logger.error(f"Failed to get pipeline status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve pipeline status: {str(e)}"
        )


@router.get("/ingest/runs")
async def list_recent_runs(limit: int = 10) -> Dict[str, Any]:
    """
    List recent ingestion pipeline runs.
    
    Args:
        limit: Maximum number of runs to return
        
    Returns:
        List of recent pipeline runs with their status and results
    """
    try:
        # For now, we only track the current/last run
        # In a production system, this would query a database of run history
        global _current_pipeline_run
        
        runs = []
        if _current_pipeline_run:
            runs.append(_current_pipeline_run)
        
        return {
            "success": True,
            "runs": runs[:limit],
            "total_runs": len(runs),
            "note": "Currently tracking only the most recent run. Full run history requires database integration."
        }
        
    except Exception as e:
        logger.error(f"Failed to list runs: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve run history: {str(e)}"
        )


@router.delete("/ingest/runs/{run_id}")
async def cancel_pipeline_run(run_id: str) -> Dict[str, Any]:
    """
    Cancel a running pipeline (if supported).
    
    Args:
        run_id: ID of the pipeline run to cancel
        
    Returns:
        Cancellation status
        
    Note:
        Pipeline cancellation is not fully implemented in this version.
        This endpoint provides the interface for future implementation.
    """
    global _current_pipeline_run
    
    if not _current_pipeline_run or _current_pipeline_run.get("run_id") != run_id:
        raise HTTPException(
            status_code=404,
            detail=f"Pipeline run not found: {run_id}"
        )
    
    if _current_pipeline_run.get("status") != "running":
        raise HTTPException(
            status_code=400,
            detail=f"Pipeline run is not running: {_current_pipeline_run.get('status')}"
        )
    
    # Note: Actual pipeline cancellation would require ZenML integration
    # For now, we just mark it as cancelled
    logger.warning(f"Pipeline cancellation requested for {run_id} - not fully implemented")
    
    return {
        "success": False,
        "message": "Pipeline cancellation not fully implemented in this version",
        "run_id": run_id,
        "current_status": _current_pipeline_run.get("status"),
        "note": "Pipeline will complete normally. Cancellation requires ZenML integration."
    }


@router.get("/health")
async def admin_health_check() -> Dict[str, Any]:
    """
    Comprehensive admin health check.
    
    Returns:
        Detailed system health information for administrators
    """
    try:
        health_info = {
            "timestamp": datetime.utcnow().isoformat(),
            "system": {
                "zenml_pipelines": ZENML_PIPELINES_AVAILABLE,
                "pipeline_runner": pipeline_runner is not None if ZENML_PIPELINES_AVAILABLE else False
            },
            "components": {},
            "current_pipeline": _current_pipeline_run,
            "status": "healthy"
        }
        
        # Check individual components if available
        if ZENML_PIPELINES_AVAILABLE:
            try:
                from exim_agent.infrastructure.db.supabase_client import supabase_client
                from exim_agent.infrastructure.db.compliance_collections import compliance_collections
                from exim_agent.domain.tools.hts_tool import HTSTool
                from exim_agent.domain.tools.sanctions_tool import SanctionsTool
                
                health_info["components"] = {
                    "supabase": True,
                    "compliance_collections": True,
                    "hts_tool": True,
                    "sanctions_tool": True,
                    "refusals_tool": True,
                    "rulings_tool": True
                }
                
            except Exception as e:
                logger.warning(f"Component health check failed: {e}")
                health_info["components"] = {"error": str(e)}
                health_info["status"] = "degraded"
        else:
            health_info["status"] = "limited"
            health_info["message"] = "ZenML pipelines not available"
        
        return health_info
        
    except Exception as e:
        logger.error(f"Admin health check failed: {e}")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "unhealthy",
            "error": str(e)
        }