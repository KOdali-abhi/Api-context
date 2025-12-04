"""
Tests for new production-ready features in API Context Memory System.

This module tests:
- Storage backends
- Authentication middleware
- Rate limiting
- Metrics collection
"""

import time
import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from api_context_memory import (
    APIContextMemory,
    # Storage backends
    MemoryStorage,
    FileStorage,
    create_storage,
    # Authentication
    BearerTokenAuth,
    APIKeyAuth,
    BasicAuth,
    CustomHeaderAuth,
    ChainedAuth,
    # Rate limiting
    TokenBucketRateLimiter,
    SlidingWindowRateLimiter,
    EndpointRateLimiter,
    RetryHandler,
    # Metrics
    MetricsCollector,
    RequestMetric,
    PerformanceTimer,
    StructuredLogger,
)


class TestStorageBackends(unittest.TestCase):
    """Test storage backend implementations."""
    
    def test_memory_storage(self):
        """Test memory storage backend."""
        storage = MemoryStorage()
        
        # Test store and retrieve
        storage.store("key1", {"value": "test"})
        result = storage.retrieve("key1")
        self.assertEqual(result["value"], "test")
        
        # Test update
        storage.update("key1", {"new_value": "updated"})
        result = storage.retrieve("key1")
        self.assertIn("new_value", result)
        
        # Test delete
        self.assertTrue(storage.delete("key1"))
        self.assertIsNone(storage.retrieve("key1"))
        
        # Test list_keys
        storage.store("prefix:key1", {"a": 1})
        storage.store("prefix:key2", {"b": 2})
        storage.store("other:key", {"c": 3})
        
        all_keys = storage.list_keys()
        self.assertEqual(len(all_keys), 3)
        
        prefix_keys = storage.list_keys("prefix:*")
        self.assertEqual(len(prefix_keys), 2)
        
        # Test exists
        self.assertTrue(storage.exists("prefix:key1"))
        self.assertFalse(storage.exists("nonexistent"))
        
        # Test clear
        storage.clear()
        self.assertEqual(len(storage.list_keys()), 0)
    
    def test_file_storage(self):
        """Test file storage backend."""
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test_storage.json")
            storage = FileStorage(file_path)
            
            # Test store and retrieve
            storage.store("key1", {"value": "test"})
            result = storage.retrieve("key1")
            self.assertEqual(result["value"], "test")
            
            # Verify file exists
            self.assertTrue(os.path.exists(file_path))
            
            # Test persistence by creating new instance
            storage2 = FileStorage(file_path)
            result = storage2.retrieve("key1")
            self.assertEqual(result["value"], "test")
    
    def test_create_storage_factory(self):
        """Test storage factory function."""
        # Memory storage
        storage = create_storage("memory")
        self.assertIsInstance(storage, MemoryStorage)
        
        # File storage
        import tempfile
        import os
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test.json")
            storage = create_storage("file", file_path=file_path)
            self.assertIsInstance(storage, FileStorage)
        
        # Invalid storage type
        with self.assertRaises(ValueError):
            create_storage("invalid")


