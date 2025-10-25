"""Pipeline runner utilities for ZenML pipelines."""

from typing import Dict, Any
from loguru import logger

from acc_llamaindex.application.zenml_pipelines.ingestion_pipeline import run_ingestion_pipeline
from acc_llamaindex.application.zenml_pipelines.memory_analytics_pipeline import memory_analytics_pipeline


class PipelineRunner:
    """
    Simplified pipeline runner for ZenML (Mem0-optimized stack).
    
    Pipelines:
    - Ingestion: Load documents into RAG
    - Memory Analytics: Analyze Mem0 usage patterns
    """
    
    def __init__(self):
        logger.info("PipelineRunner initialized (Mem0-optimized)")
    
    def run_ingestion(
        self,
        directory_path: str | None = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Run document ingestion pipeline.
        
        Args:
            directory_path: Path to documents directory
            **kwargs: Additional pipeline parameters
            
        Returns:
            Pipeline execution results
        """
        logger.info(f"Running ingestion pipeline for: {directory_path}")
        
        try:
            result = run_ingestion_pipeline(
                directory_path=directory_path,
                **kwargs
            )
            logger.info(f"Ingestion pipeline completed: {result.get('status')}")
            return result
            
        except Exception as e:
            logger.error(f"Ingestion pipeline failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def run_memory_analytics(
        self,
        user_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Run memory analytics pipeline.
        
        Analyzes Mem0 memory patterns and generates insights.
        
        Args:
            user_id: User identifier to analyze
            **kwargs: Additional pipeline parameters
            
        Returns:
            Pipeline execution results with stats and insights
        """
        logger.info(f"Running memory analytics pipeline for user: {user_id}")
        
        try:
            result = memory_analytics_pipeline(
                user_id=user_id,
                **kwargs
            )
            logger.info("Memory analytics pipeline completed")
            return {
                "status": "success",
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Memory analytics pipeline failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }


# Global singleton instance
pipeline_runner = PipelineRunner()
