"""Domain layer components for the compliance intelligence platform."""

from .crawlers import BaseCrawler, ComplianceContentType, CrawlMetadata, CrawlResult

__all__ = [
    "BaseCrawler",
    "ComplianceContentType", 
    "CrawlMetadata",
    "CrawlResult",
]