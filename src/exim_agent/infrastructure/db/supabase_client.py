"""Supabase client for compliance data storage."""

from typing import Dict, Any, List, Optional
import logging
from supabase import create_client, Client
from src.exim_agent.config import config

logger = logging.getLogger(__name__)


class SupabaseClient:
    """Simple Supabase client for compliance data operations."""
    
    def __init__(self):
        """Initialize Supabase client."""
        if not config.supabase_url or not config.supabase_anon_key:
            logger.warning("Supabase not configured - compliance data will not be stored")
            self._client = None
        else:
            self._client: Client = create_client(
                config.supabase_url, 
                config.supabase_anon_key
            )
    
    def store_compliance_data(
        self, 
        source_type: str, 
        source_id: str, 
        data: Dict[str, Any]
    ) -> bool:
        """
        Store compliance data in Supabase.
        
        Args:
            source_type: Type of data source ('hts', 'sanctions', 'refusals', 'rulings')
            source_id: Unique identifier for the data (hts_code, entity_name, etc.)
            data: The actual compliance data
            
        Returns:
            True if successful, False otherwise
        """
        if not self._client:
            logger.warning("Supabase client not available - skipping data storage")
            return False
            
        try:
            result = self._client.table('compliance_data').upsert({
                'source_type': source_type,
                'source_id': source_id,
                'data': data
            }).execute()
            
            logger.info(f"Stored {source_type} data for {source_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store compliance data: {e}")
            return False
    
    def get_compliance_data(
        self, 
        source_type: str, 
        source_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve compliance data from Supabase.
        
        Args:
            source_type: Type of data source to retrieve
            source_id: Optional specific source ID to retrieve
            
        Returns:
            List of compliance data records
        """
        if not self._client:
            logger.warning("Supabase client not available - returning empty list")
            return []
            
        try:
            query = self._client.table('compliance_data').select('*').eq('source_type', source_type)
            
            if source_id:
                query = query.eq('source_id', source_id)
                
            result = query.execute()
            return result.data
            
        except Exception as e:
            logger.error(f"Failed to retrieve compliance data: {e}")
            return []
    
    def store_weekly_pulse_digest(
        self,
        client_id: str,
        digest: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Store weekly pulse digest in Supabase.
        
        Args:
            client_id: Client identifier
            digest: Weekly pulse digest data
            
        Returns:
            Inserted record with ID, or None if failed
        """
        if not self._client:
            logger.warning("Supabase client not available - skipping digest storage")
            return None
            
        try:
            digest_record = {
                "client_id": client_id,
                "period_start": digest["period_start"],
                "period_end": digest["period_end"],
                "total_changes": digest["summary"]["total_changes"],
                "high_priority_changes": digest["summary"]["high_priority_changes"],
                "medium_priority_changes": digest["summary"].get("medium_priority_changes", 0),
                "low_priority_changes": digest["summary"].get("low_priority_changes", 0),
                "requires_action": digest["requires_action"],
                "status": digest["status"],
                "digest_data": digest,  # Full JSON
                "generated_at": digest["generated_at"]
            }
            
            result = self._client.table("weekly_pulse_digests").insert(
                digest_record
            ).execute()
            
            logger.info(f"Stored weekly pulse digest for {client_id}, period ending {digest['period_end']}")
            return result.data[0] if result.data else None
            
        except Exception as e:
            logger.error(f"Failed to store weekly pulse digest: {e}")
            return None
    
    def get_weekly_pulse_digests(
        self,
        client_id: str,
        limit: int = 10,
        requires_action_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Retrieve weekly pulse digests for a client.
        
        Args:
            client_id: Client identifier
            limit: Maximum number of digests to return
            requires_action_only: Only return digests requiring action
            
        Returns:
            List of digest records
        """
        if not self._client:
            logger.warning("Supabase client not available - returning empty list")
            return []
            
        try:
            query = self._client.table("weekly_pulse_digests").select("*").eq("client_id", client_id)
            
            if requires_action_only:
                query = query.eq("requires_action", True)
            
            result = query.order("period_end", desc=True).limit(limit).execute()
            return result.data
            
        except Exception as e:
            logger.error(f"Failed to retrieve weekly pulse digests: {e}")
            return []
    
    def get_latest_digest(
        self,
        client_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get the most recent weekly pulse digest for a client.
        
        Args:
            client_id: Client identifier
            
        Returns:
            Latest digest record or None
        """
        digests = self.get_weekly_pulse_digests(client_id, limit=1)
        return digests[0] if digests else None
    
    def health_check(self) -> bool:
        """Check if Supabase connection is healthy."""
        if not self._client:
            return False
            
        try:
            # Simple query to test connection
            result = self._client.table('compliance_data').select('id').limit(1).execute()
            return True
        except Exception as e:
            logger.error(f"Supabase health check failed: {e}")
            return False


# Global instance
supabase_client = SupabaseClient()