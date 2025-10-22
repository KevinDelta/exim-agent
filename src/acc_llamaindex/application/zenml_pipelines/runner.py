"""Pipeline runner utilities for ZenML pipelines."""

from typing import Dict, Any
from loguru import logger

from acc_llamaindex.application.zenml_pipelines.ingestion_pipeline import run_ingestion_pipeline
from acc_llamaindex.application.zenml_pipelines.distillation_pipeline import run_distillation_pipeline
from acc_llamaindex.application.zenml_pipelines.promotion_pipeline import run_promotion_pipeline


class PipelineRunner:
    """
    Unified runner for all ZenML pipelines.
    
    Provides a consistent interface for executing pipelines with
    proper error handling and logging.
    """
    
    def __init__(self):
        logger.info("PipelineRunner initialized")
    
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
    
    def run_distillation(
        self,
        session_id: str,
        n_turns: int = 5,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Run conversation distillation pipeline.
        
        Args:
            session_id: Session identifier
            n_turns: Number of turns to distill
            **kwargs: Additional pipeline parameters
            
        Returns:
            Pipeline execution results
        """
        logger.info(f"Running distillation pipeline for session: {session_id}")
        
        try:
            result = run_distillation_pipeline(
                session_id=session_id,
                n_turns=n_turns,
                **kwargs
            )
            logger.info(f"Distillation pipeline completed: {result.get('status')}")
            return result
            
        except Exception as e:
            logger.error(f"Distillation pipeline failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def run_promotion(
        self,
        salience_threshold: float | None = None,
        citation_threshold: int | None = None,
        age_days: int | None = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Run memory promotion pipeline.
        
        Args:
            salience_threshold: Minimum salience score
            citation_threshold: Minimum citation count
            age_days: Minimum fact age in days
            **kwargs: Additional pipeline parameters
            
        Returns:
            Pipeline execution results
        """
        logger.info("Running promotion pipeline")
        
        try:
            result = run_promotion_pipeline(
                salience_threshold=salience_threshold,
                citation_threshold=citation_threshold,
                age_days=age_days,
                **kwargs
            )
            logger.info(f"Promotion pipeline completed: {result.get('status')}")
            return result
            
        except Exception as e:
            logger.error(f"Promotion pipeline failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def run_all_pipelines(
        self,
        directory_path: str | None = None,
        session_id: str | None = None
    ) -> Dict[str, Any]:
        """
        Run all pipelines in sequence.
        
        Useful for testing or batch processing.
        
        Args:
            directory_path: Path for ingestion
            session_id: Session for distillation
            
        Returns:
            Combined results from all pipelines
        """
        logger.info("Running all pipelines")
        
        results = {}
        
        # Run ingestion
        if directory_path:
            results["ingestion"] = self.run_ingestion(directory_path)
        
        # Run distillation
        if session_id:
            results["distillation"] = self.run_distillation(session_id)
        
        # Run promotion
        results["promotion"] = self.run_promotion()
        
        return results


# Global singleton instance
pipeline_runner = PipelineRunner()
