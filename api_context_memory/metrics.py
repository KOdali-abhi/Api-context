"""
Metrics and logging for API Context Memory System.

This module provides enhanced logging and metrics:
- Request/response metrics
- Performance tracking
- Error statistics
- Custom metric collectors
"""

import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("api_context_memory.metrics")


@dataclass
class RequestMetric:
    """Represents metrics for a single request."""
    
    url: str
    method: str
    status_code: int
    response_time_ms: float
    request_size: int
    response_size: int
    timestamp: str
    error: Optional[str] = None
    endpoint: str = ""
    
    def __post_init__(self):
        """Extract endpoint from URL."""
        if not self.endpoint:
            from urllib.parse import urlparse
            parsed = urlparse(self.url)
            self.endpoint = f"{parsed.netloc}{parsed.path}"


@dataclass
class AggregatedMetrics:
    """Aggregated metrics for a time period."""
    
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_response_time_ms: float = 0.0
    min_response_time_ms: float = float('inf')
    max_response_time_ms: float = 0.0
    total_request_size: int = 0
    total_response_size: int = 0
    status_codes: Dict[int, int] = field(default_factory=lambda: defaultdict(int))
    errors: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    @property
    def avg_response_time_ms(self) -> float:
        """Calculate average response time."""
        if self.total_requests == 0:
            return 0.0
        return self.total_response_time_ms / self.total_requests
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "avg_response_time_ms": round(self.avg_response_time_ms, 2),
            "min_response_time_ms": round(self.min_response_time_ms, 2) if self.min_response_time_ms != float('inf') else 0,
            "max_response_time_ms": round(self.max_response_time_ms, 2),
            "total_request_size_bytes": self.total_request_size,
            "total_response_size_bytes": self.total_response_size,
            "success_rate_percent": round(self.success_rate, 2),
            "status_codes": dict(self.status_codes),
            "errors": dict(self.errors)
        }


