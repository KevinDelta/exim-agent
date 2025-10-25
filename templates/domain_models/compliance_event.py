"""Compliance event domain models."""

from datetime import datetime
from pydantic import BaseModel, Field

from .enums import EventType, RiskLevel, TileStatus


class Evidence(BaseModel):
    """Evidence supporting a compliance event."""
    
    source: str = Field(
        ...,
        description="Source name (e.g., USITC HTS, OFAC CSL, FDA)",
        examples=["USITC HTS Database", "OFAC Consolidated Screening List"]
    )
    url: str = Field(
        ...,
        description="URL to source document or data",
        examples=["https://hts.usitc.gov/view/chapter?release=2025HTSARev0"]
    )
    snippet: str = Field(
        ...,
        description="Relevant excerpt or summary from source",
        examples=["Shanghai Telecom Co. added to Entity List effective 2025-01-15"]
    )
    last_updated: str = Field(
        ...,
        description="ISO 8601 timestamp of when source was last updated",
        examples=["2025-01-15T10:00:00Z"]
    )
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "source": "OFAC CSL",
                "url": "https://api.trade.gov/consolidated_screening_list/search",
                "snippet": "Shanghai Telecom added 2025-01-15",
                "last_updated": "2025-01-15T10:00:00Z"
            }
        }


class ComplianceEvent(BaseModel):
    """A compliance event for a specific SKU + lane combination."""
    
    id: str = Field(
        ...,
        description="Unique event identifier",
        examples=["evt_001", "event_2025_01_15_abc123"]
    )
    client_id: str = Field(
        ...,
        description="Client this event belongs to",
        examples=["client_ABC"]
    )
    sku_id: str = Field(
        ...,
        description="SKU this event applies to",
        examples=["SKU-123"]
    )
    lane_id: str = Field(
        ...,
        description="Lane this event applies to",
        examples=["CNSHA-USLAX-ocean"]
    )
    type: EventType = Field(
        ...,
        description="Type of compliance event"
    )
    risk_level: RiskLevel = Field(
        ...,
        description="Risk severity level"
    )
    summary_md: str = Field(
        ...,
        description="Markdown-formatted summary of the event",
        examples=["**New entity** added to OFAC sanctions list"]
    )
    evidence: list[Evidence] = Field(
        default_factory=list,
        description="Supporting evidence and citations"
    )
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="ISO 8601 timestamp of event creation"
    )
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "id": "evt_001",
                "client_id": "client_ABC",
                "sku_id": "SKU-123",
                "lane_id": "CNSHA-USLAX-ocean",
                "type": "SANCTIONS",
                "risk_level": "warn",
                "summary_md": "New entity added to OFAC list",
                "evidence": [
                    {
                        "source": "OFAC CSL",
                        "url": "https://api.trade.gov/...",
                        "snippet": "Shanghai Telecom added",
                        "last_updated": "2025-01-15T10:00:00Z"
                    }
                ],
                "created_at": "2025-01-25T14:30:00Z"
            }
        }


class Tile(BaseModel):
    """A tile in the compliance snapshot UI."""
    
    status: TileStatus = Field(
        ...,
        description="Status indicator for this compliance area"
    )
    headline: str = Field(
        ...,
        description="Short headline (< 80 chars)",
        max_length=80,
        examples=["HTS 8517.12.00 - No Changes", "New Sanctions Alert"]
    )
    details_md: str = Field(
        ...,
        description="Markdown-formatted details",
        examples=["**Shanghai Telecom** added to Entity List. Review supplier."]
    )
    last_updated: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="ISO 8601 timestamp of last update"
    )
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "status": "attention",
                "headline": "New Sanctions Alert",
                "details_md": "**Shanghai Telecom** added to Entity List",
                "last_updated": "2025-01-25T14:30:00Z"
            }
        }


class SnapshotResponse(BaseModel):
    """Complete compliance snapshot for a SKU + lane."""
    
    client_id: str = Field(
        ...,
        description="Client identifier"
    )
    sku_id: str = Field(
        ...,
        description="SKU identifier"
    )
    lane_id: str = Field(
        ...,
        description="Lane identifier"
    )
    tiles: dict[str, Tile] = Field(
        ...,
        description="Compliance tiles keyed by area (hts, sanctions, health_safety, etc.)",
        examples=[{
            "hts": {"status": "clear", "headline": "No changes", "details_md": "..."},
            "sanctions": {"status": "attention", "headline": "New alert", "details_md": "..."}
        }]
    )
    sources: list[Evidence] = Field(
        default_factory=list,
        description="All source citations used in this snapshot"
    )
    generated_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="ISO 8601 timestamp of snapshot generation"
    )
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "client_id": "client_ABC",
                "sku_id": "SKU-123",
                "lane_id": "CNSHA-USLAX-ocean",
                "tiles": {
                    "hts": {
                        "status": "clear",
                        "headline": "HTS 8517.12.00 - No Changes",
                        "details_md": "Duty rate: Free",
                        "last_updated": "2025-01-25T14:30:00Z"
                    }
                },
                "sources": [],
                "generated_at": "2025-01-25T14:30:00Z"
            }
        }
