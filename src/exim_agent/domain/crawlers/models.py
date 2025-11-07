"""Data models for crawler domain."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class ComplianceContentType(Enum):
    """Enum for categorizing scraped compliance content types."""
    
    HTS_TARIFF_SCHEDULE = "hts_tariff_schedule"
    HTS_CLASSIFICATION_NOTES = "hts_classification_notes"
    CBP_RULING = "cbp_ruling"
    CBP_POLICY_UPDATE = "cbp_policy_update"
    SANCTIONS_LIST = "sanctions_list"
    SANCTIONS_GUIDANCE = "sanctions_guidance"
    FDA_REFUSAL = "fda_refusal"
    FDA_POLICY = "fda_policy"
    REGULATORY_UPDATE = "regulatory_update"
    TRADE_AGREEMENT = "trade_agreement"
    UNKNOWN = "unknown"


@dataclass
class CrawlMetadata:
    """Comprehensive metadata for scraped content with source attribution."""
    
    source_attribution: str
    regulatory_authority: str
    content_hash: str
    last_modified: Optional[datetime]
    extraction_method: str
    rate_limit_applied: float
    change_detected: bool
    crawl_session_id: str
    user_agent: str
    response_status: int
    content_length: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary for storage."""
        return {
            "source_attribution": self.source_attribution,
            "regulatory_authority": self.regulatory_authority,
            "content_hash": self.content_hash,
            "last_modified": self.last_modified.isoformat() if self.last_modified else None,
            "extraction_method": self.extraction_method,
            "rate_limit_applied": self.rate_limit_applied,
            "change_detected": self.change_detected,
            "crawl_session_id": self.crawl_session_id,
            "user_agent": self.user_agent,
            "response_status": self.response_status,
            "content_length": self.content_length,
        }


@dataclass
class CrawlResult:
    """Result of a web crawling operation with extracted compliance content."""
    
    source_url: str
    content_type: ComplianceContentType
    extracted_data: Dict[str, Any]
    raw_content: str
    metadata: CrawlMetadata
    extraction_confidence: float
    scraped_at: datetime
    success: bool
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert crawl result to dictionary for storage."""
        return {
            "source_url": self.source_url,
            "content_type": self.content_type.value,
            "extracted_data": self.extracted_data,
            "raw_content": self.raw_content,
            "metadata": self.metadata.to_dict(),
            "extraction_confidence": self.extraction_confidence,
            "scraped_at": self.scraped_at.isoformat(),
            "success": self.success,
            "error_message": self.error_message,
        }
    
    @property
    def is_high_confidence(self) -> bool:
        """Check if extraction confidence is above threshold."""
        return self.extraction_confidence >= 0.8
    
    @property
    def needs_manual_review(self) -> bool:
        """Check if result needs manual review due to low confidence or errors."""
        return not self.success or self.extraction_confidence < 0.6