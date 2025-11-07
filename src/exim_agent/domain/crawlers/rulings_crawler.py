"""CBP rulings crawler for advanced CROSS scraping with AI-powered content parsing."""

import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse, parse_qs

from loguru import logger

from ...infrastructure.crawl4ai.client import Crawl4AIClient
from .base_crawler import BaseCrawler
from .models import ComplianceContentType, CrawlResult


class RulingsCrawler(BaseCrawler):
    """Crawler for CBP CROSS rulings with enhanced content extraction and analysis."""
    
    def __init__(
        self,
        rate_limit: float = 0.7,  # Moderate rate limit for CBP
        **kwargs
    ):
        """Initialize CBP rulings crawler with CROSS-specific configuration."""
        super().__init__(rate_limit=rate_limit, **kwargs)
        self.base_urls = [
            "https://rulings.cbp.gov",
            "https://www.cbp.gov/trade/rulings",
        ]
        self.crawl4ai_client: Optional[Crawl4AIClient] = None
    
    def get_content_type(self) -> ComplianceContentType:
        """Return CBP ruling as primary content type."""
        return ComplianceContentType.CBP_RULING
    
    def get_regulatory_authority(self) -> str:
        """Return CBP as regulatory authority."""
        return "CBP"
    
    async def crawl(self, url: str, **kwargs) -> CrawlResult:
        """Crawl CBP ruling content with AI-powered extraction and analysis.
        
        Args:
            url: Target CBP ruling URL to crawl
            **kwargs: Additional parameters including:
                - ruling_number: Specific ruling number to extract (optional)
                - extract_precedents: Whether to find related rulings (default: True)
                - extract_rationale: Whether to extract classification rationale (default: True)
                - deep_analysis: Whether to perform deep content analysis (default: False)
        
        Returns:
            CrawlResult with extracted ruling data and analysis
        """
        if not self.validate_url(url):
            return self._create_error_result(url, "Invalid URL for CBP rulings crawler")
        
        try:
            # Initialize Crawl4AI client if needed
            if not self.crawl4ai_client:
                self.crawl4ai_client = Crawl4AIClient(
                    user_agent=self.user_agent,
                    default_timeout=self.timeout,
                )
            
            # Extract parameters
            ruling_number = kwargs.get('ruling_number')
            extract_precedents = kwargs.get('extract_precedents', True)
            extract_rationale = kwargs.get('extract_rationale', True)
            deep_analysis = kwargs.get('deep_analysis', False)
            
            # Create extraction schema for structured ruling data
            extraction_schema = self._create_ruling_extraction_schema(
                ruling_number=ruling_number,
                extract_precedents=extract_precedents,
                extract_rationale=extract_rationale,
                deep_analysis=deep_analysis,
            )
            
            # Perform AI-powered crawling with ruling-specific configuration
            async with self.crawl4ai_client:
                result = await self.crawl4ai_client.extract_content(
                    url=url,
                    content_type=ComplianceContentType.CBP_RULING,
                    extraction_schema=extraction_schema,
                    wait_for=".ruling-content, .decision-content, main, .content",
                )
            
            # Enhance result with CBP-specific processing and analysis
            enhanced_result = await self._enhance_ruling_result(result, **kwargs)
            
            # Update metadata with crawler-specific information
            enhanced_result.metadata.crawl_session_id = self.session_id
            enhanced_result.metadata.rate_limit_applied = self.rate_limit
            
            logger.info(f"Successfully crawled CBP ruling from {url}")
            return enhanced_result
            
        except Exception as e:
            logger.error(f"Error crawling CBP ruling from {url}: {str(e)}")
            return self._create_error_result(url, f"CBP ruling crawling failed: {str(e)}")
    
    async def discover_urls(self, base_url: str, **kwargs) -> List[str]:
        """Discover CBP ruling URLs from CROSS and related systems.
        
        Args:
            base_url: Starting URL for discovery (should be CBP domain)
            **kwargs: Additional parameters including:
                - date_range: Tuple of (start_date, end_date) for filtering
                - hts_codes: List of HTS codes to search for
                - keywords: List of keywords to search for
                - max_results: Maximum number of URLs to return (default: 100)
        
        Returns:
            List of discovered CBP ruling URLs
        """
        if not self.validate_url(base_url):
            logger.warning(f"Invalid base URL for CBP ruling discovery: {base_url}")
            return []
        
        discovered_urls = []
        date_range = kwargs.get('date_range')
        hts_codes = kwargs.get('hts_codes', [])
        keywords = kwargs.get('keywords', [])
        max_results = kwargs.get('max_results', 100)
        
        try:
            # Initialize Crawl4AI client if needed
            if not self.crawl4ai_client:
                self.crawl4ai_client = Crawl4AIClient(
                    user_agent=self.user_agent,
                    default_timeout=self.timeout,
                )
            
            async with self.crawl4ai_client:
                # Crawl the base page to find ruling navigation and search
                result = await self.crawl4ai_client.extract_content(
                    url=base_url,
                    content_type=ComplianceContentType.CBP_RULING,
                    wait_for="a[href*='ruling'], a[href*='decision'], .search-results",
                )
                
                # Extract ruling URLs from the crawled content
                urls = self._extract_ruling_urls_from_content(
                    result.raw_content,
                    base_url,
                    hts_codes=hts_codes,
                    keywords=keywords,
                )
                
                discovered_urls.extend(urls)
            
            # Generate search URLs for specific criteria
            search_urls = self._generate_ruling_search_urls(
                base_url,
                date_range=date_range,
                hts_codes=hts_codes,
                keywords=keywords,
            )
            
            # Crawl search results to find more rulings
            for search_url in search_urls[:5]:  # Limit search pages
                try:
                    async with self.crawl4ai_client:
                        search_result = await self.crawl4ai_client.extract_content(
                            url=search_url,
                            content_type=ComplianceContentType.CBP_RULING,
                            wait_for=".search-results, .ruling-list",
                        )
                    
                    search_urls_found = self._extract_ruling_urls_from_content(
                        search_result.raw_content,
                        search_url,
                    )
                    discovered_urls.extend(search_urls_found)
                    
                except Exception as e:
                    logger.warning(f"Error crawling search results from {search_url}: {str(e)}")
                    continue
            
            # Remove duplicates and validate
            unique_urls = list(set(discovered_urls))
            valid_urls = [url for url in unique_urls if self.validate_url(url)]
            
            # Sort by likely relevance (newer rulings first)
            sorted_urls = self._sort_ruling_urls_by_relevance(valid_urls)
            
            logger.info(f"Discovered {len(sorted_urls)} CBP ruling URLs from {base_url}")
            return sorted_urls[:max_results]
            
        except Exception as e:
            logger.error(f"Error discovering CBP ruling URLs from {base_url}: {str(e)}")
            return []
    
    def validate_url(self, url: str) -> bool:
        """Validate if URL is appropriate for CBP rulings crawler.
        
        Args:
            url: URL to validate
            
        Returns:
            True if URL is valid for CBP ruling crawling
        """
        if not super().validate_url(url):
            return False
        
        # Check if URL is from CBP domain
        parsed = urlparse(url)
        valid_domains = ['rulings.cbp.gov', 'cbp.gov', 'www.cbp.gov']
        
        return any(domain in parsed.netloc for domain in valid_domains)
    
    def should_crawl(self, url: str, last_crawled: Optional[datetime] = None) -> bool:
        """Determine if CBP ruling URL should be crawled based on freshness.
        
        Args:
            url: URL to check
            last_crawled: When this URL was last crawled
            
        Returns:
            True if URL should be crawled
        """
        if not super().should_crawl(url, last_crawled):
            return False
        
        # CBP rulings are static once published, but we may want to check for updates
        if last_crawled is None:
            return True
        
        # Check rulings monthly for any updates or corrections
        age_hours = (datetime.utcnow() - last_crawled).total_seconds() / 3600
        return age_hours >= 720  # 30 days
    
    def _create_ruling_extraction_schema(
        self,
        ruling_number: Optional[str] = None,
        extract_precedents: bool = True,
        extract_rationale: bool = True,
        deep_analysis: bool = False,
    ) -> Dict[str, Any]:
        """Create JSON schema for CBP ruling data extraction.
        
        Args:
            ruling_number: Specific ruling number to focus on
            extract_precedents: Whether to extract related rulings
            extract_rationale: Whether to extract classification rationale
            deep_analysis: Whether to perform deep content analysis
            
        Returns:
            JSON schema for structured extraction
        """
        schema = {
            "type": "object",
            "properties": {
                "ruling_info": {
                    "type": "object",
                    "properties": {
                        "ruling_number": {
                            "type": "string",
                            "description": "CBP ruling number (e.g., HQ H301234, NY N123456)"
                        },
                        "ruling_date": {
                            "type": "string",
                            "description": "Date the ruling was issued (YYYY-MM-DD format)"
                        },
                        "ruling_type": {
                            "type": "string",
                            "description": "Type of ruling (HQ, NY, etc.)"
                        },
                        "subject": {
                            "type": "string",
                            "description": "Subject or title of the ruling"
                        },
                        "requestor": {
                            "type": "string",
                            "description": "Entity that requested the ruling"
                        },
                    },
                    "required": ["ruling_number"]
                },
                "classification": {
                    "type": "object",
                    "properties": {
                        "hts_code": {
                            "type": "string",
                            "description": "HTS classification code determined by the ruling"
                        },
                        "product_description": {
                            "type": "string",
                            "description": "Description of the product being classified"
                        },
                        "country_of_origin": {
                            "type": "string",
                            "description": "Country of origin if specified"
                        },
                    }
                },
            },
            "required": ["ruling_info"]
        }
        
        # Add rationale extraction if requested
        if extract_rationale:
            schema["properties"]["rationale"] = {
                "type": "object",
                "properties": {
                    "legal_analysis": {
                        "type": "string",
                        "description": "Legal reasoning and analysis for the classification"
                    },
                    "cited_authorities": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Legal authorities, regulations, or precedents cited"
                    },
                    "key_factors": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Key factors considered in the classification decision"
                    },
                }
            }
        
        # Add precedent analysis if requested
        if extract_precedents:
            schema["properties"]["related_rulings"] = {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "ruling_number": {"type": "string"},
                        "relationship": {"type": "string", "description": "How this ruling relates (cited, similar, overruled, etc.)"},
                        "relevance": {"type": "string", "description": "Why this ruling is relevant"},
                    }
                }
            }
        
        # Add deep analysis if requested
        if deep_analysis:
            schema["properties"]["analysis"] = {
                "type": "object",
                "properties": {
                    "complexity_score": {
                        "type": "number",
                        "description": "Complexity score from 1-10 based on legal analysis depth"
                    },
                    "precedent_value": {
                        "type": "string",
                        "description": "Assessment of precedential value (high, medium, low)"
                    },
                    "industry_impact": {
                        "type": "string",
                        "description": "Potential impact on industry or trade"
                    },
                    "key_insights": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Key insights or takeaways from the ruling"
                    },
                }
            }
        
        return schema
    
    async def _enhance_ruling_result(self, result: CrawlResult, **kwargs) -> CrawlResult:
        """Enhance crawl result with CBP ruling-specific processing and analysis.
        
        Args:
            result: Base crawl result from Crawl4AI
            **kwargs: Additional processing parameters
            
        Returns:
            Enhanced CrawlResult with ruling-specific data and analysis
        """
        if not result.success:
            return result
        
        try:
            # Parse ruling information from raw content if extraction failed
            if not result.extracted_data.get('ruling_info'):
                ruling_info = self._parse_ruling_info_from_text(result.raw_content)
                if ruling_info:
                    result.extracted_data['ruling_info'] = ruling_info
            
            # Extract classification information
            if not result.extracted_data.get('classification'):
                classification = self._extract_classification_info(result.raw_content)
                if classification:
                    result.extracted_data['classification'] = classification
            
            # Find related rulings mentioned in the text
            if kwargs.get('extract_precedents', True):
                related_rulings = self._find_related_rulings_in_text(result.raw_content)
                if related_rulings:
                    result.extracted_data['related_rulings'] = related_rulings
            
            # Extract legal rationale and analysis
            if kwargs.get('extract_rationale', True):
                rationale = self._extract_legal_rationale(result.raw_content)
                if rationale:
                    result.extracted_data['rationale'] = rationale
            
            # Add metadata about extraction quality and content analysis
            result.extracted_data['extraction_metadata'] = {
                'has_ruling_number': bool(result.extracted_data.get('ruling_info', {}).get('ruling_number')),
                'has_hts_classification': bool(result.extracted_data.get('classification', {}).get('hts_code')),
                'has_rationale': bool(result.extracted_data.get('rationale')),
                'related_rulings_count': len(result.extracted_data.get('related_rulings', [])),
                'content_type': 'cbp_ruling',
                'word_count': len(result.raw_content.split()),
            }
            
            # Recalculate confidence based on ruling-specific criteria
            result.extraction_confidence = self._calculate_ruling_confidence(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error enhancing CBP ruling result: {str(e)}")
            return result
    
    def _parse_ruling_info_from_text(self, content: str) -> Optional[Dict[str, Any]]:
        """Parse basic ruling information from raw text content.
        
        Args:
            content: Raw HTML or text content
            
        Returns:
            Dictionary with ruling information or None
        """
        ruling_info = {}
        
        # Pattern for CBP ruling numbers (HQ, NY, etc.)
        ruling_pattern = r'\b([A-Z]{2,3}\s*[A-Z]?\d{6,8})\b'
        ruling_match = re.search(ruling_pattern, content)
        if ruling_match:
            ruling_info['ruling_number'] = ruling_match.group(1).replace(' ', '')
        
        # Pattern for dates (various formats)
        date_patterns = [
            r'(?:Date|Dated|Issued):\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(\w+\s+\d{1,2},\s*\d{4})',
        ]
        
        for pattern in date_patterns:
            date_match = re.search(pattern, content, re.IGNORECASE)
            if date_match:
                ruling_info['ruling_date'] = date_match.group(1)
                break
        
        # Extract subject/title
        subject_patterns = [
            r'(?:Subject|Re|Title):\s*([^\n\r]+)',
            r'<title>([^<]+)</title>',
        ]
        
        for pattern in subject_patterns:
            subject_match = re.search(pattern, content, re.IGNORECASE)
            if subject_match:
                subject = subject_match.group(1).strip()
                if len(subject) > 10:  # Reasonable subject length
                    ruling_info['subject'] = subject
                    break
        
        # Extract requestor information
        requestor_patterns = [
            r'(?:Requestor|From|Submitted by):\s*([^\n\r]+)',
            r'Dear\s+([^,\n\r]+)',
        ]
        
        for pattern in requestor_patterns:
            requestor_match = re.search(pattern, content, re.IGNORECASE)
            if requestor_match:
                ruling_info['requestor'] = requestor_match.group(1).strip()
                break
        
        return ruling_info if ruling_info else None
    
    def _extract_classification_info(self, content: str) -> Optional[Dict[str, Any]]:
        """Extract HTS classification information from ruling content.
        
        Args:
            content: Raw content
            
        Returns:
            Classification information or None
        """
        classification = {}
        
        # Pattern for HTS codes
        hts_pattern = r'\b(\d{4}\.?\d{2}\.?\d{2,4})\b'
        hts_matches = re.findall(hts_pattern, content)
        if hts_matches:
            # Take the most frequently mentioned HTS code
            from collections import Counter
            most_common = Counter(hts_matches).most_common(1)
            classification['hts_code'] = most_common[0][0]
        
        # Extract product description
        product_patterns = [
            r'(?:Product|Merchandise|Item|Article):\s*([^\n\r]+)',
            r'(?:Description|Described as):\s*([^\n\r]+)',
        ]
        
        for pattern in product_patterns:
            product_match = re.search(pattern, content, re.IGNORECASE)
            if product_match:
                description = product_match.group(1).strip()
                if len(description) > 10:
                    classification['product_description'] = description
                    break
        
        # Extract country of origin
        country_patterns = [
            r'(?:Country of origin|Origin|Made in|From)\s*:\s*([A-Za-z\s]+)',
            r'(?:imported from|originating in)\s+([A-Za-z\s]+)',
        ]
        
        for pattern in country_patterns:
            country_match = re.search(pattern, content, re.IGNORECASE)
            if country_match:
                country = country_match.group(1).strip()
                if len(country) > 2 and len(country) < 50:
                    classification['country_of_origin'] = country
                    break
        
        return classification if classification else None
    
    def _find_related_rulings_in_text(self, content: str) -> List[Dict[str, Any]]:
        """Find references to other CBP rulings in the text.
        
        Args:
            content: Raw content to search
            
        Returns:
            List of related ruling references
        """
        related_rulings = []
        
        # Pattern for ruling references
        ruling_ref_pattern = r'\b([A-Z]{2,3}\s*[A-Z]?\d{6,8})\b'
        
        matches = re.finditer(ruling_ref_pattern, content)
        
        for match in matches:
            ruling_number = match.group(1).replace(' ', '')
            
            # Get context around the match to determine relationship
            start_pos = max(0, match.start() - 100)
            end_pos = min(len(content), match.end() + 100)
            context = content[start_pos:end_pos].lower()
            
            # Determine relationship type based on context
            relationship = "mentioned"
            if any(word in context for word in ['cited', 'cites', 'citing']):
                relationship = "cited"
            elif any(word in context for word in ['similar', 'comparable', 'like']):
                relationship = "similar"
            elif any(word in context for word in ['overruled', 'revoked', 'superseded']):
                relationship = "overruled"
            elif any(word in context for word in ['distinguished', 'different']):
                relationship = "distinguished"
            
            related_rulings.append({
                'ruling_number': ruling_number,
                'relationship': relationship,
                'relevance': context[:200] + '...' if len(context) > 200 else context,
            })
        
        # Remove duplicates
        seen = set()
        unique_rulings = []
        for ruling in related_rulings:
            if ruling['ruling_number'] not in seen:
                seen.add(ruling['ruling_number'])
                unique_rulings.append(ruling)
        
        return unique_rulings
    
    def _extract_legal_rationale(self, content: str) -> Optional[Dict[str, Any]]:
        """Extract legal reasoning and analysis from ruling content.
        
        Args:
            content: Raw content
            
        Returns:
            Legal rationale information or None
        """
        rationale = {}
        
        # Look for analysis sections
        analysis_patterns = [
            r'(?:Analysis|Discussion|Reasoning|Rationale):\s*([^§]+?)(?:\n\n|\n[A-Z])',
            r'(?:LAW AND ANALYSIS|LEGAL ANALYSIS):\s*([^§]+?)(?:\n\n|\n[A-Z])',
        ]
        
        for pattern in analysis_patterns:
            analysis_match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if analysis_match:
                analysis_text = analysis_match.group(1).strip()
                if len(analysis_text) > 50:
                    rationale['legal_analysis'] = analysis_text[:2000]  # Limit length
                    break
        
        # Extract cited authorities (regulations, cases, etc.)
        authority_patterns = [
            r'\b(\d+\s+CFR\s+\d+(?:\.\d+)*)\b',
            r'\b(19\s+U\.?S\.?C\.?\s+\d+)\b',
            r'\b(GRI\s+\d+[a-z]?)\b',
            r'\b(Additional\s+U\.?S\.?\s+Note\s+\d+)\b',
        ]
        
        cited_authorities = []
        for pattern in authority_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            cited_authorities.extend(matches)
        
        if cited_authorities:
            rationale['cited_authorities'] = list(set(cited_authorities))
        
        # Extract key factors (look for numbered or bulleted lists)
        factor_patterns = [
            r'(?:factors?|considerations?|elements?).*?:\s*([^§]+?)(?:\n\n|\n[A-Z])',
        ]
        
        key_factors = []
        for pattern in factor_patterns:
            factor_match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if factor_match:
                factor_text = factor_match.group(1)
                # Split on numbered items or bullet points
                factors = re.split(r'\n\s*(?:\d+\.|\*|\-)\s*', factor_text)
                key_factors.extend([f.strip() for f in factors if len(f.strip()) > 10])
        
        if key_factors:
            rationale['key_factors'] = key_factors[:10]  # Limit to top 10
        
        return rationale if rationale else None
    
    def _calculate_ruling_confidence(self, result: CrawlResult) -> float:
        """Calculate confidence score specific to CBP ruling content.
        
        Args:
            result: Crawl result to evaluate
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        base_confidence = result.extraction_confidence
        
        # Boost confidence based on ruling-specific indicators
        ruling_info = result.extracted_data.get('ruling_info', {})
        classification = result.extracted_data.get('classification', {})
        
        # Check for essential ruling elements
        has_ruling_number = bool(ruling_info.get('ruling_number'))
        has_hts_code = bool(classification.get('hts_code'))
        has_product_desc = bool(classification.get('product_description'))
        has_rationale = bool(result.extracted_data.get('rationale'))
        
        # Calculate component scores
        structure_score = sum([has_ruling_number, has_hts_code, has_product_desc]) / 3 * 0.3
        content_score = 0.2 if has_rationale else 0.1
        
        # Check content quality indicators
        word_count = len(result.raw_content.split())
        length_score = min(word_count / 1000, 1.0) * 0.2  # Longer rulings often more complete
        
        # Check for legal terminology
        legal_terms = ['classification', 'tariff', 'hts', 'cbp', 'ruling', 'analysis']
        term_matches = sum(1 for term in legal_terms if term.lower() in result.raw_content.lower())
        term_score = min(term_matches / len(legal_terms), 1.0) * 0.3
        
        return min(base_confidence + structure_score + content_score + length_score + term_score, 1.0)
    
    def _extract_ruling_urls_from_content(
        self,
        content: str,
        base_url: str,
        hts_codes: List[str] = None,
        keywords: List[str] = None,
    ) -> List[str]:
        """Extract CBP ruling URLs from crawled content.
        
        Args:
            content: HTML content to parse
            base_url: Base URL for resolving relative links
            hts_codes: Filter for specific HTS codes
            keywords: Filter for specific keywords
            
        Returns:
            List of ruling URLs
        """
        urls = []
        
        # Pattern for ruling-related links
        link_pattern = r'href=["\']([^"\']*(?:ruling|decision|HQ|NY)[^"\']*)["\']'
        
        matches = re.finditer(link_pattern, content, re.IGNORECASE)
        
        for match in matches:
            relative_url = match.group(1)
            absolute_url = urljoin(base_url, relative_url)
            
            # Basic filtering
            if hts_codes or keywords:
                # Get surrounding context for filtering
                start_pos = max(0, match.start() - 200)
                end_pos = min(len(content), match.end() + 200)
                context = content[start_pos:end_pos].lower()
                
                # Filter by HTS codes if specified
                if hts_codes:
                    if not any(code.lower() in context for code in hts_codes):
                        continue
                
                # Filter by keywords if specified
                if keywords:
                    if not any(keyword.lower() in context for keyword in keywords):
                        continue
            
            urls.append(absolute_url)
        
        return urls
    
    def _generate_ruling_search_urls(
        self,
        base_url: str,
        date_range: Optional[tuple] = None,
        hts_codes: List[str] = None,
        keywords: List[str] = None,
    ) -> List[str]:
        """Generate search URLs for finding specific rulings.
        
        Args:
            base_url: Base CBP URL
            date_range: Tuple of (start_date, end_date)
            hts_codes: List of HTS codes to search for
            keywords: List of keywords to search for
            
        Returns:
            List of search URLs
        """
        search_urls = []
        
        # Base search URLs for CBP CROSS
        base_search_urls = [
            "https://rulings.cbp.gov/search",
            "https://www.cbp.gov/trade/rulings/search",
        ]
        
        for search_base in base_search_urls:
            # Add date range searches
            if date_range:
                start_date, end_date = date_range
                search_urls.append(
                    f"{search_base}?start_date={start_date}&end_date={end_date}"
                )
            
            # Add HTS code searches
            if hts_codes:
                for hts_code in hts_codes[:5]:  # Limit to prevent too many requests
                    search_urls.append(f"{search_base}?hts={hts_code}")
            
            # Add keyword searches
            if keywords:
                for keyword in keywords[:5]:  # Limit to prevent too many requests
                    search_urls.append(f"{search_base}?q={keyword}")
        
        return search_urls
    
    def _sort_ruling_urls_by_relevance(self, urls: List[str]) -> List[str]:
        """Sort ruling URLs by likely relevance (newer rulings first).
        
        Args:
            urls: List of URLs to sort
            
        Returns:
            Sorted list of URLs
        """
        def extract_date_score(url: str) -> float:
            """Extract a date-based relevance score from URL."""
            # Look for year patterns in URL
            year_match = re.search(r'20(\d{2})', url)
            if year_match:
                year = int(year_match.group(0))
                current_year = datetime.now().year
                # More recent years get higher scores
                return max(0, (year - 2000) / (current_year - 2000))
            return 0.5  # Default score for URLs without clear dates
        
        # Sort by date score (descending) and then alphabetically
        return sorted(urls, key=lambda url: (-extract_date_score(url), url))