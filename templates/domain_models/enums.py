"""Compliance domain enumerations."""

from enum import Enum


class EventType(str, Enum):
    """Types of compliance events."""
    HTS = "HTS"
    FTA = "FTA"
    SANCTIONS = "SANCTIONS"
    HEALTH_SAFETY = "HEALTH_SAFETY"
    RULING = "RULING"


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


class TransportMode(str, Enum):
    """Transport modes for lanes."""
    OCEAN = "ocean"
    AIR = "air"
    TRUCK = "truck"
    RAIL = "rail"
