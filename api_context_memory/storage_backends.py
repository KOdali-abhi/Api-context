"""
Storage backends for API Context Memory System.

This module provides different storage options including:
- Memory storage (default)
- File storage
- Redis storage (for production use)
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger("api_context_memory.storage")


class StorageBackend(ABC):
    """Abstract base class for storage backends."""
    
    @abstractmethod
    def store(self, key: str, value: Dict[str, Any]) -> bool:
        """Store data with the given key."""
        pass
    
    @abstractmethod
    def retrieve(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve data for the given key."""
        pass
    
    @abstractmethod
    def update(self, key: str, value: Dict[str, Any]) -> bool:
        """Update data for the given key."""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete data for the given key."""
        pass
    
    @abstractmethod
    def list_keys(self, pattern: str = "*") -> List[str]:
        """List all keys matching pattern."""
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if key exists."""
        pass
    
    @abstractmethod
    def clear(self) -> bool:
        """Clear all data."""
        pass


class MemoryStorage(StorageBackend):
    """In-memory storage backend."""
    
    def __init__(self):
        """Initialize memory storage."""
        self.data: Dict[str, Dict[str, Any]] = {}
        logger.info("Initialized memory storage backend")
    
    def store(self, key: str, value: Dict[str, Any]) -> bool:
        """Store data with the given key."""
        self.data[key] = value
        return True
    
    def retrieve(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve data for the given key."""
        return self.data.get(key)
    
    def update(self, key: str, value: Dict[str, Any]) -> bool:
        """Update data for the given key."""
        if key in self.data:
            if isinstance(self.data[key], dict) and isinstance(value, dict):
                self.data[key].update(value)
            else:
                self.data[key] = value
        else:
            self.data[key] = value
        return True
    
    def delete(self, key: str) -> bool:
        """Delete data for the given key."""
        if key in self.data:
            del self.data[key]
            return True
        return False
    
    def list_keys(self, pattern: str = "*") -> List[str]:
        """List all keys matching pattern."""
        if pattern == "*":
            return list(self.data.keys())
        # Simple pattern matching for prefix:*
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return [k for k in self.data.keys() if k.startswith(prefix)]
        return [k for k in self.data.keys() if k == pattern]
    
    def exists(self, key: str) -> bool:
        """Check if key exists."""
        return key in self.data
    
    def clear(self) -> bool:
        """Clear all data."""
        self.data = {}
        return True


class FileStorage(StorageBackend):
    """File-based storage backend."""
    
    def __init__(self, file_path: str):
        """
        Initialize file storage.
        
        Args:
            file_path: Path to the storage file
        """
        import os
        self.file_path = file_path
        self.data: Dict[str, Dict[str, Any]] = {}
        
        # Create directory if needed
        dir_path = os.path.dirname(os.path.abspath(file_path))
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        
        # Load existing data
        if os.path.exists(file_path):
            try:
                with open(file_path, "r") as f:
                    self.data = json.load(f)
            except json.JSONDecodeError:
                logger.warning(f"Could not load data from {file_path}, starting with empty storage")
        
        logger.info(f"Initialized file storage backend at {file_path}")
    
    def _save_to_file(self):
        """Save data to file."""
        with open(self.file_path, "w") as f:
            json.dump(self.data, f, indent=2)
    
    def store(self, key: str, value: Dict[str, Any]) -> bool:
        """Store data with the given key."""
        self.data[key] = value
        self._save_to_file()
        return True
    
    def retrieve(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve data for the given key."""
        return self.data.get(key)
    
    def update(self, key: str, value: Dict[str, Any]) -> bool:
        """Update data for the given key."""
        if key in self.data:
            if isinstance(self.data[key], dict) and isinstance(value, dict):
                self.data[key].update(value)
            else:
                self.data[key] = value
        else:
            self.data[key] = value
        self._save_to_file()
        return True
    
    def delete(self, key: str) -> bool:
        """Delete data for the given key."""
        if key in self.data:
            del self.data[key]
            self._save_to_file()
            return True
        return False
    
    def list_keys(self, pattern: str = "*") -> List[str]:
        """List all keys matching pattern."""
        if pattern == "*":
            return list(self.data.keys())
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return [k for k in self.data.keys() if k.startswith(prefix)]
        return [k for k in self.data.keys() if k == pattern]
    
    def exists(self, key: str) -> bool:
        """Check if key exists."""
        return key in self.data
    
    def clear(self) -> bool:
        """Clear all data."""
        self.data = {}
        self._save_to_file()
        return True


class RedisStorage(StorageBackend):
    """Redis storage backend for production use."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        prefix: str = "api_context:",
        connection_url: Optional[str] = None
    ):
        """
        Initialize Redis storage.
        
        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password (optional)
            prefix: Key prefix for all stored data
            connection_url: Redis connection URL (overrides host/port/db/password)
        """
        try:
            import redis
        except ImportError:
            raise ImportError(
                "Redis package is required for Redis storage. "
                "Install it with: pip install redis"
            )
        
        self.prefix = prefix
        
        if connection_url:
            self.client = redis.from_url(connection_url)
        else:
            self.client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=True
            )
        
        # Test connection
        try:
            self.client.ping()
            logger.info(f"Initialized Redis storage backend at {host}:{port}")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    def _prefixed_key(self, key: str) -> str:
        """Add prefix to key."""
        return f"{self.prefix}{key}"
    
    def store(self, key: str, value: Dict[str, Any]) -> bool:
        """Store data with the given key."""
        try:
            self.client.set(self._prefixed_key(key), json.dumps(value))
            return True
        except Exception as e:
            logger.error(f"Redis store error: {e}")
            return False
    
    def retrieve(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve data for the given key."""
        try:
            data = self.client.get(self._prefixed_key(key))
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Redis retrieve error: {e}")
            return None
    
    def update(self, key: str, value: Dict[str, Any]) -> bool:
        """Update data for the given key."""
        try:
            existing = self.retrieve(key)
            if existing and isinstance(existing, dict) and isinstance(value, dict):
                existing.update(value)
                return self.store(key, existing)
            return self.store(key, value)
        except Exception as e:
            logger.error(f"Redis update error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete data for the given key."""
        try:
            result = self.client.delete(self._prefixed_key(key))
            return result > 0
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False
    
    def list_keys(self, pattern: str = "*") -> List[str]:
        """List all keys matching pattern."""
        try:
            full_pattern = self._prefixed_key(pattern)
            keys = self.client.keys(full_pattern)
            # Remove prefix from keys, handling both string and bytes types
            prefix_len = len(self.prefix)
            result = []
            for k in keys:
                try:
                    if isinstance(k, str):
                        result.append(k[prefix_len:])
                    elif isinstance(k, bytes):
                        result.append(k.decode()[prefix_len:])
                    else:
                        result.append(str(k)[prefix_len:])
                except (AttributeError, UnicodeDecodeError) as e:
                    logger.warning(f"Could not decode key {k}: {e}")
            return result
        except Exception as e:
            logger.error(f"Redis list_keys error: {e}")
            return []
    
    def exists(self, key: str) -> bool:
        """Check if key exists."""
        try:
            return bool(self.client.exists(self._prefixed_key(key)))
        except Exception as e:
            logger.error(f"Redis exists error: {e}")
            return False
    
    def clear(self) -> bool:
        """Clear all data with the prefix."""
        try:
            keys = self.client.keys(f"{self.prefix}*")
            if keys:
                self.client.delete(*keys)
            return True
        except Exception as e:
            logger.error(f"Redis clear error: {e}")
            return False


def create_storage(
    storage_type: str = "memory",
    file_path: Optional[str] = None,
    redis_config: Optional[Dict[str, Any]] = None
) -> StorageBackend:
    """
    Factory function to create storage backend.
    
    Args:
        storage_type: Type of storage ("memory", "file", or "redis")
        file_path: Path to file storage (required if storage_type is "file")
        redis_config: Redis configuration dict (required if storage_type is "redis")
    
    Returns:
        StorageBackend: The appropriate storage backend instance
    """
    if storage_type == "memory":
        return MemoryStorage()
    elif storage_type == "file":
        if not file_path:
            raise ValueError("file_path is required for file storage")
        return FileStorage(file_path)
    elif storage_type == "redis":
        if not redis_config:
            redis_config = {}
        return RedisStorage(**redis_config)
    else:
        raise ValueError(f"Unknown storage type: {storage_type}")
