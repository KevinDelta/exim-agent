"""Base tool for compliance data sources."""

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
import httpx
from loguru import logger
from pydantic import BaseModel, Field

from ..models import ToolResponse


class CircuitBreakerState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """Circuit breaker implementation for external API calls."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before trying again
            expected_exception: Exception type that triggers circuit breaker
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED
    
    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitBreakerState.HALF_OPEN
            else:
                raise Exception(f"Circuit breaker is OPEN. Service unavailable.")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        return (
            self.last_failure_time and
            time.time() - self.last_failure_time >= self.recovery_timeout
        )
    
    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN


class RetryConfig(BaseModel):
    """Configuration for retry logic."""
    
    max_attempts: int = Field(
        default=3,
        description="Maximum number of retry attempts",
        ge=1,
        le=10
    )
    base_delay: float = Field(
        default=1.0,
        description="Base delay between retries in seconds",
        ge=0.1,
        le=60.0
    )
    max_delay: float = Field(
        default=30.0,
        description="Maximum delay between retries in seconds",
        ge=1.0,
        le=300.0
    )
    exponential_backoff: bool = Field(
        default=True,
        description="Use exponential backoff for retry delays"
    )
    jitter: bool = Field(
        default=True,
        description="Add random jitter to retry delays"
    )


class ComplianceTool(ABC):
    """Base class for compliance tools with caching, circuit breaker, and retry logic."""
    
    def __init__(
        self,
        cache_ttl_seconds: int = 86400,
        retry_config: Optional[RetryConfig] = None,
        circuit_breaker_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize compliance tool.
        
        Args:
            cache_ttl_seconds: Time-to-live for cache in seconds (default: 24 hours)
            retry_config: Retry configuration
            circuit_breaker_config: Circuit breaker configuration
        """
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: Dict[str, tuple[datetime, ToolResponse]] = {}
        
        # HTTP client with reasonable defaults
        self.client = httpx.Client(
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            headers={"User-Agent": "ComplianceIntelligencePlatform/1.0"}
        )
        
        # Retry configuration
        self.retry_config = retry_config or RetryConfig()
        
        # Circuit breaker
        cb_config = circuit_breaker_config or {}
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=cb_config.get("failure_threshold", 5),
            recovery_timeout=cb_config.get("recovery_timeout", 60),
            expected_exception=httpx.HTTPError
        )
        
        # Rate limiting
        self._last_request_time = 0
        self._min_request_interval = 0.1  # 100ms between requests
    
    def _get_cache_key(self, **kwargs) -> str:
        """Generate cache key from kwargs."""
        # Sort kwargs for consistent cache keys
        sorted_items = sorted(kwargs.items())
        return f"{self.__class__.__name__}:" + "_".join(f"{k}={v}" for k, v in sorted_items)
    
    def _get_from_cache(self, cache_key: str) -> Optional[ToolResponse]:
        """Get value from cache if not expired."""
        if cache_key in self._cache:
            timestamp, response = self._cache[cache_key]
            if datetime.utcnow() - timestamp < timedelta(seconds=self.cache_ttl_seconds):
                logger.debug(f"Cache hit for {cache_key}")
                # Mark as cached and return
                cached_response = response.model_copy()
                cached_response.cached = True
                return cached_response
            else:
                # Cache expired, remove it
                del self._cache[cache_key]
                logger.debug(f"Cache expired for {cache_key}")
        return None
    
    def _set_cache(self, cache_key: str, response: ToolResponse):
        """Set response in cache with current timestamp."""
        self._cache[cache_key] = (datetime.utcnow(), response)
        logger.debug(f"Cached result for {cache_key}")
    
    def _rate_limit(self):
        """Apply rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        
        if time_since_last < self._min_request_interval:
            sleep_time = self._min_request_interval - time_since_last
            logger.debug(f"Rate limiting: sleeping {sleep_time:.3f}s")
            time.sleep(sleep_time)
        
        self._last_request_time = time.time()
    
    def _retry_with_backoff(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry logic and exponential backoff."""
        import random
        
        last_exception = None
        
        for attempt in range(self.retry_config.max_attempts):
            try:
                result = func(*args, **kwargs)
                if attempt > 0:
                    logger.info(f"{self.__class__.__name__} succeeded on attempt {attempt + 1}")
                return result
            except Exception as e:
                last_exception = e
                
                # Log error for monitoring (requirement 7.1)
                logger.error(
                    f"{self.__class__.__name__} attempt {attempt + 1}/{self.retry_config.max_attempts} failed: {e}",
                    extra={
                        "tool_name": self.__class__.__name__,
                        "attempt": attempt + 1,
                        "max_attempts": self.retry_config.max_attempts,
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    }
                )
                
                if attempt == self.retry_config.max_attempts - 1:
                    # Last attempt, re-raise the exception
                    logger.error(
                        f"{self.__class__.__name__} failed after {self.retry_config.max_attempts} attempts. "
                        f"Final error: {e}"
                    )
                    raise e
                
                # Calculate delay with exponential backoff
                if self.retry_config.exponential_backoff:
                    delay = self.retry_config.base_delay * (2 ** attempt)
                else:
                    delay = self.retry_config.base_delay
                
                # Apply max delay limit
                delay = min(delay, self.retry_config.max_delay)
                
                # Add jitter if enabled
                if self.retry_config.jitter:
                    delay *= (0.5 + random.random() * 0.5)  # 50-100% of calculated delay
                
                logger.warning(
                    f"{self.__class__.__name__} retrying in {delay:.2f}s (attempt {attempt + 1}/{self.retry_config.max_attempts})"
                )
                time.sleep(delay)
        
        # This should never be reached, but just in case
        raise last_exception
    
    @abstractmethod
    def _run_impl(self, **kwargs) -> Dict[str, Any]:
        """Implementation of tool logic. Must be overridden by subclasses."""
        pass
    
    def _get_fallback_data(self, **kwargs) -> Dict[str, Any]:
        """
        Get fallback data when API fails. Override in subclasses to provide mock data.
        
        Args:
            **kwargs: Same arguments passed to _run_impl
            
        Returns:
            Dict containing fallback/mock data
            
        Raises:
            NotImplementedError: If subclass doesn't implement fallback data
        """
        raise NotImplementedError(f"{self.__class__.__name__} does not implement fallback data")
    
    def run(self, **kwargs) -> ToolResponse:
        """
        Run the tool with caching, circuit breaker, and retry logic.
        
        Returns:
            ToolResponse with execution details
        """
        start_time = time.time()
        cache_key = self._get_cache_key(**kwargs)
        retry_count = 0
        
        # Check cache first
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            return cached_result
        
        def execute_with_protection():
            nonlocal retry_count
            retry_count += 1
            
            # Apply rate limiting
            self._rate_limit()
            
            # Execute with circuit breaker protection
            return self.circuit_breaker.call(self._run_impl, **kwargs)
        
        try:
            # Execute with retry logic
            result = self._retry_with_backoff(execute_with_protection)
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            response = ToolResponse(
                success=True,
                data=result,
                cached=False,
                execution_time_ms=execution_time_ms,
                retry_count=retry_count - 1,  # Subtract 1 since we increment on first attempt
                circuit_breaker_state=self.circuit_breaker.state.value
            )
            
            # Cache successful responses
            self._set_cache(cache_key, response)
            return response
        
        except Exception as e:
            logger.error(
                f"{self.__class__.__name__} final failure after retries: {e}",
                extra={
                    "tool_name": self.__class__.__name__,
                    "total_attempts": retry_count,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "kwargs": kwargs
                }
            )
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Try to get fallback data (requirement 7.1)
            try:
                fallback_data = self._get_fallback_data(**kwargs)
                logger.info(f"{self.__class__.__name__} using fallback data after API failure")
                
                return ToolResponse(
                    success=True,
                    data=fallback_data,
                    cached=False,
                    execution_time_ms=execution_time_ms,
                    retry_count=retry_count - 1,
                    circuit_breaker_state=self.circuit_breaker.state.value,
                    error=f"API failed, using fallback: {str(e)}",
                    error_type="api_failure_fallback"
                )
            except Exception as fallback_error:
                logger.error(f"{self.__class__.__name__} fallback also failed: {fallback_error}")
                
                # Determine error type
                error_type = "http_error" if isinstance(e, httpx.HTTPError) else "unknown"
                
                return ToolResponse(
                    success=False,
                    error=str(e),
                    error_type=error_type,
                    execution_time_ms=execution_time_ms,
                    retry_count=retry_count - 1,
                    circuit_breaker_state=self.circuit_breaker.state.value
                )
    
    def clear_cache(self):
        """Clear all cached results."""
        cache_size = len(self._cache)
        self._cache.clear()
        logger.info(f"Cleared {cache_size} cached results for {self.__class__.__name__}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_entries = len(self._cache)
        expired_entries = 0
        current_time = datetime.utcnow()
        
        for timestamp, _ in self._cache.values():
            if current_time - timestamp >= timedelta(seconds=self.cache_ttl_seconds):
                expired_entries += 1
        
        return {
            "total_entries": total_entries,
            "expired_entries": expired_entries,
            "valid_entries": total_entries - expired_entries,
            "cache_ttl_seconds": self.cache_ttl_seconds
        }
    
    def get_circuit_breaker_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        return {
            "state": self.circuit_breaker.state.value,
            "failure_count": self.circuit_breaker.failure_count,
            "failure_threshold": self.circuit_breaker.failure_threshold,
            "last_failure_time": self.circuit_breaker.last_failure_time,
            "recovery_timeout": self.circuit_breaker.recovery_timeout
        }
    
    def reset_circuit_breaker(self):
        """Reset circuit breaker to closed state."""
        self.circuit_breaker.failure_count = 0
        self.circuit_breaker.last_failure_time = None
        self.circuit_breaker.state = CircuitBreakerState.CLOSED
        logger.info(f"Reset circuit breaker for {self.__class__.__name__}")
    
    def validate_response_schema(self, data: Dict[str, Any]) -> bool:
        """
        Validate response data schema. Override in subclasses for specific validation.
        
        Args:
            data: Response data to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Basic validation - ensure data is a dictionary
        return isinstance(data, dict)
    
    def __del__(self):
        """Clean up HTTP client."""
        if hasattr(self, 'client'):
            try:
                self.client.close()
            except Exception:
                pass  # Ignore cleanup errors