class TestAuthMiddleware(unittest.TestCase):
    """Test authentication middleware implementations."""
    
    def test_bearer_token_auth(self):
        """Test bearer token authentication."""
        auth = BearerTokenAuth("my-token")
        
        headers = auth.apply({})
        self.assertEqual(headers["Authorization"], "Bearer my-token")
        self.assertTrue(auth.is_valid)
        
        # Test token update
        auth.token = "new-token"
        headers = auth.apply({})
        self.assertEqual(headers["Authorization"], "Bearer new-token")
    
    def test_api_key_auth(self):
        """Test API key authentication."""
        auth = APIKeyAuth("my-api-key", header_name="X-API-Key")
        
        headers = auth.apply({})
        self.assertEqual(headers["X-API-Key"], "my-api-key")
        self.assertTrue(auth.is_valid)
        
        # Test with prefix
        auth_with_prefix = APIKeyAuth("my-key", key_prefix="Bearer ")
        headers = auth_with_prefix.apply({})
        self.assertEqual(headers["X-API-Key"], "Bearer my-key")
    
    def test_basic_auth(self):
        """Test basic authentication."""
        auth = BasicAuth("username", "password")
        
        headers = auth.apply({})
        self.assertIn("Authorization", headers)
        self.assertTrue(headers["Authorization"].startswith("Basic "))
        self.assertTrue(auth.is_valid)
    
    def test_custom_header_auth(self):
        """Test custom header authentication."""
        custom_headers = {
            "X-Custom-Header": "value1",
            "X-Another-Header": "value2"
        }
        auth = CustomHeaderAuth(custom_headers)
        
        headers = auth.apply({"Existing": "header"})
        self.assertEqual(headers["X-Custom-Header"], "value1")
        self.assertEqual(headers["X-Another-Header"], "value2")
        self.assertEqual(headers["Existing"], "header")
        self.assertTrue(auth.is_valid)
    
    def test_chained_auth(self):
        """Test chained authentication."""
        auth1 = APIKeyAuth("api-key", header_name="X-API-Key")
        auth2 = CustomHeaderAuth({"X-Custom": "value"})
        
        chained = ChainedAuth(auth1, auth2)
        
        headers = chained.apply({})
        self.assertEqual(headers["X-API-Key"], "api-key")
        self.assertEqual(headers["X-Custom"], "value")
        self.assertTrue(chained.is_valid)


class TestRateLimiter(unittest.TestCase):
    """Test rate limiter implementations."""
    
    def test_token_bucket_rate_limiter(self):
        """Test token bucket rate limiter."""
        limiter = TokenBucketRateLimiter(rate=10.0, capacity=5)
        
        # Should allow first 5 requests
        for i in range(5):
            allowed, wait = limiter.acquire()
            self.assertTrue(allowed, f"Request {i+1} should be allowed")
            self.assertEqual(wait, 0.0)
        
        # 6th request should be rate limited
        allowed, wait = limiter.acquire()
        self.assertFalse(allowed)
        self.assertGreater(wait, 0)
        
        # Test reset
        limiter.reset()
        self.assertEqual(limiter.get_remaining(), 5)
    
    def test_sliding_window_rate_limiter(self):
        """Test sliding window rate limiter."""
        limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=1.0)
        
        # Should allow first 3 requests
        for i in range(3):
            allowed, wait = limiter.acquire()
            self.assertTrue(allowed)
        
        # 4th request should be rate limited
        allowed, wait = limiter.acquire()
        self.assertFalse(allowed)
        
        # Wait for window to slide
        time.sleep(1.1)
        
        # Should allow requests again
        allowed, wait = limiter.acquire()
        self.assertTrue(allowed)
    
    def test_endpoint_rate_limiter(self):
        """Test endpoint-specific rate limiter."""
        endpoint_configs = {
            "api.example.com/v1/slow": {"rate": 1, "capacity": 1}
        }
        limiter = EndpointRateLimiter(
            default_rate=10,
            default_capacity=5,
            endpoint_configs=endpoint_configs
        )
        
        # Default endpoint should allow more requests
        for _ in range(5):
            allowed, _ = limiter.acquire("https://api.example.com/v1/fast")
            self.assertTrue(allowed)
        
        # Slow endpoint has stricter limits
        allowed, _ = limiter.acquire("https://api.example.com/v1/slow")
        self.assertTrue(allowed)
        
        allowed, _ = limiter.acquire("https://api.example.com/v1/slow")
        self.assertFalse(allowed)
    
    def test_retry_handler(self):
        """Test retry handler."""
        handler = RetryHandler(max_retries=3, base_delay=0.1)
        
        # Should allow retries
        self.assertTrue(handler.should_retry(0))
        self.assertTrue(handler.should_retry(1))
        self.assertTrue(handler.should_retry(2))
        self.assertFalse(handler.should_retry(3))
        
        # Test exponential backoff
        delay0 = handler.get_delay(0)
        delay1 = handler.get_delay(1)
        delay2 = handler.get_delay(2)
        
        self.assertLess(delay0, delay1)
        self.assertLess(delay1, delay2)


