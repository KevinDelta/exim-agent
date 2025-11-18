"""On-demand digest generation for daily/weekly compliance pulses."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from loguru import logger

from .service import compliance_service
from ...infrastructure.db.supabase_client import supabase_client

DEFAULT_SKU_LANES: List[Dict[str, str]] = [
    {"sku_id": "SKU-001", "lane_id": "CNSHA-USLAX-ocean", "hts_code": "8517.12.00"},
    {"sku_id": "SKU-002", "lane_id": "CNSHA-USLAX-ocean", "hts_code": "6203.42.40"},
    {"sku_id": "SKU-003", "lane_id": "MXNLD-USTX-truck", "hts_code": "8471.30.01"},
    {"sku_id": "SKU-004", "lane_id": "VNSGN-USLAX-ocean", "hts_code": "9403.60.80"},
    {"sku_id": "SKU-005", "lane_id": "CNSHA-USNYC-ocean", "hts_code": "8528.72.64"},
]


def load_client_sku_lanes(client_id: str) -> List[Dict[str, str]]:
    """Load SKU/lane portfolio for a client, falling back to defaults."""
    try:
        portfolio = supabase_client.get_client_portfolio(client_id)
        if portfolio:
            logger.info(
                "Loaded %s SKU+Lane combinations for client %s from Supabase",
                len(portfolio),
                client_id,
            )
            return portfolio
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.warning("Failed to load portfolio from Supabase: %s", exc)

    logger.info(
        "Using default SKU+Lane combinations for client %s (portfolio unavailable)",
        client_id,
    )
    return DEFAULT_SKU_LANES


def load_previous_snapshots(
    client_id: str,
    sku_lanes: List[Dict[str, str]],
) -> Dict[str, Dict[str, Any]]:
    """MVP placeholder for previous snapshots (returns empty mapping)."""
    logger.info(
        "No snapshot history implemented for %s; treating all lanes as new.", client_id
    )
    return {}


def generate_current_snapshots(
    client_id: str,
    sku_lanes: List[Dict[str, str]],
) -> Dict[str, Dict[str, Any]]:
    """Call the compliance graph to build per-SKU snapshots."""
    if compliance_service.graph is None:
        compliance_service.initialize()

    current_snapshots: Dict[str, Dict[str, Any]] = {}

    for sku_lane in sku_lanes:
        key = f"{sku_lane['sku_id']}:{sku_lane['lane_id']}"
        try:
            result = compliance_service.snapshot(
                client_id=client_id,
                sku_id=sku_lane["sku_id"],
                lane_id=sku_lane["lane_id"],
            )
            if result.get("success"):
                current_snapshots[key] = {
                    "snapshot": result.get("snapshot", {}),
                    "citations": result.get("citations", []),
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                }
            else:
                logger.warning("Snapshot generation failed for %s: %s", key, result)
        except Exception as exc:  # pragma: no cover - external dependency guard
            logger.error("Snapshot generation error for %s: %s", key, exc)

    return current_snapshots


def compute_deltas(
    previous_snapshots: Dict[str, Dict[str, Any]],
    current_snapshots: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Simple change detection between previous and current snapshots."""
    changes: List[Dict[str, Any]] = []

    for key, current in current_snapshots.items():
        previous = previous_snapshots.get(key, {})

        if not previous:
            changes.append(
                {
                    "sku_lane_key": key,
                    "change_type": "new_monitoring",
                    "priority": "medium",
                    "description": "Started monitoring this SKU+Lane combination",
                    "timestamp": current.get("generated_at", datetime.now(timezone.utc).isoformat()),
                }
            )
            continue

        current_tiles = current.get("snapshot", {}).get("tiles", [])
        previous_tiles = previous.get("snapshot", {}).get("tiles", [])

        def _count_by_risk(tiles: List[Dict[str, Any]]) -> Dict[str, int]:
            counts = {"high": 0, "medium": 0, "low": 0}
            for tile in tiles:
                risk = tile.get("risk_level", "low")
                counts[risk] = counts.get(risk, 0) + 1
            return counts

        current_risks = _count_by_risk(current_tiles)
        previous_risks = _count_by_risk(previous_tiles)

        if current_risks["high"] > previous_risks["high"]:
            changes.append(
                {
                    "sku_lane_key": key,
                    "change_type": "risk_escalation",
                    "priority": "high",
                    "description": "New high-risk compliance issue detected",
                    "details": {
                        "high_risk_before": previous_risks["high"],
                        "high_risk_now": current_risks["high"],
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

        if current_risks["medium"] > previous_risks["medium"]:
            changes.append(
                {
                    "sku_lane_key": key,
                    "change_type": "new_requirement",
                    "priority": "medium",
                    "description": "New compliance requirement identified",
                    "details": {
                        "medium_risk_before": previous_risks["medium"],
                        "medium_risk_now": current_risks["medium"],
                    },
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )

    return changes


def rank_by_impact(changes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sort change list using a simple priority heuristic."""
    priority_order = {"high": 3, "medium": 2, "low": 1}
    return sorted(
        changes,
        key=lambda change: priority_order.get(change.get("priority", "low"), 0),
        reverse=True,
    )


def generate_digest(
    client_id: str,
    changes: List[Dict[str, Any]],
    current_snapshots: Dict[str, Dict[str, Any]],
    period_start: str,
    period_end: str,
) -> Dict[str, Any]:
    """Assemble a digest payload."""
    high_priority = [c for c in changes if c.get("priority") == "high"]
    medium_priority = [c for c in changes if c.get("priority") == "medium"]
    low_priority = [c for c in changes if c.get("priority") == "low"]

    change_types: Dict[str, int] = {}
    for change in changes:
        change_type = change.get("change_type", "unknown")
        change_types[change_type] = change_types.get(change_type, 0) + 1

    return {
        "client_id": client_id,
        "period_start": period_start,
        "period_end": period_end,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_sku_lanes": len(current_snapshots),
            "total_changes": len(changes),
            "high_priority_changes": len(high_priority),
            "medium_priority_changes": len(medium_priority),
            "low_priority_changes": len(low_priority),
            "change_types": change_types,
        },
        "top_changes": changes[:10],
        "requires_action": len(high_priority) > 0,
        "status": "action_required" if high_priority else "monitoring",
    }


def save_digest(client_id: str, digest: Dict[str, Any]) -> bool:
    """Persist digest to Supabase when configured."""
    if not supabase_client.is_configured:
        logger.info("Supabase not configured; skipping digest persistence for %s", client_id)
        return False

    try:
        supabase_client.store_weekly_pulse_digest(client_id=client_id, digest=digest)
        logger.info("Persisted digest for %s with period ending %s", client_id, digest["period_end"])
        return True
    except Exception as exc:  # pragma: no cover - Supabase failures
        logger.warning("Failed to persist digest for %s: %s", client_id, exc)
        return False


def generate_digest_for_period(
    client_id: str,
    period_days: int = 7,
    persist: bool = False,
) -> Dict[str, Any]:
    """Public entry point used by API routes for weekly/daily pulses."""
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=period_days)

    sku_lanes = load_client_sku_lanes(client_id)
    previous = load_previous_snapshots(client_id, sku_lanes)
    current = generate_current_snapshots(client_id, sku_lanes)
    changes = rank_by_impact(compute_deltas(previous, current))
    digest = generate_digest(
        client_id=client_id,
        changes=changes,
        current_snapshots=current,
        period_start=start_date.isoformat(),
        period_end=end_date.isoformat(),
    )

    if persist:
        save_digest(client_id, digest)

    return digest


__all__ = [
    "generate_digest_for_period",
    "compute_deltas",
]
