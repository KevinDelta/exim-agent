"""Compliance service implementation."""

from typing import Dict, Any
from loguru import logger

from .compliance_graph import build_compliance_graph, ComplianceState


class ComplianceService:
    """Service for compliance operations."""
    
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
    
    def snapshot(self, client_id: str, sku_id: str, lane_id: str) -> Dict[str, Any]:
        """
        Generate compliance snapshot for SKU + Lane.
        
        Args:
            client_id: Client identifier
            sku_id: SKU identifier
            lane_id: Lane identifier
        
        Returns:
            SnapshotResponse dict
        """
        if self.graph is None:
            self.initialize()
        
        logger.info(f"Generating snapshot for {client_id}/{sku_id}/{lane_id}")
        
        # Initialize state
        initial_state: ComplianceState = {
            "client_id": client_id,
            "sku_id": sku_id,
            "lane_id": lane_id,
            "client_context": {},
            "sku_metadata": {},
            "hts_results": {},
            "sanctions_results": {},
            "refusals_results": {},
            "rulings_results": {},
            "rag_context": [],
            "snapshot": {},
            "citations": []
        }
        
        # Run graph
        try:
            result = self.graph.invoke(initial_state)
            return {
                "success": True,
                "snapshot": result.get("snapshot", {}),
                "citations": [c.dict() if hasattr(c, 'dict') else c for c in result.get("citations", [])]
            }
        except Exception as e:
            logger.error(f"Error generating snapshot: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def ask(self, client_id: str, question: str, sku_id: str = None, lane_id: str = None) -> Dict[str, Any]:
        """
        Answer compliance question with context.
        
        Args:
            client_id: Client identifier
            question: Natural language question
            sku_id: Optional SKU context
            lane_id: Optional lane context
        
        Returns:
            Answer with citations
        """
        logger.info(f"Answering question for {client_id}: {question}")
        
        # Mock implementation - in production, use LLM with RAG
        return {
            "success": True,
            "answer": "This is a mock answer. In production, this would use LLM with compliance context.",
            "citations": []
        }


# Global service instance
compliance_service = ComplianceService()