class TestMetrics(unittest.TestCase):
    """Test metrics collection."""
    
    def test_metrics_collector(self):
        """Test metrics collector."""
        collector = MetricsCollector(max_history=100)
        
        # Record some metrics
        for i in range(5):
            metric = RequestMetric(
                url="https://api.example.com/test",
                method="GET",
                status_code=200 if i < 4 else 500,
                response_time_ms=100.0 + i * 10,
                request_size=100,
                response_size=500,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            collector.record(metric)
        
        # Check global metrics
        global_metrics = collector.get_global_metrics()
        self.assertEqual(global_metrics["total_requests"], 5)
        self.assertEqual(global_metrics["successful_requests"], 4)
        self.assertEqual(global_metrics["failed_requests"], 1)
        
        # Check endpoint metrics
        endpoint_metrics = collector.get_endpoint_metrics()
        self.assertIn("api.example.com/test", endpoint_metrics)
        
        # Check error summary
        error_summary = collector.get_error_summary()
        self.assertEqual(error_summary["total_errors"], 1)
        
        # Test reset
        collector.reset()
        global_metrics = collector.get_global_metrics()
        self.assertEqual(global_metrics["total_requests"], 0)
    
    def test_performance_timer(self):
        """Test performance timer."""
        with PerformanceTimer() as timer:
            time.sleep(0.1)
        
        # Should be at least 100ms
        self.assertGreater(timer.elapsed_ms, 90)
        self.assertLess(timer.elapsed_ms, 200)
    
    def test_structured_logger(self):
        """Test structured logger."""
        logger = StructuredLogger(
            name="test_logger",
            include_timestamp=True,
            include_context=True
        )
        
        # Set context
        logger.set_context(session_id="test-session")
        
        # These should not raise
        logger.debug("Debug message", extra_field="value")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.request("GET", "https://example.com", 200, 100.0)
        
        # Clear context
        logger.clear_context()


class TestAPIContextMemoryIntegration(unittest.TestCase):
    """Integration tests for APIContextMemory with new features."""
    
    def test_init_with_auth_and_rate_limiting(self):
        """Test initialization with auth and rate limiting."""
        auth = BearerTokenAuth("test-token")
        limiter = TokenBucketRateLimiter(rate=10, capacity=10)
        
        api_memory = APIContextMemory(
            auth_middleware=auth,
            rate_limiter=limiter,
            enable_metrics=True
        )
        
        self.assertIsNotNone(api_memory.auth_middleware)
        self.assertIsNotNone(api_memory.rate_limiter)
        self.assertIsNotNone(api_memory.metrics)
    
    def test_create_client_with_features(self):
        """Test creating client with features."""
        auth = APIKeyAuth("test-key")
        limiter = SlidingWindowRateLimiter(max_requests=100, window_seconds=60)
        
        api_memory = APIContextMemory(
            auth_middleware=auth,
            rate_limiter=limiter
        )
        
        client = api_memory.create_client()
        
        # Client should have auth and rate limiter
        self.assertIsNotNone(client._auth_middleware)
        self.assertIsNotNone(client._rate_limiter)
    
    def test_get_metrics(self):
        """Test getting metrics from APIContextMemory."""
        api_memory = APIContextMemory(enable_metrics=True)
        
        # Record a manual interaction
        tab = api_memory.create_tab()
        api_memory.record_interaction(
            tab["session_id"],
            {"method": "GET", "url": "https://example.com"},
            {"status_code": 200}
        )
        
        # Get metrics
        metrics = api_memory.get_metrics()
        self.assertIn("global", metrics)
        self.assertIn("endpoints", metrics)
        self.assertIn("errors", metrics)
    
    def test_backward_compatibility(self):
        """Test backward compatibility with existing code."""
        # Old-style initialization should still work
        api_memory = APIContextMemory()
        
        # Create tab
        tab = api_memory.create_tab(metadata={"name": "Test"})
        self.assertIn("tab_id", tab)
        self.assertIn("session_id", tab)
        
        # Session operations
        session = api_memory.get_session(tab["session_id"])
        session.set("key", "value")
        api_memory.save_session(session)
        
        session = api_memory.get_session(tab["session_id"])
        self.assertEqual(session.get("key"), "value")
        
        # Client creation
        client = api_memory.create_client()
        self.assertIsNotNone(client)


if __name__ == "__main__":
    unittest.main()
