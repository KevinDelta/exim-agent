"""Client profile domain models for compliance platform."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, validator

from .enums import TransportMode, NotificationChannel, RiskLevel, MonitoringStatus


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
    
    # Alert thresholds
    duty_delta_threshold: float = Field(
        default=0.01,
        description="Minimum duty rate change to trigger alert (as decimal, e.g., 0.01 = 1%)",
        ge=0.0,
        le=1.0
    )
    risk_level_filter: RiskLevel = Field(
        default=RiskLevel.WARN,
        description="Minimum risk level for alerts"
    )
    
    # Notification preferences
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
    
    # Digest preferences
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
    
    # Monitoring preferences
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
