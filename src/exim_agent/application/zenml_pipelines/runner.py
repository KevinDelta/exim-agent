"""Pipeline runner utilities for ZenML pipelines."""

from typing import Dict, Any
from loguru import logger

from exim_agent.application.zenml_pipelines.ingestion_pipeline import run_ingestion_pipeline
from exim_agent.application.zenml_pipelines.memory_analytics_pipeline import memory_analytics_pipeline
from exim_agent.application.zenml_pipelines.compliance_ingestion import compliance_ingestion_pipeline
from exim_agent.application.zenml_pipelines.weekly_pulse import weekly_pulse_pipeline


class PipelineRunner:
    """
    Simplified pipeline runner for ZenML (Mem0-optimized stack).
    
    Pipelines:
    - Ingestion: Load documents into RAG
    - Memory Analytics: Analyze Mem0 usage patterns
    - Compliance Ingestion: Daily compliance data ingestion
    - Weekly Pulse: Weekly compliance digest generation
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
    
    def run_compliance_ingestion(
        self,
        lookback_days: int = 7,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Run compliance data ingestion pipeline.
        
        Fetches and ingests compliance updates from:
        - HTS codes and notes
        - Sanctions lists (OFAC)
        - Import refusals (FDA/FSIS)
        - CBP rulings (CROSS)
        
        Args:
            lookback_days: Number of days to look back for updates
            **kwargs: Additional pipeline parameters
            
        Returns:
            Pipeline execution results with ingestion counts
        """
        logger.info(f"Running compliance ingestion pipeline (lookback: {lookback_days} days)")
        
        try:
            result = compliance_ingestion_pipeline(
                lookback_days=lookback_days,
                **kwargs
            )
            logger.info(f"Compliance ingestion completed: {result}")
            return {
                "status": "success",
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Compliance ingestion pipeline failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def run_weekly_pulse(
        self,
        client_id: str,
        period_days: int = 7,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Run weekly compliance pulse generation pipeline.
        
        Generates a comprehensive weekly digest including:
        - New compliance requirements
        - Risk escalations
        - Delta analysis vs previous week
        - Prioritized action items
        
        Args:
            client_id: Client identifier
            period_days: Number of days in pulse period (default 7)
            **kwargs: Additional pipeline parameters
            
        Returns:
            Pipeline execution results with digest
        """
        logger.info(f"Running weekly pulse pipeline for client: {client_id}")
        
        try:
            result = weekly_pulse_pipeline(
                client_id=client_id,
                period_days=period_days,
                **kwargs
            )
            logger.info(f"Weekly pulse generated successfully for {client_id}")
            return {
                "status": "success",
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Weekly pulse pipeline failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }


# Global singleton instance
pipeline_runner = PipelineRunner()
