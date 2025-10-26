"""Base tool for compliance data sources."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from datetime import datetime, timedelta
import httpx
from loguru import logger


class ComplianceTool(ABC):
    """Base class for compliance tools with caching and error handling."""
    
    def __init__(self, cache_ttl_seconds: int = 86400):
        """
        Initialize compliance tool.
        
        Args:
            cache_ttl_seconds: Time-to-live for cache in seconds (default: 24 hours)
        """
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: Dict[str, tuple[datetime, Any]] = {}
        self.client = httpx.Client(timeout=30.0)
    
    def _get_cache_key(self, **kwargs) -> str:
        """Generate cache key from kwargs."""
        return "_".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
    
    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if cache_key in self._cache:
            timestamp, value = self._cache[cache_key]
            if datetime.utcnow() - timestamp < timedelta(seconds=self.cache_ttl_seconds):
                logger.debug(f"Cache hit for {cache_key}")
                return value
            else:
                # Cache expired, remove it
                del self._cache[cache_key]
        return None
    
    def _set_cache(self, cache_key: str, value: Any):
        """Set value in cache with current timestamp."""
        self._cache[cache_key] = (datetime.utcnow(), value)
        logger.debug(f"Cached result for {cache_key}")
    
    @abstractmethod
    def _run_impl(self, **kwargs) -> Dict[str, Any]:
        """Implementation of tool logic. Must be overridden by subclasses."""
        pass
    
    def run(self, **kwargs) -> Dict[str, Any]:
        """
        Run the tool with caching and error handling.
        
        Returns:
            Dict with 'success', 'data', and optional 'error' keys
        """
        cache_key = self._get_cache_key(**kwargs)
        
        # Check cache first
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
                # Mark the result as cached before returning
                cached_result = dict(cached_result)
                cached_result["cached"] = True
                return cached_result
        
        try:
            result = self._run_impl(**kwargs)
            response = {
                "success": True,
                "data": result,
                "cached": False,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            self._set_cache(cache_key, response)
            return response
        
        except httpx.HTTPError as e:
            logger.error(f"{self.__class__.__name__} HTTP error: {e}")
            return {
                "success": False,
                "error": f"HTTP error: {str(e)}",
                "error_type": "http_error"
            }
        
        except Exception as e:
            logger.error(f"{self.__class__.__name__} error: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "unknown"
            }
    
    def clear_cache(self):
        """Clear all cached results."""
        self._cache.clear()
        logger.info(f"Cleared cache for {self.__class__.__name__}")
    
    def __del__(self):
        """Clean up HTTP client."""
        if hasattr(self, 'client'):
            self.client.close()
