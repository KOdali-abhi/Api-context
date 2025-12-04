"""
Async support for API Context Memory System.

This module provides async HTTP client functionality using aiohttp:
- Async API client
- Concurrent request handling
- Async context manager support
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("api_context_memory.async_client")


class AsyncAPIClient:
    """Async API client with context recording."""
    
    def __init__(
        self,
        api_memory: 'APIContextMemory',
        auth_middleware: Optional['AuthMiddleware'] = None,
        rate_limiter: Optional['RateLimiter'] = None,
        timeout: float = 30.0
    ):
        """
        Initialize async API client.
        
        Args:
            api_memory: APIContextMemory instance
            auth_middleware: Optional authentication middleware
            rate_limiter: Optional rate limiter
            timeout: Request timeout in seconds
        """
        self._api_memory = api_memory
        self._auth_middleware = auth_middleware
        self._rate_limiter = rate_limiter
        self._timeout = timeout
        # aiohttp.ClientSession instance, created lazily via _ensure_session()
        # and cleaned up via close() or __aexit__
        self._session = None
        logger.info("Initialized async API client")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def _ensure_session(self):
        """Ensure aiohttp session exists."""
        if self._session is None:
            try:
                import aiohttp
                timeout = aiohttp.ClientTimeout(total=self._timeout)
                self._session = aiohttp.ClientSession(timeout=timeout)
            except ImportError:
                raise ImportError(
                    "aiohttp is required for async support. "
                    "Install it with: pip install aiohttp"
                )
    
    async def close(self):
        """Close the aiohttp session."""
        if self._session:
            await self._session.close()
            self._session = None
    
    def _apply_auth(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Apply authentication middleware if configured."""
        if self._auth_middleware:
            return self._auth_middleware.apply(headers)
        return headers
    
    async def _check_rate_limit(self, url: str) -> None:
        """Check rate limit and wait if necessary."""
        if self._rate_limiter:
            allowed, wait_time = self._rate_limiter.acquire(url)
            if not allowed:
                logger.info(f"Rate limited, waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
                # Try again after waiting
                allowed, wait_time = self._rate_limiter.acquire(url)
                if not allowed:
                    raise Exception(f"Rate limit exceeded for {url}")
    
    async def request(
        self,
        session_id: str,
        method: str,
        url: str,
        **kwargs
    ) -> 'aiohttp.ClientResponse':
        """
        Make an async API request and record the interaction.
        
        Args:
            session_id: Session identifier
            method: HTTP method
            url: URL to request
            **kwargs: Additional request arguments
            
        Returns:
            aiohttp.ClientResponse: Response object
        """
        await self._ensure_session()
        
        # Check rate limit
        await self._check_rate_limit(url)
        
        # Prepare headers with auth
        headers = kwargs.pop("headers", {})
        headers = self._apply_auth(headers)
        
        # Prepare request data for recording
        request_data = {
            "method": method,
            "url": url,
            "headers": {k: v for k, v in headers.items() if k.lower() != "authorization"},
            "params": kwargs.get("params", {}),
            "data": str(kwargs.get("data", "")),
            "json": kwargs.get("json", {})
        }
        
        try:
            async with self._session.request(
                method, url, headers=headers, **kwargs
            ) as response:
                # Read response body
                text = await response.text()
                
                # Prepare response data for recording
                response_data = {
                    "status_code": response.status,
                    "headers": dict(response.headers),
                    "content_type": response.headers.get("Content-Type", ""),
                    "content_length": len(text),
                    "text": text
                }
                
                # Record the interaction
                self._api_memory.record_interaction(session_id, request_data, response_data)
                
                return response
                
        except Exception as e:
            # Record the error
            error_data = {
                "error": str(e),
                "error_type": type(e).__name__
            }
            self._api_memory.record_interaction(session_id, request_data, error_data)
            logger.error(f"Async request failed: {str(e)}")
            raise
    
    async def get(self, session_id: str, url: str, **kwargs) -> 'aiohttp.ClientResponse':
        """Make an async GET request."""
        return await self.request(session_id, "GET", url, **kwargs)
    
    async def post(self, session_id: str, url: str, **kwargs) -> 'aiohttp.ClientResponse':
        """Make an async POST request."""
        return await self.request(session_id, "POST", url, **kwargs)
    
    async def put(self, session_id: str, url: str, **kwargs) -> 'aiohttp.ClientResponse':
        """Make an async PUT request."""
        return await self.request(session_id, "PUT", url, **kwargs)
    
    async def delete(self, session_id: str, url: str, **kwargs) -> 'aiohttp.ClientResponse':
        """Make an async DELETE request."""
        return await self.request(session_id, "DELETE", url, **kwargs)
    
    async def patch(self, session_id: str, url: str, **kwargs) -> 'aiohttp.ClientResponse':
        """Make an async PATCH request."""
        return await self.request(session_id, "PATCH", url, **kwargs)
    
    async def batch_requests(
        self,
        session_id: str,
        requests: List[Dict[str, Any]],
        max_concurrent: int = 10
    ) -> List[Tuple[Dict[str, Any], Any]]:
        """
        Execute multiple requests concurrently.
        
        Args:
            session_id: Session identifier
            requests: List of request dicts with keys: method, url, and optional kwargs
            max_concurrent: Maximum concurrent requests
            
        Returns:
            List of (request_dict, response or exception) tuples
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def limited_request(req: Dict[str, Any]):
            async with semaphore:
                try:
                    method = req.get("method", "GET")
                    url = req["url"]
                    kwargs = {k: v for k, v in req.items() if k not in ("method", "url")}
                    response = await self.request(session_id, method, url, **kwargs)
                    return req, response
                except Exception as e:
                    return req, e
        
        tasks = [limited_request(req) for req in requests]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        
        logger.info(f"Completed batch of {len(requests)} requests")
        return results


class AsyncContextManager:
    """Context manager for async API operations."""
    
    def __init__(self, api_memory: 'APIContextMemory'):
        """
        Initialize async context manager.
        
        Args:
            api_memory: APIContextMemory instance
        """
        self._api_memory = api_memory
        self._client = None
    
    async def __aenter__(self) -> AsyncAPIClient:
        """Enter async context."""
        self._client = self._api_memory.create_async_client()
        await self._client._ensure_session()
        return self._client
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        if self._client:
            await self._client.close()


async def run_async_requests(
    api_memory: 'APIContextMemory',
    session_id: str,
    requests: List[Dict[str, Any]],
    auth_middleware: Optional['AuthMiddleware'] = None,
    rate_limiter: Optional['RateLimiter'] = None,
    max_concurrent: int = 10
) -> List[Tuple[Dict[str, Any], Any]]:
    """
    Convenience function to run multiple async requests.
    
    Args:
        api_memory: APIContextMemory instance
        session_id: Session identifier
        requests: List of request dicts
        auth_middleware: Optional auth middleware
        rate_limiter: Optional rate limiter
        max_concurrent: Maximum concurrent requests
        
    Returns:
        List of (request_dict, response or exception) tuples
    """
    async with AsyncAPIClient(
        api_memory,
        auth_middleware=auth_middleware,
        rate_limiter=rate_limiter
    ) as client:
        return await client.batch_requests(session_id, requests, max_concurrent)
