"""
API Context Memory System - A streamlined library for managing API interactions

This library provides an intuitive interface for recording, analyzing, and maintaining
context across API interactions. It addresses common challenges when working with
multiple APIs by providing a simple memory layer that helps maintain context,
debug issues, and optimize API usage patterns.

Features:
- Multiple storage backends (memory, file, Redis)
- Authentication middleware (Bearer, API Key, Basic, OAuth2)
- Rate limiting (Token bucket, Sliding window)
- Async support with aiohttp
- Comprehensive metrics and logging
"""

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union, TYPE_CHECKING

import requests

# Import new modules
from .storage_backends import StorageBackend, MemoryStorage, FileStorage, RedisStorage, create_storage
from .auth_middleware import (
    AuthMiddleware, BearerTokenAuth, APIKeyAuth, BasicAuth,
    CustomHeaderAuth, OAuth2Auth, ChainedAuth
)
from .rate_limiter import (
    RateLimiter, TokenBucketRateLimiter, SlidingWindowRateLimiter,
    EndpointRateLimiter, RetryHandler
)
from .metrics import (
    MetricsCollector, RequestMetric, PerformanceTimer,
    StructuredLogger, get_metrics_collector
)

if TYPE_CHECKING:
    from .async_client import AsyncAPIClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("api_context_memory")


