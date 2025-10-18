"""Main evaluation service."""

from typing import Dict, Any, List, Optional
from loguru import logger

from .evaluators.rag_evaluator import RAGEvaluator


class EvaluationService:
    """Service for evaluating RAG responses."""
    
    def __init__(self):
        """Initialize evaluation service."""
        self.evaluator: Optional[RAGEvaluator] = None
        logger.info("EvaluationService initialized")
    
    def initialize(self):
        """Initialize the evaluator."""
        try:
            self.evaluator = RAGEvaluator()
            logger.info("RAGEvaluator initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize evaluator: {e}")
            self.evaluator = None
    
    async def evaluate_response(
        self,
        query: str,
        response: str,
        contexts: List[str],
        ground_truth: Optional[str] = None,
        metrics: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate a single RAG response.
        
        Args:
            query: User question
            response: Generated answer
            contexts: Retrieved context documents
            ground_truth: Optional ground truth answer
            metrics: List of metrics to compute (default: all)
            
        Returns:
            Evaluation results dictionary
        """
        if not self.evaluator:
            logger.warning("Evaluator not initialized")
            return {
                "error": "Evaluator not initialized",
                "metrics": {},
                "overall_score": 0.0
            }
        
        try:
            results = await self.evaluator.evaluate(
                query=query,
                response=response,
                contexts=contexts,
                ground_truth=ground_truth,
                metrics_to_compute=metrics
            )
            return results
            
        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            return {
                "error": str(e),
                "metrics": {},
                "overall_score": 0.0
            }
    
    def get_available_metrics(self) -> List[str]:
        """Get list of available metrics."""
        if self.evaluator:
            return self.evaluator.get_available_metrics()
        return []
    
    def is_enabled(self) -> bool:
        """Check if evaluation is enabled and initialized."""
        return self.evaluator is not None


# Global singleton instance
evaluation_service = EvaluationService()
