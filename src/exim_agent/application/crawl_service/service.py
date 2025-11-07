"""Simplified CrawlService for orchestrating compliance web scraping."""

import asyncio
from typing import Dict, List, Optional, Any
from loguru import logger

from ...domain.crawlers.base_crawler import BaseCrawler
from ...domain.crawlers.models import CrawlResult
from ...domain.crawlers.hts_crawler import HTSCrawler
from ...domain.crawlers.rulings_crawler import RulingsCrawler
from ...domain.crawlers.sanctions_crawler import SanctionsCrawler
from ...domain.crawlers.refusals_crawler import RefusalsCrawler


class CrawlService:
    """Simple service for orchestrating web scraping operations across compliance domains."""
    
    def __init__(self):
        """Initialize CrawlService with crawler instances."""
        self._crawlers: Dict[str, BaseCrawler] = {
            "hts": HTSCrawler(),
            "rulings": RulingsCrawler(),
            "sanctions": SanctionsCrawler(),
            "refusals": RefusalsCrawler(),
        }
        
        logger.info("CrawlService initialized with crawlers: {}", list(self._crawlers.keys()))
    
    async def crawl_compliance_sources(
        self, 
        domains: List[str]
    ) -> Dict[str, List[CrawlResult]]:
        """
        Simple orchestration of web scraping operations across compliance domains.
        
        Args:
            domains: List of compliance domains to crawl (hts, rulings, sanctions, refusals)
            
        Returns:
            Dict mapping domain names to lists of CrawlResult objects
        """
        logger.info("Starting crawl operation for domains: {}", domains)
        
        results = {}
        
        for domain in domains:
            if domain not in self._crawlers:
                logger.warning("Unknown crawler domain: {}", domain)
                results[domain] = []
                continue
            
            crawler = self._crawlers[domain]
            
            try:
                # Get default URLs for the domain
                target_urls = self._get_default_urls(domain)
                
                # Crawl each URL
                domain_results = []
                for url in target_urls:
                    try:
                        result = await crawler.crawl(url)
                        domain_results.append(result)
                    except Exception as e:
                        logger.error("Failed to crawl URL {}: {}", url, str(e))
                        # Create error result
                        error_result = crawler._create_error_result(url, str(e))
                        domain_results.append(error_result)
                
                results[domain] = domain_results
                logger.info("Completed crawling for domain {}: {} results", domain, len(domain_results))
                
            except Exception as e:
                logger.error("Failed to crawl domain {}: {}", domain, str(e))
                results[domain] = []
        
        total_results = sum(len(r) for r in results.values())
        logger.info("Crawl operation completed. Total results: {}", total_results)
        
        return results
    
    def _get_default_urls(self, domain: str) -> List[str]:
        """Get default URLs to crawl for each domain."""
        default_urls = {
            "hts": [
                "https://hts.usitc.gov/current",
                "https://hts.usitc.gov/view/Chapter%2085"
            ],
            "rulings": [
                "https://rulings.cbp.gov/search?term=classification",
                "https://rulings.cbp.gov/search?term=tariff"
            ],
            "sanctions": [
                "https://www.treasury.gov/ofac/downloads/sdnlist.txt",
                "https://www.bis.doc.gov/index.php/policy-guidance/lists-of-parties-of-concern"
            ],
            "refusals": [
                "https://www.accessdata.fda.gov/scripts/importrefusals/",
                "https://www.accessdata.fda.gov/scripts/importrefusals/ir_detail.cfm"
            ]
        }
        
        return default_urls.get(domain, [])
    
    def get_crawler_types(self) -> List[str]:
        """Get list of available crawler types."""
        return list(self._crawlers.keys())