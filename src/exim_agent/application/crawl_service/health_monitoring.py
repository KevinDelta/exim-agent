"""Health monitoring and circuit breaker patterns for crawl service."""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
import time
from collections import deque
from loguru import logger


class CircuitBreakerState(Enum):
    """States of the circuit breaker."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, requests blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthMetric:
    """Individual health metric data."""
    name: str
    value: float
    status: HealthStatus
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""
    failure_threshold: int = 5
    success_threshold: int = 3
    timeout_seconds: int = 60
    half_open_max_calls: int = 3
    
    # Failure criteria
    failure_rate_threshold: float = 0.5  # 50% failure rate
    slow_call_threshold: float = 10.0    # 10 seconds
    slow_call_rate_threshold: float = 0.5  # 50% slow calls
    
    # Monitoring window
    monitoring_window_seconds: int = 300  # 5 minutes


class CircuitBreaker:
    """Circuit breaker implementation for handling service failures gracefully."""
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        """
        Initialize circuit breaker.
        
        Args:
            name: Name of the service/component being protected
            config: Circuit breaker configuration
        """
        self.name = name
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state_changed_time = datetime.utcnow()
        
        # Call history for monitoring
        self._call_history: deque = deque(maxlen=1000)
        self._half_open_calls = 0
        
        logger.info("Circuit breaker '{}' initialized in {} state", name, self.state.value)
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerOpenError: When circuit is open
            Exception: Original function exceptions when circuit is closed
        """
        if not await self._can_execute():
            raise CircuitBreakerOpenError(f"Circuit breaker '{self.name}' is OPEN")
        
        start_time = time.time()
        success = False
        error = None
        
        try:
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            success = True
            await self._on_success()
            return result
            
        except Exception as e:
            error = e
            await self._on_failure(e)
            raise
            
        finally:
            execution_time = time.time() - start_time
            self._record_call(success, execution_time, error)
    
    async def _can_execute(self) -> bool:
        """Check if execution is allowed based on circuit breaker state."""
        if self.state == CircuitBreakerState.CLOSED:
            return True
        
        if self.state == CircuitBreakerState.OPEN:
            # Check if timeout has passed
            if self.last_failure_time:
                time_since_failure = datetime.utcnow() - self.last_failure_time
                if time_since_failure.total_seconds() >= self.config.timeout_seconds:
                    await self._transition_to_half_open()
                    return True
            return False
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            # Allow limited calls in half-open state
            return self._half_open_calls < self.config.half_open_max_calls
        
        return False
    
    async def _on_success(self) -> None:
        """Handle successful call."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                await self._transition_to_closed()
        elif self.state == CircuitBreakerState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0
    
    async def _on_failure(self, error: Exception) -> None:
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.state == CircuitBreakerState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                await self._transition_to_open()
        elif self.state == CircuitBreakerState.HALF_OPEN:
            await self._transition_to_open()
    
    async def _transition_to_open(self) -> None:
        """Transition circuit breaker to OPEN state."""
        self.state = CircuitBreakerState.OPEN
        self.state_changed_time = datetime.utcnow()
        self.success_count = 0
        self._half_open_calls = 0
        
        logger.warning("Circuit breaker '{}' transitioned to OPEN state after {} failures", 
                      self.name, self.failure_count)
    
    async def _transition_to_half_open(self) -> None:
        """Transition circuit breaker to HALF_OPEN state."""
        self.state = CircuitBreakerState.HALF_OPEN
        self.state_changed_time = datetime.utcnow()
        self.success_count = 0
        self._half_open_calls = 0
        
        logger.info("Circuit breaker '{}' transitioned to HALF_OPEN state", self.name)
    
    async def _transition_to_closed(self) -> None:
        """Transition circuit breaker to CLOSED state."""
        self.state = CircuitBreakerState.CLOSED
        self.state_changed_time = datetime.utcnow()
        self.failure_count = 0
        self.success_count = 0
        self._half_open_calls = 0
        
        logger.info("Circuit breaker '{}' transitioned to CLOSED state", self.name)
    
    def _record_call(self, success: bool, execution_time: float, error: Optional[Exception]) -> None:
        """Record call metrics for monitoring."""
        call_record = {
            "timestamp": datetime.utcnow(),
            "success": success,
            "execution_time": execution_time,
            "error_type": type(error).__name__ if error else None,
            "state": self.state.value
        }
        
        self._call_history.append(call_record)
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            self._half_open_calls += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics."""
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.config.monitoring_window_seconds)
        
        # Filter calls within monitoring window
        recent_calls = [
            call for call in self._call_history 
            if call["timestamp"] >= window_start
        ]
        
        if not recent_calls:
            return {
                "name": self.name,
                "state": self.state.value,
                "failure_count": self.failure_count,
                "success_count": self.success_count,
                "total_calls": 0,
                "success_rate": 0.0,
                "failure_rate": 0.0,
                "avg_execution_time": 0.0,
                "slow_call_rate": 0.0,
                "last_state_change": self.state_changed_time.isoformat(),
                "monitoring_window_seconds": self.config.monitoring_window_seconds
            }
        
        total_calls = len(recent_calls)
        successful_calls = len([call for call in recent_calls if call["success"]])
        failed_calls = total_calls - successful_calls
        
        success_rate = successful_calls / total_calls if total_calls > 0 else 0.0
        failure_rate = failed_calls / total_calls if total_calls > 0 else 0.0
        
        execution_times = [call["execution_time"] for call in recent_calls]
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0.0
        
        slow_calls = len([t for t in execution_times if t >= self.config.slow_call_threshold])
        slow_call_rate = slow_calls / total_calls if total_calls > 0 else 0.0
        
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "total_calls": total_calls,
            "successful_calls": successful_calls,
            "failed_calls": failed_calls,
            "success_rate": success_rate,
            "failure_rate": failure_rate,
            "avg_execution_time": avg_execution_time,
            "slow_call_rate": slow_call_rate,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "last_state_change": self.state_changed_time.isoformat(),
            "monitoring_window_seconds": self.config.monitoring_window_seconds
        }


