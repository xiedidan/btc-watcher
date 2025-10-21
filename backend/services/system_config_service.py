"""
System Configuration Service
Manages system-level configuration including market data settings
"""
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.system_config import SystemConfig
import logging

logger = logging.getLogger(__name__)


class SystemConfigService:
    """System configuration management service"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_market_data_config(self) -> Dict[str, Any]:
        """
        Get market data configuration

        Returns:
            Dict containing market data configuration
        """
        try:
            # Query system config (singleton)
            result = await self.db.execute(
                select(SystemConfig).where(SystemConfig.id == 1)
            )
            config = result.scalar_one_or_none()

            # Create default config if not exists
            if not config:
                logger.info("System config not found, creating default configuration")
                config = await self._create_default_config()

            return config.market_data

        except Exception as e:
            logger.error(f"Failed to get market data config: {e}")
            # Return default config on error
            return self._get_default_market_data_config()

    async def update_market_data_config(self, config_update: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update market data configuration (deep merge)

        Args:
            config_update: Configuration updates to apply

        Returns:
            Updated configuration
        """
        try:
            # Get existing config
            result = await self.db.execute(
                select(SystemConfig).where(SystemConfig.id == 1)
            )
            config = result.scalar_one_or_none()

            # Create if not exists
            if not config:
                config = await self._create_default_config()

            # Deep merge configuration
            current_config = config.market_data.copy()
            merged_config = self._deep_merge(current_config, config_update)

            # Validate configuration
            self._validate_config(merged_config)

            # Update configuration
            config.market_data = merged_config
            await self.db.commit()
            await self.db.refresh(config)

            logger.info("Market data configuration updated successfully")
            return config.market_data

        except ValueError as e:
            logger.error(f"Invalid configuration: {e}")
            await self.db.rollback()
            raise
        except Exception as e:
            logger.error(f"Failed to update market data config: {e}")
            await self.db.rollback()
            raise

    async def get_full_config(self) -> SystemConfig:
        """
        Get full system configuration object

        Returns:
            SystemConfig object
        """
        try:
            result = await self.db.execute(
                select(SystemConfig).where(SystemConfig.id == 1)
            )
            config = result.scalar_one_or_none()

            if not config:
                config = await self._create_default_config()

            return config

        except Exception as e:
            logger.error(f"Failed to get full system config: {e}")
            raise

    async def _create_default_config(self) -> SystemConfig:
        """
        Create default system configuration

        Returns:
            Created SystemConfig object
        """
        try:
            config = SystemConfig(
                id=1,
                market_data=self._get_default_market_data_config()
            )

            self.db.add(config)
            await self.db.commit()
            await self.db.refresh(config)

            logger.info("Default system configuration created")
            return config

        except Exception as e:
            logger.error(f"Failed to create default config: {e}")
            await self.db.rollback()
            raise

    def _get_default_market_data_config(self) -> Dict[str, Any]:
        """
        Get default market data configuration

        Returns:
            Default configuration dictionary
        """
        return {
            "default_exchange": "binance",
            "enabled_exchanges": ["binance", "okx", "bybit", "bitget"],
            "default_klines_limit": 200,
            "cache_config": {
                "ttl": {
                    "1m": 60,
                    "5m": 300,
                    "15m": 900,
                    "1h": 3600,
                    "4h": 14400,
                    "1d": 86400
                },
                "max_size_mb": 512
            },
            "update_mode": "interval",  # "interval" or "n_periods"
            "update_interval_seconds": 60,  # 每60秒更新一次
            "n_periods": 1,
            "auto_failover": True,
            "rate_limit_fallback": True,
            "auto_start_scheduler": True,  # 自动启动调度器
            "preload_symbols": [  # 预加载的货币对
                "BTC/USDT",
                "ETH/USDT",
                "BNB/USDT",
                "SOL/USDT",
                "ADA/USDT"
            ],
            "preload_timeframes": ["1m", "5m", "15m", "1h", "4h", "1d"],  # 预加载的时间周期
            "historical_data_days": {
                "1m": 7,
                "5m": 30,
                "15m": 30,
                "1h": 90,
                "4h": 365,
                "1d": 365
            }
        }

    def _deep_merge(self, base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep merge two dictionaries

        Args:
            base: Base dictionary
            update: Update dictionary to merge into base

        Returns:
            Merged dictionary
        """
        result = base.copy()

        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Recursively merge nested dictionaries
                result[key] = self._deep_merge(result[key], value)
            else:
                # Override value
                result[key] = value

        return result

    def _validate_config(self, config: Dict[str, Any]) -> None:
        """
        Validate market data configuration

        Args:
            config: Configuration to validate

        Raises:
            ValueError: If configuration is invalid
        """
        # Validate default_exchange
        if "default_exchange" not in config:
            raise ValueError("default_exchange is required")

        if not isinstance(config["default_exchange"], str):
            raise ValueError("default_exchange must be a string")

        # Validate enabled_exchanges
        if "enabled_exchanges" not in config:
            raise ValueError("enabled_exchanges is required")

        if not isinstance(config["enabled_exchanges"], list):
            raise ValueError("enabled_exchanges must be a list")

        if len(config["enabled_exchanges"]) == 0:
            raise ValueError("At least one exchange must be enabled")

        # Validate default_exchange is in enabled_exchanges
        if config["default_exchange"] not in config["enabled_exchanges"]:
            raise ValueError("default_exchange must be in enabled_exchanges list")

        # Validate update_mode
        if "update_mode" in config:
            if config["update_mode"] not in ["interval", "n_periods"]:
                raise ValueError("update_mode must be 'interval' or 'n_periods'")

        # Validate update_interval_seconds
        if "update_interval_seconds" in config:
            if not isinstance(config["update_interval_seconds"], (int, float)):
                raise ValueError("update_interval_seconds must be a number")
            if config["update_interval_seconds"] <= 0:
                raise ValueError("update_interval_seconds must be positive")

        # Validate cache_config TTL values
        if "cache_config" in config and "ttl" in config["cache_config"]:
            ttl = config["cache_config"]["ttl"]
            for timeframe, value in ttl.items():
                if not isinstance(value, int) or value <= 0:
                    raise ValueError(f"cache_config.ttl.{timeframe} must be a positive integer")

        # Validate historical_data_days
        if "historical_data_days" in config:
            historical = config["historical_data_days"]
            for timeframe, value in historical.items():
                if not isinstance(value, int) or value <= 0:
                    raise ValueError(f"historical_data_days.{timeframe} must be a positive integer")

        logger.debug("Configuration validation passed")


async def get_system_config_service(db: AsyncSession) -> SystemConfigService:
    """
    Dependency injection for SystemConfigService

    Args:
        db: Database session

    Returns:
        SystemConfigService instance
    """
    return SystemConfigService(db)
