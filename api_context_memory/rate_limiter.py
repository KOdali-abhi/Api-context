"""
Rate limiting for API Context Memory System.

This module provides rate limiting functionality:
- Token bucket algorithm
- Sliding window rate limiting
- Per-endpoint rate limiting
- Configurable retry behavior
"""

import logging
import threading
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger("api_context_memory.rate_limiter")


class RateLimiter(ABC):
    """Abstract base class for rate limiters."""
    
    @abstractmethod
    def acquire(self, key: str = "default") -> Tuple[bool, float]:
        """
        Try to acquire permission to make a request.
        
        Args:
            key: Rate limit key (e.g., endpoint or API name)
            
        Returns:
            Tuple[bool, float]: (allowed, wait_time_seconds)
        """
        pass
    
    @abstractmethod
    def reset(self, key: str = "default"):
        """Reset the rate limiter for a key."""
        pass
    
    @abstractmethod
    def get_remaining(self, key: str = "default") -> int:
        """Get remaining requests allowed."""
        pass


class TokenBucketRateLimiter(RateLimiter):
    """Token bucket rate limiter implementation."""
    
    def __init__(
        self,
        rate: float = 10.0,
        capacity: int = 10,
        per_key: bool = False
    ):
        """
        Initialize token bucket rate limiter.
        
        Args:
            rate: Tokens added per second
            capacity: Maximum tokens in bucket
            per_key: Whether to maintain separate buckets per key
        """
        self._rate = rate
        self._capacity = capacity
        self._per_key = per_key
        self._buckets: Dict[str, Dict] = defaultdict(
            lambda: {"tokens": capacity, "last_update": time.time()}
        )
        self._lock = threading.Lock()
        logger.info(f"Initialized token bucket rate limiter: rate={rate}/s, capacity={capacity}")
    
    def _refill(self, bucket: Dict) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - bucket["last_update"]
        bucket["tokens"] = min(
            self._capacity,
            bucket["tokens"] + elapsed * self._rate
        )
        bucket["last_update"] = now
    
    def acquire(self, key: str = "default") -> Tuple[bool, float]:
        """Try to acquire a token."""
        bucket_key = key if self._per_key else "default"
        
        with self._lock:
            bucket = self._buckets[bucket_key]
            self._refill(bucket)
            
            if bucket["tokens"] >= 1:
                bucket["tokens"] -= 1
                logger.debug(f"Rate limit acquired for {key}, remaining: {bucket['tokens']:.1f}")
                return True, 0.0
            else:
                wait_time = (1 - bucket["tokens"]) / self._rate
                logger.debug(f"Rate limit exceeded for {key}, wait: {wait_time:.2f}s")
                return False, wait_time
    
    def reset(self, key: str = "default"):
        """Reset the bucket for a key."""
        bucket_key = key if self._per_key else "default"
        with self._lock:
            self._buckets[bucket_key] = {
                "tokens": self._capacity,
                "last_update": time.time()
            }
    
    def get_remaining(self, key: str = "default") -> int:
        """Get remaining tokens."""
        bucket_key = key if self._per_key else "default"
        with self._lock:
            bucket = self._buckets[bucket_key]
            self._refill(bucket)
            return int(bucket["tokens"])


class SlidingWindowRateLimiter(RateLimiter):
    """Sliding window rate limiter implementation."""
    
    def __init__(
        self,
        max_requests: int = 100,
        window_seconds: float = 60.0,
        per_key: bool = False
    ):
        """
        Initialize sliding window rate limiter.
        
        Args:
            max_requests: Maximum requests per window
            window_seconds: Window size in seconds
            per_key: Whether to maintain separate windows per key
        """
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._per_key = per_key
        self._requests: Dict[str, list] = defaultdict(list)
        self._lock = threading.Lock()
        logger.info(
            f"Initialized sliding window rate limiter: "
            f"{max_requests} requests per {window_seconds}s"
        )
    
    def _clean_old_requests(self, key: str) -> None:
        """Remove requests outside the window."""
        cutoff = time.time() - self._window_seconds
        self._requests[key] = [t for t in self._requests[key] if t > cutoff]
    
    def acquire(self, key: str = "default") -> Tuple[bool, float]:
        """Try to acquire permission for a request."""
        request_key = key if self._per_key else "default"
        
        with self._lock:
            self._clean_old_requests(request_key)
            
            if len(self._requests[request_key]) < self._max_requests:
                self._requests[request_key].append(time.time())
                remaining = self._max_requests - len(self._requests[request_key])
                logger.debug(f"Rate limit acquired for {key}, remaining: {remaining}")
                return True, 0.0
            else:
                # Calculate wait time until oldest request expires
                oldest = self._requests[request_key][0]
                wait_time = oldest + self._window_seconds - time.time()
                logger.debug(f"Rate limit exceeded for {key}, wait: {wait_time:.2f}s")
                return False, max(0, wait_time)
    
    def reset(self, key: str = "default"):
        """Reset the window for a key."""
        request_key = key if self._per_key else "default"
        with self._lock:
            self._requests[request_key] = []
    
    def get_remaining(self, key: str = "default") -> int:
        """Get remaining requests in window."""
        request_key = key if self._per_key else "default"
        with self._lock:
            self._clean_old_requests(request_key)
            return self._max_requests - len(self._requests[request_key])


