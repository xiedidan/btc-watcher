"""
Rate Limit Handler Service
Implements three-layer data access: Redis -> PostgreSQL -> CCXT API
Handles rate limiting gracefully with automatic fallback
"""
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import json
import ccxt
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from core.redis_client import RedisClient
from models.kline import Kline
from models.technical_indicator import TechnicalIndicator
from services.ccxt_manager import CCXTManager
from services.indicator_calculator import IndicatorCalculator
from services.exchange_failover_manager import ExchangeFailoverManager

logger = logging.getLogger(__name__)


class DataSource:
    """Data source enum"""
    REDIS = "redis"
    DATABASE = "database"
    API = "api"


class RateLimitHandler:
    """
    Rate limit handler with three-layer data access
    Layer 1: Redis (fastest, cached)
    Layer 2: PostgreSQL (persistent storage)
    Layer 3: CCXT API (live data, may hit rate limits)
    """

    def __init__(
        self,
        db: AsyncSession,
        redis_client: RedisClient,
        ccxt_manager: CCXTManager,
        failover_manager: Optional[ExchangeFailoverManager] = None,
        cache_ttl: Optional[Dict[str, int]] = None
    ):
        self.db = db
        self.redis = redis_client
        self.ccxt_manager = ccxt_manager
        self.failover_manager = failover_manager
        self.indicator_calculator = IndicatorCalculator()

        # Default cache TTL by timeframe (in seconds)
        self.cache_ttl = cache_ttl or {
            "1m": 60,
            "5m": 300,
            "15m": 900,
            "1h": 3600,
            "4h": 14400,
            "1d": 86400
        }

    async def get_klines(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        limit: int = 200,
        force_refresh: bool = False
    ) -> Tuple[List[List], str]:
        """
        Get K-line data with three-layer fallback

        Args:
            exchange: Exchange name
            symbol: Trading pair symbol
            timeframe: Timeframe
            limit: Number of candles
            force_refresh: Force refresh from API

        Returns:
            Tuple of (OHLCV data list, data source)
        """
        cache_key = self._build_kline_cache_key(exchange, symbol, timeframe)

        # Layer 1: Try Redis cache (if not force refresh)
        if not force_refresh:
            cached_data = await self._get_klines_from_redis(cache_key)
            # 检查缓存数据是否充足（至少80%的请求数量）
            if cached_data and len(cached_data) >= limit * 0.8:
                logger.debug(f"K-line data from Redis: {exchange} {symbol} {timeframe} ({len(cached_data)} candles)")
                return cached_data, DataSource.REDIS
            elif cached_data:
                logger.warning(
                    f"Redis cache data insufficient for {exchange} {symbol} {timeframe}: "
                    f"got {len(cached_data)} candles, need at least {int(limit * 0.8)}, falling back to database"
                )

        # Layer 2: Try PostgreSQL database
        db_data = await self._get_klines_from_database(exchange, symbol, timeframe, limit)
        if db_data and len(db_data) >= limit * 0.8:  # At least 80% of requested data
            logger.debug(f"K-line data from database: {exchange} {symbol} {timeframe}")
            # Cache to Redis
            await self._cache_klines_to_redis(cache_key, db_data, timeframe)
            return db_data, DataSource.DATABASE

        # Layer 3: Fetch from CCXT API
        try:
            # Use failover manager if available
            if self.failover_manager:
                healthy_exchange = await self.failover_manager.get_healthy_exchange(exchange)
                if healthy_exchange:
                    exchange = healthy_exchange

            # Fetch from API
            api_data = await self.ccxt_manager.fetch_ohlcv(
                exchange_name=exchange,
                symbol=symbol,
                timeframe=timeframe,
                limit=limit
            )

            logger.info(f"K-line data from API: {exchange} {symbol} {timeframe}")

            # Mark exchange as successful
            if self.failover_manager:
                await self.failover_manager.mark_exchange_result(exchange, True)

            # Store to database
            await self._store_klines_to_database(exchange, symbol, timeframe, api_data)

            # Cache to Redis
            await self._cache_klines_to_redis(cache_key, api_data, timeframe)

            return api_data, DataSource.API

        except ccxt.RateLimitExceeded as e:
            logger.warning(f"Rate limit exceeded for {exchange}: {e}")

            # Mark exchange as failed
            if self.failover_manager:
                await self.failover_manager.mark_exchange_result(exchange, False, str(e))

            # Fallback to database data even if incomplete
            if db_data:
                logger.info("Falling back to database data due to rate limit")
                return db_data, DataSource.DATABASE

            raise

        except Exception as e:
            logger.error(f"Failed to fetch from API: {e}")

            # Mark exchange as failed
            if self.failover_manager:
                await self.failover_manager.mark_exchange_result(exchange, False, str(e))

            # Fallback to database data
            if db_data:
                logger.info("Falling back to database data due to API error")
                return db_data, DataSource.DATABASE

            raise

    async def get_indicators(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        indicator_type: str,
        force_refresh: bool = False
    ) -> Tuple[Optional[Dict[str, Any]], str]:
        """
        Get technical indicator data with three-layer fallback

        Args:
            exchange: Exchange name
            symbol: Trading pair symbol
            timeframe: Timeframe
            indicator_type: Indicator type (MA, MACD, RSI, BOLL, VOL)
            force_refresh: Force recalculate from OHLCV

        Returns:
            Tuple of (indicator data dict, data source)
        """
        cache_key = self._build_indicator_cache_key(exchange, symbol, timeframe, indicator_type)

        # Layer 1: Try Redis cache
        if not force_refresh:
            cached_data = await self._get_indicator_from_redis(cache_key)
            if cached_data:
                logger.debug(f"Indicator from Redis: {exchange} {symbol} {timeframe} {indicator_type}")
                return cached_data, DataSource.REDIS

        # Layer 2: Try PostgreSQL database
        db_data = await self._get_indicator_from_database(exchange, symbol, timeframe, indicator_type)
        if db_data:
            logger.debug(f"Indicator from database: {exchange} {symbol} {timeframe} {indicator_type}")
            # Cache to Redis
            await self._cache_indicator_to_redis(cache_key, db_data, timeframe)
            return db_data, DataSource.DATABASE

        # Layer 3: Calculate from OHLCV data
        try:
            # Get OHLCV data (will use three-layer fallback)
            ohlcv_data, _ = await self.get_klines(exchange, symbol, timeframe, limit=200)

            # Calculate indicator
            if indicator_type == "MA":
                indicator_data = self.indicator_calculator.calculate_ma(ohlcv_data)
            elif indicator_type == "MACD":
                indicator_data = self.indicator_calculator.calculate_macd(ohlcv_data)
            elif indicator_type == "RSI":
                indicator_data = self.indicator_calculator.calculate_rsi(ohlcv_data)
            elif indicator_type == "BOLL":
                indicator_data = self.indicator_calculator.calculate_bollinger_bands(ohlcv_data)
            elif indicator_type == "VOL":
                indicator_data = self.indicator_calculator.calculate_volume(ohlcv_data)
            else:
                raise ValueError(f"Unsupported indicator type: {indicator_type}")

            logger.info(f"Calculated indicator: {exchange} {symbol} {timeframe} {indicator_type}")

            # Store to database
            await self._store_indicator_to_database(exchange, symbol, timeframe, indicator_data)

            # Cache to Redis
            await self._cache_indicator_to_redis(cache_key, indicator_data, timeframe)

            return indicator_data, DataSource.API

        except Exception as e:
            logger.error(f"Failed to calculate indicator: {e}")
            return None, ""

    # Redis operations
    async def _get_klines_from_redis(self, cache_key: str) -> Optional[List[List]]:
        """Get K-line data from Redis"""
        try:
            if not self.redis.is_connected():
                return None

            cached = await self.redis.get(cache_key)
            if cached:
                return json.loads(cached)
            return None
        except Exception as e:
            logger.error(f"Redis get klines error: {e}")
            return None

    async def _cache_klines_to_redis(
        self,
        cache_key: str,
        data: List[List],
        timeframe: str
    ) -> bool:
        """Cache K-line data to Redis"""
        try:
            if not self.redis.is_connected():
                return False

            ttl = self.cache_ttl.get(timeframe, 300)
            await self.redis.set(cache_key, json.dumps(data), expire_seconds=ttl)
            return True
        except Exception as e:
            logger.error(f"Redis cache klines error: {e}")
            return False

    async def _get_indicator_from_redis(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get indicator data from Redis"""
        try:
            if not self.redis.is_connected():
                return None

            cached = await self.redis.get(cache_key)
            if cached:
                data = json.loads(cached)
                # 确保兼容性：如果没有values字段，从indicator_values复制
                if data and 'indicator_values' in data and 'values' not in data:
                    data['values'] = data['indicator_values']
                return data
            return None
        except Exception as e:
            logger.error(f"Redis get indicator error: {e}")
            return None

    async def _cache_indicator_to_redis(
        self,
        cache_key: str,
        data: Dict[str, Any],
        timeframe: str
    ) -> bool:
        """Cache indicator data to Redis"""
        try:
            if not self.redis.is_connected():
                return False

            ttl = self.cache_ttl.get(timeframe, 300)
            # Convert datetime to string for JSON serialization
            data_copy = data.copy()
            if 'timestamp' in data_copy and isinstance(data_copy['timestamp'], datetime):
                data_copy['timestamp'] = data_copy['timestamp'].isoformat()

            await self.redis.set(cache_key, json.dumps(data_copy), expire_seconds=ttl)
            return True
        except Exception as e:
            logger.error(f"Redis cache indicator error: {e}")
            return False

    # Database operations
    async def _get_klines_from_database(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        limit: int
    ) -> Optional[List[List]]:
        """Get K-line data from PostgreSQL"""
        try:
            # Query latest klines
            result = await self.db.execute(
                select(Kline)
                .where(
                    and_(
                        Kline.exchange == exchange,
                        Kline.symbol == symbol,
                        Kline.timeframe == timeframe
                    )
                )
                .order_by(Kline.timestamp.desc())
                .limit(limit)
            )
            klines = result.scalars().all()

            if not klines:
                return None

            # Convert to OHLCV list format and reverse (oldest first)
            ohlcv_data = [k.to_ohlcv_list() for k in reversed(klines)]
            return ohlcv_data

        except Exception as e:
            logger.error(f"Database get klines error: {e}")
            return None

    async def _store_klines_to_database(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        ohlcv_data: List[List]
    ) -> bool:
        """Store K-line data to PostgreSQL"""
        try:
            for candle in ohlcv_data:
                timestamp_ms, open_price, high, low, close, volume = candle
                timestamp = datetime.fromtimestamp(timestamp_ms / 1000)

                # Check if already exists
                result = await self.db.execute(
                    select(Kline).where(
                        and_(
                            Kline.exchange == exchange,
                            Kline.symbol == symbol,
                            Kline.timeframe == timeframe,
                            Kline.timestamp == timestamp
                        )
                    )
                )
                existing = result.scalar_one_or_none()

                if not existing:
                    kline = Kline(
                        exchange=exchange,
                        symbol=symbol,
                        timeframe=timeframe,
                        timestamp=timestamp,
                        open=open_price,
                        high=high,
                        low=low,
                        close=close,
                        volume=volume
                    )
                    self.db.add(kline)

            await self.db.commit()
            logger.debug(f"Stored {len(ohlcv_data)} klines to database")
            return True

        except Exception as e:
            logger.error(f"Database store klines error: {e}")
            await self.db.rollback()
            return False

    async def _get_indicator_from_database(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        indicator_type: str
    ) -> Optional[Dict[str, Any]]:
        """Get indicator data from PostgreSQL"""
        try:
            # Query latest indicator
            result = await self.db.execute(
                select(TechnicalIndicator)
                .where(
                    and_(
                        TechnicalIndicator.exchange == exchange,
                        TechnicalIndicator.symbol == symbol,
                        TechnicalIndicator.timeframe == timeframe,
                        TechnicalIndicator.indicator_type == indicator_type
                    )
                )
                .order_by(TechnicalIndicator.timestamp.desc())
                .limit(1)
            )
            indicator = result.scalar_one_or_none()

            if not indicator:
                return None

            # 确保返回的数据结构和indicator_calculator一致
            return {
                "indicator_type": indicator.indicator_type,
                "indicator_params": indicator.indicator_params,
                "indicator_values": indicator.indicator_values,
                "values": indicator.indicator_values,  # 前端兼容字段
                "timestamp": indicator.timestamp
            }

        except Exception as e:
            logger.error(f"Database get indicator error: {e}")
            return None

    async def _store_indicator_to_database(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        indicator_data: Dict[str, Any]
    ) -> bool:
        """Store indicator data to PostgreSQL"""
        try:
            timestamp = indicator_data.get('timestamp')
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)

            # Check if already exists
            result = await self.db.execute(
                select(TechnicalIndicator).where(
                    and_(
                        TechnicalIndicator.exchange == exchange,
                        TechnicalIndicator.symbol == symbol,
                        TechnicalIndicator.timeframe == timeframe,
                        TechnicalIndicator.timestamp == timestamp,
                        TechnicalIndicator.indicator_type == indicator_data['indicator_type']
                    )
                )
            )
            existing = result.scalar_one_or_none()

            if not existing:
                indicator = TechnicalIndicator(
                    exchange=exchange,
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=timestamp,
                    indicator_type=indicator_data['indicator_type'],
                    indicator_params=indicator_data.get('indicator_params'),
                    indicator_values=indicator_data['indicator_values']
                )
                self.db.add(indicator)
                await self.db.commit()
                logger.debug(f"Stored indicator to database: {indicator_data['indicator_type']}")

            return True

        except Exception as e:
            logger.error(f"Database store indicator error: {e}")
            await self.db.rollback()
            return False

    # Cache key builders
    def _build_kline_cache_key(self, exchange: str, symbol: str, timeframe: str) -> str:
        """Build Redis cache key for K-line data"""
        return f"kline:{exchange}:{symbol}:{timeframe}"

    def _build_indicator_cache_key(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        indicator_type: str
    ) -> str:
        """Build Redis cache key for indicator data"""
        return f"indicator:{exchange}:{symbol}:{timeframe}:{indicator_type}"


async def get_rate_limit_handler(
    db: AsyncSession,
    redis_client: RedisClient,
    ccxt_manager: CCXTManager,
    failover_manager: Optional[ExchangeFailoverManager] = None,
    cache_ttl: Optional[Dict[str, int]] = None
) -> RateLimitHandler:
    """
    Factory function for RateLimitHandler

    Args:
        db: Database session
        redis_client: Redis client
        ccxt_manager: CCXT manager
        failover_manager: Exchange failover manager
        cache_ttl: Cache TTL configuration

    Returns:
        RateLimitHandler instance
    """
    return RateLimitHandler(db, redis_client, ccxt_manager, failover_manager, cache_ttl)
