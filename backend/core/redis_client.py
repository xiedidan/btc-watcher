"""
Redis Client for Token Caching and Session Management
"""
import redis.asyncio as aioredis
from typing import Optional
from config import settings
import logging

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis client wrapper for async operations"""

    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None

    async def connect(self):
        """Initialize Redis connection"""
        try:
            # Parse Redis URL
            redis_url = settings.REDIS_URL

            # Create Redis connection
            self.redis = await aioredis.from_url(
                redis_url,
                password=settings.REDIS_PASSWORD,
                encoding="utf-8",
                decode_responses=True,
                max_connections=50,
                socket_connect_timeout=5,
                socket_keepalive=True
            )

            # Test connection
            await self.redis.ping()
            logger.info("✅ Redis connected successfully")

        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            # Don't fail the application, just log the error
            self.redis = None

    async def disconnect(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()
            logger.info("Redis connection closed")

    async def get(self, key: str) -> Optional[str]:
        """Get value from Redis"""
        if not self.redis:
            return None
        try:
            return await self.redis.get(key)
        except Exception as e:
            logger.error(f"Redis GET error: {e}")
            return None

    async def set(
        self,
        key: str,
        value: str,
        expire_seconds: Optional[int] = None
    ) -> bool:
        """Set value in Redis with optional expiration"""
        if not self.redis:
            return False
        try:
            if expire_seconds:
                await self.redis.setex(key, expire_seconds, value)
            else:
                await self.redis.set(key, value)
            return True
        except Exception as e:
            logger.error(f"Redis SET error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        if not self.redis:
            return False
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis DELETE error: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis"""
        if not self.redis:
            return False
        try:
            return await self.redis.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis EXISTS error: {e}")
            return False

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration time for key"""
        if not self.redis:
            return False
        try:
            await self.redis.expire(key, seconds)
            return True
        except Exception as e:
            logger.error(f"Redis EXPIRE error: {e}")
            return False

    async def ttl(self, key: str) -> int:
        """Get time to live for key"""
        if not self.redis:
            return -1
        try:
            return await self.redis.ttl(key)
        except Exception as e:
            logger.error(f"Redis TTL error: {e}")
            return -1

    async def keys(self, pattern: str = "*") -> list:
        """Get all keys matching pattern"""
        if not self.redis:
            return []
        try:
            return await self.redis.keys(pattern)
        except Exception as e:
            logger.error(f"Redis KEYS error: {e}")
            return []

    def is_connected(self) -> bool:
        """Check if Redis is connected"""
        return self.redis is not None


# Global Redis client instance
redis_client = RedisClient()


async def get_redis() -> RedisClient:
    """Dependency to get Redis client"""
    return redis_client