class Storage:
    """
    Storage wrapper for API context data.
    
    This class provides backward compatibility while using the new storage backends.
    For new code, consider using the storage backends directly.
    """
    
    def __init__(
        self,
        storage_type: str = "memory",
        file_path: Optional[str] = None,
        redis_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize storage.
        
        Args:
            storage_type: Type of storage ("memory", "file", or "redis")
            file_path: Path to file storage (required if storage_type is "file")
            redis_config: Redis configuration (required if storage_type is "redis")
        """
        self.storage_type = storage_type
        self.file_path = file_path
        self._backend = create_storage(storage_type, file_path, redis_config)
        
        # For backward compatibility, expose data dict for memory storage
        if storage_type == "memory":
            self.data = self._backend.data
        else:
            self.data = {}
    
    def store(self, key: str, value: Dict[str, Any]) -> bool:
        """
        Store data with the given key.
        
        Args:
            key: Storage key
            value: Data to store
            
        Returns:
            bool: True if successful
        """
        return self._backend.store(key, value)
    
    def retrieve(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve data for the given key.
        
        Args:
            key: Storage key
            
        Returns:
            Optional[Dict[str, Any]]: Retrieved data or None if not found
        """
        return self._backend.retrieve(key)
    
    def update(self, key: str, value: Dict[str, Any]) -> bool:
        """
        Update data for the given key.
        
        Args:
            key: Storage key
            value: Data to update
            
        Returns:
            bool: True if successful
        """
        return self._backend.update(key, value)
    
    def delete(self, key: str) -> bool:
        """
        Delete data for the given key.
        
        Args:
            key: Storage key
            
        Returns:
            bool: True if successful, False if key not found
        """
        return self._backend.delete(key)
    
    def list_keys(self) -> List[str]:
        """
        List all keys in storage.
        
        Returns:
            List[str]: List of keys
        """
        return self._backend.list_keys()


class Session:
    """Represents an API session with state."""
    
    def __init__(self, session_id: str, data: Optional[Dict[str, Any]] = None):
        """
        Initialize a session.
        
        Args:
            session_id: Unique session identifier
            data: Initial session data
        """
        self.session_id = session_id
        self.data = data or {}
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.updated_at = self.created_at
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a value from the session data.
        
        Args:
            key: Data key
            default: Default value if key not found
            
        Returns:
            Any: Value for the key or default if not found
        """
        return self.data.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a value in the session data.
        
        Args:
            key: Data key
            value: Value to set
        """
        self.data[key] = value
        self.updated_at = datetime.now(timezone.utc).isoformat()
    
    def delete(self, key: str) -> bool:
        """
        Delete a value from the session data.
        
        Args:
            key: Data key
            
        Returns:
            bool: True if key was found and deleted, False otherwise
        """
        if key in self.data:
            del self.data[key]
            self.updated_at = datetime.now(timezone.utc).isoformat()
            return True
        return False
    
    def clear(self) -> None:
        """Clear all session data."""
        self.data = {}
        self.updated_at = datetime.now(timezone.utc).isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert session to dictionary.
        
        Returns:
            Dict[str, Any]: Session as dictionary
        """
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "data": self.data
        }


class Tab:
    """Represents a context tab for organizing API interactions."""
    
    def __init__(self, tab_id: str, session_id: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize a tab.
        
        Args:
            tab_id: Unique tab identifier
            session_id: Associated session identifier
            metadata: Tab metadata
        """
        self.tab_id = tab_id
        self.session_id = session_id
        self.metadata = metadata or {}
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.updated_at = self.created_at
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert tab to dictionary.
        
        Returns:
            Dict[str, Any]: Tab as dictionary
        """
        return {
            "tab_id": self.tab_id,
            "session_id": self.session_id,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


class APIContextMemory:
    """
    Main class for the API Context Memory System.
    
    Features:
    - Multiple storage backends (memory, file, Redis)
    - Authentication middleware support
    - Rate limiting
    - Async client support
    - Metrics collection
    """
    
    def __init__(
        self,
        storage_type: str = "memory",
        file_path: Optional[str] = None,
        redis_config: Optional[Dict[str, Any]] = None,
        auth_middleware: Optional[AuthMiddleware] = None,
        rate_limiter: Optional[RateLimiter] = None,
        metrics_collector: Optional[MetricsCollector] = None,
        enable_metrics: bool = True
    ):
        """
        Initialize the API Context Memory System.
        
        Args:
            storage_type: Type of storage ("memory", "file", or "redis")
            file_path: Path to file storage (required if storage_type is "file")
            redis_config: Redis configuration dict (required if storage_type is "redis")
            auth_middleware: Optional authentication middleware
            rate_limiter: Optional rate limiter
            metrics_collector: Optional custom metrics collector
            enable_metrics: Enable metrics collection (default True)
        """
        self.storage = Storage(storage_type, file_path, redis_config)
        self.active_tab_id = None
        self._auth_middleware = auth_middleware
        self._rate_limiter = rate_limiter
        self._metrics_collector = metrics_collector if metrics_collector else (
            get_metrics_collector() if enable_metrics else None
        )
        logger.info(f"Initialized API Context Memory with {storage_type} storage")
    
    @property
    def auth_middleware(self) -> Optional[AuthMiddleware]:
        """Get the authentication middleware."""
        return self._auth_middleware
    
    @auth_middleware.setter
    def auth_middleware(self, middleware: Optional[AuthMiddleware]):
        """Set the authentication middleware."""
        self._auth_middleware = middleware
    
    @property
    def rate_limiter(self) -> Optional[RateLimiter]:
        """Get the rate limiter."""
        return self._rate_limiter
    
    @rate_limiter.setter
    def rate_limiter(self, limiter: Optional[RateLimiter]):
        """Set the rate limiter."""
        self._rate_limiter = limiter
    
    @property
    def metrics(self) -> Optional[MetricsCollector]:
        """Get the metrics collector."""
        return self._metrics_collector
    
    def create_tab(self, tab_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a new tab with an associated session.
        
        Args:
            tab_id: Optional tab identifier (generated if not provided)
            metadata: Optional tab metadata
            
        Returns:
            Dict[str, Any]: Tab information including tab_id and session_id
        """
        if tab_id is None:
            tab_id = str(uuid.uuid4())
        
        session_id = str(uuid.uuid4())
        
        # Create session
        session = Session(session_id)
        self.storage.store(f"session:{session_id}", session.to_dict())
        
        # Create tab
        tab = Tab(tab_id, session_id, metadata)
        self.storage.store(f"tab:{tab_id}", tab.to_dict())
        
        # Set as active tab
        self.active_tab_id = tab_id
        
        logger.info(f"Created tab {tab_id} with session {session_id}")
        return {
            "tab_id": tab_id,
            "session_id": session_id,
            "metadata": metadata or {}
        }
    
    def get_tab(self, tab_id: str) -> Optional[Dict[str, Any]]:
        """
        Get tab information.
        
        Args:
            tab_id: Tab identifier
            
        Returns:
            Optional[Dict[str, Any]]: Tab information or None if not found
        """
        tab_data = self.storage.retrieve(f"tab:{tab_id}")
        if not tab_data:
            logger.warning(f"Tab {tab_id} not found")
            return None
        
        return {
            "tab_id": tab_data["tab_id"],
            "session_id": tab_data["session_id"],
            "metadata": tab_data["metadata"]
        }
    
    def get_active_tab(self) -> Optional[Dict[str, Any]]:
        """
        Get the active tab.
        
        Returns:
            Optional[Dict[str, Any]]: Active tab information or None if no active tab
        """
        if not self.active_tab_id:
            logger.warning("No active tab")
            return None
        
        return self.get_tab(self.active_tab_id)
    
    def switch_tab(self, tab_id: str) -> bool:
        """
        Switch the active tab.
        
        Args:
            tab_id: Tab identifier
            
        Returns:
            bool: True if successful, False if tab not found
        """
        tab = self.get_tab(tab_id)
        if not tab:
            return False
        
        self.active_tab_id = tab_id
        logger.info(f"Switched to tab {tab_id}")
        return True
    
    def list_tabs(self) -> List[Dict[str, Any]]:
        """
        List all tabs.
        
        Returns:
            List[Dict[str, Any]]: List of tab information
        """
        tabs = []
        for key in self.storage.list_keys():
            if key.startswith("tab:"):
                tab_id = key[4:]  # Remove "tab:" prefix
                tab = self.get_tab(tab_id)
                if tab:
                    tabs.append(tab)
        
        return tabs
    
    def close_tab(self, tab_id: str) -> bool:
        """
        Close a tab.
        
        Args:
            tab_id: Tab identifier
            
        Returns:
            bool: True if successful, False if tab not found
        """
        tab = self.get_tab(tab_id)
        if not tab:
            return False
        
        # Delete tab and associated session
        self.storage.delete(f"tab:{tab_id}")
        self.storage.delete(f"session:{tab['session_id']}")
        
        # If this was the active tab, clear active tab
        if self.active_tab_id == tab_id:
            self.active_tab_id = None
        
        logger.info(f"Closed tab {tab_id}")
        return True
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """
        Get a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Optional[Session]: Session object or None if not found
        """
        session_data = self.storage.retrieve(f"session:{session_id}")
        if not session_data:
            logger.warning(f"Session {session_id} not found")
            return None
        
        return Session(session_data["session_id"], session_data.get("data", {}))
    
    def save_session(self, session: Session) -> bool:
        """
        Save a session.
        
        Args:
            session: Session object
            
        Returns:
            bool: True if successful
        """
        return self.storage.store(f"session:{session.session_id}", session.to_dict())
    
    def transfer_memory(self, source_tab_id: str, target_tab_id: str, keys: Optional[List[str]] = None) -> bool:
        """
        Transfer memory (context) from one tab to another.
        
        Args:
            source_tab_id: Source tab identifier
            target_tab_id: Target tab identifier
            keys: Optional list of specific keys to transfer (transfers all if None)
            
        Returns:
            bool: True if successful, False if either tab not found
        """
        source_tab = self.get_tab(source_tab_id)
        target_tab = self.get_tab(target_tab_id)
        
        if not source_tab or not target_tab:
            logger.warning(f"Tab not found: source={source_tab_id}, target={target_tab_id}")
            return False
        
        source_session = self.get_session(source_tab["session_id"])
        target_session = self.get_session(target_tab["session_id"])
        
        if not source_session or not target_session:
            logger.warning(f"Session not found: source={source_tab['session_id']}, target={target_tab['session_id']}")
            return False
        
        # Transfer data
        if keys:
            for key in keys:
                if key in source_session.data:
                    target_session.set(key, source_session.get(key))
        else:
            for key, value in source_session.data.items():
                target_session.set(key, value)
        
        # Save target session
        self.save_session(target_session)
        
        logger.info(f"Transferred memory from tab {source_tab_id} to {target_tab_id}")
        return True
    
    def record_interaction(self, session_id: str, request_data: Dict[str, Any], response_data: Dict[str, Any]) -> str:
        """
        Record an API interaction.
        
        Args:
            session_id: Session identifier
            request_data: Request data
            response_data: Response data
            
        Returns:
            str: Interaction identifier
        """
        interaction_id = str(uuid.uuid4())
        
        interaction = {
            "id": interaction_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request": request_data,
            "response": response_data
        }
        
        # Get existing interactions
        interactions_key = f"interactions:{session_id}"
        interactions = self.storage.retrieve(interactions_key) or {"interactions": []}
        
        # Add new interaction
        interactions["interactions"].append(interaction)
        
        # Save interactions
        self.storage.store(interactions_key, interactions)
        
        logger.info(f"Recorded interaction {interaction_id} for session {session_id}")
        return interaction_id
    
    def get_interactions(self, tab_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get recorded interactions for a tab.
        
        Args:
            tab_id: Tab identifier (uses active tab if None)
            
        Returns:
            List[Dict[str, Any]]: List of interactions
        """
        if tab_id is None:
            active_tab = self.get_active_tab()
            if not active_tab:
                logger.warning("No active tab to get interactions from")
                return []
            tab_id = active_tab["tab_id"]
        
        tab = self.get_tab(tab_id)
        if not tab:
            logger.warning(f"Tab {tab_id} not found")
            return []
        
        session_id = tab["session_id"]
        interactions_data = self.storage.retrieve(f"interactions:{session_id}")
        
        if not interactions_data:
            return []
        
        return interactions_data.get("interactions", [])
    
    def find_errors(self, tab_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Find error interactions for a tab.
        
        Args:
            tab_id: Tab identifier (uses active tab if None)
            
        Returns:
            List[Dict[str, Any]]: List of error interactions
        """
        interactions = self.get_interactions(tab_id)
        
        errors = []
        for interaction in interactions:
            response = interaction.get("response", {})
            status_code = response.get("status_code", 0)
            
            # Consider 4xx and 5xx status codes as errors
            if status_code >= 400 or "error" in response:
                errors.append(interaction)
        
        return errors
    
    def create_client(
        self,
        auth_middleware: Optional[AuthMiddleware] = None,
        rate_limiter: Optional[RateLimiter] = None
    ) -> 'APIClient':
        """
        Create an API client.
        
        Args:
            auth_middleware: Override auth middleware (uses instance default if None)
            rate_limiter: Override rate limiter (uses instance default if None)
        
        Returns:
            APIClient: API client object
        """
        return APIClient(
            self,
            auth_middleware=auth_middleware or self._auth_middleware,
            rate_limiter=rate_limiter or self._rate_limiter,
            metrics_collector=self._metrics_collector
        )
    
    def create_async_client(
        self,
        auth_middleware: Optional[AuthMiddleware] = None,
        rate_limiter: Optional[RateLimiter] = None,
        timeout: float = 30.0
    ) -> 'AsyncAPIClient':
        """
        Create an async API client.
        
        Args:
            auth_middleware: Override auth middleware (uses instance default if None)
            rate_limiter: Override rate limiter (uses instance default if None)
            timeout: Request timeout in seconds
        
        Returns:
            AsyncAPIClient: Async API client object
        """
        from .async_client import AsyncAPIClient
        return AsyncAPIClient(
            self,
            auth_middleware=auth_middleware or self._auth_middleware,
            rate_limiter=rate_limiter or self._rate_limiter,
            timeout=timeout
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current metrics.
        
        Returns:
            Dict with global metrics, endpoint metrics, and recent requests
        """
        if not self._metrics_collector:
            return {"error": "Metrics collection is disabled"}
        
        return {
            "global": self._metrics_collector.get_global_metrics(),
            "endpoints": self._metrics_collector.get_endpoint_metrics(),
            "errors": self._metrics_collector.get_error_summary(),
            "recent": self._metrics_collector.get_recent_metrics(20)
        }
    
    def handle_restart(self, tab_id: str, url: str, method: str = "GET", **kwargs) -> Tuple[requests.Response, str]:
        """
        Handle API reconnection by creating a new tab and transferring memory.
        
        Args:
            tab_id: Original tab identifier
            url: URL to request after reconnection
            method: HTTP method
            **kwargs: Additional request arguments
            
        Returns:
            Tuple[requests.Response, str]: Response and new tab ID
        """
        # Create new tab
        new_tab = self.create_tab(metadata={"name": "Reconnected Tab", "original_tab_id": tab_id})
        new_tab_id = new_tab["tab_id"]
        
        # Transfer memory from original tab
        self.transfer_memory(tab_id, new_tab_id)
        
        # Make request with new tab
        client = self.create_client()
        response = client.request(new_tab["session_id"], method, url, **kwargs)
        
        logger.info(f"Handled restart from tab {tab_id} to {new_tab_id}")
        return response, new_tab_id


class APIClient:
    """
    API client with context recording, authentication, and rate limiting.
    
    Features:
    - Automatic interaction recording
    - Authentication middleware support
    - Rate limiting
    - Metrics collection
    - Retry handling
    """
    
    def __init__(
        self,
        api_memory: APIContextMemory,
        auth_middleware: Optional[AuthMiddleware] = None,
        rate_limiter: Optional[RateLimiter] = None,
        metrics_collector: Optional[MetricsCollector] = None,
        retry_handler: Optional[RetryHandler] = None
    ):
        """
        Initialize API client.
        
        Args:
            api_memory: APIContextMemory instance
            auth_middleware: Optional authentication middleware
            rate_limiter: Optional rate limiter
            metrics_collector: Optional metrics collector
            retry_handler: Optional retry handler for rate limit retries
        """
        self.api_memory = api_memory
        self._auth_middleware = auth_middleware
        self._rate_limiter = rate_limiter
        self._metrics_collector = metrics_collector
        self._retry_handler = retry_handler or RetryHandler(max_retries=3)
    
    def _apply_auth(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Apply authentication middleware if configured."""
        if self._auth_middleware:
            return self._auth_middleware.apply(headers)
        return headers
    
    def _check_rate_limit(self, url: str) -> Tuple[bool, float]:
        """Check rate limit and return (allowed, wait_time)."""
        if self._rate_limiter:
            return self._rate_limiter.acquire(url)
        return True, 0.0
    
    def _record_metric(
        self,
        url: str,
        method: str,
        status_code: int,
        response_time_ms: float,
        request_size: int,
        response_size: int,
        error: Optional[str] = None
    ) -> None:
        """Record request metric."""
        if self._metrics_collector:
            metric = RequestMetric(
                url=url,
                method=method,
                status_code=status_code,
                response_time_ms=response_time_ms,
                request_size=request_size,
                response_size=response_size,
                timestamp=datetime.now(timezone.utc).isoformat(),
                error=error
            )
            self._metrics_collector.record(metric)
    
    def request(self, session_id: str, method: str, url: str, **kwargs) -> requests.Response:
        """
        Make an API request and record the interaction.
        
        Args:
            session_id: Session identifier
            method: HTTP method
            url: URL to request
            **kwargs: Additional request arguments
            
        Returns:
            requests.Response: Response object
        """
        # Check rate limit
        allowed, wait_time = self._check_rate_limit(url)
        if not allowed:
            if self._retry_handler:
                self._retry_handler.wait(0, wait_time)
                allowed, wait_time = self._check_rate_limit(url)
                if not allowed:
                    raise Exception(f"Rate limit exceeded for {url}")
            else:
                time.sleep(wait_time)
        
        # Apply authentication
        headers = kwargs.pop("headers", {})
        headers = self._apply_auth(headers)
        
        # Prepare request data for recording (exclude auth headers for security)
        request_data = {
            "method": method,
            "url": url,
            "headers": {k: v for k, v in headers.items() if k.lower() != "authorization"},
            "params": kwargs.get("params", {}),
            "data": str(kwargs.get("data", {})),
            "json": kwargs.get("json", {})
        }
        
        # Calculate request size
        request_size = len(str(request_data))
        
        # Make the request with timing
        with PerformanceTimer() as timer:
            try:
                response = requests.request(method, url, headers=headers, **kwargs)
                
                # Prepare response data for recording
                response_data = {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "content_type": response.headers.get("Content-Type", ""),
                    "content_length": len(response.content),
                    "text": response.text
                }
                
                # Record the interaction
                self.api_memory.record_interaction(session_id, request_data, response_data)
                
                # Record metric
                self._record_metric(
                    url=url,
                    method=method,
                    status_code=response.status_code,
                    response_time_ms=timer.elapsed_ms,
                    request_size=request_size,
                    response_size=len(response.content)
                )
                
                return response
            
            except Exception as e:
                # Record the error
                error_data = {
                    "error": str(e),
                    "error_type": type(e).__name__
                }
                self.api_memory.record_interaction(session_id, request_data, error_data)
                
                # Record error metric
                self._record_metric(
                    url=url,
                    method=method,
                    status_code=0,
                    response_time_ms=timer.elapsed_ms,
                    request_size=request_size,
                    response_size=0,
                    error=str(e)
                )
                
                logger.error(f"Request failed: {str(e)}")
                raise
    
    def get(self, session_id: str, url: str, **kwargs) -> requests.Response:
        """
        Make a GET request.
        
        Args:
            session_id: Session identifier
            url: URL to request
            **kwargs: Additional request arguments
            
        Returns:
            requests.Response: Response object
        """
        return self.request(session_id, "GET", url, **kwargs)
    
    def post(self, session_id: str, url: str, **kwargs) -> requests.Response:
        """
        Make a POST request.
        
        Args:
            session_id: Session identifier
            url: URL to request
            **kwargs: Additional request arguments
            
        Returns:
            requests.Response: Response object
        """
        return self.request(session_id, "POST", url, **kwargs)
    
    def put(self, session_id: str, url: str, **kwargs) -> requests.Response:
        """
        Make a PUT request.
        
        Args:
            session_id: Session identifier
            url: URL to request
            **kwargs: Additional request arguments
            
        Returns:
            requests.Response: Response object
        """
        return self.request(session_id, "PUT", url, **kwargs)
    
    def delete(self, session_id: str, url: str, **kwargs) -> requests.Response:
        """
        Make a DELETE request.
        
        Args:
            session_id: Session identifier
            url: URL to request
            **kwargs: Additional request arguments
            
        Returns:
            requests.Response: Response object
        """
        return self.request(session_id, "DELETE", url, **kwargs)
    
    def patch(self, session_id: str, url: str, **kwargs) -> requests.Response:
        """
        Make a PATCH request.
        
        Args:
            session_id: Session identifier
            url: URL to request
            **kwargs: Additional request arguments
            
        Returns:
            requests.Response: Response object
        """
        return self.request(session_id, "PATCH", url, **kwargs)
