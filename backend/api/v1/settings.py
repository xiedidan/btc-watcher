"""
Settings API endpoints
用户设置API
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any
import logging

from database import get_db
from models.user_settings import UserSettings
from api.v1.auth import get_current_user
from models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/")
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取用户设置"""
    try:
        result = await db.execute(
            select(UserSettings).where(UserSettings.user_id == current_user.id)
        )
        settings = result.scalar_one_or_none()

        if not settings:
            # 如果不存在，创建默认设置
            settings = UserSettings(user_id=current_user.id)
            db.add(settings)
            await db.commit()
            await db.refresh(settings)

        return {
            "notifications": settings.notifications or {},
            "websocket": settings.websocket or {},
            "display": settings.display or {},
            "advanced": settings.advanced or {}
        }
    except Exception as e:
        logger.error(f"Failed to get settings for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/")
async def update_settings(
    settings_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新用户设置"""
    try:
        result = await db.execute(
            select(UserSettings).where(UserSettings.user_id == current_user.id)
        )
        settings = result.scalar_one_or_none()

        if not settings:
            # 如果不存在，创建新的设置
            settings = UserSettings(user_id=current_user.id)
            db.add(settings)

        # 更新设置
        if "notifications" in settings_data:
            settings.notifications = settings_data["notifications"]
        if "websocket" in settings_data:
            settings.websocket = settings_data["websocket"]
        if "display" in settings_data:
            settings.display = settings_data["display"]
        if "advanced" in settings_data:
            settings.advanced = settings_data["advanced"]

        await db.commit()
        await db.refresh(settings)

        logger.info(f"Updated settings for user {current_user.id}")

        return {
            "message": "Settings updated successfully",
            "settings": {
                "notifications": settings.notifications,
                "websocket": settings.websocket,
                "display": settings.display,
                "advanced": settings.advanced
            }
        }
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update settings for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset")
async def reset_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """重置设置为默认值"""
    try:
        result = await db.execute(
            select(UserSettings).where(UserSettings.user_id == current_user.id)
        )
        settings = result.scalar_one_or_none()

        if not settings:
            settings = UserSettings(user_id=current_user.id)
            db.add(settings)
        else:
            # 重置为默认值
            settings.notifications = {
                "browser_enabled": True,
                "signal_enabled": True,
                "strategy_enabled": True,
                "system_enabled": True,
                "sound_enabled": False
            }
            settings.websocket = {
                "max_reconnect_attempts": 5,
                "reconnect_delay": 3,
                "heartbeat_interval": 25,
                "subscribed_topics": ["monitoring", "strategies", "signals", "capacity"]
            }
            settings.display = {
                "refresh_interval": 30,
                "page_size": 20,
                "date_format": "YYYY-MM-DD HH:mm:ss",
                "number_format": "en-US",
                "show_charts": True,
                "show_trends": True,
                "enable_animations": True
            }
            settings.advanced = {
                "debug_mode": False,
                "api_timeout": 30,
                "cache_strategy": "memory"
            }

        await db.commit()
        await db.refresh(settings)

        logger.info(f"Reset settings for user {current_user.id}")

        return {
            "message": "Settings reset to default values",
            "settings": {
                "notifications": settings.notifications,
                "websocket": settings.websocket,
                "display": settings.display,
                "advanced": settings.advanced
            }
        }
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to reset settings for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
