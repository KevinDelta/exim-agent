"""HTS-specific crawler for enhanced USITC website scraping with structured data extraction."""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

from loguru import logger

from ...infrastructure.crawl4ai.client import Crawl4AIClient
from .base_crawler import BaseCrawler
from .models import ComplianceContentType, CrawlResult


class HTSCrawler(BaseCrawler):
    """Crawler for USITC HTS tariff schedule and classification information."""
    
    def __init__(
        self,
        rate_limit: float = 0.5,  # Conservative rate limit for USITC
        **kwargs
    ):
        """Initialize HTS crawler with USITC-specific configuration."""
        super().__init__(rate_limit=rate_limit, **kwargs)
        self.base_urls = [
            "https://hts.usitc.gov",
            "https://www.usitc.gov/tata/hts",
        ]
        self.crawl4ai_client: Optional[Crawl4AIClient] = None
    
    def get_content_type(self) -> ComplianceContentType:
        """Return HTS tariff schedule as primary content type."""
        return ComplianceContentType.HTS_TARIFF_SCHEDULE
    
    def get_regulatory_authority(self) -> str:
        """Return USITC as regulatory authority."""
        return "USITC"
    
    async def crawl(self, url: str, **kwargs) -> CrawlResult:
        """Crawl HTS content from USITC website with AI-powered extraction.
        
        Args:
            url: Target USITC URL to crawl
            **kwargs: Additional parameters including:
                - hts_code: Specific HTS code to extract (optional)
                - extract_notes: Whether to extract classification notes (default: True)
                - extract_duty_rates: Whether to extract duty rates (default: True)
        
        Returns:
            CrawlResult with extracted HTS data
        """
        if not self.validate_url(url):
            return self._create_error_result(url, "Invalid URL for HTS crawler")
        
        try:
            # Initialize Crawl4AI client if needed
            if not self.crawl4ai_client:
                self.crawl4ai_client = Crawl4AIClient(
                    user_agent=self.user_agent,
                    default_timeout=self.timeout,
                )
            
            # Extract parameters
            hts_code = kwargs.get('hts_code')
            extract_notes = kwargs.get('extract_notes', True)
            extract_duty_rates = kwargs.get('extract_duty_rates', True)
            
            # Create extraction schema for structured data
            extraction_schema = self._create_hts_extraction_schema(
                hts_code=hts_code,
                extract_notes=extract_notes,
                extract_duty_rates=extract_duty_rates,
            )
            
            # Perform AI-powered crawling
            async with self.crawl4ai_client:
                result = await self.crawl4ai_client.extract_content(
                    url=url,
                    content_type=ComplianceContentType.HTS_TARIFF_SCHEDULE,
                    extraction_schema=extraction_schema,
                    wait_for="table, .hts-table, .tariff-table",
                )
            
            # Enhance result with HTS-specific processing
            enhanced_result = await self._enhance_hts_result(result, **kwargs)
            
            # Update metadata with crawler-specific information
            enhanced_result.metadata.crawl_session_id = self.session_id
            enhanced_result.metadata.rate_limit_applied = self.rate_limit
            
            logger.info(f"Successfully crawled HTS content from {url}")
            return enhanced_result
            
        except Exception as e:
            logger.error(f"Error crawling HTS content from {url}: {str(e)}")
            return self._create_error_result(url, f"HTS crawling failed: {str(e)}")
    
    async def discover_urls(self, base_url: str, **kwargs) -> List[str]:
        """Discover HTS-related URLs from USITC website.
        
        Args:
            base_url: Starting URL for discovery (should be USITC domain)
            **kwargs: Additional parameters including:
                - chapters: List of HTS chapters to discover (optional)
                - sections: List of HTS sections to discover (optional)
                - max_depth: Maximum crawl depth (default: 2)
        
        Returns:
            List of discovered HTS URLs
        """
        if not self.validate_url(base_url):
            logger.warning(f"Invalid base URL for HTS discovery: {base_url}")
            return []
        
        discovered_urls = []
        chapters = kwargs.get('chapters', [])
        sections = kwargs.get('sections', [])
        max_depth = kwargs.get('max_depth', 2)
        
        try:
            # Initialize Crawl4AI client if needed
            if not self.crawl4ai_client:
                self.crawl4ai_client = Crawl4AIClient(
                    user_agent=self.user_agent,
                    default_timeout=self.timeout,
                )
            
            async with self.crawl4ai_client:
                # Crawl the base page to find HTS navigation links
                result = await self.crawl4ai_client.extract_content(
                    url=base_url,
                    content_type=ComplianceContentType.HTS_TARIFF_SCHEDULE,
                    wait_for="a[href*='chapter'], a[href*='section'], a[href*='hts']",
                )
                
                # Extract URLs from the crawled content
                urls = self._extract_hts_urls_from_content(
                    result.raw_content,
                    base_url,
                    chapters=chapters,
                    sections=sections,
                )
                
                discovered_urls.extend(urls)
            
            # Add known HTS structure URLs
            discovered_urls.extend(self._generate_known_hts_urls(chapters, sections))
            
            # Remove duplicates and validate
            unique_urls = list(set(discovered_urls))
            valid_urls = [url for url in unique_urls if self.validate_url(url)]
            
            logger.info(f"Discovered {len(valid_urls)} HTS URLs from {base_url}")
            return valid_urls[:50]  # Limit to prevent excessive crawling
            
        except Exception as e:
            logger.error(f"Error discovering HTS URLs from {base_url}: {str(e)}")
            return []
    
    def validate_url(self, url: str) -> bool:
        """Validate if URL is appropriate for HTS crawler.
        
        Args:
            url: URL to validate
            
        Returns:
            True if URL is valid for HTS crawling
        """
        if not super().validate_url(url):
            return False
        
        # Check if URL is from USITC domain
        parsed = urlparse(url)
        valid_domains = ['hts.usitc.gov', 'usitc.gov', 'www.usitc.gov']
        
        return any(domain in parsed.netloc for domain in valid_domains)
    
    def should_crawl(self, url: str, last_crawled: Optional[datetime] = None) -> bool:
        """Determine if HTS URL should be crawled based on freshness.
        
        Args:
            url: URL to check
            last_crawled: When this URL was last crawled
            
        Returns:
            True if URL should be crawled
        """
        if not super().should_crawl(url, last_crawled):
            return False
        
        # HTS data changes less frequently, so use longer refresh intervals
        if last_crawled is None:
            return True
        
        # Crawl HTS data weekly instead of daily
        age_hours = (datetime.utcnow() - last_crawled).total_seconds() / 3600
        return age_hours >= 168  # 7 days
    
    def _create_hts_extraction_schema(
        self,
        hts_code: Optional[str] = None,
        extract_notes: bool = True,
        extract_duty_rates: bool = True,
    ) -> Dict[str, Any]:
        """Create JSON schema for HTS data extraction.
        
        Args:
            hts_code: Specific HTS code to focus on
            extract_notes: Whether to extract classification notes
            extract_duty_rates: Whether to extract duty rates
            
        Returns:
            JSON schema for structured extraction
        """
        schema = {
            "type": "object",
            "properties": {
                "hts_entries": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "hts_code": {
                                "type": "string",
                                "description": "HTS classification code (e.g., 1234.56.78)"
                            },
                            "description": {
                                "type": "string",
                                "description": "Product description for the HTS code"
                            },
                            "unit_of_quantity": {
                                "type": "string",
                                "description": "Unit of quantity (e.g., kg, No., m²)"
                            },
                        },
                        "required": ["hts_code", "description"]
                    }
                },
                "chapter_info": {
                    "type": "object",
                    "properties": {
                        "chapter_number": {"type": "string"},
                        "chapter_title": {"type": "string"},
                        "section_number": {"type": "string"},
                        "section_title": {"type": "string"},
                    }
                }
            }
        }
        
        # Add duty rates if requested
        if extract_duty_rates:
            schema["properties"]["hts_entries"]["items"]["properties"]["duty_rates"] = {
                "type": "object",
                "properties": {
                    "general": {"type": "string", "description": "General duty rate"},
                    "special": {"type": "string", "description": "Special duty rate"},
                    "column_2": {"type": "string", "description": "Column 2 duty rate"},
                }
            }
        
        # Add classification notes if requested
        if extract_notes:
            schema["properties"]["classification_notes"] = {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "note_type": {"type": "string", "description": "Type of note (chapter, heading, subheading)"},
                        "note_number": {"type": "string", "description": "Note number or identifier"},
                        "note_text": {"type": "string", "description": "Full text of the classification note"},
                        "applies_to": {"type": "string", "description": "HTS codes this note applies to"},
                    }
                }
            }
        
        return schema
    
    async def _enhance_hts_result(self, result: CrawlResult, **kwargs) -> CrawlResult:
        """Enhance crawl result with HTS-specific processing.
        
        Args:
            result: Base crawl result from Crawl4AI
            **kwargs: Additional processing parameters
            
        Returns:
            Enhanced CrawlResult with HTS-specific data
        """
        if not result.success:
            return result
        
        try:
            # Parse HTS codes from raw content if extraction failed
            if not result.extracted_data.get('hts_entries'):
                hts_codes = self._parse_hts_codes_from_text(result.raw_content)
                if hts_codes:
                    result.extracted_data['hts_entries'] = hts_codes
            
            # Extract chapter/section information
            chapter_info = self._extract_chapter_info(result.raw_content, result.source_url)
            if chapter_info:
                result.extracted_data['chapter_info'] = chapter_info
            
            # Add metadata about extraction quality
            result.extracted_data['extraction_metadata'] = {
                'hts_codes_found': len(result.extracted_data.get('hts_entries', [])),
                'has_duty_rates': any(
                    'duty_rates' in entry 
                    for entry in result.extracted_data.get('hts_entries', [])
                ),
                'has_notes': bool(result.extracted_data.get('classification_notes')),
                'content_type': 'hts_tariff_schedule',
            }
            
            # Recalculate confidence based on HTS-specific criteria
            result.extraction_confidence = self._calculate_hts_confidence(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error enhancing HTS result: {str(e)}")
            return result
    
    def _parse_hts_codes_from_text(self, content: str) -> List[Dict[str, Any]]:
        """Parse HTS codes from raw text content using regex patterns.
        
        Args:
            content: Raw HTML or text content
            
        Returns:
            List of HTS code entries
        """
        hts_entries = []
        
        # Pattern for HTS codes (e.g., 1234.56.78, 1234.56.7890)
        hts_pattern = r'\b(\d{4}\.?\d{2}\.?\d{2,4})\b'
        
        # Find all HTS code matches
        matches = re.finditer(hts_pattern, content)
        
        for match in matches:
            hts_code = match.group(1)
            
            # Try to extract description from surrounding context
            start_pos = max(0, match.start() - 200)
            end_pos = min(len(content), match.end() + 200)
            context = content[start_pos:end_pos]
            
            # Simple heuristic to extract description
            description = self._extract_description_from_context(context, hts_code)
            
            hts_entries.append({
                'hts_code': hts_code,
                'description': description,
                'unit_of_quantity': '',  # Would need more sophisticated parsing
            })
        
        return hts_entries
    
    def _extract_description_from_context(self, context: str, hts_code: str) -> str:
        """Extract product description from context around HTS code.
        
        Args:
            context: Text context around HTS code
            hts_code: The HTS code
            
        Returns:
            Extracted description or empty string
        """
        # Remove HTML tags
        clean_context = re.sub(r'<[^>]+>', ' ', context)
        
        # Split into lines and find the line with the HTS code
        lines = clean_context.split('\n')
        
        for line in lines:
            if hts_code in line:
                # Clean up the line and extract description part
                clean_line = re.sub(r'\s+', ' ', line.strip())
                
                # Try to find description after the HTS code
                parts = clean_line.split(hts_code)
                if len(parts) > 1:
                    description = parts[1].strip()
                    # Remove leading punctuation and numbers
                    description = re.sub(r'^[^\w]*', '', description)
                    # Take first reasonable chunk (up to 200 chars)
                    if len(description) > 200:
                        description = description[:200] + '...'
                    return description
        
        return ''
    
    def _extract_chapter_info(self, content: str, url: str) -> Optional[Dict[str, str]]:
        """Extract HTS chapter and section information.
        
        Args:
            content: Raw content
            url: Source URL
            
        Returns:
            Chapter/section information or None
        """
        chapter_info = {}
        
        # Try to extract from URL first
        url_match = re.search(r'chapter[_-]?(\d+)', url, re.IGNORECASE)
        if url_match:
            chapter_info['chapter_number'] = url_match.group(1)
        
        # Try to extract from content
        chapter_pattern = r'Chapter\s+(\d+)[:\-\s]*([^\n\r]+)'
        chapter_match = re.search(chapter_pattern, content, re.IGNORECASE)
        if chapter_match:
            chapter_info['chapter_number'] = chapter_match.group(1)
            chapter_info['chapter_title'] = chapter_match.group(2).strip()
        
        section_pattern = r'Section\s+([IVXLC]+)[:\-\s]*([^\n\r]+)'
        section_match = re.search(section_pattern, content, re.IGNORECASE)
        if section_match:
            chapter_info['section_number'] = section_match.group(1)
            chapter_info['section_title'] = section_match.group(2).strip()
        
        return chapter_info if chapter_info else None
    
    def _calculate_hts_confidence(self, result: CrawlResult) -> float:
        """Calculate confidence score specific to HTS content.
        
        Args:
            result: Crawl result to evaluate
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        base_confidence = result.extraction_confidence
        
        # Boost confidence based on HTS-specific indicators
        hts_entries = result.extracted_data.get('hts_entries', [])
        
        if hts_entries:
            # More HTS codes found = higher confidence
            code_score = min(len(hts_entries) / 10, 0.3)
            
            # Check if codes have proper format
            valid_codes = sum(1 for entry in hts_entries 
                            if re.match(r'\d{4}\.?\d{2}\.?\d{2,4}', entry.get('hts_code', '')))
            format_score = (valid_codes / len(hts_entries)) * 0.2 if hts_entries else 0
            
            # Check if descriptions are present
            desc_score = sum(1 for entry in hts_entries 
                           if entry.get('description', '').strip()) / len(hts_entries) * 0.2
            
            return min(base_confidence + code_score + format_score + desc_score, 1.0)
        
        return base_confidence * 0.5  # Lower confidence if no HTS codes found
    
    def _extract_hts_urls_from_content(
        self,
        content: str,
        base_url: str,
        chapters: List[str] = None,
        sections: List[str] = None,
    ) -> List[str]:
        """Extract HTS-related URLs from crawled content.
        
        Args:
            content: HTML content to parse
            base_url: Base URL for resolving relative links
            chapters: Filter for specific chapters
            sections: Filter for specific sections
            
        Returns:
            List of HTS URLs
        """
        urls = []
        
        # Pattern for HTS-related links
        link_pattern = r'href=["\']([^"\']*(?:chapter|section|hts|tariff)[^"\']*)["\']'
        
        matches = re.finditer(link_pattern, content, re.IGNORECASE)
        
        for match in matches:
            relative_url = match.group(1)
            absolute_url = urljoin(base_url, relative_url)
            
            # Filter by chapters if specified
            if chapters:
                chapter_match = re.search(r'chapter[_-]?(\d+)', absolute_url, re.IGNORECASE)
                if chapter_match and chapter_match.group(1) not in chapters:
                    continue
            
            # Filter by sections if specified
            if sections:
                section_match = re.search(r'section[_-]?([IVXLC]+)', absolute_url, re.IGNORECASE)
                if section_match and section_match.group(1) not in sections:
                    continue
            
            urls.append(absolute_url)
        
        return urls
    
    def _generate_known_hts_urls(
        self,
        chapters: List[str] = None,
        sections: List[str] = None,
    ) -> List[str]:
        """Generate URLs for known HTS structure.
        
        Args:
            chapters: Specific chapters to include
            sections: Specific sections to include
            
        Returns:
            List of known HTS URLs
        """
        urls = []
        
        # Base HTS URLs
        base_urls = [
            "https://hts.usitc.gov/current",
            "https://hts.usitc.gov/view/Schedule",
        ]
        
        urls.extend(base_urls)
        
        # Add chapter-specific URLs if requested
        if chapters:
            for chapter in chapters:
                chapter_urls = [
                    f"https://hts.usitc.gov/view/Chapter_{chapter}",
                    f"https://hts.usitc.gov/current?chapter={chapter}",
                ]
                urls.extend(chapter_urls)
        
        return urls