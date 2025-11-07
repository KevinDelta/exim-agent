"""Base crawler abstract class with common crawling functionality."""

import hashlib
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from .models import ComplianceContentType, CrawlMetadata, CrawlResult


class BaseCrawler(ABC):
    """Abstract base class for all compliance content crawlers."""
    
    def __init__(
        self,
        rate_limit: float = 1.0,
        user_agent: str = "ComplianceBot/1.0 (Compliance Intelligence Platform)",
        max_retries: int = 3,
        timeout: int = 30,
    ):
        """Initialize base crawler with common configuration.
        
        Args:
            rate_limit: Requests per second limit for respectful crawling
            user_agent: User agent string for HTTP requests
            max_retries: Maximum number of retry attempts for failed requests
            timeout: Request timeout in seconds
        """
        self.rate_limit = rate_limit
        self.user_agent = user_agent
        self.max_retries = max_retries
        self.timeout = timeout
        self.session_id = str(uuid.uuid4())
        
    @abstractmethod
    def get_content_type(self) -> ComplianceContentType:
        """Return the primary content type this crawler handles."""
        pass
    
    @abstractmethod
    def get_regulatory_authority(self) -> str:
        """Return the regulatory authority for content from this crawler."""
        pass
    
    @abstractmethod
    async def crawl(self, url: str, **kwargs) -> CrawlResult:
        """Crawl a specific URL and extract compliance content.
        
        Args:
            url: Target URL to crawl
            **kwargs: Additional crawler-specific parameters
            
        Returns:
            CrawlResult with extracted content and metadata
        """
        pass
    
    @abstractmethod
    async def discover_urls(self, base_url: str, **kwargs) -> List[str]:
        """Discover URLs to crawl from a base URL.
        
        Args:
            base_url: Starting URL for content discovery
            **kwargs: Additional discovery parameters
            
        Returns:
            List of URLs to crawl
        """
        pass
    
    def _generate_content_hash(self, content: str) -> str:
        """Generate SHA-256 hash of content for change detection.
        
        Args:
            content: Raw content to hash
            
        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _create_metadata(
        self,
        source_url: str,
        content: str,
        extraction_method: str,
        response_status: int = 200,
        last_modified: Optional[datetime] = None,
        change_detected: bool = False,
    ) -> CrawlMetadata:
        """Create standardized metadata for crawl results.
        
        Args:
            source_url: Source URL of the content
            content: Raw content for hashing
            extraction_method: Method used for content extraction
            response_status: HTTP response status code
            last_modified: Last modified timestamp from server
            change_detected: Whether content change was detected
            
        Returns:
            CrawlMetadata instance
        """
        return CrawlMetadata(
            source_attribution=source_url,
            regulatory_authority=self.get_regulatory_authority(),
            content_hash=self._generate_content_hash(content),
            last_modified=last_modified,
            extraction_method=extraction_method,
            rate_limit_applied=self.rate_limit,
            change_detected=change_detected,
            crawl_session_id=self.session_id,
            user_agent=self.user_agent,
            response_status=response_status,
            content_length=len(content),
        )
    
    def _create_error_result(
        self,
        url: str,
        error_message: str,
        response_status: int = 0,
    ) -> CrawlResult:
        """Create a CrawlResult for failed crawling attempts.
        
        Args:
            url: URL that failed to crawl
            error_message: Description of the error
            response_status: HTTP response status if available
            
        Returns:
            CrawlResult indicating failure
        """
        metadata = CrawlMetadata(
            source_attribution=url,
            regulatory_authority=self.get_regulatory_authority(),
            content_hash="",
            last_modified=None,
            extraction_method="error",
            rate_limit_applied=self.rate_limit,
            change_detected=False,
            crawl_session_id=self.session_id,
            user_agent=self.user_agent,
            response_status=response_status,
            content_length=0,
        )
        
        return CrawlResult(
            source_url=url,
            content_type=self.get_content_type(),
            extracted_data={},
            raw_content="",
            metadata=metadata,
            extraction_confidence=0.0,
            scraped_at=datetime.utcnow(),
            success=False,
            error_message=error_message,
        )
    
    async def crawl_multiple(self, urls: List[str], **kwargs) -> List[CrawlResult]:
        """Crawl multiple URLs with rate limiting.
        
        Args:
            urls: List of URLs to crawl
            **kwargs: Additional parameters passed to crawl method
            
        Returns:
            List of CrawlResult objects
        """
        results = []
        
        for url in urls:
            try:
                result = await self.crawl(url, **kwargs)
                results.append(result)
                
                # Apply rate limiting between requests
                if len(results) < len(urls):  # Don't wait after last request
                    import asyncio
                    await asyncio.sleep(1.0 / self.rate_limit)
                    
            except Exception as e:
                error_result = self._create_error_result(
                    url=url,
                    error_message=f"Unexpected error during crawl: {str(e)}"
                )
                results.append(error_result)
        
        return results
    
    def validate_url(self, url: str) -> bool:
        """Validate if URL is appropriate for this crawler.
        
        Args:
            url: URL to validate
            
        Returns:
            True if URL is valid for this crawler
        """
        # Basic URL validation - subclasses can override for domain-specific validation
        return url.startswith(('http://', 'https://'))
    
    def should_crawl(self, url: str, last_crawled: Optional[datetime] = None) -> bool:
        """Determine if URL should be crawled based on freshness and other criteria.
        
        Args:
            url: URL to check
            last_crawled: When this URL was last crawled
            
        Returns:
            True if URL should be crawled
        """
        if not self.validate_url(url):
            return False
            
        # If never crawled, should crawl
        if last_crawled is None:
            return True
            
        # Default: crawl if more than 24 hours old
        # Subclasses can override for domain-specific freshness rules
        age_hours = (datetime.utcnow() - last_crawled).total_seconds() / 3600
        return age_hours >= 24