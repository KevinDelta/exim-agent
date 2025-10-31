"""Compliance Pulse API routes."""

from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, status
from loguru import logger

from exim_agent.application.compliance_service.service import compliance_service
from exim_agent.infrastructure.db.compliance_collections import ComplianceCollections
from exim_agent.infrastructure.api.models import (
    AskRequest,
    AskResponse,
    SnapshotRequest,
    SnapshotResponse,
    WeeklyPulseResponse,
)

router = APIRouter(prefix="/compliance", tags=["compliance"])

# Initialize compliance collections
compliance_collections = ComplianceCollections()


# API Endpoints

@router.post("/snapshot", response_model=SnapshotResponse)
async def generate_snapshot(request: SnapshotRequest) -> SnapshotResponse:
    """
    Generate compliance snapshot for a SKU + Lane combination.
    
    Returns 4 tiles:
    - HTS Classification & Requirements
    - Sanctions Screening
    - Refusal History & Risks
    - Relevant CBP Rulings
    
    Each tile includes risk level, status, and actionable insights.
    """
    try:
        logger.info(f"Snapshot request: {request.client_id}/{request.sku_id}/{request.lane_id}")
        
        # Initialize service if needed
        if compliance_service.graph is None:
            compliance_service.initialize()
        
        # Generate snapshot
        result = compliance_service.snapshot(
            client_id=request.client_id,
            sku_id=request.sku_id,
            lane_id=request.lane_id
        )
        
        # Add metadata
        metadata = {
            "generated_at": datetime.utcnow().isoformat(),
            "client_id": request.client_id,
            "sku_id": request.sku_id,
            "lane_id": request.lane_id
        }
        
        return SnapshotResponse(
            success=result.get("success", False),
            snapshot=result.get("snapshot"),
            citations=result.get("citations"),
            error=result.get("error"),
            metadata=metadata
        )
        
    except Exception as e:
        logger.error(f"Snapshot generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate snapshot: {str(e)}"
        )


@router.get("/pulse/{client_id}/weekly", response_model=WeeklyPulseResponse)
async def get_weekly_pulse(client_id: str) -> WeeklyPulseResponse:
    """
    Get weekly compliance pulse digest for a client.
    
    Returns:
    - Summary of new/changed compliance requirements
    - Delta analysis (what changed this week vs last week)
    - Prioritized action items
    - Trend analysis
    
    This endpoint would typically be called by a scheduled job
    or on-demand for compliance review meetings.
    """
    try:
        logger.info(f"Weekly pulse request for client: {client_id}")
        
        # Calculate period (last 7 days)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)
        
        # TODO: Implement full weekly pulse logic
        # For MVP, return a placeholder response
        # Full implementation would:
        # 1. Query events collection for changes in date range
        # 2. Compare current snapshots vs previous snapshots
        # 3. Rank changes by risk/impact
        # 4. Generate summary insights
        
        summary = {
            "total_sku_lanes": 0,
            "high_priority_changes": 0,
            "medium_priority_changes": 0,
            "low_priority_changes": 0,
            "new_sanctions": 0,
            "new_refusals": 0,
            "policy_updates": 0
        }
        
        changes = [
            {
                "sku_id": "example_sku",
                "lane_id": "example_lane",
                "change_type": "new_ruling",
                "priority": "high",
                "description": "New CBP ruling affects classification",
                "timestamp": datetime.utcnow().isoformat()
            }
        ]
        
        return WeeklyPulseResponse(
            success=True,
            client_id=client_id,
            period_start=start_date.isoformat(),
            period_end=end_date.isoformat(),
            summary=summary,
            changes=changes,
            error=None
        )
        
    except Exception as e:
        logger.error(f"Weekly pulse generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate weekly pulse: {str(e)}"
        )


@router.post("/ask", response_model=AskResponse)
async def ask_compliance_question(request: AskRequest) -> AskResponse:
    """
    Answer compliance questions using RAG.
    
    Queries:
    - HTS notes and requirements
    - CBP rulings database
    - Refusal summaries
    - Policy snippets
    - Client-specific context (via mem0)
    
    Returns natural language answer with citations.
    """
    try:
        logger.info(f"Q&A request from {request.client_id}: {request.question}")
        
        # Initialize service if needed
        if compliance_service.graph is None:
            compliance_service.initialize()
        
        # Process question
        result = compliance_service.ask(
            client_id=request.client_id,
            question=request.question,
            sku_id=request.sku_id,
            lane_id=request.lane_id
        )
        
        return AskResponse(
            success=result.get("success", False),
            answer=result.get("answer"),
            citations=result.get("citations"),
            question=request.question,
            error=result.get("error")
        )
        
    except Exception as e:
        logger.error(f"Q&A request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process question: {str(e)}"
        )


@router.get("/collections/status")
async def get_collections_status():
    """
    Get status of compliance collections.
    
    Returns document counts and collection metadata.
    """
    try:
        # Initialize if needed
        if not compliance_collections._initialized:
            compliance_collections.initialize()
        
        stats = compliance_collections.get_stats()
        
        return {
            "success": True,
            "collections": stats,
            "total_documents": sum(s.get("count", 0) for s in stats.values() if isinstance(s, dict))
        }
        
    except Exception as e:
        logger.error(f"Failed to get collections status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get collections status: {str(e)}"
        )


@router.post("/collections/seed")
async def seed_compliance_data():
    """
    Seed compliance collections with sample data.
    
    Only for development/testing. Should be protected in production.
    """
    try:
        logger.info("Seeding compliance collections...")
        
        # Initialize if needed
        if not compliance_collections._initialized:
            compliance_collections.initialize()
        
        # Seed data
        compliance_collections.seed_sample_data()
        
        # Get updated stats
        stats = compliance_collections.get_stats()
        
        return {
            "success": True,
            "message": "Collections seeded successfully",
            "collections": stats
        }
        
    except Exception as e:
        logger.error(f"Failed to seed collections: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to seed collections: {str(e)}"
        )
