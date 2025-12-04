"""
Authentication middleware for API Context Memory System.

This module provides authentication handlers for API requests:
- Bearer token authentication
- API key authentication
- Basic authentication
- Custom header authentication
- OAuth2 support
"""

import base64
import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("api_context_memory.auth")


class AuthMiddleware(ABC):
    """Abstract base class for authentication middleware."""
    
    @abstractmethod
    def apply(self, headers: Dict[str, str], **kwargs) -> Dict[str, str]:
        """
        Apply authentication to request headers.
        
        Args:
            headers: Current request headers
            **kwargs: Additional arguments
            
        Returns:
            Dict[str, str]: Updated headers with authentication
        """
        pass
    
    @abstractmethod
    def refresh(self) -> bool:
        """
        Refresh authentication credentials if needed.
        
        Returns:
            bool: True if refresh was successful or not needed
        """
        pass
    
    @property
    @abstractmethod
    def is_valid(self) -> bool:
        """Check if authentication is still valid."""
        pass


class BearerTokenAuth(AuthMiddleware):
    """Bearer token authentication middleware."""
    
    def __init__(
        self,
        token: str,
        token_refresh_callback: Optional[Callable[[], str]] = None,
        header_name: str = "Authorization"
    ):
        """
        Initialize bearer token authentication.
        
        Args:
            token: Bearer token
            token_refresh_callback: Optional callback to refresh token
            header_name: Header name for the token
        """
        self._token = token
        self._refresh_callback = token_refresh_callback
        self._header_name = header_name
        logger.info("Initialized Bearer token authentication")
    
    @property
    def token(self) -> str:
        """Get the current token."""
        return self._token
    
    @token.setter
    def token(self, value: str):
        """Set a new token."""
        self._token = value
    
    def apply(self, headers: Dict[str, str], **kwargs) -> Dict[str, str]:
        """Apply bearer token to headers."""
        headers = headers.copy()
        headers[self._header_name] = f"Bearer {self._token}"
        return headers
    
    def refresh(self) -> bool:
        """Refresh the token using callback if available."""
        if self._refresh_callback:
            try:
                self._token = self._refresh_callback()
                logger.info("Bearer token refreshed successfully")
                return True
            except Exception as e:
                logger.error(f"Failed to refresh bearer token: {e}")
                return False
        return True
    
    @property
    def is_valid(self) -> bool:
        """Check if token is set."""
        return bool(self._token)


class APIKeyAuth(AuthMiddleware):
    """API key authentication middleware."""
    
    def __init__(
        self,
        api_key: str,
        header_name: str = "X-API-Key",
        key_prefix: str = ""
    ):
        """
        Initialize API key authentication.
        
        Args:
            api_key: The API key
            header_name: Header name for the API key
            key_prefix: Optional prefix for the key value
        """
        self._api_key = api_key
        self._header_name = header_name
        self._key_prefix = key_prefix
        logger.info(f"Initialized API key authentication with header: {header_name}")
    
    def apply(self, headers: Dict[str, str], **kwargs) -> Dict[str, str]:
        """Apply API key to headers."""
        headers = headers.copy()
        value = f"{self._key_prefix}{self._api_key}" if self._key_prefix else self._api_key
        headers[self._header_name] = value
        return headers
    
    def refresh(self) -> bool:
        """API keys don't typically need refresh."""
        return True
    
    @property
    def is_valid(self) -> bool:
        """Check if API key is set."""
        return bool(self._api_key)


class BasicAuth(AuthMiddleware):
    """Basic authentication middleware."""
    
    def __init__(self, username: str, password: str):
        """
        Initialize basic authentication.
        
        Args:
            username: Username
            password: Password
        """
        self._username = username
        self._password = password
        logger.info(f"Initialized Basic authentication for user: {username}")
    
    def apply(self, headers: Dict[str, str], **kwargs) -> Dict[str, str]:
        """Apply basic auth to headers."""
        headers = headers.copy()
        credentials = base64.b64encode(
            f"{self._username}:{self._password}".encode()
        ).decode()
        headers["Authorization"] = f"Basic {credentials}"
        return headers
    
    def refresh(self) -> bool:
        """Basic auth doesn't need refresh."""
        return True
    
    @property
    def is_valid(self) -> bool:
        """Check if credentials are set."""
        return bool(self._username and self._password)


