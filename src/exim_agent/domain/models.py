from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .compliance.enums import (
    AlertStatus,
    ComplianceArea,
    EventType,
    MonitoringStatus,
    NotificationChannel,
    RiskLevel,
    TileStatus,
    TransportMode,
)


class DocumentStatus(str, Enum):
    """Status of document processing."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Document(BaseModel):
    """Domain model for a document."""
    file_path: Path
    file_name: str
    file_type: str
    size_bytes: int
    status: DocumentStatus = DocumentStatus.PENDING
    error_message: Optional[str] = None
    
    class Config:
        use_enum_values = True


class IngestionResult(BaseModel):
    """Result of document ingestion operation."""
    success: bool
    documents_processed: int
    documents_failed: int
    failed_documents: list[str] = Field(default_factory=list)
    message: str
    collection_stats: Optional[dict] = None


class ToolResponse(BaseModel):
    """Standardized tool response format."""

    success: bool = Field(
        ...,
        description="Whether the tool execution was successful"
    )
    data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Tool result data"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if execution failed"
    )
    error_type: Optional[str] = Field(
        default=None,
        description="Type of error that occurred"
    )
    cached: bool = Field(
        default=False,
        description="Whether result was served from cache"
    )
    execution_time_ms: int = Field(
        default=0,
        description="Execution time in milliseconds"
    )
    retry_count: int = Field(
        default=0,
        description="Number of retries performed"
    )
    circuit_breaker_state: str = Field(
        default="closed",
        description="Current circuit breaker state"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="ISO 8601 timestamp of execution"
    )


class LaneRef(BaseModel):
    """Reference to a logistics lane (origin-destination-mode)."""

    lane_id: str = Field(
        ...,
        description="Unique lane identifier (e.g., CNSHA-USLAX-ocean)",
        examples=["CNSHA-USLAX-ocean", "MXNLD-USTX-truck"]
    )
    origin_port: str = Field(
        ...,
        description="Origin port code (UN/LOCODE or similar)",
        examples=["CNSHA", "MXNLD"]
    )
    destination_port: str = Field(
        ...,
        description="Destination port code",
        examples=["USLAX", "USTX"]
    )
    mode: TransportMode = Field(
        ...,
        description="Transport mode"
    )
    status: MonitoringStatus = Field(
        default=MonitoringStatus.ACTIVE,
        description="Monitoring status for this lane"
    )
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="ISO 8601 timestamp of lane creation"
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="ISO 8601 timestamp of last update"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "lane_id": "CNSHA-USLAX-ocean",
                "origin_port": "CNSHA",
                "destination_port": "USLAX",
                "mode": "ocean",
                "status": "active",
                "created_at": "2025-01-25T14:30:00Z",
                "updated_at": "2025-01-25T14:30:00Z"
            }
        }
    )


class SkuRef(BaseModel):
    """Reference to a Stock Keeping Unit with compliance metadata."""

    sku_id: str = Field(
        ...,
        description="Unique SKU identifier",
        examples=["SKU-123", "PROD-ABC-001"]
    )
    description: str = Field(
        ...,
        description="Product description",
        examples=["Cellular phones with camera", "Auto parts - brake pads"]
    )
    hts_code: str = Field(
        ...,
        description="Harmonized Tariff Schedule code (US HTS)",
        examples=["8517.12.00", "8708.30.50"],
        pattern=r"^\d{4}\.\d{2}\.\d{2}$"
    )
    origin_country: str = Field(
        ...,
        description="ISO 2-letter country code of origin",
        examples=["CN", "MX", "VN"],
        min_length=2,
        max_length=2
    )
    supplier_name: Optional[str] = Field(
        default=None,
        description="Primary supplier name for sanctions screening",
        examples=["Shanghai Electronics Co.", "Tijuana Manufacturing"]
    )
    lanes: list[str] = Field(
        default_factory=list,
        description="List of lane IDs this SKU travels on",
        examples=[["CNSHA-USLAX-ocean", "CNSHA-USNYC-ocean"]]
    )
    status: MonitoringStatus = Field(
        default=MonitoringStatus.ACTIVE,
        description="Monitoring status for this SKU"
    )
    risk_level: Optional[RiskLevel] = Field(
        default=None,
        description="Current assessed risk level"
    )
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="ISO 8601 timestamp of SKU creation"
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="ISO 8601 timestamp of last update"
    )

    @field_validator('hts_code')
    def validate_hts_code(cls, v):
        """Validate HTS code format."""
        if not v or len(v) < 4:
            raise ValueError("HTS code must be at least 4 characters")
        return v.upper()

    @field_validator('origin_country')
    def validate_country_code(cls, v):
        """Validate country code format."""
        return v.upper()

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sku_id": "SKU-123",
                "description": "Cellular phones with camera",
                "hts_code": "8517.12.00",
                "origin_country": "CN",
                "supplier_name": "Shanghai Electronics Co.",
                "lanes": ["CNSHA-USLAX-ocean"],
                "status": "active",
                "risk_level": "warn",
                "created_at": "2025-01-25T14:30:00Z",
                "updated_at": "2025-01-25T14:30:00Z"
            }
        }
    )


class CompliancePreferences(BaseModel):
    """Client-specific compliance monitoring preferences."""

    duty_delta_threshold: float = Field(
        default=0.01,
        description="Minimum duty rate change to trigger alert (as decimal, e.g., 0.01 = 1%)",
        ge=0.0,
        le=1.0
    )
    risk_level_filter: RiskLevel = Field(
        default=RiskLevel.LOW,
        description="Minimum risk level for alerts"
    )
    notification_channels: list[NotificationChannel] = Field(
        default_factory=lambda: [NotificationChannel.EMAIL],
        description="Preferred notification channels"
    )
    email_addresses: list[str] = Field(
        default_factory=list,
        description="Email addresses for notifications"
    )
    webhook_urls: list[str] = Field(
        default_factory=list,
        description="Webhook URLs for real-time notifications"
    )
    slack_channels: list[str] = Field(
        default_factory=list,
        description="Slack channels for notifications"
    )
    weekly_digest_enabled: bool = Field(
        default=True,
        description="Enable weekly compliance digest"
    )
    weekly_digest_day: str = Field(
        default="sunday",
        description="Day of week for digest delivery",
        pattern=r"^(monday|tuesday|wednesday|thursday|friday|saturday|sunday)$"
    )
    digest_time_utc: str = Field(
        default="09:00",
        description="Time of day for digest delivery (UTC, HH:MM format)",
        pattern=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$"
    )
    auto_dismiss_resolved: bool = Field(
        default=True,
        description="Automatically dismiss alerts when issues are resolved"
    )
    consolidate_similar_alerts: bool = Field(
        default=True,
        description="Group similar alerts together"
    )
    alert_retention_days: int = Field(
        default=90,
        description="Number of days to retain alert history",
        ge=1,
        le=365
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "duty_delta_threshold": 0.01,
                "risk_level_filter": "warn",
                "notification_channels": ["email", "webhook"],
                "email_addresses": ["ops@company.com", "compliance@company.com"],
                "webhook_urls": ["https://api.company.com/compliance-webhook"],
                "weekly_digest_enabled": True,
                "weekly_digest_day": "sunday",
                "digest_time_utc": "09:00",
                "auto_dismiss_resolved": True,
                "consolidate_similar_alerts": True,
                "alert_retention_days": 90
            }
        }
    )


class ClientProfile(BaseModel):
    """Client profile with watchlist of SKUs and lanes."""

    id: str = Field(
        ...,
        description="Unique client identifier",
        examples=["client_ABC", "org_12345"]
    )
    name: str = Field(
        ...,
        description="Client organization name",
        examples=["ABC Imports Co.", "Global Trade Partners"]
    )
    contact_email: str = Field(
        ...,
        description="Primary contact email address",
        examples=["ops@abcimports.com"]
    )
    contact_phone: Optional[str] = Field(
        default=None,
        description="Primary contact phone number",
        examples=["+1-555-0100"]
    )
    lanes: list[LaneRef] = Field(
        default_factory=list,
        description="List of monitored logistics lanes"
    )
    watch_skus: list[SkuRef] = Field(
        default_factory=list,
        description="List of SKUs to monitor for compliance changes"
    )
    preferences: CompliancePreferences = Field(
        default_factory=CompliancePreferences,
        description="Client-specific compliance preferences and thresholds"
    )
    is_active: bool = Field(
        default=True,
        description="Whether the client profile is active"
    )
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="ISO 8601 timestamp of profile creation"
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="ISO 8601 timestamp of last update"
    )

    @field_validator('contact_email')
    def validate_email(cls, v):
        """Basic email validation."""
        if '@' not in v or '.' not in v:
            raise ValueError("Invalid email format")
        return v.lower()

    def get_monitored_sku_count(self) -> int:
        """Get count of actively monitored SKUs."""
        return len([sku for sku in self.watch_skus if sku.status == MonitoringStatus.ACTIVE])

    def get_monitored_lane_count(self) -> int:
        """Get count of actively monitored lanes."""
        return len([lane for lane in self.lanes if lane.status == MonitoringStatus.ACTIVE])

    def get_sku_by_id(self, sku_id: str) -> Optional[SkuRef]:
        """Get SKU reference by ID."""
        return next((sku for sku in self.watch_skus if sku.sku_id == sku_id), None)

    def get_lane_by_id(self, lane_id: str) -> Optional[LaneRef]:
        """Get lane reference by ID."""
        return next((lane for lane in self.lanes if lane.lane_id == lane_id), None)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "client_ABC",
                "name": "ABC Imports Co.",
                "contact_email": "ops@abcimports.com",
                "contact_phone": "+1-555-0100",
                "lanes": [
                    {
                        "lane_id": "CNSHA-USLAX-ocean",
                        "origin_port": "CNSHA",
                        "destination_port": "USLAX",
                        "mode": "ocean",
                        "status": "active",
                        "created_at": "2025-01-25T14:30:00Z",
                        "updated_at": "2025-01-25T14:30:00Z"
                    }
                ],
                "watch_skus": [
                    {
                        "sku_id": "SKU-123",
                        "description": "Cellular phones with camera",
                        "hts_code": "8517.12.00",
                        "origin_country": "CN",
                        "supplier_name": "Shanghai Electronics Co.",
                        "lanes": ["CNSHA-USLAX-ocean"],
                        "status": "active",
                        "risk_level": "warn",
                        "created_at": "2025-01-25T14:30:00Z",
                        "updated_at": "2025-01-25T14:30:00Z"
                    }
                ],
                "preferences": {
                    "duty_delta_threshold": 0.01,
                    "risk_level_filter": "warn",
                    "notification_channels": ["email"],
                    "email_addresses": ["ops@abcimports.com"],
                    "weekly_digest_enabled": True,
                    "weekly_digest_day": "sunday"
                },
                "is_active": True,
                "created_at": "2025-01-25T14:30:00Z",
                "updated_at": "2025-01-25T14:30:00Z"
            }
        }
    )


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
                "answer": (
                    "Based on current data, SKU-123 has a **moderate sanctions risk** due to its origin from China "
                    "and supplier Shanghai Electronics Co. No direct matches found in OFAC lists, but enhanced due "
                    "diligence recommended."
                ),
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
                "compliance_areas": [
                    "hts_classification",
                    "sanctions_screening",
                    "health_safety"
                ],
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
        risk_order = {
            TileStatus.CLEAR: 0,
            TileStatus.ATTENTION: 1,
            TileStatus.ACTION: 2,
            TileStatus.ERROR: 3,
        }
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
                        "details_md": (
                            "**Shanghai Electronics Co.** - No direct matches but enhanced due diligence recommended"
                        ),
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
