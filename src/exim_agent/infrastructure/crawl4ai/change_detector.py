"""Change detector service for monitoring content changes and versioning."""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

from loguru import logger


class ContentVersion:
    """Represents a version of content with metadata."""
    
    def __init__(
        self,
        content_hash: str,
        timestamp: datetime,
        content_length: int,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.content_hash = content_hash
        self.timestamp = timestamp
        self.content_length = content_length
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "content_hash": self.content_hash,
            "timestamp": self.timestamp.isoformat(),
            "content_length": self.content_length,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContentVersion":
        """Create from dictionary."""
        return cls(
            content_hash=data["content_hash"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            content_length=data["content_length"],
            metadata=data.get("metadata", {}),
        )


class ChangeDetector:
    """Service for monitoring content changes and versioning."""
    
    def __init__(
        self,
        max_versions_per_url: int = 10,
        change_threshold: float = 0.1,
        min_change_interval: int = 3600,  # 1 hour in seconds
    ):
        """Initialize change detector.
        
        Args:
            max_versions_per_url: Maximum versions to keep per URL
            change_threshold: Minimum content change ratio to consider significant
            min_change_interval: Minimum seconds between change notifications
        """
        self.max_versions_per_url = max_versions_per_url
        self.change_threshold = change_threshold
        self.min_change_interval = min_change_interval
        
        # In-memory storage for content versions
        # In production, this would be backed by a database
        self._content_versions: Dict[str, List[ContentVersion]] = {}
        self._last_change_notification: Dict[str, datetime] = {}
    
    def generate_content_hash(self, content: str) -> str:
        """Generate SHA-256 hash of content.
        
        Args:
            content: Content to hash
            
        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def detect_change(
        self,
        url: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Optional[ContentVersion]]:
        """Detect if content has changed since last version.
        
        Args:
            url: URL of the content
            content: Current content
            metadata: Additional metadata for this version
            
        Returns:
            Tuple of (has_changed, previous_version)
        """
        content_hash = self.generate_content_hash(content)
        current_time = datetime.utcnow()
        
        # Get previous versions for this URL
        versions = self._content_versions.get(url, [])
        
        # Check if content has changed
        if not versions:
            # First time seeing this URL
            has_changed = True
            previous_version = None
        else:
            latest_version = versions[-1]
            has_changed = latest_version.content_hash != content_hash
            previous_version = latest_version if has_changed else None
        
        # Store new version if changed or if this is the first version
        if has_changed or not versions:
            new_version = ContentVersion(
                content_hash=content_hash,
                timestamp=current_time,
                content_length=len(content),
                metadata=metadata,
            )
            
            self._add_version(url, new_version)
            
            if has_changed and previous_version:
                logger.info(
                    f"Content change detected for {url}: "
                    f"{previous_version.content_hash[:8]} -> {content_hash[:8]}"
                )
        
        return has_changed, previous_version
    
    def _add_version(self, url: str, version: ContentVersion):
        """Add a new version for URL, maintaining version limit.
        
        Args:
            url: URL of the content
            version: New content version
        """
        if url not in self._content_versions:
            self._content_versions[url] = []
        
        versions = self._content_versions[url]
        versions.append(version)
        
        # Maintain version limit
        if len(versions) > self.max_versions_per_url:
            versions.pop(0)  # Remove oldest version
    
    def should_notify_change(self, url: str) -> bool:
        """Check if enough time has passed to notify about changes.
        
        Args:
            url: URL to check
            
        Returns:
            True if change notification should be sent
        """
        last_notification = self._last_change_notification.get(url)
        if not last_notification:
            return True
        
        time_since_last = (datetime.utcnow() - last_notification).total_seconds()
        return time_since_last >= self.min_change_interval
    
    def mark_change_notified(self, url: str):
        """Mark that change notification was sent for URL.
        
        Args:
            url: URL that was notified
        """
        self._last_change_notification[url] = datetime.utcnow()
    
    def calculate_change_significance(
        self,
        current_content: str,
        previous_version: ContentVersion,
    ) -> float:
        """Calculate significance of content change.
        
        Args:
            current_content: Current content
            previous_version: Previous version to compare against
            
        Returns:
            Change significance ratio (0.0 to 1.0)
        """
        current_length = len(current_content)
        previous_length = previous_version.content_length
        
        if previous_length == 0:
            return 1.0 if current_length > 0 else 0.0
        
        # Simple length-based change calculation
        # In production, could use more sophisticated diff algorithms
        length_change = abs(current_length - previous_length) / previous_length
        
        return min(length_change, 1.0)
    
    def is_significant_change(
        self,
        current_content: str,
        previous_version: ContentVersion,
    ) -> bool:
        """Check if change is significant enough to act upon.
        
        Args:
            current_content: Current content
            previous_version: Previous version to compare against
            
        Returns:
            True if change is significant
        """
        significance = self.calculate_change_significance(current_content, previous_version)
        return significance >= self.change_threshold
    
    def get_version_history(self, url: str) -> List[ContentVersion]:
        """Get version history for URL.
        
        Args:
            url: URL to get history for
            
        Returns:
            List of content versions, oldest first
        """
        return self._content_versions.get(url, []).copy()
    
    def get_latest_version(self, url: str) -> Optional[ContentVersion]:
        """Get latest version for URL.
        
        Args:
            url: URL to get latest version for
            
        Returns:
            Latest content version or None if no versions exist
        """
        versions = self._content_versions.get(url, [])
        return versions[-1] if versions else None
    
    def get_change_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get summary of changes in the last N hours.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Dictionary with change statistics
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        total_urls = len(self._content_versions)
        changed_urls = set()
        total_changes = 0
        
        for url, versions in self._content_versions.items():
            recent_versions = [v for v in versions if v.timestamp >= cutoff_time]
            if len(recent_versions) > 1:
                changed_urls.add(url)
                total_changes += len(recent_versions) - 1
        
        return {
            "time_period_hours": hours,
            "total_monitored_urls": total_urls,
            "urls_with_changes": len(changed_urls),
            "total_changes": total_changes,
            "change_rate": len(changed_urls) / total_urls if total_urls > 0 else 0.0,
            "changed_urls": list(changed_urls),
        }
    
    def cleanup_old_versions(self, days: int = 30):
        """Clean up versions older than specified days.
        
        Args:
            days: Number of days to keep versions for
        """
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        cleaned_count = 0
        
        for url in list(self._content_versions.keys()):
            versions = self._content_versions[url]
            
            # Keep at least one version and all recent versions
            recent_versions = [v for v in versions if v.timestamp >= cutoff_time]
            
            if not recent_versions and versions:
                # Keep the most recent version even if it's old
                recent_versions = [versions[-1]]
            
            if len(recent_versions) < len(versions):
                cleaned_count += len(versions) - len(recent_versions)
                self._content_versions[url] = recent_versions
        
        logger.info(f"Cleaned up {cleaned_count} old content versions")
    
    def export_versions(self, url: Optional[str] = None) -> Dict[str, Any]:
        """Export version data for backup or analysis.
        
        Args:
            url: Specific URL to export, or None for all URLs
            
        Returns:
            Dictionary with version data
        """
        if url:
            versions = self._content_versions.get(url, [])
            return {
                url: [v.to_dict() for v in versions]
            }
        else:
            return {
                url: [v.to_dict() for v in versions]
                for url, versions in self._content_versions.items()
            }
    
    def import_versions(self, data: Dict[str, Any]):
        """Import version data from backup.
        
        Args:
            data: Dictionary with version data from export_versions
        """
        for url, version_dicts in data.items():
            versions = [ContentVersion.from_dict(v) for v in version_dicts]
            self._content_versions[url] = versions
        
        logger.info(f"Imported version data for {len(data)} URLs")