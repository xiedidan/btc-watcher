"""
Notifications API endpoints
通知管理和配置
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import logging

from database import get_db
from services.notification_service import NotificationService
from models.notification import (
    NotificationChannelConfig,
    NotificationFrequencyLimit,
    NotificationTimeRule,
    NotificationHistory
)

router = APIRouter()
logger = logging.getLogger(__name__)

# Global service instance (will be injected from main.py)
_notification_service: Optional[NotificationService] = None


def get_notification_service():
    """Get notification service instance"""
    if _notification_service is None:
        raise HTTPException(status_code=500, detail="Notification service not initialized")
    return _notification_service


@router.post("/send")
async def send_notification(
    user_id: int,
    title: str,
    message: str,
    channel: str = "telegram",
    priority: str = "P2",
    notification_type: str = "system",
    notif_service: NotificationService = Depends(get_notification_service)
):
    """发送通知"""
    try:
        success = await notif_service.send_notification(
            user_id=user_id,
            title=title,
            message=message,
            channel=channel,
            priority=priority,
            notification_type=notification_type
        )

        if success:
            return {
                "status": "success",
                "message": "Notification queued successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to queue notification")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test")
async def test_notification(
    channel: str = "telegram",
    notif_service: NotificationService = Depends(get_notification_service)
):
    """测试通知渠道"""
    try:
        success = await notif_service.send_notification(
            user_id=1,  # Admin user
            title="🧪 Test Notification",
            message="This is a test notification from BTC Watcher.",
            channel=channel,
            priority="P2",
            notification_type="system"
        )

        return {
            "status": "success" if success else "failed",
            "channel": channel,
            "message": f"Test notification {'sent' if success else 'failed'}"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_notification_statistics(
    hours: int = 24,
    notif_service: NotificationService = Depends(get_notification_service)
):
    """获取通知统计"""
    try:
        stats = await notif_service.get_notification_stats(hours=hours)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/channels")
async def get_notification_channels():
    """获取可用的通知渠道"""
    return {
        "channels": [
            {
                "id": "telegram",
                "name": "Telegram",
                "description": "Telegram Bot通知",
                "icon": "📱"
            },
            {
                "id": "wechat",
                "name": "企业微信",
                "description": "企业微信群机器人通知",
                "icon": "💬"
            },
            {
                "id": "feishu",
                "name": "飞书",
                "description": "飞书群机器人通知",
                "icon": "🚀"
            },
            {
                "id": "email",
                "name": "邮件",
                "description": "SMTP邮件通知",
                "icon": "📧"
            }
        ]
    }


# ==================== Channel Configuration APIs ====================

@router.get("/channels/config")
async def list_channel_configs(
    user_id: int = 1,  # TODO: Get from auth
    db: AsyncSession = Depends(get_db)
):
    """获取用户的通知渠道配置列表"""
    try:
        result = await db.execute(
            select(NotificationChannelConfig)
            .where(NotificationChannelConfig.user_id == user_id)
            .order_by(NotificationChannelConfig.priority)
        )
        configs = result.scalars().all()

        return {
            "total": len(configs),
            "configs": [
                {
                    "id": c.id,
                    "channel_type": c.channel_type,
                    "channel_name": c.channel_name,
                    "enabled": c.enabled,
                    "priority": c.priority,
                    "supported_priorities": c.supported_priorities,
                    "templates": c.templates,
                    "rate_limit_enabled": c.rate_limit_enabled,
                    "max_notifications_per_hour": c.max_notifications_per_hour,
                    "statistics": {
                        "total_sent": c.total_sent,
                        "total_failed": c.total_failed,
                        "last_sent_at": c.last_sent_at.isoformat() if c.last_sent_at else None
                    }
                }
                for c in configs
            ]
        }
    except Exception as e:
        logger.error(f"Failed to list channel configs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/channels/config")
async def create_channel_config(
    config_data: dict,
    user_id: int = 1,  # TODO: Get from auth
    db: AsyncSession = Depends(get_db)
):
    """创建通知渠道配置"""
    try:
        config = NotificationChannelConfig(
            user_id=user_id,
            channel_type=config_data["channel_type"],
            channel_name=config_data["channel_name"],
            enabled=config_data.get("enabled", True),
            priority=config_data.get("priority", 1),
            supported_priorities=config_data.get("supported_priorities", ["P2", "P1", "P0"]),
            config=config_data.get("config", {}),
            templates=config_data.get("templates", {}),
            rate_limit_enabled=config_data.get("rate_limit_enabled", True),
            max_notifications_per_hour=config_data.get("max_notifications_per_hour", 60),
            max_notifications_per_day=config_data.get("max_notifications_per_day", 500)
        )

        db.add(config)
        await db.commit()
        await db.refresh(config)

        logger.info(f"Created channel config {config.id} for user {user_id}")

        return {
            "id": config.id,
            "message": "Channel configuration created successfully"
        }
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create channel config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/channels/config/{config_id}")
async def update_channel_config(
    config_id: int,
    config_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """更新通知渠道配置"""
    try:
        result = await db.execute(
            select(NotificationChannelConfig).where(NotificationChannelConfig.id == config_id)
        )
        config = result.scalar_one_or_none()

        if not config:
            raise HTTPException(status_code=404, detail="Channel config not found")

        # Update fields
        for field in ["channel_name", "enabled", "priority", "supported_priorities",
                      "config", "templates", "rate_limit_enabled",
                      "max_notifications_per_hour", "max_notifications_per_day"]:
            if field in config_data:
                setattr(config, field, config_data[field])

        await db.commit()
        await db.refresh(config)

        logger.info(f"Updated channel config {config_id}")

        return {
            "id": config.id,
            "message": "Channel configuration updated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update channel config {config_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/channels/config/{config_id}")
async def delete_channel_config(
    config_id: int,
    db: AsyncSession = Depends(get_db)
):
    """删除通知渠道配置"""
    try:
        result = await db.execute(
            select(NotificationChannelConfig).where(NotificationChannelConfig.id == config_id)
        )
        config = result.scalar_one_or_none()

        if not config:
            raise HTTPException(status_code=404, detail="Channel config not found")

        await db.delete(config)
        await db.commit()

        logger.info(f"Deleted channel config {config_id}")

        return {
            "id": config_id,
            "message": "Channel configuration deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete channel config {config_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Frequency Limit APIs ====================

@router.get("/frequency-limits")
async def get_frequency_limits(
    user_id: int = 1,  # TODO: Get from auth
    db: AsyncSession = Depends(get_db)
):
    """获取用户的频率限制配置"""
    try:
        result = await db.execute(
            select(NotificationFrequencyLimit)
            .where(NotificationFrequencyLimit.user_id == user_id)
            .limit(1)
        )
        config = result.scalar_one_or_none()

        if not config:
            # Return default configuration
            return {
                "exists": False,
                "config": {
                    "p2_min_interval": 0,
                    "p1_min_interval": 60,
                    "p0_batch_interval": 300,
                    "p0_batch_enabled": True,
                    "p0_batch_max_size": 10,
                    "enabled": True
                }
            }

        return {
            "exists": True,
            "config": {
                "id": config.id,
                "p2_min_interval": config.p2_min_interval,
                "p1_min_interval": config.p1_min_interval,
                "p0_batch_interval": config.p0_batch_interval,
                "p0_batch_enabled": config.p0_batch_enabled,
                "p0_batch_max_size": config.p0_batch_max_size,
                "enabled": config.enabled
            }
        }
    except Exception as e:
        logger.error(f"Failed to get frequency limits: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/frequency-limits")
async def update_frequency_limits(
    config_data: dict,
    user_id: int = 1,  # TODO: Get from auth
    db: AsyncSession = Depends(get_db)
):
    """更新用户的频率限制配置"""
    try:
        result = await db.execute(
            select(NotificationFrequencyLimit)
            .where(NotificationFrequencyLimit.user_id == user_id)
            .limit(1)
        )
        config = result.scalar_one_or_none()

        if not config:
            # Create new configuration
            config = NotificationFrequencyLimit(
                user_id=user_id,
                p2_min_interval=config_data.get("p2_min_interval", 0),
                p1_min_interval=config_data.get("p1_min_interval", 60),
                p0_batch_interval=config_data.get("p0_batch_interval", 300),
                p0_batch_enabled=config_data.get("p0_batch_enabled", True),
                p0_batch_max_size=config_data.get("p0_batch_max_size", 10),
                enabled=config_data.get("enabled", True)
            )
            db.add(config)
        else:
            # Update existing configuration
            for field in ["p2_min_interval", "p1_min_interval", "p0_batch_interval",
                          "p0_batch_enabled", "p0_batch_max_size", "enabled"]:
                if field in config_data:
                    setattr(config, field, config_data[field])

        await db.commit()
        await db.refresh(config)

        logger.info(f"Updated frequency limits for user {user_id}")

        return {
            "id": config.id,
            "message": "Frequency limits updated successfully"
        }
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update frequency limits: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Time Rule APIs ====================

@router.get("/time-rules")
async def list_time_rules(
    user_id: int = 1,  # TODO: Get from auth
    db: AsyncSession = Depends(get_db)
):
    """获取用户的时间规则配置列表"""
    try:
        result = await db.execute(
            select(NotificationTimeRule)
            .where(NotificationTimeRule.user_id == user_id)
            .order_by(NotificationTimeRule.created_at.desc())
        )
        rules = result.scalars().all()

        return {
            "total": len(rules),
            "rules": [
                {
                    "id": r.id,
                    "rule_name": r.rule_name,
                    "enabled": r.enabled,
                    "quiet_hours": {
                        "enabled": r.quiet_hours_enabled,
                        "start_time": r.quiet_start_time,
                        "end_time": r.quiet_end_time,
                        "priority_filter": r.quiet_priority_filter
                    },
                    "weekend_mode": {
                        "enabled": r.weekend_mode_enabled,
                        "downgrade_p1_to_p0": r.weekend_downgrade_p1_to_p0,
                        "batch_p0": r.weekend_batch_p0
                    },
                    "working_hours": {
                        "enabled": r.working_hours_enabled,
                        "start_time": r.working_start_time,
                        "end_time": r.working_end_time,
                        "working_days": r.working_days
                    },
                    "holiday_mode": {
                        "enabled": r.holiday_mode_enabled,
                        "dates": r.holiday_dates
                    }
                }
                for r in rules
            ]
        }
    except Exception as e:
        logger.error(f"Failed to list time rules: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/time-rules")
async def create_time_rule(
    rule_data: dict,
    user_id: int = 1,  # TODO: Get from auth
    db: AsyncSession = Depends(get_db)
):
    """创建时间规则配置"""
    try:
        rule = NotificationTimeRule(
            user_id=user_id,
            rule_name=rule_data["rule_name"],
            enabled=rule_data.get("enabled", True),
            quiet_hours_enabled=rule_data.get("quiet_hours_enabled", False),
            quiet_start_time=rule_data.get("quiet_start_time", "22:00"),
            quiet_end_time=rule_data.get("quiet_end_time", "08:00"),
            quiet_priority_filter=rule_data.get("quiet_priority_filter", "P2"),
            weekend_mode_enabled=rule_data.get("weekend_mode_enabled", False),
            weekend_downgrade_p1_to_p0=rule_data.get("weekend_downgrade_p1_to_p0", True),
            weekend_batch_p0=rule_data.get("weekend_batch_p0", True),
            working_hours_enabled=rule_data.get("working_hours_enabled", False),
            working_start_time=rule_data.get("working_start_time", "09:00"),
            working_end_time=rule_data.get("working_end_time", "18:00"),
            working_days=rule_data.get("working_days", [1, 2, 3, 4, 5]),
            holiday_mode_enabled=rule_data.get("holiday_mode_enabled", False),
            holiday_dates=rule_data.get("holiday_dates", [])
        )

        db.add(rule)
        await db.commit()
        await db.refresh(rule)

        logger.info(f"Created time rule {rule.id} for user {user_id}")

        return {
            "id": rule.id,
            "message": "Time rule created successfully"
        }
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create time rule: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/time-rules/{rule_id}")
async def update_time_rule(
    rule_id: int,
    rule_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """更新时间规则配置"""
    try:
        result = await db.execute(
            select(NotificationTimeRule).where(NotificationTimeRule.id == rule_id)
        )
        rule = result.scalar_one_or_none()

        if not rule:
            raise HTTPException(status_code=404, detail="Time rule not found")

        # Update fields
        for field in ["rule_name", "enabled", "quiet_hours_enabled", "quiet_start_time",
                      "quiet_end_time", "quiet_priority_filter", "weekend_mode_enabled",
                      "weekend_downgrade_p1_to_p0", "weekend_batch_p0", "working_hours_enabled",
                      "working_start_time", "working_end_time", "working_days",
                      "holiday_mode_enabled", "holiday_dates"]:
            if field in rule_data:
                setattr(rule, field, rule_data[field])

        await db.commit()
        await db.refresh(rule)

        logger.info(f"Updated time rule {rule_id}")

        return {
            "id": rule.id,
            "message": "Time rule updated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update time rule {rule_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/time-rules/{rule_id}")
async def delete_time_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db)
):
    """删除时间规则配置"""
    try:
        result = await db.execute(
            select(NotificationTimeRule).where(NotificationTimeRule.id == rule_id)
        )
        rule = result.scalar_one_or_none()

        if not rule:
            raise HTTPException(status_code=404, detail="Time rule not found")

        await db.delete(rule)
        await db.commit()

        logger.info(f"Deleted time rule {rule_id}")

        return {
            "id": rule_id,
            "message": "Time rule deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete time rule {rule_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

