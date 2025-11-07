"""ZenML pipeline for weekly compliance pulse generation."""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from loguru import logger

from zenml import pipeline, step

from exim_agent.application.compliance_service.service import compliance_service
from exim_agent.infrastructure.db.compliance_collections import compliance_collections


@step
def load_client_sku_lanes(
    client_id: str
) -> List[Dict[str, str]]:
    """
    Step 1: Load all SKU+Lane combinations for a client.
    
    In production, this would query a database of client configurations.
    For MVP, returns sample data.
    
    Args:
        client_id: Client identifier
        
    Returns:
        List of {sku_id, lane_id, hts_code} dicts
    """
    logger.info(f"Loading SKU+Lane combinations for client: {client_id}")
    
    # Sample data - in production, would query from database
    sku_lanes = [
        {"sku_id": "SKU-001", "lane_id": "CNSHA-USLAX-ocean", "hts_code": "8517.12.00"},
        {"sku_id": "SKU-002", "lane_id": "CNSHA-USLAX-ocean", "hts_code": "6203.42.40"},
        {"sku_id": "SKU-003", "lane_id": "MXNLD-USTX-truck", "hts_code": "8471.30.01"},
        {"sku_id": "SKU-004", "lane_id": "VNSGN-USLAX-ocean", "hts_code": "9403.60.80"},
        {"sku_id": "SKU-005", "lane_id": "CNSHA-USNYC-ocean", "hts_code": "8528.72.64"},
    ]
    
    logger.info(f"Loaded {len(sku_lanes)} SKU+Lane combinations")
    return sku_lanes


@step
def load_previous_snapshots(
    client_id: str,
    sku_lanes: List[Dict[str, str]]
) -> Dict[str, Dict[str, Any]]:
    """
    Step 2: Load previous week's snapshots from storage.
    
    Args:
        client_id: Client identifier
        sku_lanes: List of SKU+Lane combinations
        
    Returns:
        Dict mapping "sku_id:lane_id" to previous snapshot
    """
    logger.info(f"Loading previous snapshots for {len(sku_lanes)} SKU+Lanes...")
    
    # In production, would query from events collection or snapshot storage
    # For MVP, return empty dict (no previous snapshots)
    previous_snapshots = {}
    
    # Could query events collection for last week's snapshots
    # for sku_lane in sku_lanes:
    #     key = f"{sku_lane['sku_id']}:{sku_lane['lane_id']}"
    #     previous_snapshots[key] = {...}
    
    logger.info(f"Loaded {len(previous_snapshots)} previous snapshots")
    return previous_snapshots


