"""
Market Data API Routes
Provides endpoints for K-line data and technical indicators
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from core.redis_client import get_redis, RedisClient
from services.ccxt_manager import get_ccxt_manager, CCXTManager
from services.rate_limit_handler import get_rate_limit_handler, RateLimitHandler
from services.market_data_scheduler import get_market_data_scheduler, MarketDataScheduler
from services.system_config_service import get_system_config_service, SystemConfigService
from api.v1.auth import get_current_user
from models.user import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Global instances (will be injected during startup)
_ccxt_manager: Optional[CCXTManager] = None
_rate_limit_handler: Optional[RateLimitHandler] = None
_market_data_scheduler: Optional[MarketDataScheduler] = None


# Response models
class KlineResponse(BaseModel):
    """K-line data response"""
    exchange: str
    symbol: str
    timeframe: str
    data: List[List]  # [[timestamp, open, high, low, close, volume], ...]
    source: str  # "redis", "database", or "api"
    count: int

    class Config:
        json_schema_extra = {
            "example": {
                "exchange": "binance",
                "symbol": "BTC/USDT",
                "timeframe": "1h",
                "data": [[1634567890000, 45000.0, 45100.0, 44900.0, 45050.0, 1234.5]],
                "source": "redis",
                "count": 1
            }
        }


class IndicatorResponse(BaseModel):
    """Technical indicator response"""
    exchange: str
    symbol: str
    timeframe: str
    indicator_type: str
    indicator_params: Optional[Dict[str, Any]] = None
    indicator_values: Dict[str, Any]
    timestamp: str
    source: str

    class Config:
        json_schema_extra = {
            "example": {
                "exchange": "binance",
                "symbol": "BTC/USDT",
                "timeframe": "1h",
                "indicator_type": "MA",
                "indicator_params": {"periods": [5, 10, 20, 30]},
                "indicator_values": {"ma5": 45000.0, "ma10": 44950.0},
                "timestamp": "2025-10-18T10:00:00",
                "source": "database"
            }
        }


class AllIndicatorsResponse(BaseModel):
    """All indicators response"""
    exchange: str
    symbol: str
    timeframe: str
    indicators: Dict[str, Any]  # {"MA": {...}, "MACD": {...}, ...}


# Dependencies
async def get_handler(
    db: AsyncSession = Depends(get_db),
    redis_client: RedisClient = Depends(get_redis)
) -> RateLimitHandler:
    """Get rate limit handler instance"""
    global _ccxt_manager, _rate_limit_handler

    if _rate_limit_handler:
        return _rate_limit_handler

    # Create CCXT manager if needed
    if not _ccxt_manager:
        _ccxt_manager = await get_ccxt_manager(db)

    # Create rate limit handler
    _rate_limit_handler = await get_rate_limit_handler(
        db, redis_client, _ccxt_manager
    )

    return _rate_limit_handler


# K-line endpoints
@router.get("/market/klines", response_model=KlineResponse)
async def get_klines(
    symbol: str = Query(..., description="Trading pair symbol (e.g., BTC/USDT)"),
    timeframe: str = Query(..., description="Timeframe (1m, 5m, 15m, 1h, 4h, 1d)"),
    exchange: str = Query("binance", description="Exchange name"),
    limit: int = Query(200, description="Number of candles to fetch", ge=1, le=1000),
    force_refresh: bool = Query(False, description="Force refresh from API"),
    handler: RateLimitHandler = Depends(get_handler),
    current_user: User = Depends(get_current_user)
):
    """
    Get K-line (OHLCV) data

    Returns K-line data from three-layer architecture:
    1. Redis cache (fastest)
    2. PostgreSQL database (persistent)
    3. CCXT API (live data)
    """
    try:
        ohlcv_data, source = await handler.get_klines(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            limit=limit,
            force_refresh=force_refresh
        )

        return KlineResponse(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            data=ohlcv_data,
            source=source,
            count=len(ohlcv_data)
        )

    except Exception as e:
        logger.error(f"Failed to get klines: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Indicator endpoints
@router.get("/market/indicators/{indicator_type}", response_model=IndicatorResponse)
async def get_indicator(
    indicator_type: str,
    symbol: str = Query(..., description="Trading pair symbol (e.g., BTC/USDT)"),
    timeframe: str = Query(..., description="Timeframe (1m, 5m, 15m, 1h, 4h, 1d)"),
    exchange: str = Query("binance", description="Exchange name"),
    force_refresh: bool = Query(False, description="Force recalculate indicator"),
    handler: RateLimitHandler = Depends(get_handler),
    current_user: User = Depends(get_current_user)
):
    """
    Get technical indicator data

    Supported indicators:
    - MA: Moving Average
    - MACD: Moving Average Convergence Divergence
    - RSI: Relative Strength Index
    - BOLL: Bollinger Bands
    - VOL: Volume
    """
    try:
        # Validate indicator type
        valid_indicators = ["MA", "MACD", "RSI", "BOLL", "VOL"]
        if indicator_type.upper() not in valid_indicators:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid indicator type. Must be one of: {', '.join(valid_indicators)}"
            )

        indicator_data, source = await handler.get_indicators(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            indicator_type=indicator_type.upper(),
            force_refresh=force_refresh
        )

        if not indicator_data:
            raise HTTPException(status_code=404, detail="Indicator data not found")

        # Convert timestamp to string if it's a datetime object
        timestamp = indicator_data.get('timestamp')
        if isinstance(timestamp, datetime):
            timestamp = timestamp.isoformat()

        return IndicatorResponse(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            indicator_type=indicator_data['indicator_type'],
            indicator_params=indicator_data.get('indicator_params'),
            indicator_values=indicator_data['indicator_values'],
            timestamp=timestamp,
            source=source
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get indicator: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market/indicators", response_model=AllIndicatorsResponse)
async def get_all_indicators(
    symbol: str = Query(..., description="Trading pair symbol (e.g., BTC/USDT)"),
    timeframe: str = Query(..., description="Timeframe (1m, 5m, 15m, 1h, 4h, 1d)"),
    exchange: str = Query("binance", description="Exchange name"),
    force_refresh: bool = Query(False, description="Force recalculate indicators"),
    handler: RateLimitHandler = Depends(get_handler),
    current_user: User = Depends(get_current_user)
):
    """
    Get all technical indicators for a symbol

    Returns MA, MACD, RSI, BOLL, and VOL indicators
    """
    try:
        indicators = {}
        indicator_types = ["MA", "MACD", "RSI", "BOLL", "VOL"]

        for indicator_type in indicator_types:
            try:
                indicator_data, _ = await handler.get_indicators(
                    exchange=exchange,
                    symbol=symbol,
                    timeframe=timeframe,
                    indicator_type=indicator_type,
                    force_refresh=force_refresh
                )

                if indicator_data:
                    # Convert timestamp to string
                    if isinstance(indicator_data.get('timestamp'), datetime):
                        indicator_data['timestamp'] = indicator_data['timestamp'].isoformat()

                    indicators[indicator_type] = indicator_data

            except Exception as e:
                logger.warning(f"Failed to get {indicator_type} indicator: {e}")
                # Continue with other indicators

        return AllIndicatorsResponse(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            indicators=indicators
        )

    except Exception as e:
        logger.error(f"Failed to get all indicators: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Exchange endpoints
@router.get("/market/exchanges")
async def get_supported_exchanges(
    current_user: User = Depends(get_current_user)
):
    """Get list of supported exchanges"""
    global _ccxt_manager

    if not _ccxt_manager:
        db = await get_db().__anext__()
        _ccxt_manager = await get_ccxt_manager(db)

    return {
        "exchanges": _ccxt_manager.get_supported_exchanges()
    }


@router.get("/market/timeframes")
async def get_supported_timeframes(
    current_user: User = Depends(get_current_user)
):
    """Get list of supported timeframes"""
    global _ccxt_manager

    if not _ccxt_manager:
        db = await get_db().__anext__()
        _ccxt_manager = await get_ccxt_manager(db)

    return {
        "timeframes": _ccxt_manager.get_supported_timeframes()
    }


# Scheduler endpoints
@router.post("/market/scheduler/start")
async def start_scheduler(
    db: AsyncSession = Depends(get_db),
    redis_client: RedisClient = Depends(get_redis),
    current_user: User = Depends(get_current_user)
):
    """Start market data scheduler"""
    global _market_data_scheduler, _rate_limit_handler

    try:
        if not _market_data_scheduler:
            # Create dependencies
            if not _rate_limit_handler:
                handler = await get_handler(db, redis_client)
            else:
                handler = _rate_limit_handler

            config_service = await get_system_config_service(db)

            # Create scheduler
            _market_data_scheduler = await get_market_data_scheduler(
                db, handler, config_service
            )

        await _market_data_scheduler.start()

        return {
            "message": "Market data scheduler started successfully",
            "status": _market_data_scheduler.get_job_status()
        }

    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/market/scheduler/stop")
async def stop_scheduler(
    current_user: User = Depends(get_current_user)
):
    """Stop market data scheduler"""
    global _market_data_scheduler

    try:
        if not _market_data_scheduler:
            raise HTTPException(status_code=400, detail="Scheduler is not initialized")

        await _market_data_scheduler.stop()

        return {
            "message": "Market data scheduler stopped successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop scheduler: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market/scheduler/status")
async def get_scheduler_status(
    current_user: User = Depends(get_current_user)
):
    """Get market data scheduler status"""
    global _market_data_scheduler

    if not _market_data_scheduler:
        return {
            "is_running": False,
            "message": "Scheduler not initialized"
        }

    return _market_data_scheduler.get_job_status()


@router.post("/market/scheduler/trigger")
async def trigger_manual_update(
    symbol: Optional[str] = Query(None, description="Specific symbol to update"),
    timeframe: Optional[str] = Query(None, description="Specific timeframe to update"),
    current_user: User = Depends(get_current_user)
):
    """Trigger manual market data update"""
    global _market_data_scheduler

    try:
        if not _market_data_scheduler:
            raise HTTPException(status_code=400, detail="Scheduler is not initialized")

        await _market_data_scheduler.trigger_manual_update(symbol, timeframe)

        return {
            "message": "Manual update triggered successfully",
            "symbol": symbol or "all",
            "timeframe": timeframe or "all"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to trigger manual update: {e}")
        raise HTTPException(status_code=500, detail=str(e))
