"""Sanctions crawler for multi-source sanctions monitoring and discovery."""

import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

from loguru import logger

from ...infrastructure.crawl4ai.client import Crawl4AIClient
from .base_crawler import BaseCrawler
from .models import ComplianceContentType, CrawlResult


class SanctionsCrawler(BaseCrawler):
    """Crawler for multi-source sanctions list monitoring with change detection."""
    
    def __init__(
        self,
        rate_limit: float = 0.5,  # Conservative rate limit for government sites
        **kwargs
    ):
        """Initialize sanctions crawler with multi-source configuration."""
        super().__init__(rate_limit=rate_limit, **kwargs)
        self.base_urls = [
            "https://www.treasury.gov/ofac",
            "https://sanctionssearch.ofac.treas.gov",
            "https://www.bis.doc.gov/index.php/policy-guidance/lists-of-parties-of-concern",
            "https://www.state.gov/sanctions",
        ]
        self.crawl4ai_client: Optional[Crawl4AIClient] = None
    
    def get_content_type(self) -> ComplianceContentType:
        """Return sanctions list as primary content type."""
        return ComplianceContentType.SANCTIONS_LIST
    
    def get_regulatory_authority(self) -> str:
        """Return appropriate authority based on URL context."""
        return "OFAC"  # Default, will be updated based on source
    
    async def crawl(self, url: str, **kwargs) -> CrawlResult:
        """Crawl sanctions content with AI-powered extraction and entity recognition.
        
        Args:
            url: Target sanctions URL to crawl
            **kwargs: Additional parameters including:
                - list_type: Type of sanctions list (SDN, SSI, etc.)
                - extract_entities: Whether to extract entity details (default: True)
                - extract_programs: Whether to extract sanctions programs (default: True)
                - change_detection: Whether to detect changes from previous crawl (default: True)
        
        Returns:
            CrawlResult with extracted sanctions data
        """
        if not self.validate_url(url):
            return self._create_error_result(url, "Invalid URL for sanctions crawler")
        
        try:
            # Initialize Crawl4AI client if needed
            if not self.crawl4ai_client:
                self.crawl4ai_client = Crawl4AIClient(
                    user_agent=self.user_agent,
                    default_timeout=self.timeout,
                )
            
            # Extract parameters
            list_type = kwargs.get('list_type')
            extract_entities = kwargs.get('extract_entities', True)
            extract_programs = kwargs.get('extract_programs', True)
            change_detection = kwargs.get('change_detection', True)
            
            # Create extraction schema for structured sanctions data
            extraction_schema = self._create_sanctions_extraction_schema(
                list_type=list_type,
                extract_entities=extract_entities,
                extract_programs=extract_programs,
            )
            
            # Perform AI-powered crawling with sanctions-specific configuration
            async with self.crawl4ai_client:
                result = await self.crawl4ai_client.extract_content(
                    url=url,
                    content_type=ComplianceContentType.SANCTIONS_LIST,
                    extraction_schema=extraction_schema,
                    wait_for="table, .sanctions-table, .entity-list, .sdn-list",
                )
            
            # Enhance result with sanctions-specific processing
            enhanced_result = await self._enhance_sanctions_result(result, **kwargs)
            
            # Update metadata with crawler-specific information
            enhanced_result.metadata.crawl_session_id = self.session_id
            enhanced_result.metadata.rate_limit_applied = self.rate_limit
            enhanced_result.metadata.regulatory_authority = self._determine_authority(url)
            
            logger.info(f"Successfully crawled sanctions content from {url}")
            return enhanced_result
            
        except Exception as e:
            logger.error(f"Error crawling sanctions content from {url}: {str(e)}")
            return self._create_error_result(url, f"Sanctions crawling failed: {str(e)}")
    
    async def discover_urls(self, base_url: str, **kwargs) -> List[str]:
        """Discover sanctions-related URLs from government websites.
        
        Args:
            base_url: Starting URL for discovery
            **kwargs: Additional parameters including:
                - list_types: List of sanctions list types to discover
                - include_guidance: Whether to include guidance documents (default: True)
                - max_depth: Maximum crawl depth (default: 2)
        
        Returns:
            List of discovered sanctions URLs
        """
        if not self.validate_url(base_url):
            logger.warning(f"Invalid base URL for sanctions discovery: {base_url}")
            return []
        
        discovered_urls = []
        list_types = kwargs.get('list_types', ['SDN', 'SSI', 'EL', 'DPL'])
        include_guidance = kwargs.get('include_guidance', True)
        max_depth = kwargs.get('max_depth', 2)
        
        try:
            # Initialize Crawl4AI client if needed
            if not self.crawl4ai_client:
                self.crawl4ai_client = Crawl4AIClient(
                    user_agent=self.user_agent,
                    default_timeout=self.timeout,
                )
            
            async with self.crawl4ai_client:
                # Crawl the base page to find sanctions navigation
                result = await self.crawl4ai_client.extract_content(
                    url=base_url,
                    content_type=ComplianceContentType.SANCTIONS_LIST,
                    wait_for="a[href*='sanction'], a[href*='sdn'], a[href*='list']",
                )
                
                # Extract sanctions URLs from the crawled content
                urls = self._extract_sanctions_urls_from_content(
                    result.raw_content,
                    base_url,
                    list_types=list_types,
                    include_guidance=include_guidance,
                )
                
                discovered_urls.extend(urls)
            
            # Add known sanctions list URLs
            known_urls = self._generate_known_sanctions_urls(list_types)
            discovered_urls.extend(known_urls)
            
            # Remove duplicates and validate
            unique_urls = list(set(discovered_urls))
            valid_urls = [url for url in unique_urls if self.validate_url(url)]
            
            logger.info(f"Discovered {len(valid_urls)} sanctions URLs from {base_url}")
            return valid_urls[:30]  # Limit to prevent excessive crawling
            
        except Exception as e:
            logger.error(f"Error discovering sanctions URLs from {base_url}: {str(e)}")
            return []
    
    def validate_url(self, url: str) -> bool:
        """Validate if URL is appropriate for sanctions crawler.
        
        Args:
            url: URL to validate
            
        Returns:
            True if URL is valid for sanctions crawling
        """
        if not super().validate_url(url):
            return False
        
        # Check if URL is from valid government domains
        parsed = urlparse(url)
        valid_domains = [
            'treasury.gov', 'ofac.treas.gov', 'sanctionssearch.ofac.treas.gov',
            'bis.doc.gov', 'state.gov', 'export.gov'
        ]
        
        return any(domain in parsed.netloc for domain in valid_domains)
    
    def should_crawl(self, url: str, last_crawled: Optional[datetime] = None) -> bool:
        """Determine if sanctions URL should be crawled based on freshness.
        
        Args:
            url: URL to check
            last_crawled: When this URL was last crawled
            
        Returns:
            True if URL should be crawled
        """
        if not super().should_crawl(url, last_crawled):
            return False
        
        # Sanctions lists change frequently, check daily
        if last_crawled is None:
            return True
        
        # Check sanctions lists daily for updates
        age_hours = (datetime.utcnow() - last_crawled).total_seconds() / 3600
        return age_hours >= 24  # Daily updates
    
    def _determine_authority(self, url: str) -> str:
        """Determine regulatory authority from URL.
        
        Args:
            url: Source URL
            
        Returns:
            Regulatory authority name
        """
        url_lower = url.lower()
        
        if 'ofac' in url_lower or 'treasury.gov' in url_lower:
            return 'OFAC'
        elif 'bis.doc.gov' in url_lower:
            return 'BIS'
        elif 'state.gov' in url_lower:
            return 'State Department'
        else:
            return 'Unknown'
    
    def _create_sanctions_extraction_schema(
        self,
        list_type: Optional[str] = None,
        extract_entities: bool = True,
        extract_programs: bool = True,
    ) -> Dict[str, Any]:
        """Create JSON schema for sanctions data extraction.
        
        Args:
            list_type: Type of sanctions list
            extract_entities: Whether to extract entity details
            extract_programs: Whether to extract sanctions programs
            
        Returns:
            JSON schema for structured extraction
        """
        schema = {
            "type": "object",
            "properties": {
                "list_info": {
                    "type": "object",
                    "properties": {
                        "list_name": {
                            "type": "string",
                            "description": "Name of the sanctions list (SDN, SSI, etc.)"
                        },
                        "last_updated": {
                            "type": "string",
                            "description": "Date the list was last updated"
                        },
                        "total_entries": {
                            "type": "number",
                            "description": "Total number of entries in the list"
                        },
                        "authority": {
                            "type": "string",
                            "description": "Regulatory authority (OFAC, BIS, etc.)"
                        },
                    }
                },
            }
        }
        
        # Add entity extraction if requested
        if extract_entities:
            schema["properties"]["sanctioned_entities"] = {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Primary name of the sanctioned entity"
                        },
                        "entity_type": {
                            "type": "string",
                            "description": "Type of entity (Individual, Entity, Vessel, Aircraft)"
                        },
                        "sdn_number": {
                            "type": "string",
                            "description": "SDN number if applicable"
                        },
                        "aliases": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Alternative names or aliases"
                        },
                        "addresses": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "address": {"type": "string"},
                                    "country": {"type": "string"},
                                    "city": {"type": "string"},
                                }
                            }
                        },
                        "identification": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id_type": {"type": "string", "description": "Type of ID (Passport, Tax ID, etc.)"},
                                    "id_number": {"type": "string"},
                                    "country": {"type": "string"},
                                }
                            }
                        },
                        "programs": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Sanctions programs this entity is subject to"
                        },
                    },
                    "required": ["name"]
                }
            }
        
        # Add program extraction if requested
        if extract_programs:
            schema["properties"]["sanctions_programs"] = {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "program_name": {"type": "string"},
                        "program_code": {"type": "string"},
                        "description": {"type": "string"},
                        "authority": {"type": "string"},
                        "effective_date": {"type": "string"},
                    }
                }
            }
        
        return schema
    
    async def _enhance_sanctions_result(self, result: CrawlResult, **kwargs) -> CrawlResult:
        """Enhance crawl result with sanctions-specific processing.
        
        Args:
            result: Base crawl result from Crawl4AI
            **kwargs: Additional processing parameters
            
        Returns:
            Enhanced CrawlResult with sanctions-specific data
        """
        if not result.success:
            return result
        
        try:
            # Parse sanctions entities from raw content if extraction failed
            if not result.extracted_data.get('sanctioned_entities'):
                entities = self._parse_entities_from_text(result.raw_content)
                if entities:
                    result.extracted_data['sanctioned_entities'] = entities
            
            # Extract list metadata
            if not result.extracted_data.get('list_info'):
                list_info = self._extract_list_metadata(result.raw_content, result.source_url)
                if list_info:
                    result.extracted_data['list_info'] = list_info
            
            # Detect changes if previous data available
            if kwargs.get('change_detection', True):
                changes = self._detect_list_changes(result.extracted_data, kwargs.get('previous_data'))
                if changes:
                    result.extracted_data['changes_detected'] = changes
            
            # Add metadata about extraction quality
            result.extracted_data['extraction_metadata'] = {
                'entities_found': len(result.extracted_data.get('sanctioned_entities', [])),
                'has_list_info': bool(result.extracted_data.get('list_info')),
                'has_programs': bool(result.extracted_data.get('sanctions_programs')),
                'content_type': 'sanctions_list',
                'authority': self._determine_authority(result.source_url),
            }
            
            # Recalculate confidence based on sanctions-specific criteria
            result.extraction_confidence = self._calculate_sanctions_confidence(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error enhancing sanctions result: {str(e)}")
            return result
    
    def _parse_entities_from_text(self, content: str) -> List[Dict[str, Any]]:
        """Parse sanctioned entities from raw text content.
        
        Args:
            content: Raw HTML or text content
            
        Returns:
            List of sanctioned entity entries
        """
        entities = []
        
        # Pattern for SDN numbers
        sdn_pattern = r'\b(\d{4,6})\b'
        
        # Look for table rows or structured data
        # This is a simplified parser - real implementation would be more sophisticated
        lines = content.split('\n')
        
        for line in lines:
            # Skip empty lines and headers
            if not line.strip() or len(line.strip()) < 10:
                continue
            
            # Look for patterns that suggest entity data
            if any(keyword in line.lower() for keyword in ['individual', 'entity', 'vessel', 'aircraft']):
                entity = self._parse_entity_from_line(line)
                if entity:
                    entities.append(entity)
        
        return entities[:100]  # Limit to prevent excessive data
    
    def _parse_entity_from_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse entity information from a single line of text.
        
        Args:
            line: Text line containing entity information
            
        Returns:
            Entity dictionary or None
        """
        # This is a simplified parser - real implementation would be more sophisticated
        parts = line.split('\t')  # Assume tab-separated
        
        if len(parts) < 2:
            parts = re.split(r'\s{2,}', line)  # Split on multiple spaces
        
        if len(parts) >= 2:
            entity = {
                'name': parts[0].strip(),
                'entity_type': 'Unknown',
                'aliases': [],
                'addresses': [],
                'identification': [],
                'programs': [],
            }
            
            # Try to extract entity type
            for part in parts:
                if any(etype in part.lower() for etype in ['individual', 'entity', 'vessel', 'aircraft']):
                    entity['entity_type'] = part.strip()
                    break
            
            # Try to extract SDN number
            sdn_match = re.search(r'\b(\d{4,6})\b', line)
            if sdn_match:
                entity['sdn_number'] = sdn_match.group(1)
            
            return entity
        
        return None
    
    def _extract_list_metadata(self, content: str, url: str) -> Optional[Dict[str, Any]]:
        """Extract sanctions list metadata from content.
        
        Args:
            content: Raw content
            url: Source URL
            
        Returns:
            List metadata or None
        """
        metadata = {}
        
        # Determine list name from URL or content
        if 'sdn' in url.lower():
            metadata['list_name'] = 'SDN'
        elif 'ssi' in url.lower():
            metadata['list_name'] = 'SSI'
        elif 'el' in url.lower() or 'entity' in url.lower():
            metadata['list_name'] = 'Entity List'
        elif 'dpl' in url.lower():
            metadata['list_name'] = 'Denied Persons List'
        
        # Try to extract last updated date
        date_patterns = [
            r'(?:Last Updated|Updated|Modified):\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(?:as of|effective)\s+(\w+\s+\d{1,2},\s*\d{4})',
        ]
        
        for pattern in date_patterns:
            date_match = re.search(pattern, content, re.IGNORECASE)
            if date_match:
                metadata['last_updated'] = date_match.group(1)
                break
        
        # Try to extract total entries count
        count_patterns = [
            r'(\d+)\s+(?:entries|records|individuals|entities)',
            r'Total:\s*(\d+)',
        ]
        
        for pattern in count_patterns:
            count_match = re.search(pattern, content, re.IGNORECASE)
            if count_match:
                metadata['total_entries'] = int(count_match.group(1))
                break
        
        # Set authority
        metadata['authority'] = self._determine_authority(url)
        
        return metadata if metadata else None
    
    def _detect_list_changes(
        self,
        current_data: Dict[str, Any],
        previous_data: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Detect changes between current and previous sanctions data.
        
        Args:
            current_data: Current extraction data
            previous_data: Previous extraction data for comparison
            
        Returns:
            Changes detected or None
        """
        if not previous_data:
            return None
        
        changes = {
            'additions': [],
            'removals': [],
            'modifications': [],
            'summary': {},
        }
        
        # Compare entity counts
        current_entities = current_data.get('sanctioned_entities', [])
        previous_entities = previous_data.get('sanctioned_entities', [])
        
        current_names = {entity.get('name', '') for entity in current_entities}
        previous_names = {entity.get('name', '') for entity in previous_entities}
        
        # Find additions and removals
        additions = current_names - previous_names
        removals = previous_names - current_names
        
        changes['additions'] = list(additions)
        changes['removals'] = list(removals)
        
        # Summary statistics
        changes['summary'] = {
            'total_current': len(current_entities),
            'total_previous': len(previous_entities),
            'net_change': len(current_entities) - len(previous_entities),
            'additions_count': len(additions),
            'removals_count': len(removals),
        }
        
        return changes if (additions or removals) else None
    
    def _calculate_sanctions_confidence(self, result: CrawlResult) -> float:
        """Calculate confidence score specific to sanctions content.
        
        Args:
            result: Crawl result to evaluate
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        base_confidence = result.extraction_confidence
        
        # Boost confidence based on sanctions-specific indicators
        entities = result.extracted_data.get('sanctioned_entities', [])
        list_info = result.extracted_data.get('list_info', {})
        
        # Check for essential sanctions elements
        has_entities = len(entities) > 0
        has_list_info = bool(list_info)
        has_authority = bool(list_info.get('authority'))
        
        # Calculate component scores
        structure_score = sum([has_entities, has_list_info, has_authority]) / 3 * 0.3
        
        # Entity quality score
        if entities:
            valid_entities = sum(1 for entity in entities if entity.get('name', '').strip())
            entity_score = (valid_entities / len(entities)) * 0.3
        else:
            entity_score = 0.0
        
        # Check for sanctions-specific keywords
        sanctions_terms = ['sdn', 'ofac', 'sanctions', 'blocked', 'designated', 'entity list']
        term_matches = sum(1 for term in sanctions_terms 
                          if term.lower() in result.raw_content.lower())
        term_score = min(term_matches / len(sanctions_terms), 1.0) * 0.4
        
        return min(base_confidence + structure_score + entity_score + term_score, 1.0)
    
    def _extract_sanctions_urls_from_content(
        self,
        content: str,
        base_url: str,
        list_types: List[str] = None,
        include_guidance: bool = True,
    ) -> List[str]:
        """Extract sanctions-related URLs from crawled content.
        
        Args:
            content: HTML content to parse
            base_url: Base URL for resolving relative links
            list_types: Filter for specific list types
            include_guidance: Whether to include guidance documents
            
        Returns:
            List of sanctions URLs
        """
        urls = []
        
        # Pattern for sanctions-related links
        link_patterns = [
            r'href=["\']([^"\']*(?:sanction|sdn|ssi|entity|dpl)[^"\']*)["\']',
            r'href=["\']([^"\']*(?:ofac|bis|treasury)[^"\']*)["\']',
        ]
        
        for pattern in link_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            
            for match in matches:
                relative_url = match.group(1)
                absolute_url = urljoin(base_url, relative_url)
                
                # Filter by list types if specified
                if list_types:
                    if not any(list_type.lower() in absolute_url.lower() 
                             for list_type in list_types):
                        continue
                
                # Skip guidance documents if not requested
                if not include_guidance:
                    if any(term in absolute_url.lower() 
                          for term in ['guidance', 'faq', 'help', 'about']):
                        continue
                
                urls.append(absolute_url)
        
        return urls
    
    def _generate_known_sanctions_urls(self, list_types: List[str] = None) -> List[str]:
        """Generate URLs for known sanctions lists.
        
        Args:
            list_types: Specific list types to include
            
        Returns:
            List of known sanctions URLs
        """
        urls = []
        
        # Base sanctions URLs
        base_urls = [
            "https://sanctionssearch.ofac.treas.gov/",
            "https://www.treasury.gov/ofac/downloads/",
        ]
        
        urls.extend(base_urls)
        
        # Add list-specific URLs if requested
        if list_types:
            list_urls = {
                'SDN': [
                    "https://www.treasury.gov/ofac/downloads/sdn.xml",
                    "https://www.treasury.gov/ofac/downloads/sdn.pdf",
                ],
                'SSI': [
                    "https://www.treasury.gov/ofac/downloads/ssi.xml",
                ],
                'EL': [
                    "https://www.bis.doc.gov/index.php/policy-guidance/lists-of-parties-of-concern/entity-list",
                ],
                'DPL': [
                    "https://www.bis.doc.gov/index.php/policy-guidance/lists-of-parties-of-concern/denied-persons-list",
                ],
            }
            
            for list_type in list_types:
                if list_type in list_urls:
                    urls.extend(list_urls[list_type])
        
        return urls