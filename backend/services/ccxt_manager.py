"""
CCXT Exchange Manager Service
Manages cryptocurrency exchange connections and data fetching
"""
from typing import Dict, List, Optional, Any
import ccxt.async_support as ccxt
from datetime import datetime, timedelta
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.proxy import Proxy

logger = logging.getLogger(__name__)


class CCXTManager:
    """Cryptocurrency exchange manager using CCXT library"""

    # Exchange class mapping
    EXCHANGE_CLASSES = {
        "binance": ccxt.binance,
        "okx": ccxt.okx,
        "bybit": ccxt.bybit,
        "bitget": ccxt.bitget,
    }

    # Timeframe mapping (system -> CCXT)
    TIMEFRAME_MAP = {
        "1m": "1m",
        "5m": "5m",
        "15m": "15m",
        "1h": "1h",
        "4h": "4h",
        "1d": "1d",
    }

    def __init__(self, db: AsyncSession):
        self.db = db
        self.exchanges: Dict[str, ccxt.Exchange] = {}
        self._proxy_config: Optional[Dict[str, str]] = None

    async def initialize_exchange(
        self,
        exchange_name: str,
        use_proxy: bool = True,
        config: Optional[Dict[str, Any]] = None
    ) -> ccxt.Exchange:
        """
        Initialize an exchange client

        Args:
            exchange_name: Exchange name (binance, okx, bybit, bitget)
            use_proxy: Whether to use proxy
            config: Additional exchange configuration

        Returns:
            Initialized CCXT exchange instance

        Raises:
            ValueError: If exchange is not supported
        """
        if exchange_name not in self.EXCHANGE_CLASSES:
            raise ValueError(f"Unsupported exchange: {exchange_name}")

        # Check if already initialized
        if exchange_name in self.exchanges:
            return self.exchanges[exchange_name]

        try:
            # Get exchange class
            exchange_class = self.EXCHANGE_CLASSES[exchange_name]

            # Build exchange configuration
            exchange_config = {
                "enableRateLimit": True,
                "timeout": 30000,  # 30 seconds
            }

            # Add proxy if enabled
            if use_proxy:
                proxy = await self._get_healthy_proxy()
                if proxy:
                    self._proxy_config = self._build_proxy_config(proxy)
                    exchange_config.update(self._proxy_config)
                    logger.info(f"Using proxy for {exchange_name}: {proxy.host}:{proxy.port}")
                else:
                    logger.warning(f"No healthy proxy found, using direct connection for {exchange_name}")

            # Merge custom config
            if config:
                exchange_config.update(config)

            # Initialize exchange
            exchange = exchange_class(exchange_config)

            # Load markets
            await exchange.load_markets()

            # Store instance
            self.exchanges[exchange_name] = exchange

            logger.info(f"Exchange {exchange_name} initialized successfully")
            return exchange

        except Exception as e:
            logger.error(f"Failed to initialize exchange {exchange_name}: {e}")
            raise

    async def fetch_ohlcv(
        self,
        exchange_name: str,
        symbol: str,
        timeframe: str,
        limit: int = 200,
        since: Optional[int] = None
    ) -> List[List]:
        """
        Fetch OHLCV (K-line) data from exchange

        Args:
            exchange_name: Exchange name
            symbol: Trading pair symbol (e.g., BTC/USDT)
            timeframe: Timeframe (1m, 5m, 15m, 1h, 4h, 1d)
            limit: Number of candles to fetch
            since: Timestamp in milliseconds to fetch from

        Returns:
            List of OHLCV data: [[timestamp, open, high, low, close, volume], ...]

        Raises:
            ccxt.RateLimitExceeded: If rate limit is hit
            ccxt.NetworkError: If network error occurs
        """
        try:
            # Get or initialize exchange
            exchange = self.exchanges.get(exchange_name)
            if not exchange:
                exchange = await self.initialize_exchange(exchange_name)

            # Convert timeframe
            ccxt_timeframe = self.TIMEFRAME_MAP.get(timeframe, timeframe)

            # Fetch OHLCV data
            ohlcv = await exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe=ccxt_timeframe,
                limit=limit,
                since=since
            )

            logger.debug(
                f"Fetched {len(ohlcv)} candles from {exchange_name} "
                f"for {symbol} {timeframe}"
            )

            return ohlcv

        except ccxt.RateLimitExceeded as e:
            logger.warning(f"Rate limit exceeded for {exchange_name}: {e}")
            raise
        except ccxt.NetworkError as e:
            logger.error(f"Network error for {exchange_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to fetch OHLCV from {exchange_name}: {e}")
            raise

    async def fetch_ticker(
        self,
        exchange_name: str,
        symbol: str
    ) -> Dict[str, Any]:
        """
        Fetch current ticker data for a symbol

        Args:
            exchange_name: Exchange name
            symbol: Trading pair symbol (e.g., BTC/USDT)

        Returns:
            Ticker data dictionary containing bid, ask, last price, etc.
        """
        try:
            # Get or initialize exchange
            exchange = self.exchanges.get(exchange_name)
            if not exchange:
                exchange = await self.initialize_exchange(exchange_name)

            # Fetch ticker
            ticker = await exchange.fetch_ticker(symbol)

            logger.debug(f"Fetched ticker from {exchange_name} for {symbol}")
            return ticker

        except Exception as e:
            logger.error(f"Failed to fetch ticker from {exchange_name}: {e}")
            raise

    async def test_exchange_connection(self, exchange_name: str) -> bool:
        """
        Test exchange connection health

        Args:
            exchange_name: Exchange name to test

        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            # Get or initialize exchange
            exchange = self.exchanges.get(exchange_name)
            if not exchange:
                exchange = await self.initialize_exchange(exchange_name)

            # Test by fetching BTC/USDT ticker
            await exchange.fetch_ticker("BTC/USDT")

            logger.info(f"Exchange {exchange_name} connection test passed")
            return True

        except Exception as e:
            logger.error(f"Exchange {exchange_name} connection test failed: {e}")
            return False

    async def close_exchange(self, exchange_name: str) -> None:
        """
        Close an exchange connection

        Args:
            exchange_name: Exchange name to close
        """
        if exchange_name in self.exchanges:
            try:
                await self.exchanges[exchange_name].close()
                del self.exchanges[exchange_name]
                logger.info(f"Exchange {exchange_name} closed")
            except Exception as e:
                logger.error(f"Failed to close exchange {exchange_name}: {e}")

    async def close_all_exchanges(self) -> None:
        """Close all exchange connections"""
        for exchange_name in list(self.exchanges.keys()):
            await self.close_exchange(exchange_name)

    async def _get_healthy_proxy(self) -> Optional[Proxy]:
        """
        Get a healthy proxy from database

        Returns:
            Healthy Proxy object or None
        """
        try:
            # Query for healthy proxies ordered by priority
            result = await self.db.execute(
                select(Proxy)
                .where(Proxy.is_active == True)
                .where(Proxy.is_healthy == True)
                .order_by(Proxy.priority.asc())
                .limit(1)
            )
            proxy = result.scalar_one_or_none()

            return proxy

        except Exception as e:
            logger.error(f"Failed to get healthy proxy: {e}")
            return None

    def _build_proxy_config(self, proxy: Proxy) -> Dict[str, str]:
        """
        Build proxy configuration for CCXT

        Args:
            proxy: Proxy object

        Returns:
            Proxy configuration dictionary
        """
        # Build proxy URL based on type
        if proxy.proxy_type == "http":
            proxy_url = f"http://{proxy.host}:{proxy.port}"
        elif proxy.proxy_type == "https":
            proxy_url = f"https://{proxy.host}:{proxy.port}"
        elif proxy.proxy_type == "socks5":
            proxy_url = f"socks5://{proxy.host}:{proxy.port}"
        else:
            proxy_url = f"http://{proxy.host}:{proxy.port}"

        # Add authentication if credentials provided
        if proxy.username and proxy.password:
            protocol = proxy.proxy_type if proxy.proxy_type in ["http", "https", "socks5"] else "http"
            proxy_url = f"{protocol}://{proxy.username}:{proxy.password}@{proxy.host}:{proxy.port}"

        # For async CCXT with aiohttp, use 'aiohttp_proxy' parameter
        return {
            "aiohttp_proxy": proxy_url,
        }

    def get_supported_exchanges(self) -> List[str]:
        """
        Get list of supported exchanges

        Returns:
            List of exchange names
        """
        return list(self.EXCHANGE_CLASSES.keys())

    def get_supported_timeframes(self) -> List[str]:
        """
        Get list of supported timeframes

        Returns:
            List of timeframe strings
        """
        return list(self.TIMEFRAME_MAP.keys())


async def get_ccxt_manager(db: AsyncSession) -> CCXTManager:
    """
    Dependency injection for CCXTManager

    Args:
        db: Database session

    Returns:
        CCXTManager instance
    """
    return CCXTManager(db)