class EndpointRateLimiter(RateLimiter):
    """Rate limiter with per-endpoint configuration."""
    
    def __init__(
        self,
        default_rate: float = 10.0,
        default_capacity: int = 10,
        endpoint_configs: Optional[Dict[str, Dict]] = None
    ):
        """
        Initialize endpoint rate limiter.
        
        Args:
            default_rate: Default tokens per second
            default_capacity: Default bucket capacity
            endpoint_configs: Per-endpoint configurations
                Example: {"api.example.com/v1": {"rate": 5, "capacity": 5}}
        """
        self._default_rate = default_rate
        self._default_capacity = default_capacity
        self._endpoint_configs = endpoint_configs or {}
        self._limiters: Dict[str, TokenBucketRateLimiter] = {}
        self._lock = threading.Lock()
        logger.info(
            f"Initialized endpoint rate limiter with {len(self._endpoint_configs)} custom configs"
        )
    
    def _get_limiter(self, endpoint: str) -> TokenBucketRateLimiter:
        """Get or create a rate limiter for an endpoint."""
        with self._lock:
            if endpoint not in self._limiters:
                config = self._endpoint_configs.get(endpoint, {})
                rate = config.get("rate", self._default_rate)
                capacity = config.get("capacity", self._default_capacity)
                self._limiters[endpoint] = TokenBucketRateLimiter(
                    rate=rate,
                    capacity=capacity,
                    per_key=False
                )
            return self._limiters[endpoint]
    
    def _extract_endpoint(self, url: str) -> str:
        """Extract endpoint identifier from URL."""
        parsed = urlparse(url)
        return f"{parsed.netloc}{parsed.path}"
    
    def acquire(self, key: str = "default") -> Tuple[bool, float]:
        """Try to acquire permission for an endpoint."""
        endpoint = self._extract_endpoint(key) if "://" in key else key
        limiter = self._get_limiter(endpoint)
        return limiter.acquire()
    
    def reset(self, key: str = "default"):
        """Reset the limiter for an endpoint."""
        endpoint = self._extract_endpoint(key) if "://" in key else key
        if endpoint in self._limiters:
            self._limiters[endpoint].reset()
    
    def get_remaining(self, key: str = "default") -> int:
        """Get remaining requests for an endpoint."""
        endpoint = self._extract_endpoint(key) if "://" in key else key
        limiter = self._get_limiter(endpoint)
        return limiter.get_remaining()
    
    def add_endpoint_config(self, endpoint: str, rate: float, capacity: int):
        """Add configuration for a specific endpoint."""
        self._endpoint_configs[endpoint] = {"rate": rate, "capacity": capacity}
        with self._lock:
            if endpoint in self._limiters:
                del self._limiters[endpoint]


class RetryHandler:
    """Handler for rate limit retries with exponential backoff."""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0
    ):
        """
        Initialize retry handler.
        
        Args:
            max_retries: Maximum number of retries
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential backoff
        """
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._max_delay = max_delay
        self._exponential_base = exponential_base
        logger.info(
            f"Initialized retry handler: max_retries={max_retries}, "
            f"base_delay={base_delay}s, max_delay={max_delay}s"
        )
    
    def get_delay(self, attempt: int, rate_limit_wait: float = 0.0) -> float:
        """
        Get delay for a retry attempt.
        
        Args:
            attempt: Current attempt number (0-indexed)
            rate_limit_wait: Wait time suggested by rate limiter
            
        Returns:
            float: Delay in seconds
        """
        if rate_limit_wait > 0:
            return min(rate_limit_wait, self._max_delay)
        
        delay = self._base_delay * (self._exponential_base ** attempt)
        return min(delay, self._max_delay)
    
    def should_retry(self, attempt: int) -> bool:
        """Check if should retry after an attempt."""
        return attempt < self._max_retries
    
    def wait(self, attempt: int, rate_limit_wait: float = 0.0) -> None:
        """Wait before next retry."""
        delay = self.get_delay(attempt, rate_limit_wait)
        logger.info(f"Waiting {delay:.2f}s before retry {attempt + 1}")
        time.sleep(delay)
