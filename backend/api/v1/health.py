"""
Health Check API Routes
Provides comprehensive health check endpoints for all system components
"""
from fastapi import APIRouter, Depends
from typing import Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from core.redis_client import get_redis, RedisClient
from api.v1.auth import get_current_user
from models.user import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Global service instances (injected during startup)
_ccxt_manager = None
_failover_manager = None
_market_data_scheduler = None


@router.get("/health/market-data")
async def market_data_health_check(
    db: AsyncSession = Depends(get_db),
    redis_client: RedisClient = Depends(get_redis),
    current_user: User = Depends(get_current_user)
):
    """
    Market data service health check

    Checks health of:
    - Redis cache
    - PostgreSQL database
    - CCXT exchanges
    - Market data scheduler
    """
    health_status = {
        "timestamp": datetime.now().isoformat(),
        "overall_status": "healthy",
        "components": {}
    }

    # Check Redis
    try:
        redis_connected = redis_client.is_connected()
        if redis_connected:
            await redis_client.redis.ping()
            health_status["components"]["redis"] = {
                "status": "healthy",
                "message": "Redis connection active"
            }
        else:
            health_status["components"]["redis"] = {
                "status": "unhealthy",
                "message": "Redis not connected"
            }
            health_status["overall_status"] = "degraded"

    except Exception as e:
        health_status["components"]["redis"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["overall_status"] = "degraded"

    # Check PostgreSQL
    try:
        # Try a simple query
        from sqlalchemy import text
        result = await db.execute(text("SELECT 1"))
        result.fetchone()

        health_status["components"]["postgresql"] = {
            "status": "healthy",
            "message": "Database connection active"
        }

    except Exception as e:
        health_status["components"]["postgresql"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["overall_status"] = "unhealthy"

    # Check CCXT Manager
    global _ccxt_manager
    if _ccxt_manager:
        try:
            supported_exchanges = _ccxt_manager.get_supported_exchanges()
            initialized_exchanges = list(_ccxt_manager.exchanges.keys())

            health_status["components"]["ccxt_manager"] = {
                "status": "healthy",
                "supported_exchanges": supported_exchanges,
                "initialized_exchanges": initialized_exchanges,
                "exchange_count": len(initialized_exchanges)
            }

        except Exception as e:
            health_status["components"]["ccxt_manager"] = {
                "status": "degraded",
                "error": str(e)
            }
            health_status["overall_status"] = "degraded"
    else:
        health_status["components"]["ccxt_manager"] = {
            "status": "not_initialized",
            "message": "CCXT Manager not initialized"
        }

    # Check Exchange Failover Manager
    global _failover_manager
    if _failover_manager:
        try:
            exchange_health = _failover_manager.get_all_health_status()
            current_exchange = _failover_manager.get_current_exchange()

            health_status["components"]["exchange_failover"] = {
                "status": "healthy",
                "current_exchange": current_exchange,
                "exchange_health": exchange_health
            }

        except Exception as e:
            health_status["components"]["exchange_failover"] = {
                "status": "degraded",
                "error": str(e)
            }
    else:
        health_status["components"]["exchange_failover"] = {
            "status": "not_initialized",
            "message": "Exchange Failover Manager not initialized"
        }

    # Check Market Data Scheduler
    global _market_data_scheduler
    if _market_data_scheduler:
        try:
            scheduler_status = _market_data_scheduler.get_job_status()

            health_status["components"]["scheduler"] = {
                "status": "healthy" if scheduler_status.get("is_running") else "stopped",
                **scheduler_status
            }

        except Exception as e:
            health_status["components"]["scheduler"] = {
                "status": "unhealthy",
                "error": str(e)
            }
    else:
        health_status["components"]["scheduler"] = {
            "status": "not_initialized",
            "message": "Market Data Scheduler not initialized"
        }

    return health_status


@router.get("/health/exchanges")
async def exchange_health_check(
    current_user: User = Depends(get_current_user)
):
    """
    Exchange connectivity health check

    Tests connectivity to all enabled exchanges
    """
    global _failover_manager

    if not _failover_manager:
        return {
            "error": "Exchange Failover Manager not initialized"
        }

    try:
        # Trigger health check for all exchanges
        exchange_health = await _failover_manager.check_all_exchanges_health()

        # Calculate overall status
        healthy_count = sum(1 for h in exchange_health.values() if h.get("is_healthy"))
        total_count = len(exchange_health)

        overall_status = "healthy" if healthy_count == total_count else (
            "degraded" if healthy_count > 0 else "unhealthy"
        )

        return {
            "timestamp": datetime.now().isoformat(),
            "overall_status": overall_status,
            "healthy_count": healthy_count,
            "total_count": total_count,
            "exchanges": exchange_health
        }

    except Exception as e:
        logger.error(f"Failed to check exchange health: {e}")
        return {
            "error": str(e),
            "overall_status": "unhealthy"
        }


@router.get("/health/cache")
async def cache_health_check(
    redis_client: RedisClient = Depends(get_redis),
    current_user: User = Depends(get_current_user)
):
    """
    Cache system health check

    Checks Redis cache health and statistics
    """
    health_info = {
        "timestamp": datetime.now().isoformat(),
        "status": "unknown"
    }

    try:
        if not redis_client.is_connected():
            health_info["status"] = "disconnected"
            health_info["message"] = "Redis client not connected"
            return health_info

        # Test connection
        await redis_client.redis.ping()

        # Get cache statistics
        info = await redis_client.redis.info()
        memory_info = await redis_client.redis.info("memory")

        # Get key counts for market data
        kline_keys = await redis_client.keys("kline:*")
        indicator_keys = await redis_client.keys("indicator:*")

        health_info.update({
            "status": "healthy",
            "connected_clients": info.get("connected_clients", 0),
            "used_memory_human": memory_info.get("used_memory_human", "unknown"),
            "cache_stats": {
                "kline_keys": len(kline_keys),
                "indicator_keys": len(indicator_keys),
                "total_keys": len(kline_keys) + len(indicator_keys)
            }
        })

    except Exception as e:
        health_info["status"] = "unhealthy"
        health_info["error"] = str(e)

    return health_info


@router.get("/health/database")
async def database_health_check(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Database health check

    Checks PostgreSQL database health and statistics
    """
    health_info = {
        "timestamp": datetime.now().isoformat(),
        "status": "unknown"
    }

    try:
        from sqlalchemy import text
        from models.kline import Kline
        from models.technical_indicator import TechnicalIndicator

        # Test connection
        result = await db.execute(text("SELECT version()"))
        version = result.fetchone()[0]

        # Get table statistics
        kline_count_result = await db.execute(
            text("SELECT COUNT(*) FROM klines")
        )
        kline_count = kline_count_result.fetchone()[0]

        indicator_count_result = await db.execute(
            text("SELECT COUNT(*) FROM technical_indicators")
        )
        indicator_count = indicator_count_result.fetchone()[0]

        health_info.update({
            "status": "healthy",
            "database_version": version,
            "table_stats": {
                "klines_count": kline_count,
                "indicators_count": indicator_count
            }
        })

    except Exception as e:
        health_info["status"] = "unhealthy"
        health_info["error"] = str(e)

    return health_info
