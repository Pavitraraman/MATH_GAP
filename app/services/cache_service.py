import time
import logging
from typing import Any, Optional

logger = logging.getLogger("math_gap.cache_service")


class CacheService:
    def __init__(self):
        self._cache = {}  # Maps key -> (value, expiry_timestamp)

    def get(self, key: str) -> Optional[Any]:
        """Retrieves an item from cache if it exists and has not expired."""
        if key not in self._cache:
            return None
            
        value, expiry = self._cache[key]
        if time.time() > expiry:
            # Clean up expired entry
            del self._cache[key]
            logger.info("Cache expired for key: %s", key)
            return None
            
        return value

    def set(self, key: str, value: Any, ttl_seconds: int = 120):
        """Saves an item to cache with a Time-To-Live (TTL) constraint in seconds."""
        expiry = time.time() + ttl_seconds
        self._cache[key] = (value, expiry)
        logger.info("Cached key '%s' with TTL %d seconds", key, ttl_seconds)

    def invalidate(self, key: str):
        """Explicitly deletes a specific key from the cache."""
        if key in self._cache:
            del self._cache[key]
            logger.info("Invalidated cache key: %s", key)

    def invalidate_all(self):
        """Cleanses all entries from the cache."""
        self._cache.clear()
        logger.info("Invalidated entire cache pool")


# Global cache service instance
cache_service = CacheService()
