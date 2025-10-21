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
