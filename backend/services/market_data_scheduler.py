"""
Market Data Scheduler Service
Schedules periodic market data updates using APScheduler
"""
from typing import Dict, List, Optional, Callable
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from services.rate_limit_handler import RateLimitHandler
from services.system_config_service import SystemConfigService

logger = logging.getLogger(__name__)


class MarketDataScheduler:
    """
    Market data update scheduler
    Supports two modes:
    1. Fixed interval mode - Update all timeframes at same interval
    2. N-periods mode - Update each timeframe at its native interval
    """

    # Timeframe to seconds mapping for N-periods mode
    TIMEFRAME_SECONDS = {
        "1m": 60,
        "5m": 300,
        "15m": 900,
        "1h": 3600,
        "4h": 14400,
        "1d": 86400,
    }

    def __init__(
        self,
        db: AsyncSession,
        rate_limit_handler: RateLimitHandler,
        config_service: SystemConfigService,
        session_factory: Optional[async_sessionmaker] = None
    ):
        self.db = db  # Keep for config_service compatibility
        self.rate_limit_handler = rate_limit_handler  # Template instance
        self.config_service = config_service
        self.session_factory = session_factory
        self.scheduler = AsyncIOScheduler()
        self.is_running = False

        # Configuration
        self.update_mode = "interval"  # or "n_periods"
        self.update_interval_seconds = 5
        self.default_exchange = "binance"
        self.enabled_exchanges = ["binance"]
        self.symbols = ["BTC/USDT"]
        self.timeframes = ["1m", "5m", "15m", "1h", "4h", "1d"]
        self.indicator_types = ["MA", "MACD", "RSI", "BOLL", "VOL"]

    async def initialize(self):
        """Initialize scheduler with configuration from database"""
        try:
            # Load configuration
            config = await self.config_service.get_market_data_config()

            self.update_mode = config.get("update_mode", "interval")
            self.update_interval_seconds = config.get("update_interval_seconds", 60)
            self.default_exchange = config.get("default_exchange", "binance")
            self.enabled_exchanges = config.get("enabled_exchanges", ["binance"])

            # Load preload symbols and timeframes
            self.symbols = config.get("preload_symbols", ["BTC/USDT"])
            self.timeframes = config.get("preload_timeframes", ["1m", "5m", "15m", "1h", "4h", "1d"])

            logger.info(
                f"Scheduler initialized: mode={self.update_mode}, "
                f"interval={self.update_interval_seconds}s, "
                f"exchange={self.default_exchange}, "
                f"symbols={self.symbols}, "
                f"timeframes={self.timeframes}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize scheduler: {e}")
            # Use default configuration

    async def start(self):
        """Start the scheduler"""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return

        try:
            # Initialize configuration
            await self.initialize()

            if self.update_mode == "interval":
                # Fixed interval mode - one job for all timeframes
                self._schedule_fixed_interval_updates()
            else:
                # N-periods mode - separate job for each timeframe
                self._schedule_n_periods_updates()

            # Start scheduler
            self.scheduler.start()
            self.is_running = True

            logger.info("Market data scheduler started successfully")

        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            raise

    async def stop(self):
        """Stop the scheduler"""
        if not self.is_running:
            logger.warning("Scheduler is not running")
            return

        try:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            logger.info("Market data scheduler stopped")

        except Exception as e:
            logger.error(f"Failed to stop scheduler: {e}")

    def _schedule_fixed_interval_updates(self):
        """Schedule updates in fixed interval mode"""
        trigger = IntervalTrigger(seconds=self.update_interval_seconds)

        self.scheduler.add_job(
            self._update_all_market_data,
            trigger=trigger,
            id="market_data_update_all",
            name="Update all market data",
            replace_existing=True
        )

        logger.info(
            f"Scheduled fixed interval updates: every {self.update_interval_seconds}s"
        )

    def _schedule_n_periods_updates(self):
        """Schedule updates in N-periods mode (one job per timeframe)"""
        for timeframe in self.timeframes:
            interval_seconds = self.TIMEFRAME_SECONDS.get(timeframe)
            if not interval_seconds:
                logger.warning(f"Unknown timeframe: {timeframe}, skipping")
                continue

            trigger = IntervalTrigger(seconds=interval_seconds)

            self.scheduler.add_job(
                self._update_timeframe_data,
                trigger=trigger,
                args=[timeframe],
                id=f"market_data_update_{timeframe}",
                name=f"Update {timeframe} market data",
                replace_existing=True
            )

            logger.info(f"Scheduled {timeframe} updates: every {interval_seconds}s")

    async def _update_all_market_data(self):
        """Update market data for all symbols and timeframes"""
        logger.debug("Starting market data update (all timeframes)")

        success_count = 0
        failure_count = 0

        # Process updates sequentially to avoid database session conflicts
        # This ensures only one database operation at a time
        for symbol in self.symbols:
            for timeframe in self.timeframes:
                try:
                    result = await self._update_symbol_timeframe(symbol, timeframe)
                    if result:
                        success_count += 1
                    else:
                        failure_count += 1
                except Exception as e:
                    logger.error(f"Failed to update {symbol} {timeframe}: {e}")
                    failure_count += 1

        logger.info(
            f"Market data update completed: "
            f"{success_count} success, {failure_count} failed"
        )

    async def _update_timeframe_data(self, timeframe: str):
        """Update market data for specific timeframe"""
        logger.debug(f"Starting market data update ({timeframe})")

        success_count = 0
        failure_count = 0

        # Process updates sequentially to avoid database session conflicts
        for symbol in self.symbols:
            try:
                result = await self._update_symbol_timeframe(symbol, timeframe)
                if result:
                    success_count += 1
                else:
                    failure_count += 1
            except Exception as e:
                logger.error(f"Failed to update {symbol} {timeframe}: {e}")
                failure_count += 1

        logger.debug(
            f"Market data update completed ({timeframe}): "
            f"{success_count} success, {failure_count} failed"
        )

    async def _update_symbol_timeframe(self, symbol: str, timeframe: str) -> bool:
        """
        Update K-line and indicator data for a specific symbol and timeframe

        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe

        Returns:
            True if successful, False otherwise
        """
        try:
            # Fetch K-line data from API to ensure latest data
            # 调度器定时更新应该强制从API获取最新数据，而不是使用可能过时的缓存
            klines, source = await self.rate_limit_handler.get_klines(
                exchange=self.default_exchange,
                symbol=symbol,
                timeframe=timeframe,
                limit=200,
                force_refresh=True  # 强制从API刷新以获取最新数据
            )

            logger.debug(
                f"Updated {symbol} {timeframe} K-lines from {source} "
                f"({len(klines)} candles)"
            )

            # Update indicators
            for indicator_type in self.indicator_types:
                try:
                    indicator_data, ind_source = await self.rate_limit_handler.get_indicators(
                        exchange=self.default_exchange,
                        symbol=symbol,
                        timeframe=timeframe,
                        indicator_type=indicator_type,
                        force_refresh=True  # Force recalculate
                    )

                    if indicator_data:
                        logger.debug(
                            f"Updated {symbol} {timeframe} {indicator_type} "
                            f"from {ind_source}"
                        )

                except Exception as e:
                    logger.error(
                        f"Failed to update indicator {indicator_type} "
                        f"for {symbol} {timeframe}: {e}"
                    )

            return True

        except Exception as e:
            logger.error(
                f"Failed to update market data for {symbol} {timeframe}: {e}"
            )
            return False

    async def update_configuration(self, new_config: Dict):
        """
        Update scheduler configuration dynamically

        Args:
            new_config: New configuration dictionary
        """
        try:
            # Update configuration in database
            await self.config_service.update_market_data_config(new_config)

            # Restart scheduler with new configuration
            if self.is_running:
                await self.stop()
                await self.start()

            logger.info("Scheduler configuration updated successfully")

        except Exception as e:
            logger.error(f"Failed to update scheduler configuration: {e}")
            raise

    def get_job_status(self) -> Dict:
        """
        Get current scheduler status

        Returns:
            Dictionary with scheduler status
        """
        jobs = self.scheduler.get_jobs()

        return {
            "is_running": self.is_running,
            "update_mode": self.update_mode,
            "update_interval_seconds": self.update_interval_seconds,
            "job_count": len(jobs),
            "jobs": [
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None
                }
                for job in jobs
            ]
        }

    async def trigger_manual_update(
        self,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None
    ):
        """
        Trigger manual market data update

        Args:
            symbol: Specific symbol to update (None for all)
            timeframe: Specific timeframe to update (None for all)
        """
        logger.info(f"Manual update triggered: symbol={symbol}, timeframe={timeframe}")

        if symbol and timeframe:
            # Update specific symbol and timeframe
            await self._update_symbol_timeframe(symbol, timeframe)
        elif timeframe:
            # Update specific timeframe for all symbols
            await self._update_timeframe_data(timeframe)
        else:
            # Update all
            await self._update_all_market_data()


async def get_market_data_scheduler(
    db: AsyncSession,
    rate_limit_handler: RateLimitHandler,
    config_service: SystemConfigService
) -> MarketDataScheduler:
    """
    Factory function for MarketDataScheduler

    Args:
        db: Database session
        rate_limit_handler: Rate limit handler instance
        config_service: System config service instance

    Returns:
        MarketDataScheduler instance
    """
    return MarketDataScheduler(db, rate_limit_handler, config_service)
