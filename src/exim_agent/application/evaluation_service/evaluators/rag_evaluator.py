"""RAG evaluator for single query evaluation."""

from typing import Dict, Any, List, Optional
from loguru import logger
import asyncio

from ..metrics.faithfulness import FaithfulnessMetric
from ..metrics.relevance import AnswerRelevanceMetric
from ..metrics.context_precision import ContextPrecisionMetric


class RAGEvaluator:
    """Evaluator for RAG system responses."""
    
    def __init__(self):
        """Initialize RAG evaluator with metrics."""
        self.metrics = {
            "faithfulness": FaithfulnessMetric(),
            "answer_relevance": AnswerRelevanceMetric(),
            "context_precision": ContextPrecisionMetric(),
        }
        logger.info("RAGEvaluator initialized with metrics")
    
    async def evaluate(
        self,
        query: str,
        response: str,
        contexts: List[str],
        ground_truth: Optional[str] = None,
        metrics_to_compute: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate a RAG response.
        
        Args:
            query: User question
            response: Generated answer
            contexts: Retrieved context documents
            ground_truth: Optional ground truth answer
            metrics_to_compute: List of metric names (default: all)
            
        Returns:
            Dictionary with evaluation results
        """
        if metrics_to_compute is None:
            metrics_to_compute = list(self.metrics.keys())
        
        results = {
            "query": query,
            "response": response,
            "num_contexts": len(contexts),
            "metrics": {},
            "overall_score": 0.0
        }
        
        # Compute metrics in parallel
        tasks = []
        metric_names = []
        
        for metric_name in metrics_to_compute:
            if metric_name not in self.metrics:
                logger.warning(f"Unknown metric: {metric_name}")
                continue
            
            metric = self.metrics[metric_name]
            task = metric.compute(
                query=query,
                response=response,
                contexts=contexts,
                ground_truth=ground_truth
            )
            tasks.append(task)
            metric_names.append(metric_name)
        
        # Execute all metrics in parallel
        try:
            metric_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            scores = []
            for metric_name, metric_result in zip(metric_names, metric_results):
                if isinstance(metric_result, Exception):
                    logger.error(f"Failed to compute {metric_name}: {metric_result}")
                    results["metrics"][metric_name] = {
                        "score": 0.0,
                        "reason": f"Error: {str(metric_result)}",
                        "details": {}
                    }
                else:
                    results["metrics"][metric_name] = metric_result
                    scores.append(metric_result["score"])
                    
                    logger.info(
                        f"{metric_name}: {metric_result['score']:.3f} - {metric_result['reason']}"
                    )
            
            # Calculate overall score
            if scores:
                results["overall_score"] = sum(scores) / len(scores)
            
        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            results["error"] = str(e)
        
        return results
    
    def get_available_metrics(self) -> List[str]:
        """Get list of available metrics."""
        return list(self.metrics.keys())
