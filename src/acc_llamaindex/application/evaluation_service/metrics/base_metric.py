"""Base metric interface for evaluation."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List


class BaseMetric(ABC):
    """Abstract base class for evaluation metrics."""
    
    @abstractmethod
    async def compute(
        self,
        query: str,
        response: str,
        contexts: List[str],
        ground_truth: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compute the metric.
        
        Args:
            query: The user's question
            response: The generated answer
            contexts: Retrieved context documents
            ground_truth: Optional ground truth answer
            
        Returns:
            Dictionary with metric results:
            {
                "score": float,  # 0.0 to 1.0
                "reason": str,   # Explanation
                "details": dict  # Additional info
            }
        """
        pass
    
    @abstractmethod
    def get_metric_name(self) -> str:
        """Get the metric name."""
        pass
    
    def validate_inputs(
        self,
        query: str,
        response: str,
        contexts: List[str]
    ) -> bool:
        """Validate metric inputs."""
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        if not response or not response.strip():
            raise ValueError("Response cannot be empty")
        if not contexts:
            raise ValueError("Contexts cannot be empty")
        return True
