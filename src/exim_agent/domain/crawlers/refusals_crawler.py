"""Refusals crawler for FDA and regulatory agency refusal data collection."""

import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

from loguru import logger

from ...infrastructure.crawl4ai.client import Crawl4AIClient
from .base_crawler import BaseCrawler
from .models import ComplianceContentType, CrawlResult


class RefusalsCrawler(BaseCrawler):
    """Crawler for FDA and regulatory agency refusal data with product categorization."""
    
    def __init__(
        self,
        rate_limit: float = 0.5,  # Conservative rate limit for FDA
        **kwargs
    ):
        """Initialize refusals crawler with FDA-specific configuration."""
        super().__init__(rate_limit=rate_limit, **kwargs)
        self.base_urls = [
            "https://www.accessdata.fda.gov/scripts/importrefusals/",
            "https://www.fda.gov/food/importing-food-products-united-states",
            "https://www.cbp.gov/trade/basic-import-export/import-docs",
        ]
        self.crawl4ai_client: Optional[Crawl4AIClient] = None
    
    def get_content_type(self) -> ComplianceContentType:
        """Return FDA refusal as primary content type."""
        return ComplianceContentType.FDA_REFUSAL
    
    def get_regulatory_authority(self) -> str:
        """Return appropriate authority based on URL context."""
        return "FDA"  # Default, will be updated based on source
    
    async def crawl(self, url: str, **kwargs) -> CrawlResult:
        """Crawl refusal data with AI-powered extraction and risk assessment.
        
        Args:
            url: Target refusal URL to crawl
            **kwargs: Additional parameters including:
                - date_range: Tuple of (start_date, end_date) for filtering
                - product_categories: List of product categories to focus on
                - extract_risk_factors: Whether to extract risk assessment (default: True)
                - extract_firms: Whether to extract firm information (default: True)
        
        Returns:
            CrawlResult with extracted refusal data and risk assessment
        """
        if not self.validate_url(url):
            return self._create_error_result(url, "Invalid URL for refusals crawler")
        
        try:
            # Initialize Crawl4AI client if needed
            if not self.crawl4ai_client:
                self.crawl4ai_client = Crawl4AIClient(
                    user_agent=self.user_agent,
                    default_timeout=self.timeout,
                )
            
            # Extract parameters
            date_range = kwargs.get('date_range')
            product_categories = kwargs.get('product_categories', [])
            extract_risk_factors = kwargs.get('extract_risk_factors', True)
            extract_firms = kwargs.get('extract_firms', True)
            
            # Create extraction schema for structured refusal data
            extraction_schema = self._create_refusal_extraction_schema(
                date_range=date_range,
                product_categories=product_categories,
                extract_risk_factors=extract_risk_factors,
                extract_firms=extract_firms,
            )
            
            # Perform AI-powered crawling with refusal-specific configuration
            async with self.crawl4ai_client:
                result = await self.crawl4ai_client.extract_content(
                    url=url,
                    content_type=ComplianceContentType.FDA_REFUSAL,
                    extraction_schema=extraction_schema,
                    wait_for="table, .refusal-table, .import-alert, .data-table",
                )
            
            # Enhance result with refusal-specific processing and risk assessment
            enhanced_result = await self._enhance_refusal_result(result, **kwargs)
            
            # Update metadata with crawler-specific information
            enhanced_result.metadata.crawl_session_id = self.session_id
            enhanced_result.metadata.rate_limit_applied = self.rate_limit
            enhanced_result.metadata.regulatory_authority = self._determine_authority(url)
            
            logger.info(f"Successfully crawled refusal data from {url}")
            return enhanced_result
            
        except Exception as e:
            logger.error(f"Error crawling refusal data from {url}: {str(e)}")
            return self._create_error_result(url, f"Refusal crawling failed: {str(e)}")
    
    async def discover_urls(self, base_url: str, **kwargs) -> List[str]:
        """Discover refusal-related URLs from FDA and regulatory websites.
        
        Args:
            base_url: Starting URL for discovery
            **kwargs: Additional parameters including:
                - agencies: List of agencies to include (FDA, USDA, etc.)
                - product_types: List of product types to focus on
                - include_alerts: Whether to include import alerts (default: True)
        
        Returns:
            List of discovered refusal URLs
        """
        if not self.validate_url(base_url):
            logger.warning(f"Invalid base URL for refusal discovery: {base_url}")
            return []
        
        discovered_urls = []
        agencies = kwargs.get('agencies', ['FDA', 'USDA', 'CBP'])
        product_types = kwargs.get('product_types', [])
        include_alerts = kwargs.get('include_alerts', True)
        
        try:
            # Initialize Crawl4AI client if needed
            if not self.crawl4ai_client:
                self.crawl4ai_client = Crawl4AIClient(
                    user_agent=self.user_agent,
                    default_timeout=self.timeout,
                )
            
            async with self.crawl4ai_client:
                # Crawl the base page to find refusal navigation
                result = await self.crawl4ai_client.extract_content(
                    url=base_url,
                    content_type=ComplianceContentType.FDA_REFUSAL,
                    wait_for="a[href*='refusal'], a[href*='import'], a[href*='alert']",
                )
                
                # Extract refusal URLs from the crawled content
                urls = self._extract_refusal_urls_from_content(
                    result.raw_content,
                    base_url,
                    agencies=agencies,
                    product_types=product_types,
                    include_alerts=include_alerts,
                )
                
                discovered_urls.extend(urls)
            
            # Add known refusal system URLs
            known_urls = self._generate_known_refusal_urls(agencies, include_alerts)
            discovered_urls.extend(known_urls)
            
            # Remove duplicates and validate
            unique_urls = list(set(discovered_urls))
            valid_urls = [url for url in unique_urls if self.validate_url(url)]
            
            logger.info(f"Discovered {len(valid_urls)} refusal URLs from {base_url}")
            return valid_urls[:25]  # Limit to prevent excessive crawling
            
        except Exception as e:
            logger.error(f"Error discovering refusal URLs from {base_url}: {str(e)}")
            return []
    
    def validate_url(self, url: str) -> bool:
        """Validate if URL is appropriate for refusals crawler.
        
        Args:
            url: URL to validate
            
        Returns:
            True if URL is valid for refusal crawling
        """
        if not super().validate_url(url):
            return False
        
        # Check if URL is from valid regulatory domains
        parsed = urlparse(url)
        valid_domains = [
            'fda.gov', 'accessdata.fda.gov', 'usda.gov', 'cbp.gov',
            'aphis.usda.gov', 'fsis.usda.gov'
        ]
        
        return any(domain in parsed.netloc for domain in valid_domains)
    
    def should_crawl(self, url: str, last_crawled: Optional[datetime] = None) -> bool:
        """Determine if refusal URL should be crawled based on freshness.
        
        Args:
            url: URL to check
            last_crawled: When this URL was last crawled
            
        Returns:
            True if URL should be crawled
        """
        if not super().should_crawl(url, last_crawled):
            return False
        
        # Refusal data updates frequently, check daily
        if last_crawled is None:
            return True
        
        # Check refusal data daily for new entries
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
        
        if 'fda.gov' in url_lower:
            return 'FDA'
        elif 'usda.gov' in url_lower:
            return 'USDA'
        elif 'cbp.gov' in url_lower:
            return 'CBP'
        elif 'aphis' in url_lower:
            return 'APHIS'
        elif 'fsis' in url_lower:
            return 'FSIS'
        else:
            return 'Unknown'
    
    def _create_refusal_extraction_schema(
        self,
        date_range: Optional[tuple] = None,
        product_categories: List[str] = None,
        extract_risk_factors: bool = True,
        extract_firms: bool = True,
    ) -> Dict[str, Any]:
        """Create JSON schema for refusal data extraction.
        
        Args:
            date_range: Date range for filtering
            product_categories: Product categories to focus on
            extract_risk_factors: Whether to extract risk assessment
            extract_firms: Whether to extract firm information
            
        Returns:
            JSON schema for structured extraction
        """
        schema = {
            "type": "object",
            "properties": {
                "refusal_entries": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "refusal_date": {
                                "type": "string",
                                "description": "Date of refusal (YYYY-MM-DD format)"
                            },
                            "product_description": {
                                "type": "string",
                                "description": "Description of the refused product"
                            },
                            "product_code": {
                                "type": "string",
                                "description": "FDA product code if available"
                            },
                            "refusal_reason": {
                                "type": "string",
                                "description": "Reason for refusal (adulteration, misbranding, etc.)"
                            },
                            "country_of_origin": {
                                "type": "string",
                                "description": "Country where product originated"
                            },
                            "port_of_entry": {
                                "type": "string",
                                "description": "US port where refusal occurred"
                            },
                        },
                        "required": ["refusal_date", "product_description", "refusal_reason"]
                    }
                },
                "summary_stats": {
                    "type": "object",
                    "properties": {
                        "total_refusals": {"type": "number"},
                        "date_range": {"type": "string"},
                        "top_reasons": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "top_countries": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                    }
                }
            }
        }
        
        # Add firm information if requested
        if extract_firms:
            schema["properties"]["refusal_entries"]["items"]["properties"]["firm_info"] = {
                "type": "object",
                "properties": {
                    "firm_name": {"type": "string"},
                    "firm_address": {"type": "string"},
                    "firm_country": {"type": "string"},
                    "fei_number": {"type": "string", "description": "FDA Establishment Identifier"},
                }
            }
        
        # Add risk assessment if requested
        if extract_risk_factors:
            schema["properties"]["risk_assessment"] = {
                "type": "object",
                "properties": {
                    "high_risk_products": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Products with frequent refusals"
                    },
                    "high_risk_countries": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Countries with high refusal rates"
                    },
                    "common_violations": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Most common refusal reasons"
                    },
                    "trend_analysis": {
                        "type": "string",
                        "description": "Analysis of refusal trends over time"
                    },
                }
            }
        
        return schema
    
    async def _enhance_refusal_result(self, result: CrawlResult, **kwargs) -> CrawlResult:
        """Enhance crawl result with refusal-specific processing and risk assessment.
        
        Args:
            result: Base crawl result from Crawl4AI
            **kwargs: Additional processing parameters
            
        Returns:
            Enhanced CrawlResult with refusal-specific data and analysis
        """
        if not result.success:
            return result
        
        try:
            # Parse refusal entries from raw content if extraction failed
            if not result.extracted_data.get('refusal_entries'):
                refusals = self._parse_refusals_from_text(result.raw_content)
                if refusals:
                    result.extracted_data['refusal_entries'] = refusals
            
            # Generate summary statistics
            refusal_entries = result.extracted_data.get('refusal_entries', [])
            if refusal_entries:
                summary_stats = self._generate_summary_statistics(refusal_entries)
                result.extracted_data['summary_stats'] = summary_stats
            
            # Perform risk assessment if requested
            if kwargs.get('extract_risk_factors', True) and refusal_entries:
                risk_assessment = self._perform_risk_assessment(refusal_entries)
                result.extracted_data['risk_assessment'] = risk_assessment
            
            # Categorize products
            if refusal_entries:
                categorized_products = self._categorize_products(refusal_entries)
                result.extracted_data['product_categories'] = categorized_products
            
            # Add metadata about extraction quality
            result.extracted_data['extraction_metadata'] = {
                'refusals_found': len(refusal_entries),
                'has_summary_stats': bool(result.extracted_data.get('summary_stats')),
                'has_risk_assessment': bool(result.extracted_data.get('risk_assessment')),
                'content_type': 'fda_refusal',
                'authority': self._determine_authority(result.source_url),
                'date_range_detected': self._detect_date_range(refusal_entries),
            }
            
            # Recalculate confidence based on refusal-specific criteria
            result.extraction_confidence = self._calculate_refusal_confidence(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error enhancing refusal result: {str(e)}")
            return result
    
    def _parse_refusals_from_text(self, content: str) -> List[Dict[str, Any]]:
        """Parse refusal entries from raw text content.
        
        Args:
            content: Raw HTML or text content
            
        Returns:
            List of refusal entries
        """
        refusals = []
        
        # Look for table rows or structured data
        lines = content.split('\n')
        
        for line in lines:
            # Skip empty lines and headers
            if not line.strip() or len(line.strip()) < 20:
                continue
            
            # Look for patterns that suggest refusal data
            if self._looks_like_refusal_entry(line):
                refusal = self._parse_refusal_from_line(line)
                if refusal:
                    refusals.append(refusal)
        
        return refusals[:500]  # Limit to prevent excessive data
    
    def _looks_like_refusal_entry(self, line: str) -> bool:
        """Check if a line looks like a refusal entry.
        
        Args:
            line: Text line to check
            
        Returns:
            True if line appears to contain refusal data
        """
        # Look for date patterns and refusal-related keywords
        has_date = bool(re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', line))
        has_refusal_keywords = any(keyword in line.lower() for keyword in [
            'adulterated', 'misbranded', 'filthy', 'pesticide', 'salmonella',
            'refused', 'detention', 'violation'
        ])
        
        return has_date and (has_refusal_keywords or len(line.split()) > 5)
    
    def _parse_refusal_from_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse refusal information from a single line of text.
        
        Args:
            line: Text line containing refusal information
            
        Returns:
            Refusal dictionary or None
        """
        # This is a simplified parser - real implementation would be more sophisticated
        parts = line.split('\t')  # Assume tab-separated
        
        if len(parts) < 3:
            parts = re.split(r'\s{2,}', line)  # Split on multiple spaces
        
        if len(parts) >= 3:
            refusal = {
                'refusal_date': '',
                'product_description': '',
                'refusal_reason': '',
                'country_of_origin': '',
                'port_of_entry': '',
                'firm_info': {},
            }
            
            # Try to extract date
            date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', line)
            if date_match:
                refusal['refusal_date'] = date_match.group(1)
            
            # Extract product description (usually the longest part)
            longest_part = max(parts, key=len) if parts else ''
            if len(longest_part) > 10:
                refusal['product_description'] = longest_part.strip()
            
            # Try to identify refusal reason
            reason_keywords = {
                'adulterated': 'Adulterated',
                'misbranded': 'Misbranded',
                'filthy': 'Filthy/Decomposed',
                'pesticide': 'Pesticide Residue',
                'salmonella': 'Salmonella',
                'listeria': 'Listeria',
                'e. coli': 'E. Coli',
            }
            
            for keyword, reason in reason_keywords.items():
                if keyword in line.lower():
                    refusal['refusal_reason'] = reason
                    break
            
            if not refusal['refusal_reason']:
                refusal['refusal_reason'] = 'Unknown'
            
            # Try to extract country (look for country patterns)
            country_match = re.search(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', line)
            if country_match:
                potential_country = country_match.group(1)
                # Simple country validation (this would be more sophisticated in practice)
                if len(potential_country) > 3 and potential_country not in ['United', 'States']:
                    refusal['country_of_origin'] = potential_country
            
            return refusal
        
        return None
    
    def _generate_summary_statistics(self, refusal_entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary statistics from refusal entries.
        
        Args:
            refusal_entries: List of refusal entries
            
        Returns:
            Summary statistics
        """
        from collections import Counter
        
        total_refusals = len(refusal_entries)
        
        # Count refusal reasons
        reasons = [entry.get('refusal_reason', 'Unknown') for entry in refusal_entries]
        top_reasons = [reason for reason, count in Counter(reasons).most_common(5)]
        
        # Count countries
        countries = [entry.get('country_of_origin', 'Unknown') 
                    for entry in refusal_entries if entry.get('country_of_origin')]
        top_countries = [country for country, count in Counter(countries).most_common(5)]
        
        # Detect date range
        dates = [entry.get('refusal_date', '') for entry in refusal_entries 
                if entry.get('refusal_date')]
        date_range = f"{min(dates)} to {max(dates)}" if dates else "Unknown"
        
        return {
            'total_refusals': total_refusals,
            'date_range': date_range,
            'top_reasons': top_reasons,
            'top_countries': top_countries,
        }
    
    def _perform_risk_assessment(self, refusal_entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform risk assessment based on refusal patterns.
        
        Args:
            refusal_entries: List of refusal entries
            
        Returns:
            Risk assessment results
        """
        from collections import Counter
        
        # Analyze product risk
        products = [entry.get('product_description', '') for entry in refusal_entries]
        product_counter = Counter(products)
        high_risk_products = [product for product, count in product_counter.most_common(10) 
                             if count > 1]
        
        # Analyze country risk
        countries = [entry.get('country_of_origin', '') for entry in refusal_entries 
                    if entry.get('country_of_origin')]
        country_counter = Counter(countries)
        high_risk_countries = [country for country, count in country_counter.most_common(10) 
                              if count > 1]
        
        # Analyze violation patterns
        reasons = [entry.get('refusal_reason', '') for entry in refusal_entries]
        reason_counter = Counter(reasons)
        common_violations = [reason for reason, count in reason_counter.most_common(5)]
        
        # Simple trend analysis
        trend_analysis = f"Analyzed {len(refusal_entries)} refusals. "
        if high_risk_countries:
            trend_analysis += f"Top risk country: {high_risk_countries[0]}. "
        if common_violations:
            trend_analysis += f"Most common violation: {common_violations[0]}."
        
        return {
            'high_risk_products': high_risk_products,
            'high_risk_countries': high_risk_countries,
            'common_violations': common_violations,
            'trend_analysis': trend_analysis,
        }
    
    def _categorize_products(self, refusal_entries: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Categorize products based on descriptions.
        
        Args:
            refusal_entries: List of refusal entries
            
        Returns:
            Categorized products
        """
        categories = {
            'Food Products': [],
            'Dietary Supplements': [],
            'Cosmetics': [],
            'Medical Devices': [],
            'Drugs': [],
            'Other': [],
        }
        
        category_keywords = {
            'Food Products': ['food', 'fruit', 'vegetable', 'meat', 'fish', 'dairy', 'spice'],
            'Dietary Supplements': ['supplement', 'vitamin', 'mineral', 'herbal'],
            'Cosmetics': ['cosmetic', 'makeup', 'lotion', 'cream', 'shampoo'],
            'Medical Devices': ['device', 'instrument', 'equipment', 'implant'],
            'Drugs': ['drug', 'pharmaceutical', 'medicine', 'tablet', 'capsule'],
        }
        
        for entry in refusal_entries:
            product_desc = entry.get('product_description', '').lower()
            categorized = False
            
            for category, keywords in category_keywords.items():
                if any(keyword in product_desc for keyword in keywords):
                    categories[category].append(entry.get('product_description', ''))
                    categorized = True
                    break
            
            if not categorized:
                categories['Other'].append(entry.get('product_description', ''))
        
        # Remove empty categories and limit entries
        return {category: products[:20] for category, products in categories.items() 
                if products}
    
    def _detect_date_range(self, refusal_entries: List[Dict[str, Any]]) -> str:
        """Detect the date range covered by refusal entries.
        
        Args:
            refusal_entries: List of refusal entries
            
        Returns:
            Date range string
        """
        dates = []
        for entry in refusal_entries:
            date_str = entry.get('refusal_date', '')
            if date_str:
                try:
                    # Try to parse various date formats
                    for fmt in ['%m/%d/%Y', '%m-%d-%Y', '%Y-%m-%d']:
                        try:
                            date_obj = datetime.strptime(date_str, fmt)
                            dates.append(date_obj)
                            break
                        except ValueError:
                            continue
                except:
                    continue
        
        if dates:
            min_date = min(dates).strftime('%Y-%m-%d')
            max_date = max(dates).strftime('%Y-%m-%d')
            return f"{min_date} to {max_date}"
        
        return "Unknown"
    
    def _calculate_refusal_confidence(self, result: CrawlResult) -> float:
        """Calculate confidence score specific to refusal content.
        
        Args:
            result: Crawl result to evaluate
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        base_confidence = result.extraction_confidence
        
        # Boost confidence based on refusal-specific indicators
        refusal_entries = result.extracted_data.get('refusal_entries', [])
        summary_stats = result.extracted_data.get('summary_stats', {})
        
        # Check for essential refusal elements
        has_refusals = len(refusal_entries) > 0
        has_dates = sum(1 for entry in refusal_entries if entry.get('refusal_date')) > 0
        has_reasons = sum(1 for entry in refusal_entries if entry.get('refusal_reason')) > 0
        
        # Calculate component scores
        structure_score = sum([has_refusals, has_dates, has_reasons]) / 3 * 0.3
        
        # Data quality score
        if refusal_entries:
            complete_entries = sum(1 for entry in refusal_entries 
                                 if all(entry.get(field) for field in 
                                       ['refusal_date', 'product_description', 'refusal_reason']))
            quality_score = (complete_entries / len(refusal_entries)) * 0.3
        else:
            quality_score = 0.0
        
        # Check for refusal-specific keywords
        refusal_terms = ['refusal', 'refused', 'adulterated', 'misbranded', 'fda', 'import alert']
        term_matches = sum(1 for term in refusal_terms 
                          if term.lower() in result.raw_content.lower())
        term_score = min(term_matches / len(refusal_terms), 1.0) * 0.4
        
        return min(base_confidence + structure_score + quality_score + term_score, 1.0)
    
    def _extract_refusal_urls_from_content(
        self,
        content: str,
        base_url: str,
        agencies: List[str] = None,
        product_types: List[str] = None,
        include_alerts: bool = True,
    ) -> List[str]:
        """Extract refusal-related URLs from crawled content.
        
        Args:
            content: HTML content to parse
            base_url: Base URL for resolving relative links
            agencies: Filter for specific agencies
            product_types: Filter for specific product types
            include_alerts: Whether to include import alerts
            
        Returns:
            List of refusal URLs
        """
        urls = []
        
        # Pattern for refusal-related links
        link_patterns = [
            r'href=["\']([^"\']*(?:refusal|import|alert|detention)[^"\']*)["\']',
            r'href=["\']([^"\']*(?:fda|usda|aphis)[^"\']*)["\']',
        ]
        
        for pattern in link_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            
            for match in matches:
                relative_url = match.group(1)
                absolute_url = urljoin(base_url, relative_url)
                
                # Filter by agencies if specified
                if agencies:
                    if not any(agency.lower() in absolute_url.lower() 
                             for agency in agencies):
                        continue
                
                # Skip alerts if not requested
                if not include_alerts:
                    if 'alert' in absolute_url.lower():
                        continue
                
                urls.append(absolute_url)
        
        return urls
    
    def _generate_known_refusal_urls(
        self,
        agencies: List[str] = None,
        include_alerts: bool = True,
    ) -> List[str]:
        """Generate URLs for known refusal systems.
        
        Args:
            agencies: Specific agencies to include
            include_alerts: Whether to include import alerts
            
        Returns:
            List of known refusal URLs
        """
        urls = []
        
        # Base refusal URLs by agency
        agency_urls = {
            'FDA': [
                "https://www.accessdata.fda.gov/scripts/importrefusals/",
                "https://www.fda.gov/food/importing-food-products-united-states/import-refusals",
            ],
            'USDA': [
                "https://www.aphis.usda.gov/aphis/ourfocus/importexport",
                "https://www.fsis.usda.gov/wps/portal/fsis/topics/international-affairs/importing-products",
            ],
            'CBP': [
                "https://www.cbp.gov/trade/basic-import-export/refusing-merchandise",
            ],
        }
        
        # Add agency-specific URLs
        if agencies:
            for agency in agencies:
                if agency in agency_urls:
                    urls.extend(agency_urls[agency])
        else:
            # Add all if no specific agencies requested
            for agency_list in agency_urls.values():
                urls.extend(agency_list)
        
        # Add import alert URLs if requested
        if include_alerts:
            alert_urls = [
                "https://www.accessdata.fda.gov/cms_ia/importalert_1.html",
                "https://www.fda.gov/food/importing-food-products-united-states/import-alerts",
            ]
            urls.extend(alert_urls)
        
        return urls