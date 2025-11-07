"""Rate limiter component for respectful web crawling."""

import asyncio
import time
from collections import defaultdict, deque
from typing import Dict, Optional
from urllib.parse import urlparse

from loguru import logger


class RateLimiter:
    """Rate limiter with configurable delays and respectful crawling behavior."""
    
    def __init__(
        self,
        default_rate: float = 1.0,
        domain_rates: Optional[Dict[str, float]] = None,
        burst_size: int = 5,
        backoff_factor: float = 2.0,
        max_backoff: float = 60.0,
    ):
        """Initialize rate limiter.
        
        Args:
            default_rate: Default requests per second
            domain_rates: Domain-specific rate limits (domain -> rate)
            burst_size: Number of requests allowed in burst
            backoff_factor: Exponential backoff multiplier
            max_backoff: Maximum backoff delay in seconds
        """
        self.default_rate = default_rate
        self.domain_rates = domain_rates or {}
        self.burst_size = burst_size
        self.backoff_factor = backoff_factor
        self.max_backoff = max_backoff
        
        # Track request history per domain
        self._request_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=burst_size))
        self._last_request: Dict[str, float] = {}
        self._backoff_delays: Dict[str, float] = defaultdict(float)
        self._locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
    
    def get_domain(self, url: str) -> str:
        """Extract domain from URL.
        
        Args:
            url: Full URL
            
        Returns:
            Domain name
        """
        try:
            return urlparse(url).netloc.lower()
        except Exception:
            return "unknown"
    
    def get_rate_limit(self, domain: str) -> float:
        """Get rate limit for domain.
        
        Args:
            domain: Domain name
            
        Returns:
            Requests per second limit
        """
        return self.domain_rates.get(domain, self.default_rate)
    
    async def acquire(self, url: str) -> float:
        """Acquire permission to make request with rate limiting.
        
        Args:
            url: Target URL
            
        Returns:
            Actual delay applied in seconds
        """
        domain = self.get_domain(url)
        
        async with self._locks[domain]:
            return await self._acquire_for_domain(domain)
    
    async def _acquire_for_domain(self, domain: str) -> float:
        """Acquire permission for specific domain.
        
        Args:
            domain: Domain name
            
        Returns:
            Actual delay applied in seconds
        """
        now = time.time()
        rate_limit = self.get_rate_limit(domain)
        min_interval = 1.0 / rate_limit
        
        # Check if we need to apply backoff
        backoff_delay = self._backoff_delays[domain]
        if backoff_delay > 0:
            logger.info(f"Applying backoff delay of {backoff_delay:.2f}s for {domain}")
            await asyncio.sleep(backoff_delay)
            self._backoff_delays[domain] = 0  # Reset after applying
            return backoff_delay
        
        # Check burst limit
        history = self._request_history[domain]
        if len(history) >= self.burst_size:
            # Check if oldest request is within the time window
            oldest_request = history[0]
            time_window = self.burst_size / rate_limit
            
            if now - oldest_request < time_window:
                # Need to wait
                wait_time = time_window - (now - oldest_request)
                logger.debug(f"Burst limit reached for {domain}, waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
                now = time.time()
        
        # Check minimum interval since last request
        last_request = self._last_request.get(domain, 0)
        if last_request > 0:
            time_since_last = now - last_request
            if time_since_last < min_interval:
                wait_time = min_interval - time_since_last
                logger.debug(f"Rate limiting {domain}, waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
                now = time.time()
        
        # Record this request
        history.append(now)
        self._last_request[domain] = now
        
        return 0.0  # No additional delay was needed
    
    def record_error(self, url: str, status_code: int):
        """Record an error response for backoff calculation.
        
        Args:
            url: URL that returned error
            status_code: HTTP status code
        """
        domain = self.get_domain(url)
        
        # Apply backoff for rate limiting or server errors
        if status_code == 429 or status_code >= 500:
            current_backoff = self._backoff_delays[domain]
            if current_backoff == 0:
                new_backoff = 1.0  # Start with 1 second
            else:
                new_backoff = min(current_backoff * self.backoff_factor, self.max_backoff)
            
            self._backoff_delays[domain] = new_backoff
            logger.warning(
                f"Error {status_code} for {domain}, applying backoff delay of {new_backoff:.2f}s"
            )
    
    def record_success(self, url: str):
        """Record a successful response.
        
        Args:
            url: URL that succeeded
        """
        domain = self.get_domain(url)
        
        # Reduce backoff on success
        if self._backoff_delays[domain] > 0:
            self._backoff_delays[domain] = max(
                self._backoff_delays[domain] / self.backoff_factor,
                0.0
            )
    
    def get_stats(self) -> Dict[str, Dict[str, float]]:
        """Get rate limiting statistics.
        
        Returns:
            Dictionary with stats per domain
        """
        stats = {}
        now = time.time()
        
        for domain in set(list(self._request_history.keys()) + list(self._last_request.keys())):
            history = self._request_history[domain]
            last_request = self._last_request.get(domain, 0)
            
            # Calculate recent request rate
            recent_requests = [t for t in history if now - t <= 60]  # Last minute
            recent_rate = len(recent_requests) / 60.0
            
            stats[domain] = {
                "rate_limit": self.get_rate_limit(domain),
                "recent_rate": recent_rate,
                "last_request_ago": now - last_request if last_request > 0 else -1,
                "backoff_delay": self._backoff_delays[domain],
                "total_requests": len(history),
            }
        
        return stats
    
    def reset_domain(self, domain: str):
        """Reset rate limiting state for a domain.
        
        Args:
            domain: Domain to reset
        """
        if domain in self._request_history:
            self._request_history[domain].clear()
        if domain in self._last_request:
            del self._last_request[domain]
        if domain in self._backoff_delays:
            self._backoff_delays[domain] = 0
        
        logger.info(f"Reset rate limiting state for {domain}")
    
    def update_domain_rate(self, domain: str, rate: float):
        """Update rate limit for a specific domain.
        
        Args:
            domain: Domain name
            rate: New requests per second limit
        """
        self.domain_rates[domain] = rate
        logger.info(f"Updated rate limit for {domain} to {rate} req/s")