@step
def generate_current_snapshots(
    client_id: str,
    sku_lanes: List[Dict[str, str]]
) -> Dict[str, Dict[str, Any]]:
    """
    Step 3: Generate current snapshots for all SKU+Lanes.
    
    Args:
        client_id: Client identifier
        sku_lanes: List of SKU+Lane combinations
        
    Returns:
        Dict mapping "sku_id:lane_id" to current snapshot
    """
    logger.info(f"Generating current snapshots for {len(sku_lanes)} SKU+Lanes...")
    
    # Initialize service if needed
    if compliance_service.graph is None:
        compliance_service.initialize()
    
    current_snapshots = {}
    
    for sku_lane in sku_lanes:
        sku_id = sku_lane["sku_id"]
        lane_id = sku_lane["lane_id"]
        key = f"{sku_id}:{lane_id}"
        
        try:
            result = compliance_service.snapshot(
                client_id=client_id,
                sku_id=sku_id,
                lane_id=lane_id
            )
            
            if result.get("success"):
                current_snapshots[key] = {
                    "snapshot": result.get("snapshot", {}),
                    "citations": result.get("citations", []),
                    "generated_at": datetime.now().isoformat()
                }
            else:
                logger.warning(f"Failed to generate snapshot for {key}: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"Error generating snapshot for {key}: {e}")
    
    logger.info(f"Generated {len(current_snapshots)} current snapshots")
    return current_snapshots


@step
def compute_deltas(
    previous_snapshots: Dict[str, Dict[str, Any]],
    current_snapshots: Dict[str, Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Step 4: Compute deltas between previous and current snapshots.
    
    Args:
        previous_snapshots: Previous week's snapshots
        current_snapshots: Current snapshots
        
    Returns:
        List of change events with priority
    """
    logger.info("Computing deltas between snapshots...")
    
    changes = []
    
    for key, current in current_snapshots.items():
        previous = previous_snapshots.get(key, {})
        
        # If no previous snapshot, everything is new
        if not previous:
            changes.append({
                "sku_lane_key": key,
                "change_type": "new_monitoring",
                "priority": "medium",
                "description": "Started monitoring this SKU+Lane combination",
                "timestamp": current.get("generated_at", datetime.utcnow().isoformat())
            })
            continue
        
        # Compare snapshots to find changes
        # This is simplified - full implementation would do deep comparison
        current_snapshot = current.get("snapshot", {})
        previous_snapshot = previous.get("snapshot", {})
        
        # Check for tile changes
        current_tiles = current_snapshot.get("tiles", [])
        previous_tiles = previous_snapshot.get("tiles", [])
        
        # Simple comparison: count tiles by risk level
        def count_by_risk(tiles):
            counts = {"high": 0, "medium": 0, "low": 0}
            for tile in tiles:
                risk = tile.get("risk_level", "low")
                counts[risk] = counts.get(risk, 0) + 1
            return counts
        
        current_risks = count_by_risk(current_tiles)
        previous_risks = count_by_risk(previous_tiles)
        
        # Detect risk escalations
        if current_risks["high"] > previous_risks["high"]:
            changes.append({
                "sku_lane_key": key,
                "change_type": "risk_escalation",
                "priority": "high",
                "description": f"New high-risk compliance issue detected",
                "details": {
                    "high_risk_before": previous_risks["high"],
                    "high_risk_now": current_risks["high"]
                },
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # Detect new medium risks
        if current_risks["medium"] > previous_risks["medium"]:
            changes.append({
                "sku_lane_key": key,
                "change_type": "new_requirement",
                "priority": "medium",
                "description": f"New compliance requirement identified",
                "details": {
                    "medium_risk_before": previous_risks["medium"],
                    "medium_risk_now": current_risks["medium"]
                },
                "timestamp": datetime.utcnow().isoformat()
            })
    
    logger.info(f"Computed {len(changes)} changes")
    return changes


@step
def rank_by_impact(
    changes: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Step 5: Rank changes by business impact.
    
    Args:
        changes: List of change events
        
    Returns:
        Ranked list of changes
    """
    logger.info(f"Ranking {len(changes)} changes by impact...")
    
    # Priority order
    priority_order = {"high": 3, "medium": 2, "low": 1}
    
    # Sort by priority
    ranked = sorted(
        changes,
        key=lambda x: priority_order.get(x.get("priority", "low"), 0),
        reverse=True
    )
    
    logger.info("Changes ranked successfully")
    return ranked


@step
def generate_digest(
    client_id: str,
    changes: List[Dict[str, Any]],
    current_snapshots: Dict[str, Dict[str, Any]],
    period_start: str,
    period_end: str
) -> Dict[str, Any]:
    """
    Step 6: Generate weekly pulse digest.
    
    Args:
        client_id: Client identifier
        changes: Ranked list of changes
        current_snapshots: Current snapshots
        period_start: Period start date (ISO format)
        period_end: Period end date (ISO format)
        
    Returns:
        Weekly pulse digest
    """
    logger.info(f"Generating weekly pulse digest for {client_id}...")
    
    # Categorize changes
    high_priority = [c for c in changes if c.get("priority") == "high"]
    medium_priority = [c for c in changes if c.get("priority") == "medium"]
    low_priority = [c for c in changes if c.get("priority") == "low"]
    
    # Count change types
    change_types = {}
    for change in changes:
        change_type = change.get("change_type", "unknown")
        change_types[change_type] = change_types.get(change_type, 0) + 1
    
    digest = {
        "client_id": client_id,
        "period_start": period_start,
        "period_end": period_end,
        "generated_at": datetime.utcnow().isoformat(),
        "summary": {
            "total_sku_lanes": len(current_snapshots),
            "total_changes": len(changes),
            "high_priority_changes": len(high_priority),
            "medium_priority_changes": len(medium_priority),
            "low_priority_changes": len(low_priority),
            "change_types": change_types
        },
        "top_changes": changes[:10],  # Top 10 most important changes
        "requires_action": len(high_priority) > 0,
        "status": "action_required" if len(high_priority) > 0 else "monitoring"
    }
    
    logger.info(f"Generated digest with {len(changes)} total changes")
    return digest


@step
def save_digest(
    client_id: str,
    digest: Dict[str, Any]
) -> bool:
    """
    Step 7: Save digest to Supabase (primary storage) and optionally index in Chroma.
    
    Architecture:
    - Supabase: Primary storage for structured transactional data
    - Chroma: Optional semantic search index for digest summaries
    
    Args:
        client_id: Client identifier
        digest: Weekly pulse digest
        
    Returns:
        True if successful
    """
    logger.info(f"Saving digest for {client_id}...")
    
    try:
        # 1. PRIMARY: Save to Supabase (source of truth for transactional data)
        from exim_agent.infrastructure.db.supabase_client import supabase_client
        
        result = supabase_client.store_weekly_pulse_digest(
            client_id=client_id,
            digest=digest
        )
        
        if not result:
            logger.warning("Failed to save digest to Supabase, but continuing...")
        else:
            logger.info(f"Digest saved to Supabase with ID: {result.get('id')}")
        
        # 2. OPTIONAL: Index summary in Chroma for semantic search
        # Only index if you need to semantically search across digest content
        try:
            summary_text = f"""
Weekly Compliance Pulse for {client_id}
Period: {digest['period_start']} to {digest['period_end']}
Total Changes: {digest['summary']['total_changes']}
High Priority Changes: {digest['summary']['high_priority_changes']}
Medium Priority Changes: {digest['summary'].get('medium_priority_changes', 0)}
Status: {digest['status']}
Requires Action: {'Yes' if digest['requires_action'] else 'No'}

Change Types:
{', '.join(f"{k}: {v}" for k, v in digest['summary'].get('change_types', {}).items())}

Top Changes:
{chr(10).join(f"- {c.get('description', '')} (Priority: {c.get('priority', 'unknown')})" for c in digest.get('top_changes', [])[:5])}
"""
            
            # Index in Chroma for semantic search capabilities
            policy_collection = compliance_collections.get_collection(
                compliance_collections.POLICY
            )
            
            policy_collection.add_texts(
                texts=[summary_text],
                metadatas=[{
                    "doc_type": "weekly_pulse",
                    "client_id": client_id,
                    "digest_id": result.get('id') if result else None,
                    "period_end": digest['period_end'],
                    "requires_action": str(digest['requires_action']),
                    "status": digest['status'],
                    "total_changes": digest['summary']['total_changes'],
                    "source": "weekly_pulse_pipeline",
                    "ingested_at": datetime.utcnow().isoformat()
                }],
                ids=[f"pulse_{client_id}_{digest['period_end']}"]
            )
            
            logger.info("Digest summary indexed in Chroma for semantic search")
            
        except Exception as chroma_error:
            logger.warning(f"Failed to index digest in Chroma (non-critical): {chroma_error}")
        
        logger.info("Digest saved successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to save digest: {e}")
        return False


@pipeline
def weekly_pulse_pipeline(
    client_id: str,
    period_days: int = 7
):
    """
    Weekly compliance pulse generation pipeline.
    
    Steps:
    1. Load client SKU+Lane combinations
    2. Load previous week's snapshots
    3. Generate current snapshots for all SKUs
    4. Compute deltas (what changed)
    5. Rank changes by impact
    6. Generate digest summary
    7. Save digest to storage
    
    Args:
        client_id: Client identifier
        period_days: Number of days in pulse period (default 7)
    """
    # Calculate period
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=period_days)
    period_start = start_date.isoformat()
    period_end = end_date.isoformat()
    
    # Load client configuration
    sku_lanes = load_client_sku_lanes(client_id=client_id)
    
    # Load previous snapshots
    previous_snapshots = load_previous_snapshots(
        client_id=client_id,
        sku_lanes=sku_lanes
    )
    
    # Generate current snapshots
    current_snapshots = generate_current_snapshots(
        client_id=client_id,
        sku_lanes=sku_lanes
    )
    
    # Compute deltas
    changes = compute_deltas(
        previous_snapshots=previous_snapshots,
        current_snapshots=current_snapshots
    )
    
    # Rank by impact
    ranked_changes = rank_by_impact(changes=changes)
    
    # Generate digest
    digest = generate_digest(
        client_id=client_id,
        changes=ranked_changes,
        current_snapshots=current_snapshots,
        period_start=period_start,
        period_end=period_end
    )
    
    # Save digest
    saved = save_digest(
        client_id=client_id,
        digest=digest
    )
    
    return digest
