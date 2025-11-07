"""Integration mixins and enhancements for existing compliance tools."""

from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger

from ...domain.tools.base_tool import ComplianceTool
from ...domain.tools.hts_tool import HTSTool
from ...domain.tools.rulings_tool import RulingsTool
from ...domain.tools.sanctions_tool import SanctionsTool
from ...domain.tools.refusals_tool import RefusalsTool
from ...domain.crawlers.models import CrawlResult
from .service import CrawlService


class CrawlEnhancementMixin:
    """Mixin to add crawling enhancement capabilities to existing tools."""
    
    def __init__(self, *args, **kwargs):
        """Initialize mixin with crawl service integration."""
        super().__init__(*args, **kwargs)
        self._crawl_service: Optional[CrawlService] = None
        self._enhancement_enabled = True
    
    def set_crawl_service(self, crawl_service: CrawlService) -> None:
        """Set the crawl service for enhancement operations."""
        self._crawl_service = crawl_service
    
    def enable_crawl_enhancement(self, enabled: bool = True) -> None:
        """Enable or disable crawl enhancement for this tool."""
        self._enhancement_enabled = enabled
    
    async def _enhance_with_crawling(
        self, 
        base_result: Dict[str, Any], 
        crawler_type: str, 
        search_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enhance base tool result with crawled data.
        
        Args:
            base_result: Result from the base tool implementation
            crawler_type: Type of crawler to use for enhancement
            search_params: Parameters for crawling enhancement
            
        Returns:
            Enhanced result combining base data with crawled content
        """
        if not self._enhancement_enabled or not self._crawl_service:
            return base_result
        
        try:
            logger.info("Enhancing {} result with crawling", crawler_type)
            
            # Perform targeted crawling based on search parameters
            crawl_results = await self._crawl_service.crawl_compliance_sources(
                domains=[crawler_type],
                parameters=search_params
            )
            
            crawler_results = crawl_results.get(crawler_type, [])
            
            if not crawler_results:
                logger.info("No crawl enhancement data found for {}", crawler_type)
                return self._add_enhancement_metadata(base_result, enhanced=False)
            
            # Merge crawled data with base result
            enhanced_result = self._merge_crawl_data(base_result, crawler_results)
            
            logger.info("Successfully enhanced {} result with {} crawled items", 
                       crawler_type, len(crawler_results))
            
            return enhanced_result
            
        except Exception as e:
            logger.warning("Crawl enhancement failed for {}: {}", crawler_type, str(e))
            return self._add_enhancement_metadata(base_result, enhanced=False, error=str(e))
    
    def _merge_crawl_data(
        self, 
        base_result: Dict[str, Any], 
        crawl_results: List[CrawlResult]
    ) -> Dict[str, Any]:
        """
        Merge crawled data with base tool result.
        
        Args:
            base_result: Original tool result
            crawl_results: List of crawl results to merge
            
        Returns:
            Enhanced result with merged data
        """
        enhanced_result = base_result.copy()
        
        # Add crawl enhancement section
        enhanced_result["crawl_enhancement"] = {
            "enhanced": True,
            "crawl_count": len(crawl_results),
            "enhancement_timestamp": datetime.utcnow().isoformat(),
            "crawled_sources": []
        }
        
        # Process each crawl result
        for crawl_result in crawl_results:
            if not crawl_result.success:
                continue
            
            source_info = {
                "source_url": crawl_result.source_url,
                "content_type": crawl_result.content_type.value,
                "confidence": crawl_result.extraction_confidence,
                "scraped_at": crawl_result.scraped_at.isoformat()
            }
            
            enhanced_result["crawl_enhancement"]["crawled_sources"].append(source_info)
            
            # Merge extracted data based on content type
            self._merge_extracted_data(enhanced_result, crawl_result)
        
        return enhanced_result
    
    def _merge_extracted_data(self, enhanced_result: Dict[str, Any], crawl_result: CrawlResult) -> None:
        """
        Merge extracted data from crawl result into enhanced result.
        
        Args:
            enhanced_result: Result being enhanced (modified in place)
            crawl_result: Crawl result to merge data from
        """
        extracted_data = crawl_result.extracted_data
        
        # Add additional details if available
        if "additional_details" not in enhanced_result:
            enhanced_result["additional_details"] = {}
        
        # Merge based on content type
        content_type = crawl_result.content_type.value
        
        if content_type not in enhanced_result["additional_details"]:
            enhanced_result["additional_details"][content_type] = []
        
        enhanced_result["additional_details"][content_type].append({
            "source": crawl_result.source_url,
            "data": extracted_data,
            "confidence": crawl_result.extraction_confidence
        })
    
    def _add_enhancement_metadata(
        self, 
        result: Dict[str, Any], 
        enhanced: bool, 
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add enhancement metadata to result.
        
        Args:
            result: Base result to enhance
            enhanced: Whether enhancement was successful
            error: Optional error message
            
        Returns:
            Result with enhancement metadata
        """
        result = result.copy()
        result["crawl_enhancement"] = {
            "enhanced": enhanced,
            "enhancement_timestamp": datetime.utcnow().isoformat(),
            "error": error
        }
        return result
    
    def _needs_enhancement(self, result: Dict[str, Any]) -> bool:
        """
        Determine if result needs crawl enhancement.
        
        Args:
            result: Tool result to check
            
        Returns:
            True if enhancement would be beneficial
        """
        # Check if result is from fallback/mock data
        if result.get("status") == "fallback" or result.get("fallback_data"):
            return True
        
        # Check if result has limited information
        if result.get("api_source") == "Fallback mock data":
            return True
        
        # Check for specific indicators that more data would be helpful
        description = result.get("description", "")
        if len(description) < 50:  # Very short description
            return True
        
        return False


class EnhancedHTSTool(CrawlEnhancementMixin, HTSTool):
    """HTS Tool enhanced with web crawling capabilities."""
    
    async def _run_impl_with_crawling(self, hts_code: str, lane_id: str = None) -> Dict[str, Any]:
        """
        Enhanced HTS lookup with crawling integration.
        
        Args:
            hts_code: HTS code to search
            lane_id: Optional lane identifier
            
        Returns:
            Enhanced HTS data with crawled content
        """
        # Get base result from existing implementation
        base_result = self._run_impl(hts_code, lane_id)
        
        # Check if enhancement is needed
        if not self._needs_enhancement(base_result):
            return self._add_enhancement_metadata(base_result, enhanced=False)
        
        # Enhance with crawling
        search_params = {
            "hts_code": hts_code,
            "search_terms": [hts_code, f"HTS {hts_code}"],
            "max_urls": 10
        }
        
        return await self._enhance_with_crawling(base_result, "hts", search_params)
    
    def _needs_enhancement(self, result: Dict[str, Any]) -> bool:
        """Check if HTS result needs enhancement."""
        if super()._needs_enhancement(result):
            return True
        
        # HTS-specific enhancement criteria
        duty_rate = result.get("duty_rate", "")
        if duty_rate in ["Varies", "See USITC website for current rates"]:
            return True
        
        return False


class EnhancedRulingsTool(CrawlEnhancementMixin, RulingsTool):
    """Rulings Tool enhanced with web crawling capabilities."""
    
    async def _run_impl_with_crawling(
        self, 
        search_term: str = None, 
        hts_code: str = None, 
        keyword: str = None, 
        lane_id: str = None, 
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Enhanced rulings search with crawling integration.
        
        Args:
            search_term: Search term for rulings
            hts_code: HTS code to search for
            keyword: Alternative search term
            lane_id: Optional lane identifier
            limit: Maximum number of rulings
            
        Returns:
            Enhanced rulings data with additional crawled content
        """
        # Get base result from existing implementation
        base_result = self._run_impl(search_term, hts_code, keyword, lane_id, limit)
        
        # Check if enhancement is needed
        if not self._needs_enhancement(base_result):
            return self._add_enhancement_metadata(base_result, enhanced=False)
        
        # Enhance with crawling
        actual_search_term = search_term or keyword or hts_code
        search_params = {
            "search_term": actual_search_term,
            "hts_code": hts_code,
            "limit": limit,
            "max_urls": 15
        }
        
        return await self._enhance_with_crawling(base_result, "rulings", search_params)
    
    def _needs_enhancement(self, result: Dict[str, Any]) -> bool:
        """Check if rulings result needs enhancement."""
        if super()._needs_enhancement(result):
            return True
        
        # Rulings-specific enhancement criteria
        total_rulings = result.get("total_rulings", 0)
        if total_rulings < 3:  # Few rulings found, try to find more
            return True
        
        return False


class EnhancedSanctionsTool(CrawlEnhancementMixin, SanctionsTool):
    """Sanctions Tool enhanced with web crawling capabilities."""
    
    async def _run_impl_with_crawling(self, party_name: str, lane_id: str = None) -> Dict[str, Any]:
        """
        Enhanced sanctions screening with crawling integration.
        
        Args:
            party_name: Name of party to screen
            lane_id: Optional lane identifier
            
        Returns:
            Enhanced sanctions data with additional sources
        """
        # Get base result from existing implementation
        base_result = self._run_impl(party_name, lane_id)
        
        # Check if enhancement is needed
        if not self._needs_enhancement(base_result):
            return self._add_enhancement_metadata(base_result, enhanced=False)
        
        # Enhance with crawling
        search_params = {
            "party_name": party_name,
            "search_terms": [party_name],
            "max_urls": 8
        }
        
        return await self._enhance_with_crawling(base_result, "sanctions", search_params)
    
    def _needs_enhancement(self, result: Dict[str, Any]) -> bool:
        """Check if sanctions result needs enhancement."""
        if super()._needs_enhancement(result):
            return True
        
        # Sanctions-specific enhancement criteria
        sources_checked = result.get("sources_checked", [])
        if len(sources_checked) <= 1:  # Only checked one source
            return True
        
        return False


class EnhancedRefusalsTool(CrawlEnhancementMixin, RefusalsTool):
    """Refusals Tool enhanced with web crawling capabilities."""
    
    async def _run_impl_with_crawling(
        self, 
        country: str = None, 
        product_type: str = None, 
        hts_code: str = None
    ) -> Dict[str, Any]:
        """
        Enhanced refusals lookup with crawling integration.
        
        Args:
            country: Country code to filter by
            product_type: Product type to filter by
            hts_code: HTS code for filtering
            
        Returns:
            Enhanced refusals data with additional sources
        """
        # Get base result from existing implementation
        base_result = self._run_impl(country, product_type, hts_code)
        
        # Check if enhancement is needed
        if not self._needs_enhancement(base_result):
            return self._add_enhancement_metadata(base_result, enhanced=False)
        
        # Enhance with crawling
        search_params = {
            "country": country,
            "product_type": product_type,
            "hts_code": hts_code,
            "max_urls": 12
        }
        
        return await self._enhance_with_crawling(base_result, "refusals", search_params)
    
    def _needs_enhancement(self, result: Dict[str, Any]) -> bool:
        """Check if refusals result needs enhancement."""
        if super()._needs_enhancement(result):
            return True
        
        # Refusals-specific enhancement criteria
        total_refusals = result.get("total_refusals", 0)
        if total_refusals == 0:  # No refusals found, try to find more data
            return True
        
        return False


class ToolIntegrationManager:
    """Manager for integrating crawling capabilities with existing tools."""
    
    def __init__(self, crawl_service: CrawlService):
        """
        Initialize tool integration manager.
        
        Args:
            crawl_service: CrawlService instance for enhancement operations
        """
        self.crawl_service = crawl_service
        self._enhanced_tools: Dict[str, ComplianceTool] = {}
        
        # Create enhanced tool instances
        self._create_enhanced_tools()
    
    def _create_enhanced_tools(self) -> None:
        """Create enhanced versions of existing compliance tools."""
        # Create enhanced tool instances
        enhanced_hts = EnhancedHTSTool()
        enhanced_hts.set_crawl_service(self.crawl_service)
        
        enhanced_rulings = EnhancedRulingsTool()
        enhanced_rulings.set_crawl_service(self.crawl_service)
        
        enhanced_sanctions = EnhancedSanctionsTool()
        enhanced_sanctions.set_crawl_service(self.crawl_service)
        
        enhanced_refusals = EnhancedRefusalsTool()
        enhanced_refusals.set_crawl_service(self.crawl_service)
        
        self._enhanced_tools = {
            "hts": enhanced_hts,
            "rulings": enhanced_rulings,
            "sanctions": enhanced_sanctions,
            "refusals": enhanced_refusals
        }
        
        logger.info("Created enhanced tools: {}", list(self._enhanced_tools.keys()))
    
    def get_enhanced_tool(self, tool_name: str) -> Optional[ComplianceTool]:
        """
        Get enhanced version of a compliance tool.
        
        Args:
            tool_name: Name of the tool to get
            
        Returns:
            Enhanced tool instance or None if not found
        """
        return self._enhanced_tools.get(tool_name)
    
    def get_available_tools(self) -> List[str]:
        """Get list of available enhanced tools."""
        return list(self._enhanced_tools.keys())
    
    def enable_enhancement(self, tool_name: str, enabled: bool = True) -> bool:
        """
        Enable or disable crawl enhancement for a specific tool.
        
        Args:
            tool_name: Name of the tool
            enabled: Whether to enable enhancement
            
        Returns:
            True if successful, False if tool not found
        """
        tool = self._enhanced_tools.get(tool_name)
        if not tool or not hasattr(tool, 'enable_crawl_enhancement'):
            return False
        
        tool.enable_crawl_enhancement(enabled)
        logger.info("Set crawl enhancement for {} to {}", tool_name, enabled)
        return True
    
    async def enhance_tool_data(
        self, 
        tool_name: str, 
        search_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Use enhanced tool to get data with crawling integration.
        
        Args:
            tool_name: Name of the tool to use
            search_params: Parameters for the tool operation
            
        Returns:
            Enhanced tool result
        """
        tool = self._enhanced_tools.get(tool_name)
        if not tool:
            raise ValueError(f"Unknown enhanced tool: {tool_name}")
        
        # Call the appropriate enhanced method based on tool type
        if tool_name == "hts":
            return await tool._run_impl_with_crawling(
                hts_code=search_params.get("hts_code"),
                lane_id=search_params.get("lane_id")
            )
        elif tool_name == "rulings":
            return await tool._run_impl_with_crawling(
                search_term=search_params.get("search_term"),
                hts_code=search_params.get("hts_code"),
                keyword=search_params.get("keyword"),
                lane_id=search_params.get("lane_id"),
                limit=search_params.get("limit", 10)
            )
        elif tool_name == "sanctions":
            return await tool._run_impl_with_crawling(
                party_name=search_params.get("party_name"),
                lane_id=search_params.get("lane_id")
            )
        elif tool_name == "refusals":
            return await tool._run_impl_with_crawling(
                country=search_params.get("country"),
                product_type=search_params.get("product_type"),
                hts_code=search_params.get("hts_code")
            )
        else:
            raise ValueError(f"No enhanced implementation for tool: {tool_name}")
    
    def get_integration_status(self) -> Dict[str, Any]:
        """Get status of tool integration."""
        return {
            "enhanced_tools_count": len(self._enhanced_tools),
            "available_tools": list(self._enhanced_tools.keys()),
            "crawl_service_available": self.crawl_service is not None,
            "integration_timestamp": datetime.utcnow().isoformat()
        }