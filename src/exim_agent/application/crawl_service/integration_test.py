"""Integration test for CrawlService implementation."""

import asyncio
from datetime import datetime
from loguru import logger

from .service import CrawlService
from .tool_integration import ToolIntegrationManager
from .health_monitoring import CircuitBreakerConfig


async def test_crawl_service_integration():
    """Test basic CrawlService functionality."""
    logger.info("Starting CrawlService integration test")
    
    # Initialize CrawlService
    crawl_service = CrawlService()
    
    # Test basic functionality
    crawler_types = crawl_service.get_crawler_types()
    logger.info("Available crawlers: {}", crawler_types)
    
    # Test health monitoring
    health_status = await crawl_service.get_health_status()
    logger.info("Health status: {}", health_status["status"])
    
    # Test tool integration
    integration_manager = ToolIntegrationManager(crawl_service)
    available_tools = integration_manager.get_available_tools()
    logger.info("Enhanced tools: {}", available_tools)
    
    # Test task submission (without actual execution)
    task_id = await crawl_service.submit_crawl_task(
        crawler_type="hts",
        target_url="https://hts.usitc.gov/test",
        parameters={"test": True}
    )
    logger.info("Submitted test task: {}", task_id)
    
    # Test task status
    task_status = await crawl_service.get_task_status(task_id)
    logger.info("Task status: {}", task_status["status"] if task_status else "Not found")
    
    # Test scheduling
    schedule_id = crawl_service.schedule_crawling_tasks({
        "crawler_type": "hts",
        "frequency_hours": 24,
        "parameters": {"test_schedule": True}
    })
    logger.info("Created schedule: {}", schedule_id)
    
    # Test summaries
    tasks_summary = crawl_service.get_active_tasks_summary()
    schedules_summary = crawl_service.get_schedules_summary()
    
    logger.info("Tasks summary: {} total tasks", tasks_summary["total_tasks"])
    logger.info("Schedules summary: {} total schedules", schedules_summary["total_schedules"])
    
    logger.info("CrawlService integration test completed successfully")
    
    return {
        "crawlers_available": len(crawler_types),
        "health_status": health_status["status"],
        "enhanced_tools": len(available_tools),
        "test_task_created": task_id is not None,
        "test_schedule_created": schedule_id is not None
    }


if __name__ == "__main__":
    # Run the integration test
    result = asyncio.run(test_crawl_service_integration())
    print(f"Integration test result: {result}")