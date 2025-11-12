"""Simple compliance service implementation for MVP."""

from typing import Dict, Any, Optional
from loguru import logger

from .compliance_graph import build_compliance_graph, ComplianceState
from exim_agent.application.memory_service.mem0_client import mem0_client


class ComplianceService:
    """Simple service for compliance operations MVP."""
    
    def __init__(self):
        """Initialize compliance service."""
        self.graph = None
        logger.info("ComplianceService initialized")
    
    def initialize(self):
        """Initialize the compliance graph."""
        if self.graph is None:
            logger.info("Building compliance graph...")
            self.graph = build_compliance_graph()
            logger.info("Compliance graph built successfully")
    
    def snapshot(self, client_id: str, sku_id: str, lane_id: str, hts_code: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate simple compliance snapshot for SKU + Lane.
        
        Args:
            client_id: Client identifier
            sku_id: SKU identifier
            lane_id: Lane identifier
            hts_code: Optional HTS code
        Returns:
            Simple SnapshotResponse dict
        """
        if self.graph is None:
            self.initialize()
        
        logger.info(f"Generating snapshot for {client_id}/{sku_id}/{lane_id}")

        # Initialize simple state
        normalized_hts = hts_code or "8517.12.00"
        initial_state: ComplianceState = {
            "client_id": client_id,
            "sku_id": sku_id,
            "lane_id": lane_id,
            "hts_code": normalized_hts,
            "question": None,  # Snapshot mode
            "hts_results": {},
            "sanctions_results": {},
            "refusals_results": {},
            "rulings_results": {},
            "rag_context": [],
            "snapshot": {},
            "citations": [],
            "answer": None
        }
        
        # Run graph
        try:
            result = self.graph.invoke(initial_state)
            
            snapshot_data = result.get("snapshot", {})
            
            # Persist snapshot summary to Mem0 for follow-up chat context
            if snapshot_data and mem0_client.is_enabled():
                try:
                    self._persist_snapshot_to_memory(
                        client_id=client_id,
                        sku_id=sku_id,
                        lane_id=lane_id,
                        hts_code=normalized_hts,
                        snapshot=snapshot_data
                    )
                except Exception as mem_error:
                    # Don't fail snapshot generation if memory persistence fails
                    logger.warning(f"Failed to persist snapshot to memory: {mem_error}")
            
            return {
                "success": True,
                "snapshot": snapshot_data,
                "citations": [c.model_dump() if hasattr(c, 'model_dump') else c for c in result.get("citations", [])]
            }
            
        except Exception as e:
            logger.error(f"Error generating snapshot: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    

    
    def ask(self, client_id: str, question: str, sku_id: str = None, lane_id: str = None, hts_code: Optional[str] = None) -> Dict[str, Any]:
        """
        Answer compliance question using simple RAG.
        
        Args:
            client_id: Client identifier
            question: Natural language question
            sku_id: Optional SKU context
            lane_id: Optional lane context
        
        Returns:
            Simple answer with citations
        """
        if self.graph is None:
            self.initialize()
        
        logger.info(f"Processing Q&A for {client_id}: {question}")
        
        # Initialize state for Q&A mode
        normalized_hts = hts_code or "8517.12.00"
        initial_state: ComplianceState = {
            "client_id": client_id,
            "sku_id": sku_id or "general",
            "lane_id": lane_id or "general",
            "hts_code": normalized_hts,
            "question": question,
            "hts_results": {},
            "sanctions_results": {},
            "refusals_results": {},
            "rulings_results": {},
            "rag_context": [],
            "snapshot": {},
            "citations": [],
            "answer": None
        }
        
        try:
            result = self.graph.invoke(initial_state)
            
            return {
                "success": True,
                "answer": result.get("answer", "I apologize, but I couldn't generate an answer."),
                "citations": [c.model_dump() if hasattr(c, 'model_dump') else c for c in result.get("citations", [])],
                "question": question
            }
            
        except Exception as e:
            logger.error(f"Error processing Q&A: {e}")
            return {
                "success": False,
                "error": str(e),
                "question": question
            }
    
    def _persist_snapshot_to_memory(
        self,
        client_id: str,
        sku_id: str,
        lane_id: str,
        hts_code: Optional[str] = None,
        snapshot: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Persist compliance snapshot summary to Mem0 for follow-up chat context.
        
        Creates a concise summary with key entities that can be retrieved
        during subsequent Q&A sessions even without explicit context injection.
        """
        if not snapshot:
            logger.warning("Cannot persist snapshot to memory: snapshot is None")
            return
        
        # Extract key information from snapshot
        risk_level = snapshot.get("overall_risk_level", "unknown")
        alert_count = snapshot.get("active_alerts_count", 0)
        tiles = snapshot.get("tiles", {})
        
        # Build summary of key findings
        findings = []
        
        # HTS Classification
        if hts_tile := tiles.get("hts_classification"):
            hts_headline = hts_tile.get("headline", "")
            findings.append(f"HTS Classification: {hts_headline}")
        
        # Sanctions
        if sanctions_tile := tiles.get("sanctions_screening"):
            sanctions_status = sanctions_tile.get("status", "")
            sanctions_headline = sanctions_tile.get("headline", "")
            if sanctions_status in ["attention", "action"]:
                findings.append(f"⚠️ {sanctions_headline}")
            else:
                findings.append(f"Sanctions: {sanctions_headline}")
        
        # Refusals
        if refusals_tile := tiles.get("refusal_history"):
            refusals_headline = refusals_tile.get("headline", "")
            findings.append(f"Refusal History: {refusals_headline}")
        
        # Rulings
        if rulings_tile := tiles.get("cbp_rulings"):
            rulings_headline = rulings_tile.get("headline", "")
            findings.append(f"Rulings: {rulings_headline}")
        
        # Build summary message
        summary_parts = [
            f"Compliance snapshot generated for client {client_id}",
            f"SKU: {sku_id}",
            f"Lane: {lane_id}",
        ]
        
        if hts_code:
            summary_parts.append(f"HTS Code: {hts_code}")
        
        summary_parts.extend([
            f"Overall Risk Level: {risk_level}",
            f"Active Alerts: {alert_count}",
            "",
            "Key Findings:"
        ])
        summary_parts.extend(findings)
        
        summary = "\n".join(summary_parts)
        
        # Create memory message
        # Format as a system message that provides context for future conversations
        messages = [
            {
                "role": "system",
                "content": f"Compliance analysis completed. {summary}"
            }
        ]
        
        # Add to Mem0 with metadata for filtering
        mem0_client.add(
            messages=messages,
            user_id=client_id,
            session_id=f"compliance-{sku_id}-{lane_id}",
            metadata={
                "type": "compliance_snapshot",
                "client_id": client_id,
                "sku_id": sku_id,
                "lane_id": lane_id,
                "hts_code": hts_code,
                "risk_level": risk_level,
                "alert_count": alert_count,
                "tile_keys": list(tiles.keys())
            }
        )
        
        logger.info(f"Persisted compliance snapshot to memory for {client_id}/{sku_id}/{lane_id}")


# Global service instance
compliance_service = ComplianceService()
