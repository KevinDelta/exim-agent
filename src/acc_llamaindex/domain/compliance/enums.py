"""Compliance domain enumerations."""

from enum import Enum


class EventType(str, Enum):
    """Types of compliance events."""
    HTS = "HTS"
    FTA = "FTA"
    SANCTIONS = "SANCTIONS"
    HEALTH_SAFETY = "HEALTH_SAFETY"
    RULING = "RULING"
    POLICY_UPDATE = "POLICY_UPDATE"
    SYSTEM_ALERT = "SYSTEM_ALERT"


class RiskLevel(str, Enum):
    """Risk severity levels for compliance events."""
    INFO = "info"
    WARN = "warn"
    CRITICAL = "critical"


class TileStatus(str, Enum):
    """Status indicators for snapshot tiles."""
    CLEAR = "clear"
    ATTENTION = "attention"
    ACTION = "action"
    ERROR = "error"


class TransportMode(str, Enum):
    """Transport modes for lanes."""
    OCEAN = "ocean"
    AIR = "air"
    TRUCK = "truck"
    RAIL = "rail"


class NotificationChannel(str, Enum):
    """Notification delivery channels."""
    EMAIL = "email"
    WEBHOOK = "webhook"
    SLACK = "slack"
    SMS = "sms"


class AlertStatus(str, Enum):
    """Status of compliance alerts."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    DISMISSED = "dismissed"
    RESOLVED = "resolved"


class MonitoringStatus(str, Enum):
    """Status of SKU/lane monitoring."""
    ACTIVE = "active"
    PAUSED = "paused"
    INACTIVE = "inactive"


class ComplianceArea(str, Enum):
    """Compliance monitoring areas."""
    HTS_CLASSIFICATION = "hts_classification"
    SANCTIONS_SCREENING = "sanctions_screening"
    HEALTH_SAFETY = "health_safety"
    TRADE_RULINGS = "trade_rulings"
    FTA_ELIGIBILITY = "fta_eligibility"
    POLICY_CHANGES = "policy_changes"