class CustomHeaderAuth(AuthMiddleware):
    """Custom header authentication middleware."""
    
    def __init__(self, headers: Dict[str, str]):
        """
        Initialize custom header authentication.
        
        Args:
            headers: Dictionary of custom headers to add
        """
        self._custom_headers = headers
        logger.info(f"Initialized custom header authentication with {len(headers)} headers")
    
    def apply(self, headers: Dict[str, str], **kwargs) -> Dict[str, str]:
        """Apply custom headers."""
        headers = headers.copy()
        headers.update(self._custom_headers)
        return headers
    
    def refresh(self) -> bool:
        """Custom headers don't need refresh."""
        return True
    
    @property
    def is_valid(self) -> bool:
        """Check if headers are set."""
        return bool(self._custom_headers)
    
    def update_headers(self, headers: Dict[str, str]):
        """Update custom headers."""
        self._custom_headers.update(headers)


class OAuth2Auth(AuthMiddleware):
    """OAuth2 authentication middleware with token refresh support."""
    
    def __init__(
        self,
        access_token: str,
        refresh_token: Optional[str] = None,
        token_url: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        expires_at: Optional[float] = None
    ):
        """
        Initialize OAuth2 authentication.
        
        Args:
            access_token: OAuth2 access token
            refresh_token: OAuth2 refresh token (optional)
            token_url: Token refresh endpoint URL
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret
            expires_at: Token expiration timestamp
        """
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._token_url = token_url
        self._client_id = client_id
        self._client_secret = client_secret
        self._expires_at = expires_at
        logger.info("Initialized OAuth2 authentication")
    
    @property
    def access_token(self) -> str:
        """Get the current access token."""
        return self._access_token
    
    def apply(self, headers: Dict[str, str], **kwargs) -> Dict[str, str]:
        """Apply OAuth2 token to headers."""
        headers = headers.copy()
        headers["Authorization"] = f"Bearer {self._access_token}"
        return headers
    
    def refresh(self) -> bool:
        """Refresh the OAuth2 token."""
        if not all([self._refresh_token, self._token_url, self._client_id]):
            logger.warning("Missing required OAuth2 refresh configuration")
            return False
        
        try:
            import requests
            
            data = {
                "grant_type": "refresh_token",
                "refresh_token": self._refresh_token,
                "client_id": self._client_id,
            }
            
            if self._client_secret:
                data["client_secret"] = self._client_secret
            
            response = requests.post(self._token_url, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            self._access_token = token_data["access_token"]
            
            if "refresh_token" in token_data:
                self._refresh_token = token_data["refresh_token"]
            
            if "expires_in" in token_data:
                import time
                self._expires_at = time.time() + token_data["expires_in"]
            
            logger.info("OAuth2 token refreshed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to refresh OAuth2 token: {e}")
            return False
    
    @property
    def is_valid(self) -> bool:
        """Check if token is valid and not expired."""
        if not self._access_token:
            return False
        
        if self._expires_at:
            import time
            # Consider token invalid if it expires within 60 seconds
            return time.time() < (self._expires_at - 60)
        
        return True


class ChainedAuth(AuthMiddleware):
    """Chain multiple authentication middlewares together."""
    
    def __init__(self, *auth_middlewares: AuthMiddleware):
        """
        Initialize chained authentication.
        
        Args:
            *auth_middlewares: Authentication middlewares to chain
        """
        self._middlewares = list(auth_middlewares)
        logger.info(f"Initialized chained authentication with {len(self._middlewares)} middlewares")
    
    def add(self, middleware: AuthMiddleware):
        """Add a middleware to the chain."""
        self._middlewares.append(middleware)
    
    def apply(self, headers: Dict[str, str], **kwargs) -> Dict[str, str]:
        """Apply all authentication middlewares in order."""
        for middleware in self._middlewares:
            headers = middleware.apply(headers, **kwargs)
        return headers
    
    def refresh(self) -> bool:
        """Refresh all middlewares."""
        success = True
        for middleware in self._middlewares:
            if not middleware.refresh():
                success = False
        return success
    
    @property
    def is_valid(self) -> bool:
        """Check if all middlewares are valid."""
        return all(m.is_valid for m in self._middlewares)
