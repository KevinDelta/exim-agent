"""CBP rulings tool with web scraping for CROSS website."""

import time
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from urllib.parse import urlencode, urljoin
import httpx
from bs4 import BeautifulSoup
from loguru import logger

from .base_tool import ComplianceTool
from ...infrastructure.db.supabase_client import supabase_client


class RulingsTool(ComplianceTool):
    """Tool for scraping CBP classification rulings from CROSS website."""
    
    def __init__(self):
        """Initialize CBP rulings scraping tool."""
        super().__init__()
        self.name = "find_rulings"
        self.description = "Search CBP classification rulings from CROSS website"
        
        # CBP CROSS base URLs
        self.base_url = "https://rulings.cbp.gov"
        self.search_url = f"{self.base_url}/search"
        
        # Rate limiting: maximum 0.7 requests per second (requirement 2.1)
        self._min_request_interval = 1.43  # ~0.7 requests per second
        
        # Update User-Agent for politeness (requirement 2.2)
        self.client.headers.update({
            "User-Agent": "ComplianceIntelligencePlatform/1.0 (Trade Compliance Research; contact@compliance.example.com)"
        })
    
    def _run_impl(self, search_term: str = None, hts_code: str = None, keyword: str = None, 
                  lane_id: str = None, limit: int = 10) -> Dict[str, Any]:
        """
        Search CBP CROSS website for classification rulings.
        
        Args:
            search_term: Search term for rulings (primary parameter)
            hts_code: HTS code to search for or filter by
            keyword: Alternative search term (for backward compatibility)
            lane_id: Optional lane identifier (for compatibility)
            limit: Maximum number of rulings to retrieve
        
        Returns:
            Dict containing ruling search results with Supabase storage
        """
        # Handle different parameter combinations for backward compatibility
        if not search_term and not hts_code and not keyword:
            raise ValueError("Must provide at least one of: search_term, hts_code, or keyword")
        
        # Determine the actual search term to use
        actual_search_term = search_term or keyword or hts_code
        logger.info(f"Scraping CBP CROSS rulings - Search: {actual_search_term}, HTS: {hts_code}")
        
        try:
            # Perform search and get ruling URLs
            ruling_urls = self._search_rulings(actual_search_term, hts_code, limit)
            
            if not ruling_urls:
                logger.info("No rulings found for search criteria")
                return self._empty_result()
            
            # Scrape individual ruling details
            rulings = []
            for url in ruling_urls:
                try:
                    ruling_data = self._scrape_ruling_detail(url)
                    if ruling_data:
                        rulings.append(ruling_data)
                        
                        # Store in Supabase (requirement 2.3)
                        self._store_ruling_data(ruling_data)
                        
                    # Rate limiting between requests
                    time.sleep(self._min_request_interval)
                    
                except Exception as e:
                    logger.warning(f"Failed to scrape ruling {url}: {e}")
                    continue
            
            result = {
                "total_rulings": len(rulings),
                "rulings": rulings,
                "precedent_analysis": {
                    "authoritative_rulings": len([r for r in rulings if r.get("ruling_type") == "HQ"])
                },
                "search_date": datetime.utcnow().isoformat() + "Z",
                "search_term": actual_search_term,
                "hts_filter": hts_code
            }
            
            logger.info(f"Successfully scraped {len(rulings)} rulings")
            return result
            
        except Exception as e:
            logger.error(f"CBP CROSS scraping failed: {e}")
            # Re-raise to let base class handle retry and fallback
            raise e
    
    def _search_rulings(self, search_term: str, hts_code: str = None, limit: int = 10) -> List[str]:
        """
        Search CBP CROSS for ruling URLs.
        
        Args:
            search_term: Search term
            hts_code: Optional HTS code filter
            limit: Maximum results
            
        Returns:
            List of ruling detail URLs
        """
        # Build search parameters
        params = {
            "search": search_term,
            "limit": min(limit, 50)  # Reasonable limit
        }
        
        if hts_code:
            params["hts"] = hts_code
        
        search_url_with_params = f"{self.search_url}?{urlencode(params)}"
        
        try:
            # Apply rate limiting
            time.sleep(self._min_request_interval)
            
            response = self.client.get(search_url_with_params, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract ruling links from search results
            ruling_urls = []
            
            # Look for ruling links (adjust selectors based on actual CROSS structure)
            ruling_links = soup.find_all('a', href=re.compile(r'/ruling/'))
            
            for link in ruling_links[:limit]:
                href = link.get('href')
                if href:
                    full_url = urljoin(self.base_url, href)
                    ruling_urls.append(full_url)
            
            logger.info(f"Found {len(ruling_urls)} ruling URLs from search")
            return ruling_urls
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error during CROSS search: {e}")
            raise
        except Exception as e:
            logger.error(f"Error parsing CROSS search results: {e}")
            raise
    
    def _scrape_ruling_detail(self, ruling_url: str) -> Optional[Dict[str, Any]]:
        """
        Scrape individual ruling detail page.
        
        Args:
            ruling_url: URL of the ruling detail page
            
        Returns:
            Dict with ruling data or None if failed
        """
        try:
            response = self.client.get(ruling_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract ruling data (adjust selectors based on actual CROSS structure)
            ruling_data = {
                "source_url": ruling_url,
                "ruling_number": self._extract_text(soup, 'span.ruling-number, .ruling-id'),
                "date_issued": self._extract_date(soup, '.date-issued, .ruling-date'),
                "hts_references": self._extract_hts_codes(soup),
                "full_text": self._extract_full_text(soup),
                "classification_rationale": self._extract_text(soup, '.rationale, .holding'),
                "ruling_type": self._determine_ruling_type(ruling_url),
                "scraped_at": datetime.utcnow().isoformat()
            }
            
            # Convert HTML to Markdown format (requirement 2.4)
            if ruling_data["full_text"]:
                ruling_data["full_text_markdown"] = self._html_to_markdown(ruling_data["full_text"])
            
            return ruling_data
            
        except Exception as e:
            logger.error(f"Failed to scrape ruling detail {ruling_url}: {e}")
            return None
    
    def _extract_text(self, soup: BeautifulSoup, selector: str) -> str:
        """Extract text content using CSS selector."""
        element = soup.select_one(selector)
        return element.get_text(strip=True) if element else ""
    
    def _extract_date(self, soup: BeautifulSoup, selector: str) -> str:
        """Extract and normalize date from element."""
        date_text = self._extract_text(soup, selector)
        if date_text:
            # Try to parse and normalize date format
            try:
                # Handle common date formats
                for fmt in ["%m/%d/%Y", "%Y-%m-%d", "%B %d, %Y"]:
                    try:
                        parsed_date = datetime.strptime(date_text, fmt)
                        return parsed_date.strftime("%Y-%m-%d")
                    except ValueError:
                        continue
            except Exception:
                pass
        return date_text
    
    def _extract_hts_codes(self, soup: BeautifulSoup) -> List[str]:
        """Extract HTS codes from ruling text."""
        hts_codes = []
        
        # Look for HTS code patterns in text
        text_content = soup.get_text()
        hts_pattern = r'\b\d{4}\.\d{2}\.\d{2}\b'
        matches = re.findall(hts_pattern, text_content)
        
        return list(set(matches))  # Remove duplicates
    
    def _extract_full_text(self, soup: BeautifulSoup) -> str:
        """Extract the full ruling text content."""
        # Look for main content area (adjust selector based on actual structure)
        content_selectors = [
            '.ruling-content',
            '.main-content', 
            '.ruling-text',
            'main',
            '.content'
        ]
        
        for selector in content_selectors:
            content = soup.select_one(selector)
            if content:
                return content.get_text(separator='\n', strip=True)
        
        # Fallback to body content
        body = soup.find('body')
        return body.get_text(separator='\n', strip=True) if body else ""
    
    def _html_to_markdown(self, html_content: str) -> str:
        """Convert HTML content to Markdown format (requirement 2.4)."""
        # Simple HTML to Markdown conversion
        # For production, consider using a library like html2text
        
        # Basic conversions
        markdown = html_content
        markdown = re.sub(r'<h[1-6][^>]*>(.*?)</h[1-6]>', r'## \1', markdown, flags=re.IGNORECASE)
        markdown = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n\n', markdown, flags=re.IGNORECASE)
        markdown = re.sub(r'<br[^>]*>', '\n', markdown, flags=re.IGNORECASE)
        markdown = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', markdown, flags=re.IGNORECASE)
        markdown = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', markdown, flags=re.IGNORECASE)
        
        # Remove remaining HTML tags
        markdown = re.sub(r'<[^>]+>', '', markdown)
        
        # Clean up whitespace
        markdown = re.sub(r'\n\s*\n\s*\n', '\n\n', markdown)
        
        return markdown.strip()
    
    def _determine_ruling_type(self, ruling_url: str) -> str:
        """Determine ruling type from URL or content."""
        if '/hq/' in ruling_url.lower():
            return "HQ"  # Headquarters ruling
        elif '/ny/' in ruling_url.lower():
            return "NY"  # New York ruling
        else:
            return "OTHER"
    
    def _store_ruling_data(self, ruling_data: Dict[str, Any]) -> None:
        """Store ruling data in Supabase."""
        if ruling_data.get("ruling_number"):
            success = supabase_client.store_compliance_data(
                source_type="rulings",
                source_id=ruling_data["ruling_number"],
                data=ruling_data
            )
            
            if success:
                logger.debug(f"Stored ruling {ruling_data['ruling_number']} in Supabase")
            else:
                logger.warning(f"Failed to store ruling {ruling_data['ruling_number']} in Supabase")
    
    def _empty_result(self) -> Dict[str, Any]:
        """Return empty result structure."""
        return {
            "total_rulings": 0,
            "rulings": [],
            "precedent_analysis": {
                "authoritative_rulings": 0
            },
            "search_date": datetime.utcnow().isoformat() + "Z"
        }
    
    def _get_fallback_data(self, search_term: str = None, hts_code: str = None, keyword: str = None, 
                          lane_id: str = None, limit: int = 10, **kwargs) -> Dict[str, Any]:
        """Fallback to mock data when scraping fails (requirement 7.1)."""
        # Handle different parameter combinations for backward compatibility
        actual_search_term = search_term or keyword or hts_code
        
        logger.info(f"Using fallback mock data for CBP rulings - Search: {actual_search_term}")
        
        # Simple mock rulings data
        mock_rulings = {
            "8517.12.00": {
                "total_rulings": 5,
                "recent_ruling": "NY N312345",
                "classification_confirmed": True
            },
            "8708.30.50": {
                "total_rulings": 3,
                "recent_ruling": "HQ H234567", 
                "classification_confirmed": True
            },
            "0306.17.00": {
                "total_rulings": 2,
                "recent_ruling": "NY N298123",
                "classification_confirmed": True
            }
        }
        
        # Use HTS code if provided, otherwise use search term
        lookup_key = hts_code or actual_search_term
        
        if lookup_key in mock_rulings:
            data = mock_rulings[lookup_key]
            return {
                "total_rulings": data["total_rulings"],
                "rulings": [{
                    "ruling_number": data["recent_ruling"],
                    "hts_code": lookup_key,
                    "date_issued": "2024-12-15",
                    "classification_rationale": f"Products properly classified under HTS {lookup_key}",
                    "source_url": f"https://rulings.cbp.gov/ruling/{data['recent_ruling']}",
                    "ruling_type": "NY" if data["recent_ruling"].startswith("NY") else "HQ",
                    "fallback_data": True
                }],
                "precedent_analysis": {
                    "authoritative_rulings": 1 if data["total_rulings"] > 0 else 0
                },
                "search_date": datetime.utcnow().isoformat() + "Z",
                "search_term": actual_search_term,
                "hts_filter": hts_code,
                "fallback_mode": True
            }
        else:
            return self._empty_result()