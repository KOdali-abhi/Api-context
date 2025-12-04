"""
API Context Memory System - A streamlined library for managing API interactions

This library provides an intuitive interface for recording, analyzing, and maintaining
context across API interactions.

Features:
- Multiple storage backends (memory, file, Redis)
- Authentication middleware (Bearer, API Key, Basic, OAuth2)
- Rate limiting (Token bucket, Sliding window)
- Async support with aiohttp
- Comprehensive metrics and logging
"""

from .api_context_memory import (
    APIContextMemory,
    APIClient,
    Session,
    Storage,
    Tab
)

# Storage backends
from .storage_backends import (
    StorageBackend,
    MemoryStorage,
    FileStorage,
    RedisStorage,
    create_storage
)

# Authentication
from .auth_middleware import (
    AuthMiddleware,
    BearerTokenAuth,
    APIKeyAuth,
    BasicAuth,
    CustomHeaderAuth,
    OAuth2Auth,
    ChainedAuth
)

# Rate limiting
from .rate_limiter import (
    RateLimiter,
    TokenBucketRateLimiter,
    SlidingWindowRateLimiter,
    EndpointRateLimiter,
    RetryHandler
)

# Metrics
from .metrics import (
    MetricsCollector,
    RequestMetric,
    AggregatedMetrics,
    PerformanceTimer,
    StructuredLogger,
    get_metrics_collector,
    reset_metrics_collector
)

__version__ = "0.3.0"

__all__ = [
    # Core
    "APIContextMemory",
    "APIClient",
    "Session",
    "Storage",
    "Tab",
    # Storage backends
    "StorageBackend",
    "MemoryStorage",
    "FileStorage",
    "RedisStorage",
    "create_storage",
    # Authentication
    "AuthMiddleware",
    "BearerTokenAuth",
    "APIKeyAuth",
    "BasicAuth",
    "CustomHeaderAuth",
    "OAuth2Auth",
    "ChainedAuth",
    # Rate limiting
    "RateLimiter",
    "TokenBucketRateLimiter",
    "SlidingWindowRateLimiter",
    "EndpointRateLimiter",
    "RetryHandler",
    # Metrics
    "MetricsCollector",
    "RequestMetric",
    "AggregatedMetrics",
    "PerformanceTimer",
    "StructuredLogger",
    "get_metrics_collector",
    "reset_metrics_collector",
]