class MetricsCollector:
    """Collects and aggregates API metrics."""
    
    def __init__(
        self,
        max_history: int = 10000,
        enable_detailed_logging: bool = True
    ):
        """
        Initialize metrics collector.
        
        Args:
            max_history: Maximum number of metrics to keep in history
            enable_detailed_logging: Enable detailed request logging
        """
        self._max_history = max_history
        self._enable_detailed_logging = enable_detailed_logging
        self._metrics: List[RequestMetric] = []
        self._endpoint_metrics: Dict[str, AggregatedMetrics] = defaultdict(AggregatedMetrics)
        self._global_metrics = AggregatedMetrics()
        self._lock = threading.Lock()
        self._callbacks: List[Callable[[RequestMetric], None]] = []
        logger.info(f"Initialized metrics collector with max_history={max_history}")
    
    def record(self, metric: RequestMetric) -> None:
        """
        Record a request metric.
        
        Args:
            metric: RequestMetric to record
        """
        with self._lock:
            # Add to history
            self._metrics.append(metric)
            if len(self._metrics) > self._max_history:
                self._metrics.pop(0)
            
            # Update global metrics
            self._update_aggregated(self._global_metrics, metric)
            
            # Update endpoint metrics
            self._update_aggregated(self._endpoint_metrics[metric.endpoint], metric)
        
        # Log if enabled
        if self._enable_detailed_logging:
            log_level = logging.WARNING if metric.error else logging.INFO
            logger.log(
                log_level,
                f"{metric.method} {metric.url} - {metric.status_code} "
                f"({metric.response_time_ms:.0f}ms)"
            )
        
        # Call callbacks
        for callback in self._callbacks:
            try:
                callback(metric)
            except Exception as e:
                logger.error(f"Metric callback error: {e}")
    
    def _update_aggregated(self, agg: AggregatedMetrics, metric: RequestMetric) -> None:
        """Update aggregated metrics with a new metric."""
        agg.total_requests += 1
        agg.total_response_time_ms += metric.response_time_ms
        agg.min_response_time_ms = min(agg.min_response_time_ms, metric.response_time_ms)
        agg.max_response_time_ms = max(agg.max_response_time_ms, metric.response_time_ms)
        agg.total_request_size += metric.request_size
        agg.total_response_size += metric.response_size
        agg.status_codes[metric.status_code] += 1
        
        if metric.error:
            agg.failed_requests += 1
            agg.errors[metric.error] += 1
        elif metric.status_code < 400:
            agg.successful_requests += 1
        else:
            agg.failed_requests += 1
    
    def get_global_metrics(self) -> Dict[str, Any]:
        """Get global aggregated metrics."""
        with self._lock:
            return self._global_metrics.to_dict()
    
    def get_endpoint_metrics(self, endpoint: Optional[str] = None) -> Dict[str, Any]:
        """
        Get metrics for specific endpoint or all endpoints.
        
        Args:
            endpoint: Specific endpoint or None for all
            
        Returns:
            Dict with endpoint metrics
        """
        with self._lock:
            if endpoint:
                if endpoint in self._endpoint_metrics:
                    return {endpoint: self._endpoint_metrics[endpoint].to_dict()}
                return {}
            return {ep: m.to_dict() for ep, m in self._endpoint_metrics.items()}
    
    def get_recent_metrics(self, count: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent request metrics.
        
        Args:
            count: Number of recent metrics to return
            
        Returns:
            List of metric dictionaries
        """
        with self._lock:
            recent = self._metrics[-count:] if count < len(self._metrics) else self._metrics
            return [
                {
                    "url": m.url,
                    "method": m.method,
                    "status_code": m.status_code,
                    "response_time_ms": m.response_time_ms,
                    "timestamp": m.timestamp,
                    "error": m.error
                }
                for m in recent
            ]
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of errors."""
        with self._lock:
            return {
                "total_errors": self._global_metrics.failed_requests,
                "error_rate_percent": round(
                    100 - self._global_metrics.success_rate, 2
                ) if self._global_metrics.total_requests > 0 else 0,
                "error_types": dict(self._global_metrics.errors),
                "error_status_codes": {
                    k: v for k, v in self._global_metrics.status_codes.items()
                    if k >= 400
                }
            }
    
    def add_callback(self, callback: Callable[[RequestMetric], None]) -> None:
        """
        Add a callback to be called for each metric.
        
        Args:
            callback: Function that receives RequestMetric
        """
        self._callbacks.append(callback)
    
    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._metrics = []
            self._endpoint_metrics = defaultdict(AggregatedMetrics)
            self._global_metrics = AggregatedMetrics()
        logger.info("Metrics reset")


class PerformanceTimer:
    """Context manager for timing operations."""
    
    def __init__(self):
        """Initialize timer."""
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
    
    def __enter__(self):
        """Start timing."""
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timing."""
        self.end_time = time.perf_counter()
    
    @property
    def elapsed_ms(self) -> float:
        """Get elapsed time in milliseconds."""
        if self.start_time is None:
            return 0.0
        end = self.end_time if self.end_time else time.perf_counter()
        return (end - self.start_time) * 1000


class StructuredLogger:
    """Structured logging for API operations."""
    
    def __init__(
        self,
        name: str = "api_context_memory",
        level: int = logging.INFO,
        include_timestamp: bool = True,
        include_context: bool = True
    ):
        """
        Initialize structured logger.
        
        Args:
            name: Logger name
            level: Logging level
            include_timestamp: Include ISO timestamp in logs
            include_context: Include context data in logs
        """
        self._logger = logging.getLogger(name)
        self._logger.setLevel(level)
        self._include_timestamp = include_timestamp
        self._include_context = include_context
        self._context: Dict[str, Any] = {}
    
    def set_context(self, **kwargs) -> None:
        """Set context data to include in all logs."""
        self._context.update(kwargs)
    
    def clear_context(self) -> None:
        """Clear context data."""
        self._context = {}
    
    def _format_message(self, message: str, **kwargs) -> str:
        """Format message with context and kwargs."""
        data = {}
        
        if self._include_timestamp:
            data["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        if self._include_context:
            data.update(self._context)
        
        data.update(kwargs)
        data["message"] = message
        
        # Format as structured log
        parts = [f"{k}={v}" for k, v in data.items()]
        return " | ".join(parts)
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        self._logger.debug(self._format_message(message, **kwargs))
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        self._logger.info(self._format_message(message, **kwargs))
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        self._logger.warning(self._format_message(message, **kwargs))
    
    def error(self, message: str, **kwargs) -> None:
        """Log error message."""
        self._logger.error(self._format_message(message, **kwargs))
    
    def request(
        self,
        method: str,
        url: str,
        status_code: int,
        response_time_ms: float,
        **kwargs
    ) -> None:
        """Log a request with standard fields."""
        level = logging.WARNING if status_code >= 400 else logging.INFO
        self._logger.log(
            level,
            self._format_message(
                "HTTP Request",
                method=method,
                url=url,
                status_code=status_code,
                response_time_ms=round(response_time_ms, 2),
                **kwargs
            )
        )


# Global metrics collector instance
_global_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create global metrics collector."""
    global _global_metrics_collector
    if _global_metrics_collector is None:
        _global_metrics_collector = MetricsCollector()
    return _global_metrics_collector


def reset_metrics_collector() -> None:
    """Reset global metrics collector."""
    global _global_metrics_collector
    if _global_metrics_collector:
        _global_metrics_collector.reset()
