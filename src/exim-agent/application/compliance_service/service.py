"""Simple compliance service implementation for MVP."""

from typing import Dict, Any
from loguru import logger

from .compliance_graph import build_compliance_graph, ComplianceState


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
    
    def snapshot(self, client_id: str, sku_id: str, lane_id: str) -> Dict[str, Any]:
        """
        Generate simple compliance snapshot for SKU + Lane.
        
        Args:
            client_id: Client identifier
            sku_id: SKU identifier
            lane_id: Lane identifier
        
        Returns:
            Simple SnapshotResponse dict
        """
        if self.graph is None:
            self.initialize()
        
        logger.info(f"Generating snapshot for {client_id}/{sku_id}/{lane_id}")
        
        # Initialize simple state
        initial_state: ComplianceState = {
            "client_id": client_id,
            "sku_id": sku_id,
            "lane_id": lane_id,
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
            
            return {
                "success": True,
                "snapshot": result.get("snapshot", {}),
                "citations": [c.model_dump() if hasattr(c, 'model_dump') else c for c in result.get("citations", [])]
            }
            
        except Exception as e:
            logger.error(f"Error generating snapshot: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    

    
    def ask(self, client_id: str, question: str, sku_id: str = None, lane_id: str = None) -> Dict[str, Any]:
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
        initial_state: ComplianceState = {
            "client_id": client_id,
            "sku_id": sku_id or "general",
            "lane_id": lane_id or "general",
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


# Global service instance
compliance_service = ComplianceService()
