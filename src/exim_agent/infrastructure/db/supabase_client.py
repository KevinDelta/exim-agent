"""Supabase client for compliance data storage."""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import hashlib
from supabase import create_client, Client
from exim_agent.config import config

logger = logging.getLogger(__name__)


class SupabaseClient:
    """Simple Supabase client for compliance data operations."""
    
    def __init__(self):
        """Initialize Supabase client."""
        if not config.supabase_url:
            logger.warning("Supabase not configured - compliance data will not be stored")
            self._client = None
        else:
            # Use service_role key for backend operations (bypasses RLS)
            # Falls back to anon_key if service key not available
            api_key = config.supabase_service_key or config.supabase_anon_key
            
            if not api_key:
                logger.warning("No Supabase API key configured")
                self._client = None
            else:
                self._client: Client = create_client(
                    config.supabase_url, 
                    api_key
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

    def store_memory_analytics(
        self,
        user_id: str,
        analysis: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Persist memory analytics snapshot for historical tracking."""
        if not self._client:
            logger.warning("Supabase client not available - skipping memory analytics storage")
            return None

        try:
            record = {
                "user_id": user_id,
                "total_memories": analysis["stats"].get("total_memories", 0),
                "avg_memory_length": analysis["stats"].get("avg_memory_length", 0.0),
                "memory_types": analysis["stats"].get("memory_types", {}),
                "insights": analysis.get("insights", []),
                "recommendations": analysis.get("recommendations", []),
                "analyzed_at": analysis.get("analyzed_at") or datetime.utcnow().isoformat()
            }

            result = self._client.table("memory_analytics").insert(record).execute()
            logger.info(f"Stored memory analytics snapshot for user {user_id}")
            return result.data[0] if result.data else None

        except Exception as e:
            logger.error(f"Failed to store memory analytics: {e}")
            return None

    def get_memory_analytics(
        self,
        user_id: str,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """Retrieve recent memory analytics snapshots for a user."""
        if not self._client:
            logger.warning("Supabase client not available - returning empty analytics list")
            return []

        try:
            result = (
                self._client
                .table("memory_analytics")
                .select("*")
                .eq("user_id", user_id)
                .order("analyzed_at", desc=True)
                .limit(limit)
                .execute()
            )
            return result.data

        except Exception as e:
            logger.error(f"Failed to retrieve memory analytics: {e}")
            return []

    def get_client_portfolio(
        self,
        client_id: str,
        active_only: bool = True
    ) -> List[Dict[str, str]]:
        """
        Retrieve client's SKU+Lane portfolio from database.
        
        Args:
            client_id: Client identifier
            active_only: Only return active SKU+Lane combinations (default True)
            
        Returns:
            List of {sku_id, lane_id, hts_code} dicts
        """
        if not self._client:
            logger.warning("Supabase client not available - returning empty portfolio")
            return []
        
        try:
            query = self._client.table("client_portfolios").select("sku_id, lane_id, hts_code").eq("client_id", client_id)
            
            if active_only:
                query = query.eq("active", True)
            
            result = query.order("sku_id").execute()
            
            logger.info(f"Retrieved {len(result.data)} SKU+Lane combinations for client {client_id}")
            return result.data
            
        except Exception as e:
            logger.error(f"Failed to retrieve client portfolio: {e}")
            return []

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

    # Crawling-specific methods

    def store_crawled_compliance_data(
        self,
        source_type: str,
        source_id: str,
        data: Dict[str, Any],
        crawl_metadata: Dict[str, Any],
        source_url: str
    ) -> bool:
        """
        Store crawled compliance data with comprehensive metadata and source attribution.
        
        Args:
            source_type: Type of data source ('hts', 'sanctions', 'refusals', 'rulings')
            source_id: Unique identifier for the data
            data: The actual compliance data
            crawl_metadata: Crawling metadata including source attribution, confidence, etc.
            source_url: Original URL where content was crawled from
            
        Returns:
            True if successful, False otherwise
        """
        if not self._client:
            logger.warning("Supabase client not available - skipping crawled data storage")
            return False
        
        try:
            # Generate content hash for change detection
            content_hash = self._generate_content_hash(data)
            
            # Enhanced crawl metadata with source attribution
            enhanced_metadata = {
                **crawl_metadata,
                'source_url': source_url,
                'source_attribution': f"Crawled from {source_url}",
                'stored_at': datetime.utcnow().isoformat()
            }
            
            # Check if content already exists and has changed
            existing = self.get_compliance_data(source_type, source_id)
            change_detected = True
            
            if existing:
                existing_record = existing[0]
                existing_hash = existing_record.get('content_hash')
                change_detected = existing_hash != content_hash
            
            # Store with crawling-specific fields
            result = self._client.table('compliance_data').upsert({
                'source_type': source_type,
                'source_id': source_id,
                'data': data,
                'crawl_metadata': enhanced_metadata,
                'content_hash': content_hash,
                'last_crawled_at': datetime.utcnow().isoformat(),
                'change_detected': change_detected
            }).execute()
            
            # Log the crawling operation
            self._log_crawling_operation(
                source_url=source_url,
                source_type=source_type,
                operation_type='store',
                status='success',
                metadata={
                    'source_id': source_id,
                    'content_hash': content_hash,
                    'change_detected': change_detected,
                    'extraction_confidence': crawl_metadata.get('extraction_confidence', 0.0)
                }
            )
            
            logger.info(f"Stored crawled {source_type} data for {source_id} (change_detected: {change_detected})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store crawled compliance data: {e}")
            
            # Log the error
            self._log_crawling_operation(
                source_url=source_url,
                source_type=source_type,
                operation_type='store',
                status='failure',
                error_message=str(e)
            )
            return False

    def get_crawled_content_by_hash(self, content_hash: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve compliance data by content hash for deduplication.
        
        Args:
            content_hash: SHA-256 hash of the content
            
        Returns:
            Compliance data record or None if not found
        """
        if not self._client:
            logger.warning("Supabase client not available - returning None")
            return None
        
        try:
            result = self._client.table('compliance_data').select('*').eq('content_hash', content_hash).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to retrieve content by hash: {e}")
            return None

    def get_content_changes_since(
        self,
        since: datetime,
        source_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve content that has changed since a specific timestamp.
        
        Args:
            since: Timestamp to check changes since
            source_type: Optional filter by source type
            
        Returns:
            List of changed compliance data records
        """
        if not self._client:
            logger.warning("Supabase client not available - returning empty list")
            return []
        
        try:
            query = (
                self._client.table('compliance_data')
                .select('*')
                .eq('change_detected', True)
                .gte('last_crawled_at', since.isoformat())
            )
            
            if source_type:
                query = query.eq('source_type', source_type)
            
            result = query.order('last_crawled_at', desc=True).execute()
            return result.data
        except Exception as e:
            logger.error(f"Failed to retrieve content changes: {e}")
            return []

    def get_content_versions(
        self,
        source_type: str,
        source_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Retrieve version history for specific compliance content.
        
        Args:
            source_type: Type of data source
            source_id: Unique identifier for the data
            limit: Maximum number of versions to return
            
        Returns:
            List of content versions ordered by version number (newest first)
        """
        if not self._client:
            logger.warning("Supabase client not available - returning empty list")
            return []
        
        try:
            # First get the compliance_data record
            compliance_result = (
                self._client.table('compliance_data')
                .select('id')
                .eq('source_type', source_type)
                .eq('source_id', source_id)
                .execute()
            )
            
            if not compliance_result.data:
                return []
            
            compliance_id = compliance_result.data[0]['id']
            
            # Get version history
            versions_result = (
                self._client.table('compliance_content_versions')
                .select('*')
                .eq('compliance_data_id', compliance_id)
                .order('version_number', desc=True)
                .limit(limit)
                .execute()
            )
            
            return versions_result.data
        except Exception as e:
            logger.error(f"Failed to retrieve content versions: {e}")
            return []

    def get_source_attribution(
        self,
        source_type: str,
        source_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve source attribution and lineage information for compliance content.
        
        Args:
            source_type: Type of data source
            source_id: Unique identifier for the data
            
        Returns:
            Source attribution metadata or None if not found
        """
        if not self._client:
            logger.warning("Supabase client not available - returning None")
            return None
        
        try:
            result = (
                self._client.table('compliance_data')
                .select('crawl_metadata, content_hash, last_crawled_at, created_at, updated_at')
                .eq('source_type', source_type)
                .eq('source_id', source_id)
                .execute()
            )
            
            if not result.data:
                return None
            
            record = result.data[0]
            crawl_metadata = record.get('crawl_metadata', {})
            
            return {
                'source_url': crawl_metadata.get('source_url'),
                'source_attribution': crawl_metadata.get('source_attribution'),
                'regulatory_authority': crawl_metadata.get('regulatory_authority'),
                'extraction_method': crawl_metadata.get('extraction_method'),
                'extraction_confidence': crawl_metadata.get('extraction_confidence'),
                'content_hash': record.get('content_hash'),
                'last_crawled_at': record.get('last_crawled_at'),
                'first_stored_at': record.get('created_at'),
                'last_updated_at': record.get('updated_at')
            }
        except Exception as e:
            logger.error(f"Failed to retrieve source attribution: {e}")
            return None

    def get_crawling_audit_log(
        self,
        source_type: Optional[str] = None,
        status: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Retrieve crawling audit log entries for monitoring and troubleshooting.
        
        Args:
            source_type: Optional filter by source type
            status: Optional filter by operation status
            since: Optional filter by timestamp
            limit: Maximum number of entries to return
            
        Returns:
            List of audit log entries
        """
        if not self._client:
            logger.warning("Supabase client not available - returning empty list")
            return []
        
        try:
            query = self._client.table('crawling_audit_log').select('*')
            
            if source_type:
                query = query.eq('source_type', source_type)
            
            if status:
                query = query.eq('status', status)
            
            if since:
                query = query.gte('created_at', since.isoformat())
            
            result = query.order('created_at', desc=True).limit(limit).execute()
            return result.data
        except Exception as e:
            logger.error(f"Failed to retrieve crawling audit log: {e}")
            return []

    def _generate_content_hash(self, data: Dict[str, Any]) -> str:
        """Generate SHA-256 hash of content for change detection."""
        import json
        content_str = json.dumps(data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(content_str.encode('utf-8')).hexdigest()

    def _log_crawling_operation(
        self,
        source_url: str,
        source_type: str,
        operation_type: str,
        status: str,
        metadata: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        execution_time_ms: Optional[int] = None
    ) -> bool:
        """Log crawling operation to audit trail."""
        if not self._client:
            return False
        
        try:
            self._client.table('crawling_audit_log').insert({
                'source_url': source_url,
                'source_type': source_type,
                'operation_type': operation_type,
                'status': status,
                'metadata': metadata or {},
                'error_message': error_message,
                'execution_time_ms': execution_time_ms
            }).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to log crawling operation: {e}")
            return False


# Global instance
supabase_client = SupabaseClient()