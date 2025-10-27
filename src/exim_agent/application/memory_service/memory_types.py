"""Memory type definitions for Mem0 integration."""

from enum import Enum
from typing import TypedDict


class MemoryType(str, Enum):
    """Memory type identifiers."""
    USER = "user"
    AGENT = "agent"
    SESSION = "session"


class MemoryMessage(TypedDict):
    """Message format for Mem0."""
    role: str  # "user" or "assistant"
    content: str
