"""Simple crawling management API routes."""

from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, BackgroundTasks
from loguru import logger

from exim_agent.application.crawl_service.service import CrawlService
from exim_agent.infrastructure.api.models import CrawlRequest, CrawlResponse

router = APIRouter(prefix="/crawl", tags=["crawling"])

# Global crawl service instance
crawl_service: Optional[CrawlService] = None


def get_crawl_service() -> CrawlService:
    """Get or initialize the crawl service."""
    global crawl_service
    if crawl_service is None:
        crawl_service = CrawlService()
        logger.info("Initialized CrawlService for API endpoints")
    return crawl_service


async def run_crawl_operation_background(domains: List[str]) -> Dict[str, Any]:
    """Run crawling operation in background."""
    try:
        service = get_crawl_service()
        logger.info("Starting crawl operation for domains: {}", domains)
        
        results = await service.crawl_compliance_sources(domains=domains)
        
        # Store results in Supabase
        from exim_agent.infrastructure.db.supabase_client import supabase_client
        
        total_stored = 0
        for domain, domain_results in results.items():
            for result in domain_results:
                if result.success and result.extracted_data:
                    content_data = {
                        "data_type": domain,
                        "source_url": result.source_url,
                        "data": result.extracted_data,
                        "crawl_metadata": {
                            "extraction_confidence": result.extraction_confidence,
                            "crawled_at": datetime.utcnow().isoformat(),
                            "success": result.success
                        }
                    }
                    supabase_client.store_compliance_data([content_data])
                    total_stored += 1
        
        logger.info("Crawl operation completed. Stored {} items", total_stored)
        return {
            "success": True,
            "results_count": total_stored,
            "completed_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Crawl operation failed: {}", str(e))
        return {
            "success": False,
            "error": str(e),
            "completed_at": datetime.utcnow().isoformat()
        }


@router.post("/trigger", response_model=CrawlResponse)
async def trigger_manual_crawl(
    request: CrawlRequest,
    background_tasks: BackgroundTasks
) -> CrawlResponse:
    """
    Manually trigger compliance crawling for specified domains.
    
    This endpoint starts crawling operations for compliance domains
    and stores the results in Supabase for use by the existing system.
    """
    try:
        service = get_crawl_service()
        
        # Validate domains
        available_crawlers = service.get_crawler_types()
        invalid_domains = [d for d in request.domains if d not in available_crawlers]
        if invalid_domains:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid crawler domains: {invalid_domains}. Available: {available_crawlers}"
            )
        
        logger.info("Triggering manual crawl for domains: {}", request.domains)
        
        # Start crawling in background
        background_tasks.add_task(run_crawl_operation_background, request.domains)
        
        return CrawlResponse(
            success=True,
            message=f"Crawling started for domains: {', '.join(request.domains)}",
            results_count=0  # Will be updated when background task completes
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to trigger manual crawl: {}", str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start crawling operation: {str(e)}"
        )


@router.get("/status")
async def get_crawl_service_status() -> Dict[str, Any]:
    """Get basic status of the crawling service."""
    try:
        service = get_crawl_service()
        crawler_types = service.get_crawler_types()
        
        return {
            "success": True,
            "service_status": "operational",
            "available_crawlers": crawler_types,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to get crawl service status: {}", str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve service status: {str(e)}"
        )