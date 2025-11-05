"""Compliance event domain models."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .enums import EventType, RiskLevel, TileStatus, AlertStatus, ComplianceArea


class Evidence(BaseModel):
    """Evidence supporting a compliance event."""
    
    source: str = Field(
        ...,
        description="Source name (e.g., USITC HTS, OFAC CSL, FDA)",
        examples=["USITC HTS Database", "OFAC Consolidated Screening List"]
    )
    url: Optional[str] = Field(
        default=None,
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
    confidence: float = Field(
        default=1.0,
        description="Confidence score for this evidence (0.0 to 1.0)",
        ge=0.0,
        le=1.0
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "source": "OFAC CSL",
                "url": "https://api.trade.gov/consolidated_screening_list/search",
                "snippet": "Shanghai Telecom added 2025-01-15",
                "last_updated": "2025-01-15T10:00:00Z",
                "confidence": 0.95
            }
        }
    )


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
    compliance_area: ComplianceArea = Field(
        ...,
        description="Specific compliance area affected"
    )
    risk_level: RiskLevel = Field(
        ...,
        description="Risk severity level"
    )
    status: AlertStatus = Field(
        default=AlertStatus.ACTIVE,
        description="Current status of the alert"
    )
    title: str = Field(
        ...,
        description="Brief title for the event",
        max_length=120,
        examples=["New OFAC Sanctions Alert", "HTS Duty Rate Change"]
    )
    summary_md: str = Field(
        ...,
        description="Markdown-formatted summary of the event",
        examples=["**New entity** added to OFAC sanctions list"]
    )
    impact_assessment: Optional[str] = Field(
        default=None,
        description="Assessment of potential business impact",
        examples=["May require supplier change", "Duty increase of 2.5%"]
    )
    recommended_actions: list[str] = Field(
        default_factory=list,
        description="Recommended actions to address the event",
        examples=[["Review supplier compliance", "Consider alternative sourcing"]]
    )
    evidence: list[Evidence] = Field(
        default_factory=list,
        description="Supporting evidence and citations"
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for categorization and filtering",
        examples=[["china", "electronics", "sanctions"]]
    )
    acknowledged_by: Optional[str] = Field(
        default=None,
        description="User who acknowledged the alert"
    )
    acknowledged_at: Optional[str] = Field(
        default=None,
        description="ISO 8601 timestamp of acknowledgment"
    )
    resolved_at: Optional[str] = Field(
        default=None,
        description="ISO 8601 timestamp of resolution"
    )
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat() + "Z",
        description="ISO 8601 timestamp of event creation"
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now().isoformat() + "Z",
        description="ISO 8601 timestamp of last update"
    )
    
    @field_validator('title')
    def validate_title(cls, v):
        """Ensure title is not empty."""
        if not v or not v.strip():
            raise ValueError("Title cannot be empty")
        return v.strip()
    
    def acknowledge(self, user_id: str) -> None:
        """Mark event as acknowledged."""
        self.status = AlertStatus.ACKNOWLEDGED
        self.acknowledged_by = user_id
        self.acknowledged_at = datetime.now().isoformat() + "Z"
        self.updated_at = datetime.now().isoformat() + "Z"
    
    def dismiss(self) -> None:
        """Mark event as dismissed."""
        self.status = AlertStatus.DISMISSED
        self.updated_at = datetime.now().isoformat() + "Z"
    
    def resolve(self) -> None:
        """Mark event as resolved."""
        self.status = AlertStatus.RESOLVED
        self.resolved_at = datetime.now().isoformat() + "Z"
        self.updated_at = datetime.now().isoformat() + "Z"
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "evt_001",
                "client_id": "client_ABC",
                "sku_id": "SKU-123",
                "lane_id": "CNSHA-USLAX-ocean",
                "type": "SANCTIONS",
                "compliance_area": "sanctions_screening",
                "risk_level": "warn",
                "status": "active",
                "title": "New OFAC Sanctions Alert",
                "summary_md": "**Shanghai Telecom Co.** added to OFAC Entity List",
                "impact_assessment": "May require supplier verification",
                "recommended_actions": ["Review supplier compliance", "Verify entity details"],
                "evidence": [
                    {
                        "source": "OFAC CSL",
                        "url": "https://api.trade.gov/...",
                        "snippet": "Shanghai Telecom added 2025-01-15",
                        "last_updated": "2025-01-15T10:00:00Z",
                        "confidence": 0.95
                    }
                ],
                "tags": ["china", "electronics", "sanctions"],
                "created_at": "2025-01-25T14:30:00Z",
                "updated_at": "2025-01-25T14:30:00Z"
            }
        }
    )


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
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "attention",
                "headline": "New Sanctions Alert",
                "details_md": "**Shanghai Telecom** added to Entity List",
                "last_updated": "2025-01-25T14:30:00Z"
            }
        }
    )


class IntelligenceResponse(BaseModel):
    """Response from compliance intelligence agent."""
    
    query: str = Field(
        ...,
        description="Original query that was asked"
    )
    answer: str = Field(
        ...,
        description="Generated answer to the query"
    )
    confidence: float = Field(
        ...,
        description="Confidence score for the answer (0.0 to 1.0)",
        ge=0.0,
        le=1.0
    )
    sources: list[Evidence] = Field(
        default_factory=list,
        description="Source citations used in the answer"
    )
    related_events: list[str] = Field(
        default_factory=list,
        description="IDs of related compliance events"
    )
    follow_up_questions: list[str] = Field(
        default_factory=list,
        description="Suggested follow-up questions"
    )
    processing_time_ms: int = Field(
        ...,
        description="Time taken to process the query in milliseconds"
    )
    generated_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="ISO 8601 timestamp of response generation"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "What are the current sanctions risks for SKU-123?",
                "answer": "Based on current data, SKU-123 has a **moderate sanctions risk** due to its origin from China and supplier Shanghai Electronics Co. No direct matches found in OFAC lists, but enhanced due diligence recommended.",
                "confidence": 0.85,
                "sources": [
                    {
                        "source": "OFAC CSL",
                        "url": "https://api.trade.gov/...",
                        "snippet": "No matches found for Shanghai Electronics Co.",
                        "last_updated": "2025-01-25T10:00:00Z",
                        "confidence": 0.95
                    }
                ],
                "related_events": ["evt_001", "evt_002"],
                "follow_up_questions": [
                    "What alternative suppliers are available?",
                    "How often should we re-screen this supplier?"
                ],
                "processing_time_ms": 1250,
                "generated_at": "2025-01-25T14:30:00Z"
            }
        }
    )


class MonitoringConfig(BaseModel):
    """Configuration for SKU/lane monitoring."""
    
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
    compliance_areas: list[ComplianceArea] = Field(
        default_factory=lambda: list(ComplianceArea),
        description="Compliance areas to monitor"
    )
    alert_thresholds: dict[str, float] = Field(
        default_factory=dict,
        description="Custom alert thresholds for this SKU/lane combination",
        examples=[{"duty_delta": 0.005, "risk_score": 0.7}]
    )
    is_active: bool = Field(
        default=True,
        description="Whether monitoring is active"
    )
    last_checked: Optional[str] = Field(
        default=None,
        description="ISO 8601 timestamp of last compliance check"
    )
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="ISO 8601 timestamp of configuration creation"
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="ISO 8601 timestamp of last update"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "client_id": "client_ABC",
                "sku_id": "SKU-123",
                "lane_id": "CNSHA-USLAX-ocean",
                "compliance_areas": ["hts_classification", "sanctions_screening", "health_safety"],
                "alert_thresholds": {
                    "duty_delta": 0.005,
                    "risk_score": 0.7
                },
                "is_active": True,
                "last_checked": "2025-01-25T14:00:00Z",
                "created_at": "2025-01-25T14:30:00Z",
                "updated_at": "2025-01-25T14:30:00Z"
            }
        }
    )


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
    overall_risk_level: RiskLevel = Field(
        ...,
        description="Overall risk assessment for this SKU/lane combination"
    )
    risk_score: float = Field(
        ...,
        description="Numerical risk score (0.0 to 1.0)",
        ge=0.0,
        le=1.0
    )
    active_alerts_count: int = Field(
        default=0,
        description="Number of active alerts for this SKU/lane",
        ge=0
    )
    last_change_detected: Optional[str] = Field(
        default=None,
        description="ISO 8601 timestamp of last compliance change detected"
    )
    sources: list[Evidence] = Field(
        default_factory=list,
        description="All source citations used in this snapshot"
    )
    processing_time_ms: int = Field(
        ...,
        description="Time taken to generate snapshot in milliseconds"
    )
    generated_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="ISO 8601 timestamp of snapshot generation"
    )
    
    def get_highest_risk_tile(self) -> Optional[Tile]:
        """Get the tile with the highest risk status."""
        risk_order = {TileStatus.CLEAR: 0, TileStatus.ATTENTION: 1, TileStatus.ACTION: 2, TileStatus.ERROR: 3}
        highest_tile = None
        highest_risk = -1
        
        for tile in self.tiles.values():
            tile_risk = risk_order.get(tile.status, 0)
            if tile_risk > highest_risk:
                highest_risk = tile_risk
                highest_tile = tile
        
        return highest_tile
    
    def get_tiles_by_status(self, status: TileStatus) -> list[Tile]:
        """Get all tiles with a specific status."""
        return [tile for tile in self.tiles.values() if tile.status == status]
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "client_id": "client_ABC",
                "sku_id": "SKU-123",
                "lane_id": "CNSHA-USLAX-ocean",
                "tiles": {
                    "hts": {
                        "status": "clear",
                        "headline": "HTS 8517.12.00 - No Changes",
                        "details_md": "**Duty Rate:** Free\n**Special Requirements:** FCC authorization",
                        "last_updated": "2025-01-25T14:30:00Z"
                    },
                    "sanctions": {
                        "status": "attention",
                        "headline": "Supplier Requires Review",
                        "details_md": "**Shanghai Electronics Co.** - No direct matches but enhanced due diligence recommended",
                        "last_updated": "2025-01-25T14:30:00Z"
                    }
                },
                "overall_risk_level": "warn",
                "risk_score": 0.65,
                "active_alerts_count": 1,
                "last_change_detected": "2025-01-24T10:15:00Z",
                "sources": [
                    {
                        "source": "USITC HTS Database",
                        "url": "https://hts.usitc.gov/...",
                        "snippet": "HTS 8517.12.00 - Cellular telephones",
                        "last_updated": "2025-01-20T00:00:00Z",
                        "confidence": 1.0
                    }
                ],
                "processing_time_ms": 2150,
                "generated_at": "2025-01-25T14:30:00Z"
            }
        }
    )
