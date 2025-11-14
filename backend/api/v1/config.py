"""
System Configuration API Routes
Provides endpoints for managing system configuration
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from services.system_config_service import get_system_config_service, SystemConfigService
from api.v1.auth import get_current_user
from models.user import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response models
class MarketDataConfigUpdate(BaseModel):
    """Market data configuration update request"""
    default_exchange: str | None = None
    enabled_exchanges: list[str] | None = None
    default_klines_limit: int | None = None
    update_mode: str | None = None  # "interval" or "n_periods"
    update_interval_seconds: int | None = None
    n_periods: int | None = None
    auto_failover: bool | None = None
    rate_limit_fallback: bool | None = None
    cache_config: Dict[str, Any] | None = None
    historical_data_days: Dict[str, int] | None = None

    class Config:
        json_schema_extra = {
            "example": {
                "default_exchange": "binance",
                "enabled_exchanges": ["binance", "okx", "bybit"],
                "update_mode": "interval",
                "update_interval_seconds": 5,
                "auto_failover": True,
                "rate_limit_fallback": True
            }
        }


class MarketDataConfigResponse(BaseModel):
    """Market data configuration response"""
    default_exchange: str
    enabled_exchanges: list[str]
    default_klines_limit: int
    cache_config: Dict[str, Any]
    update_mode: str
    update_interval_seconds: int
    n_periods: int
    auto_failover: bool
    rate_limit_fallback: bool
    historical_data_days: Dict[str, int]


class SystemConfigResponse(BaseModel):
    """Full system configuration response"""
    id: int
    market_data: Dict[str, Any]
    heartbeat_monitor: Dict[str, Any]
    updated_at: str


# Endpoints
@router.get("/config", response_model=SystemConfigResponse)
async def get_system_config(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get full system configuration

    Returns complete system configuration including market data settings
    """
    try:
        config_service = await get_system_config_service(db)
        config = await config_service.get_full_config()

        return SystemConfigResponse(
            id=config.id,
            market_data=config.market_data,
            heartbeat_monitor=config.heartbeat_monitor,
            updated_at=config.updated_at.isoformat()
        )

    except Exception as e:
        logger.error(f"Failed to get system config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config/market-data", response_model=MarketDataConfigResponse)
async def get_market_data_config(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get market data configuration

    Returns market data specific configuration
    """
    try:
        config_service = await get_system_config_service(db)
        config = await config_service.get_market_data_config()

        return MarketDataConfigResponse(**config)

    except Exception as e:
        logger.error(f"Failed to get market data config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/config/market-data", response_model=MarketDataConfigResponse)
async def update_market_data_config(
    config_update: MarketDataConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update market data configuration

    Updates market data configuration with deep merge.
    Only provided fields will be updated, others remain unchanged.
    """
    try:
        config_service = await get_system_config_service(db)

        # Convert to dict and remove None values
        update_dict = config_update.model_dump(exclude_none=True)

        # Update configuration
        updated_config = await config_service.update_market_data_config(update_dict)

        logger.info(f"Market data configuration updated by user {current_user.id}")

        return MarketDataConfigResponse(**updated_config)

    except ValueError as e:
        logger.warning(f"Invalid configuration update: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update market data config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config/market-data/reset")
async def reset_market_data_config(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Reset market data configuration to defaults

    Resets all market data configuration to default values
    """
    try:
        config_service = await get_system_config_service(db)

        # Get default configuration
        default_config = config_service._get_default_market_data_config()

        # Update with default configuration
        updated_config = await config_service.update_market_data_config(default_config)

        logger.info(f"Market data configuration reset to defaults by user {current_user.id}")

        return {
            "message": "Market data configuration reset to defaults",
            "config": updated_config
        }

    except Exception as e:
        logger.error(f"Failed to reset market data config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config/defaults/market-data")
async def get_default_market_data_config(
    current_user: User = Depends(get_current_user)
):
    """
    Get default market data configuration

    Returns default market data configuration values
    """
    try:
        from services.system_config_service import SystemConfigService

        # Get default config from service class
        config_service = SystemConfigService(None)  # No DB needed for defaults
        default_config = config_service._get_default_market_data_config()

        return {
            "default_config": default_config
        }

    except Exception as e:
        logger.error(f"Failed to get default market data config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Heartbeat Monitor Configuration Models
class HeartbeatMonitorConfigUpdate(BaseModel):
    """Heartbeat monitor configuration update request"""
    enabled: bool | None = None
    default_timeout_seconds: int | None = None
    check_interval_seconds: int | None = None
    auto_restart: bool | None = None
    max_restart_attempts: int | None = None
    restart_cooldown_seconds: int | None = None
    notification_enabled: bool | None = None
    notification_priority: str | None = None

    class Config:
        json_schema_extra = {
            "example": {
                "enabled": True,
                "default_timeout_seconds": 300,
                "check_interval_seconds": 30,
                "auto_restart": True,
                "max_restart_attempts": 3,
                "restart_cooldown_seconds": 60,
                "notification_enabled": True,
                "notification_priority": "P2"
            }
        }


class HeartbeatMonitorConfigResponse(BaseModel):
    """Heartbeat monitor configuration response"""
    enabled: bool
    default_timeout_seconds: int
    check_interval_seconds: int
    auto_restart: bool
    max_restart_attempts: int
    restart_cooldown_seconds: int
    notification_enabled: bool
    notification_priority: str


# Heartbeat Monitor Endpoints
@router.get("/config/heartbeat-monitor", response_model=HeartbeatMonitorConfigResponse)
async def get_heartbeat_monitor_config(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get heartbeat monitor configuration
    
    Returns heartbeat monitor specific configuration
    """
    try:
        config_service = await get_system_config_service(db)
        config = await config_service.get_full_config()
        
        return HeartbeatMonitorConfigResponse(**config.heartbeat_monitor)
    
    except Exception as e:
        logger.error(f"Failed to get heartbeat monitor config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/config/heartbeat-monitor", response_model=HeartbeatMonitorConfigResponse)
async def update_heartbeat_monitor_config(
    config_update: HeartbeatMonitorConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update heartbeat monitor configuration
    
    Updates heartbeat monitor configuration with deep merge.
    Only provided fields will be updated, others remain unchanged.
    """
    try:
        config_service = await get_system_config_service(db)
        
        # Get current config
        current_config = await config_service.get_full_config()
        
        # Convert update to dict and remove None values
        update_dict = config_update.model_dump(exclude_none=True)
        
        # Merge with existing config
        updated_heartbeat_config = {**current_config.heartbeat_monitor, **update_dict}
        
        # Update in database
        from sqlalchemy import update
        from models.system_config import SystemConfig
        
        stmt = update(SystemConfig).where(
            SystemConfig.id == 1
        ).values(
            heartbeat_monitor=updated_heartbeat_config
        )
        
        await db.execute(stmt)
        await db.commit()
        
        logger.info(f"Heartbeat monitor configuration updated by user {current_user.id}")
        
        return HeartbeatMonitorConfigResponse(**updated_heartbeat_config)
    
    except ValueError as e:
        logger.warning(f"Invalid heartbeat monitor configuration update: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update heartbeat monitor config: {e}")
        raise HTTPException(status_code=500, detail=str(e))
