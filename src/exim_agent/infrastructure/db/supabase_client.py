"""Minimal Supabase client used by the MVP stack."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger
from supabase import Client, create_client

from exim_agent.config import config


class SupabaseClient:
    """Lightweight helper for optional Supabase persistence."""

    def __init__(self) -> None:
        self._client: Optional[Client] = None
        self.is_configured = False

        if not config.supabase_url:
            logger.info("Supabase URL not configured; running in stateless mode")
            return

        api_key = config.supabase_service_key or config.supabase_anon_key
        if not api_key:
            logger.warning("Supabase API key missing; skipping client initialization")
            return

        try:
            self._client = create_client(config.supabase_url, api_key)
            self.is_configured = True
            logger.info("Supabase client initialized")
        except Exception as exc:  # pragma: no cover - SDK level failures
            logger.error("Failed to initialize Supabase client: %s", exc)
            self._client = None

    # ------------------------------------------------------------------
    # Generic compliance data helpers used by HTS/sanctions/rulings tools
    # ------------------------------------------------------------------
    def store_compliance_data(
        self, source_type: str, source_id: str, data: Dict[str, Any]
    ) -> bool:
        if not self._client:
            logger.debug("Supabase unavailable; skipping %s data store", source_type)
            return False

        try:
            (
                self._client.table("compliance_data")
                .upsert(
                    {
                        "source_type": source_type,
                        "source_id": source_id,
                        "data": data,
                    }
                )
                .execute()
            )
            return True
        except Exception as exc:  # pragma: no cover - Supabase failures
            logger.error("Failed to store %s data (%s): %s", source_type, source_id, exc)
            return False

    def get_compliance_data(
        self, source_type: str, source_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        if not self._client:
            return []

        try:
            query = (
                self._client.table("compliance_data")
                .select("*")
                .eq("source_type", source_type)
            )
            if source_id:
                query = query.eq("source_id", source_id)
            return query.execute().data
        except Exception as exc:  # pragma: no cover
            logger.error("Failed to fetch %s data: %s", source_type, exc)
            return []

    # ------------------------------------------------------------------
    # Pulse digests
    # ------------------------------------------------------------------
    def store_weekly_pulse_digest(
        self, client_id: str, digest: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        if not self._client:
            return None

        record = {
            "client_id": client_id,
            "period_start": digest["period_start"],
            "period_end": digest["period_end"],
            "total_changes": digest["summary"]["total_changes"],
            "high_priority_changes": digest["summary"].get("high_priority_changes", 0),
            "medium_priority_changes": digest["summary"].get("medium_priority_changes", 0),
            "low_priority_changes": digest["summary"].get("low_priority_changes", 0),
            "requires_action": digest["requires_action"],
            "status": digest["status"],
            "digest_data": digest,
            "generated_at": digest["generated_at"],
        }

        try:
            result = (
                self._client.table("weekly_pulse_digests")
                .insert(record)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as exc:  # pragma: no cover
            logger.error("Failed to store digest for %s: %s", client_id, exc)
            return None

    def get_weekly_pulse_digests(
        self, client_id: str, limit: int = 10, requires_action_only: bool = False
    ) -> List[Dict[str, Any]]:
        if not self._client:
            return []

        try:
            query = (
                self._client.table("weekly_pulse_digests")
                .select("*")
                .eq("client_id", client_id)
            )
            if requires_action_only:
                query = query.eq("requires_action", True)
            result = query.order("period_end", desc=True).limit(limit).execute()
            return result.data
        except Exception as exc:  # pragma: no cover
            logger.error("Failed to retrieve digests for %s: %s", client_id, exc)
            return []

    def get_latest_digest(self, client_id: str) -> Optional[Dict[str, Any]]:
        digests = self.get_weekly_pulse_digests(client_id, limit=1)
        return digests[0] if digests else None

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------
    def get_client_portfolio(
        self, client_id: str, active_only: bool = True
    ) -> List[Dict[str, str]]:
        if not self._client:
            return []

        try:
            query = (
                self._client.table("client_portfolios")
                .select("sku_id, lane_id, hts_code")
                .eq("client_id", client_id)
            )
            if active_only:
                query = query.eq("active", True)
            result = query.order("sku_id").execute()
            return result.data
        except Exception as exc:  # pragma: no cover
            logger.error("Failed to fetch portfolio for %s: %s", client_id, exc)
            return []

    def health_check(self) -> bool:
        if not self._client:
            return False
        try:
            self._client.table("compliance_data").select("id").limit(1).execute()
            return True
        except Exception:  # pragma: no cover
            return False


supabase_client = SupabaseClient()


__all__ = ["supabase_client", "SupabaseClient"]