class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class HealthMonitor:
    """Health monitoring system for crawl service components."""
    
    def __init__(self):
        """Initialize health monitor."""
        self._metrics: Dict[str, HealthMetric] = {}
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._health_checks: Dict[str, Callable] = {}
        self._monitoring_enabled = True
        
        logger.info("Health monitor initialized")
    
    def register_circuit_breaker(
        self, 
        name: str, 
        config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """
        Register a circuit breaker for a service component.
        
        Args:
            name: Name of the component
            config: Circuit breaker configuration
            
        Returns:
            CircuitBreaker instance
        """
        if config is None:
            config = CircuitBreakerConfig()
        
        circuit_breaker = CircuitBreaker(name, config)
        self._circuit_breakers[name] = circuit_breaker
        
        logger.info("Registered circuit breaker for '{}'", name)
        return circuit_breaker
    
    def get_circuit_breaker(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name."""
        return self._circuit_breakers.get(name)
    
    def register_health_check(self, name: str, check_func: Callable) -> None:
        """
        Register a health check function.
        
        Args:
            name: Name of the health check
            check_func: Function that returns health status
        """
        self._health_checks[name] = check_func
        logger.info("Registered health check '{}'", name)
    
    async def run_health_checks(self) -> Dict[str, HealthMetric]:
        """
        Run all registered health checks.
        
        Returns:
            Dict of health metrics by check name
        """
        if not self._monitoring_enabled:
            return {}
        
        health_results = {}
        
        for name, check_func in self._health_checks.items():
            try:
                if asyncio.iscoroutinefunction(check_func):
                    result = await check_func()
                else:
                    result = check_func()
                
                # Convert result to HealthMetric
                if isinstance(result, HealthMetric):
                    metric = result
                elif isinstance(result, dict):
                    metric = HealthMetric(
                        name=name,
                        value=result.get("value", 0.0),
                        status=HealthStatus(result.get("status", "unknown")),
                        timestamp=datetime.utcnow(),
                        details=result.get("details", {})
                    )
                else:
                    # Assume numeric result
                    metric = HealthMetric(
                        name=name,
                        value=float(result),
                        status=HealthStatus.HEALTHY if result > 0 else HealthStatus.UNHEALTHY,
                        timestamp=datetime.utcnow()
                    )
                
                health_results[name] = metric
                self._metrics[name] = metric
                
            except Exception as e:
                logger.error("Health check '{}' failed: {}", name, str(e))
                error_metric = HealthMetric(
                    name=name,
                    value=0.0,
                    status=HealthStatus.UNHEALTHY,
                    timestamp=datetime.utcnow(),
                    details={"error": str(e)}
                )
                health_results[name] = error_metric
                self._metrics[name] = error_metric
        
        return health_results
    
    def get_overall_health(self) -> Dict[str, Any]:
        """
        Get overall health status of the system.
        
        Returns:
            Overall health summary
        """
        if not self._metrics:
            return {
                "status": HealthStatus.UNKNOWN.value,
                "message": "No health metrics available",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Determine overall status based on individual metrics
        statuses = [metric.status for metric in self._metrics.values()]
        
        if any(status == HealthStatus.UNHEALTHY for status in statuses):
            overall_status = HealthStatus.UNHEALTHY
            message = "One or more components are unhealthy"
        elif any(status == HealthStatus.DEGRADED for status in statuses):
            overall_status = HealthStatus.DEGRADED
            message = "Some components are degraded"
        elif all(status == HealthStatus.HEALTHY for status in statuses):
            overall_status = HealthStatus.HEALTHY
            message = "All components are healthy"
        else:
            overall_status = HealthStatus.UNKNOWN
            message = "Health status is unclear"
        
        # Get circuit breaker summary
        circuit_breaker_summary = {}
        for name, cb in self._circuit_breakers.items():
            cb_metrics = cb.get_metrics()
            circuit_breaker_summary[name] = {
                "state": cb_metrics["state"],
                "failure_rate": cb_metrics["failure_rate"],
                "success_rate": cb_metrics["success_rate"]
            }
        
        return {
            "status": overall_status.value,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "component_count": len(self._metrics),
            "healthy_components": len([m for m in self._metrics.values() if m.status == HealthStatus.HEALTHY]),
            "degraded_components": len([m for m in self._metrics.values() if m.status == HealthStatus.DEGRADED]),
            "unhealthy_components": len([m for m in self._metrics.values() if m.status == HealthStatus.UNHEALTHY]),
            "circuit_breakers": circuit_breaker_summary,
            "monitoring_enabled": self._monitoring_enabled
        }
    
    def get_detailed_health(self) -> Dict[str, Any]:
        """
        Get detailed health information including all metrics and circuit breakers.
        
        Returns:
            Detailed health report
        """
        overall_health = self.get_overall_health()
        
        # Add detailed metrics
        detailed_metrics = {}
        for name, metric in self._metrics.items():
            detailed_metrics[name] = {
                "value": metric.value,
                "status": metric.status.value,
                "timestamp": metric.timestamp.isoformat(),
                "details": metric.details
            }
        
        # Add detailed circuit breaker metrics
        detailed_circuit_breakers = {}
        for name, cb in self._circuit_breakers.items():
            detailed_circuit_breakers[name] = cb.get_metrics()
        
        return {
            **overall_health,
            "metrics": detailed_metrics,
            "circuit_breakers": detailed_circuit_breakers
        }
    
    def enable_monitoring(self, enabled: bool = True) -> None:
        """Enable or disable health monitoring."""
        self._monitoring_enabled = enabled
        logger.info("Health monitoring {}", "enabled" if enabled else "disabled")
    
    def clear_metrics(self) -> None:
        """Clear all stored metrics."""
        self._metrics.clear()
        logger.info("Cleared all health metrics")
    
    def get_metric(self, name: str) -> Optional[HealthMetric]:
        """Get specific health metric by name."""
        return self._metrics.get(name)
    
    def set_metric(self, metric: HealthMetric) -> None:
        """Set a health metric directly."""
        self._metrics[metric.name] = metric


class CrawlServiceHealthChecks:
    """Predefined health checks for crawl service components."""
    
    def __init__(self, crawl_service):
        """
        Initialize health checks for crawl service.
        
        Args:
            crawl_service: CrawlService instance to monitor
        """
        self.crawl_service = crawl_service
    
    async def check_crawler_availability(self) -> HealthMetric:
        """Check if crawlers are available and responsive."""
        try:
            crawler_types = self.crawl_service.get_crawler_types()
            available_count = len(crawler_types)
            
            if available_count >= 4:  # All expected crawlers
                status = HealthStatus.HEALTHY
            elif available_count >= 2:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.UNHEALTHY
            
            return HealthMetric(
                name="crawler_availability",
                value=available_count,
                status=status,
                timestamp=datetime.utcnow(),
                details={
                    "available_crawlers": crawler_types,
                    "expected_count": 4
                }
            )
            
        except Exception as e:
            return HealthMetric(
                name="crawler_availability",
                value=0.0,
                status=HealthStatus.UNHEALTHY,
                timestamp=datetime.utcnow(),
                details={"error": str(e)}
            )
    
    async def check_task_queue_health(self) -> HealthMetric:
        """Check task queue health and processing capacity."""
        try:
            summary = self.crawl_service.get_active_tasks_summary()
            queue_size = summary.get("queue_size", 0)
            active_workers = summary.get("active_workers", 0)
            
            # Determine health based on queue size and worker availability
            if queue_size == 0 and active_workers > 0:
                status = HealthStatus.HEALTHY
                value = 100.0
            elif queue_size < 10 and active_workers > 0:
                status = HealthStatus.HEALTHY
                value = 90.0
            elif queue_size < 50:
                status = HealthStatus.DEGRADED
                value = 70.0
            else:
                status = HealthStatus.UNHEALTHY
                value = 30.0
            
            return HealthMetric(
                name="task_queue_health",
                value=value,
                status=status,
                timestamp=datetime.utcnow(),
                details={
                    "queue_size": queue_size,
                    "active_workers": active_workers,
                    "total_tasks": summary.get("total_tasks", 0)
                }
            )
            
        except Exception as e:
            return HealthMetric(
                name="task_queue_health",
                value=0.0,
                status=HealthStatus.UNHEALTHY,
                timestamp=datetime.utcnow(),
                details={"error": str(e)}
            )
    
    async def check_schedule_health(self) -> HealthMetric:
        """Check health of scheduled crawling tasks."""
        try:
            summary = self.crawl_service.get_schedules_summary()
            total_schedules = summary.get("total_schedules", 0)
            enabled_schedules = summary.get("enabled_schedules", 0)
            
            if total_schedules == 0:
                status = HealthStatus.HEALTHY  # No schedules is OK
                value = 100.0
            else:
                enabled_ratio = enabled_schedules / total_schedules
                if enabled_ratio >= 0.8:
                    status = HealthStatus.HEALTHY
                    value = 100.0 * enabled_ratio
                elif enabled_ratio >= 0.5:
                    status = HealthStatus.DEGRADED
                    value = 100.0 * enabled_ratio
                else:
                    status = HealthStatus.UNHEALTHY
                    value = 100.0 * enabled_ratio
            
            return HealthMetric(
                name="schedule_health",
                value=value,
                status=status,
                timestamp=datetime.utcnow(),
                details={
                    "total_schedules": total_schedules,
                    "enabled_schedules": enabled_schedules,
                    "disabled_schedules": summary.get("disabled_schedules", 0)
                }
            )
            
        except Exception as e:
            return HealthMetric(
                name="schedule_health",
                value=0.0,
                status=HealthStatus.UNHEALTHY,
                timestamp=datetime.utcnow(),
                details={"error": str(e)}
            )