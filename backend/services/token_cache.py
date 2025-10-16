"""
Token Cache Service using Redis
Caches JWT tokens to reduce authentication overhead
"""
import json
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from core.redis_client import RedisClient
from config import settings
import logging

logger = logging.getLogger(__name__)


class TokenCacheService:
    """Service for caching authentication tokens"""

    def __init__(self, redis_client: RedisClient):
        self.redis = redis_client
        self.token_prefix = "auth:token:"
        self.user_prefix = "auth:user:"
        # Cache tokens for slightly less than JWT expiration to ensure freshness
        self.cache_ttl = (settings.JWT_EXPIRE_HOURS * 3600) - 300  # 5 minutes before JWT expires

    def _make_token_key(self, token: str) -> str:
        """Generate Redis key for token"""
        # Use first 32 chars of token as key (safe and unique)
        token_hash = token[:32] if len(token) > 32 else token
        return f"{self.token_prefix}{token_hash}"

    def _make_user_key(self, user_id: int) -> str:
        """Generate Redis key for user data"""
        return f"{self.user_prefix}{user_id}"

    async def cache_token(
        self,
        token: str,
        user_data: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache token with associated user data

        Args:
            token: JWT token string
            user_data: User information dict (id, username, email, etc.)
            ttl: Time to live in seconds (default: cache_ttl)

        Returns:
            True if successful, False otherwise
        """
        if not self.redis.is_connected():
            logger.warning("Redis not connected, skipping token cache")
            return False

        try:
            cache_ttl = ttl or self.cache_ttl
            token_key = self._make_token_key(token)

            # Prepare cache data
            cache_data = {
                "user_id": user_data.get("id"),
                "username": user_data.get("username"),
                "email": user_data.get("email"),
                "is_active": user_data.get("is_active", True),
                "cached_at": datetime.utcnow().isoformat()
            }

            # Store token -> user mapping
            success = await self.redis.set(
                token_key,
                json.dumps(cache_data),
                expire_seconds=cache_ttl
            )

            if success:
                logger.debug(f"Token cached for user {user_data.get('username')}")
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to cache token: {e}")
            return False

    async def get_cached_user(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached user data from token

        Args:
            token: JWT token string

        Returns:
            User data dict or None if not found
        """
        if not self.redis.is_connected():
            return None

        try:
            token_key = self._make_token_key(token)
            cached_data = await self.redis.get(token_key)

            if not cached_data:
                logger.debug("Token not found in cache (cache miss)")
                return None

            user_data = json.loads(cached_data)
            logger.debug(f"Token found in cache (cache hit) for user {user_data.get('username')}")
            return user_data

        except Exception as e:
            logger.error(f"Failed to get cached user: {e}")
            return None

    async def invalidate_token(self, token: str) -> bool:
        """
        Remove token from cache (logout)

        Args:
            token: JWT token string

        Returns:
            True if successful
        """
        if not self.redis.is_connected():
            return False

        try:
            token_key = self._make_token_key(token)
            success = await self.redis.delete(token_key)

            if success:
                logger.info("Token invalidated successfully")
            return success

        except Exception as e:
            logger.error(f"Failed to invalidate token: {e}")
            return False

    async def invalidate_user_tokens(self, user_id: int) -> bool:
        """
        Invalidate all tokens for a specific user

        Args:
            user_id: User ID

        Returns:
            True if successful
        """
        if not self.redis.is_connected():
            return False

        try:
            # Find all tokens for this user
            pattern = f"{self.token_prefix}*"
            keys = await self.redis.keys(pattern)

            deleted_count = 0
            for key in keys:
                cached_data = await self.redis.get(key)
                if cached_data:
                    user_data = json.loads(cached_data)
                    if user_data.get("user_id") == user_id:
                        await self.redis.delete(key)
                        deleted_count += 1

            logger.info(f"Invalidated {deleted_count} tokens for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to invalidate user tokens: {e}")
            return False

    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics

        Returns:
            Dict with cache stats
        """
        if not self.redis.is_connected():
            return {"connected": False}

        try:
            token_keys = await self.redis.keys(f"{self.token_prefix}*")

            return {
                "connected": True,
                "cached_tokens": len(token_keys),
                "cache_ttl_seconds": self.cache_ttl,
                "cache_ttl_hours": self.cache_ttl / 3600
            }

        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"connected": True, "error": str(e)}


# Global token cache service instance (will be initialized in main.py)
token_cache_service: Optional[TokenCacheService] = None


def get_token_cache() -> Optional[TokenCacheService]:
    """Get token cache service instance"""
    return token_cache_service
