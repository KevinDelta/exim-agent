"""Crawl4AI client wrapper with AI-powered content extraction configuration."""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from crawl4ai import AsyncWebCrawler
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from loguru import logger

from ...domain.crawlers.models import ComplianceContentType, CrawlMetadata, CrawlResult


class Crawl4AIClient:
    """Wrapper around Crawl4AI library with platform-specific configuration."""
    
    def __init__(
        self,
        ai_model: str = "gpt-5-mini",
        max_concurrent: int = 3,
        default_timeout: int = 30,
        user_agent: str = "ComplianceBot/1.0 (Compliance Intelligence Platform)",
        enable_js: bool = True,
        enable_css: bool = False,
    ):
        """Initialize Crawl4AI client with configuration.
        
        Args:
            ai_model: LLM model for content extraction
            max_concurrent: Maximum concurrent crawling operations
            default_timeout: Default timeout for requests in seconds
            user_agent: User agent string for requests
            enable_js: Whether to enable JavaScript execution
            enable_css: Whether to load CSS (disabled for performance)
        """
        self.ai_model = ai_model
        self.max_concurrent = max_concurrent
        self.default_timeout = default_timeout
        self.user_agent = user_agent
        self.enable_js = enable_js
        self.enable_css = enable_css
        self._crawler: Optional[AsyncWebCrawler] = None
        self._semaphore = asyncio.Semaphore(max_concurrent)
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_crawler()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
        
    async def _ensure_crawler(self):
        """Ensure crawler is initialized."""
        if self._crawler is None:
            self._crawler = AsyncWebCrawler(
                verbose=False,
                headless=True,
                browser_type="chromium",
                user_agent=self.user_agent,
            )
            await self._crawler.start()
            logger.info("Crawl4AI client initialized")
    
    async def close(self):
        """Close the crawler and cleanup resources."""
        if self._crawler:
            await self._crawler.close()
            self._crawler = None
            logger.info("Crawl4AI client closed")
    
    async def extract_content(
        self,
        url: str,
        content_type: ComplianceContentType,
        extraction_schema: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        wait_for: Optional[str] = None,
    ) -> CrawlResult:
        """Extract content from a URL using AI-powered extraction.
        
        Args:
            url: Target URL to crawl
            content_type: Type of compliance content expected
            extraction_schema: JSON schema for structured extraction
            timeout: Request timeout (uses default if None)
            wait_for: CSS selector to wait for before extraction
            
        Returns:
            CrawlResult with extracted content and metadata
        """
        async with self._semaphore:
            await self._ensure_crawler()
            
            try:
                # Configure extraction strategy based on content type
                extraction_strategy = self._get_extraction_strategy(content_type, extraction_schema)
                
                # Perform the crawl
                result = await self._crawler.arun(
                    url=url,
                    extraction_strategy=extraction_strategy,
                    bypass_cache=True,
                    js_code=self._get_js_code(content_type) if self.enable_js else None,
                    wait_for=wait_for,
                    timeout=timeout or self.default_timeout,
                    css_selector=self._get_css_selector(content_type),
                )
                
                # Process the result
                return self._process_crawl_result(url, content_type, result)
                
            except Exception as e:
                logger.error(f"Error crawling {url}: {str(e)}")
                return self._create_error_result(url, content_type, str(e))
    
    def _get_extraction_strategy(
        self,
        content_type: ComplianceContentType,
        schema: Optional[Dict[str, Any]] = None,
    ) -> LLMExtractionStrategy:
        """Get extraction strategy based on content type.
        
        Args:
            content_type: Type of compliance content
            schema: Optional JSON schema for extraction
            
        Returns:
            Configured LLMExtractionStrategy
        """
        # Default extraction prompts for different content types
        prompts = {
            ComplianceContentType.HTS_TARIFF_SCHEDULE: (
                "Extract HTS tariff schedule information including HTS codes, "
                "descriptions, duty rates, and any special provisions or notes."
            ),
            ComplianceContentType.CBP_RULING: (
                "Extract CBP ruling information including ruling number, date, "
                "HTS classification, product description, and ruling rationale."
            ),
            ComplianceContentType.SANCTIONS_LIST: (
                "Extract sanctions list information including entity names, "
                "addresses, identification numbers, and sanction types."
            ),
            ComplianceContentType.FDA_REFUSAL: (
                "Extract FDA refusal information including product details, "
                "refusal reasons, firm information, and dates."
            ),
        }
        
        prompt = prompts.get(
            content_type,
            "Extract relevant compliance information from this page."
        )
        
        return LLMExtractionStrategy(
            provider="openai",
            api_token=None,  # Will use environment variable
            model=self.ai_model,
            schema=schema,
            extraction_type="schema" if schema else "block",
            instruction=prompt,
        )
    
    def _get_css_selector(self, content_type: ComplianceContentType) -> Optional[str]:
        """Get CSS selector for content type-specific extraction.
        
        Args:
            content_type: Type of compliance content
            
        Returns:
            CSS selector string or None for full page
        """
        selectors = {
            ComplianceContentType.HTS_TARIFF_SCHEDULE: "table, .tariff-table, .hts-table",
            ComplianceContentType.CBP_RULING: ".ruling-content, .decision-content, main",
            ComplianceContentType.SANCTIONS_LIST: "table, .sanctions-table, .entity-list",
            ComplianceContentType.FDA_REFUSAL: "table, .refusal-table, .import-alert",
        }
        
        return selectors.get(content_type)
    
    def _get_js_code(self, content_type: ComplianceContentType) -> Optional[str]:
        """Get JavaScript code for content type-specific page interaction.
        
        Args:
            content_type: Type of compliance content
            
        Returns:
            JavaScript code string or None
        """
        # JavaScript to handle dynamic content loading
        js_snippets = {
            ComplianceContentType.HTS_TARIFF_SCHEDULE: """
                // Wait for tables to load
                const tables = document.querySelectorAll('table');
                if (tables.length === 0) {
                    await new Promise(resolve => setTimeout(resolve, 2000));
                }
            """,
            ComplianceContentType.CBP_RULING: """
                // Expand any collapsed content sections
                const expandButtons = document.querySelectorAll('[aria-expanded="false"]');
                expandButtons.forEach(btn => btn.click());
                await new Promise(resolve => setTimeout(resolve, 1000));
            """,
        }
        
        return js_snippets.get(content_type)
    
    def _process_crawl_result(
        self,
        url: str,
        content_type: ComplianceContentType,
        crawl_result: Any,
    ) -> CrawlResult:
        """Process Crawl4AI result into domain CrawlResult.
        
        Args:
            url: Source URL
            content_type: Content type
            crawl_result: Raw Crawl4AI result
            
        Returns:
            Processed CrawlResult
        """
        # Extract data from Crawl4AI result
        raw_content = getattr(crawl_result, 'cleaned_html', '') or getattr(crawl_result, 'markdown', '')
        extracted_data = getattr(crawl_result, 'extracted_content', {})
        
        # Calculate extraction confidence based on content quality
        confidence = self._calculate_confidence(raw_content, extracted_data)
        
        # Create metadata
        metadata = CrawlMetadata(
            source_attribution=url,
            regulatory_authority=self._get_regulatory_authority(url),
            content_hash=self._generate_content_hash(raw_content),
            last_modified=None,  # Could be extracted from headers if available
            extraction_method=f"crawl4ai_{self.ai_model}",
            rate_limit_applied=0.0,  # Will be set by rate limiter
            change_detected=False,  # Will be set by change detector
            crawl_session_id="",  # Will be set by calling crawler
            user_agent=self.user_agent,
            response_status=getattr(crawl_result, 'status_code', 200),
            content_length=len(raw_content),
        )
        
        return CrawlResult(
            source_url=url,
            content_type=content_type,
            extracted_data=extracted_data if isinstance(extracted_data, dict) else {},
            raw_content=raw_content,
            metadata=metadata,
            extraction_confidence=confidence,
            scraped_at=datetime.utcnow(),
            success=True,
        )
    
    def _calculate_confidence(self, raw_content: str, extracted_data: Any) -> float:
        """Calculate extraction confidence score.
        
        Args:
            raw_content: Raw HTML/text content
            extracted_data: Extracted structured data
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not raw_content:
            return 0.0
            
        # Base confidence on content length and structure
        content_score = min(len(raw_content) / 1000, 1.0) * 0.3
        
        # Boost confidence if structured data was extracted
        structure_score = 0.4 if extracted_data and isinstance(extracted_data, dict) else 0.1
        
        # Check for compliance-related keywords
        compliance_keywords = [
            'hts', 'tariff', 'duty', 'classification', 'ruling', 'cbp',
            'sanctions', 'ofac', 'fda', 'refusal', 'import', 'export'
        ]
        
        keyword_matches = sum(1 for keyword in compliance_keywords 
                            if keyword.lower() in raw_content.lower())
        keyword_score = min(keyword_matches / len(compliance_keywords), 1.0) * 0.3
        
        return min(content_score + structure_score + keyword_score, 1.0)
    
    def _get_regulatory_authority(self, url: str) -> str:
        """Determine regulatory authority from URL.
        
        Args:
            url: Source URL
            
        Returns:
            Regulatory authority name
        """
        url_lower = url.lower()
        
        if 'usitc.gov' in url_lower:
            return 'USITC'
        elif 'cbp.gov' in url_lower:
            return 'CBP'
        elif 'treasury.gov' in url_lower or 'ofac' in url_lower:
            return 'OFAC'
        elif 'fda.gov' in url_lower:
            return 'FDA'
        elif 'bis.doc.gov' in url_lower:
            return 'BIS'
        else:
            return 'Unknown'
    
    def _generate_content_hash(self, content: str) -> str:
        """Generate SHA-256 hash of content."""
        import hashlib
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _create_error_result(
        self,
        url: str,
        content_type: ComplianceContentType,
        error_message: str,
    ) -> CrawlResult:
        """Create error result for failed crawls.
        
        Args:
            url: Source URL
            content_type: Content type
            error_message: Error description
            
        Returns:
            CrawlResult indicating failure
        """
        metadata = CrawlMetadata(
            source_attribution=url,
            regulatory_authority=self._get_regulatory_authority(url),
            content_hash="",
            last_modified=None,
            extraction_method="error",
            rate_limit_applied=0.0,
            change_detected=False,
            crawl_session_id="",
            user_agent=self.user_agent,
            response_status=0,
            content_length=0,
        )
        
        return CrawlResult(
            source_url=url,
            content_type=content_type,
            extracted_data={},
            raw_content="",
            metadata=metadata,
            extraction_confidence=0.0,
            scraped_at=datetime.utcnow(),
            success=False,
            error_message=error_message,
        )