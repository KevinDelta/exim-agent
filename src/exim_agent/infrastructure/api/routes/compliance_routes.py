"""Compliance Pulse API routes."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from loguru import logger

from exim_agent.application.compliance_service.service import compliance_service
from exim_agent.application.compliance_service.digest_service import (
    generate_digest_for_period,
)
from exim_agent.infrastructure.db.compliance_collections import ComplianceCollections
from exim_agent.infrastructure.db.supabase_client import supabase_client
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


def _serialize_changes(digest: Dict[str, Any]) -> List[Dict[str, Any]]:
    changes = []
    for change in digest.get("top_changes", []):
        sku = "unknown"
        lane = "unknown"
        key = change.get("sku_lane_key", "")
        if ":" in key:
            sku, lane = key.split(":", 1)
        changes.append(
            {
                "sku_id": sku,
                "lane_id": lane,
                "change_type": change.get("change_type", "unknown"),
                "priority": change.get("priority", "low"),
                "description": change.get("description", ""),
                "timestamp": change.get("timestamp", ""),
            }
        )
    return changes


def _build_pulse_response(
    *,
    client_id: str,
    digest: Dict[str, Any],
    period_type: str,
    metadata_extra: Optional[Dict[str, Any]] = None,
) -> WeeklyPulseResponse:
    metadata = {
        "generated_at": digest.get("generated_at"),
        "requires_action": digest.get("requires_action"),
        "status": digest.get("status"),
        "period_type": period_type,
        "source": metadata_extra.pop("source", "on_demand") if metadata_extra else "on_demand",
    }
    if metadata_extra:
        metadata.update(metadata_extra)

    return WeeklyPulseResponse(
        success=True,
        client_id=client_id,
        period_start=digest.get("period_start"),
        period_end=digest.get("period_end"),
        summary=digest.get("summary", {}),
        changes=_serialize_changes(digest),
        metadata=metadata,
        error=None,
    )


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
async def get_weekly_pulse(
    client_id: str,
    limit: int = 1,
    requires_action_only: bool = False,
    use_stored: bool = True,
    persist: bool = False,
) -> WeeklyPulseResponse:
    """Return a weekly digest from storage or generate one on demand."""
    try:
        if use_stored and supabase_client.is_configured:
            digests = supabase_client.get_weekly_pulse_digests(
                client_id=client_id,
                limit=limit,
                requires_action_only=requires_action_only,
            )
            if digests:
                latest = digests[0]
                return _build_pulse_response(
                    client_id=client_id,
                    digest=latest.get("digest_data", {}),
                    period_type="weekly",
                    metadata_extra={
                        "digest_id": latest.get("id"),
                        "total_digests_available": len(digests),
                        "source": "stored",
                    },
                )

        digest = generate_digest_for_period(
            client_id=client_id,
            period_days=7,
            persist=persist and supabase_client.is_configured,
        )
        return _build_pulse_response(
            client_id=client_id,
            digest=digest,
            period_type="weekly",
            metadata_extra={"source": "on_demand"},
        )

    except Exception as exc:
        logger.error(f"Weekly pulse generation failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve weekly pulse: {exc}",
        )


@router.get("/pulse/{client_id}/daily", response_model=WeeklyPulseResponse)
async def get_daily_pulse(
    client_id: str,
    use_stored: bool = True,
    persist: bool = False,
    requires_action_only: bool = False,
) -> WeeklyPulseResponse:
    """Return a daily digest (period_days=1)."""
    try:
        if use_stored and supabase_client.is_configured:
            digests = supabase_client.get_weekly_pulse_digests(
                client_id=client_id,
                limit=10,
                requires_action_only=requires_action_only,
            )
            for stored in digests:
                digest_data = stored.get("digest_data", {})
                period_start = digest_data.get("period_start")
                period_end = digest_data.get("period_end")
                if not (period_start and period_end):
                    continue
                try:
                    start_dt = datetime.fromisoformat(period_start.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(period_end.replace('Z', '+00:00'))
                except ValueError:
                    continue
                if (end_dt - start_dt).days <= 1:
                    return _build_pulse_response(
                        client_id=client_id,
                        digest=digest_data,
                        period_type="daily",
                        metadata_extra={
                            "digest_id": stored.get("id"),
                            "total_digests_available": len(digests),
                            "source": "stored",
                        },
                    )

        digest = generate_digest_for_period(
            client_id=client_id,
            period_days=1,
            persist=persist and supabase_client.is_configured,
        )
        return _build_pulse_response(
            client_id=client_id,
            digest=digest,
            period_type="daily",
            metadata_extra={"source": "on_demand"},
        )

    except Exception as exc:
        logger.error(f"Daily pulse generation failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve daily pulse: {exc}",
        )


@router.get("/pulse/{client_id}/latest", response_model=WeeklyPulseResponse)
async def get_latest_pulse(client_id: str) -> WeeklyPulseResponse:
    """Return the most recent stored digest or generate a fresh weekly one."""
    try:
        if supabase_client.is_configured:
            latest = supabase_client.get_latest_digest(client_id)
            if latest:
                digest_data = latest.get("digest_data", {})
                period_start = digest_data.get("period_start")
                period_end = digest_data.get("period_end")
                period_type = "unknown"
                if period_start and period_end:
                    try:
                        start_dt = datetime.fromisoformat(period_start.replace('Z', '+00:00'))
                        end_dt = datetime.fromisoformat(period_end.replace('Z', '+00:00'))
                        period_type = "daily" if (end_dt - start_dt).days <= 1 else "weekly"
                    except ValueError:
                        period_type = "unknown"
                return _build_pulse_response(
                    client_id=client_id,
                    digest=digest_data,
                    period_type=period_type,
                    metadata_extra={
                        "digest_id": latest.get("id"),
                        "source": "stored",
                    },
                )

        digest = generate_digest_for_period(client_id=client_id, period_days=7)
        return _build_pulse_response(
            client_id=client_id,
            digest=digest,
            period_type="weekly",
            metadata_extra={"source": "on_demand"},
        )

    except Exception as exc:
        logger.error(f"Latest pulse retrieval failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve latest pulse: {exc}",
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
