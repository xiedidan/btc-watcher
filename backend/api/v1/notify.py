"""
NotifyHub API Endpoints
NotifyHub通知中心API接口
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta
import logging

from database import get_db
from services.notifyhub.core import notify_hub
from models.notification import (
    NotificationChannelConfig,
    NotificationFrequencyLimit,
    NotificationTimeRule,
    NotificationHistory
)

router = APIRouter()
logger = logging.getLogger(__name__)


# ==================== Pydantic Models ====================

class NotificationSendRequest(BaseModel):
    """发送通知请求"""
    title: str
    message: str
    notification_type: str  # signal/alert/info/system
    priority: str = "P1"  # P0/P1/P2
    metadata: Optional[dict] = None
    strategy_id: Optional[int] = None
    signal_id: Optional[int] = None


class ChannelConfigRequest(BaseModel):
    """渠道配置请求"""
    channel_type: str
    channel_name: str
    enabled: bool = True
    priority: int = 1
    supported_priorities: List[str] = ["P2", "P1", "P0"]
    config: dict
    rate_limit_enabled: bool = True
    max_notifications_per_hour: int = 60
    max_notifications_per_day: int = 500


class FrequencyLimitRequest(BaseModel):
    """频率限制配置请求"""
    p2_min_interval: int = 0
    p1_min_interval: int = 60
    p0_batch_interval: int = 300
    p0_batch_enabled: bool = True
    p0_batch_max_size: int = 10
    enabled: bool = True


class TimeRuleRequest(BaseModel):
    """时间规则配置请求"""
    rule_name: str
    enabled: bool = True
    quiet_hours_enabled: bool = False
    quiet_start_time: str = "22:00"
    quiet_end_time: str = "08:00"
    quiet_priority_filter: str = "P2"
    weekend_mode_enabled: bool = False
    weekend_downgrade_p1_to_p0: bool = True
    weekend_batch_p0: bool = True
    working_hours_enabled: bool = False
    working_start_time: str = "09:00"
    working_end_time: str = "18:00"
    working_days: List[int] = [1, 2, 3, 4, 5]
    holiday_mode_enabled: bool = False
    holiday_dates: List[str] = []


# ==================== 通知发送接口 ====================

@router.post("/send")
async def send_notification(
    request: NotificationSendRequest,
    user_id: int = 1,  # TODO: Get from auth
    db: AsyncSession = Depends(get_db)
):
    """
    发送通知（统一入口）

    业务代码通过此接口发送通知，NotifyHub会自动路由到用户配置的渠道
    """
    try:
        success = await notify_hub.notify(
            user_id=user_id,
            title=request.title,
            message=request.message,
            notification_type=request.notification_type,
            priority=request.priority,
            metadata=request.metadata,
            strategy_id=request.strategy_id,
            signal_id=request.signal_id
        )

        if success:
            return {
                "success": True,
                "message": "Notification queued successfully",
                "queued": True,
                "estimated_send_time": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to queue notification")

    except Exception as e:
        logger.error(f"Failed to send notification: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 渠道配置管理 ====================

@router.get("/channels")
async def list_channels(
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
            "success": True,
            "data": {
                "channels": [
                    {
                        "id": c.id,
                        "channel_type": c.channel_type,
                        "channel_name": c.channel_name,
                        "enabled": c.enabled,
                        "priority": c.priority,
                        "supported_priorities": c.supported_priorities,
                        "config": c.config,
                        "rate_limit_enabled": c.rate_limit_enabled,
                        "max_notifications_per_hour": c.max_notifications_per_hour,
                        "max_notifications_per_day": c.max_notifications_per_day,
                        "total_sent": c.total_sent,
                        "total_failed": c.total_failed,
                        "last_sent_at": c.last_sent_at.isoformat() if c.last_sent_at else None,
                        "created_at": c.created_at.isoformat() if c.created_at else None
                    }
                    for c in configs
                ]
            }
        }
    except Exception as e:
        logger.error(f"Failed to list channels: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/channels")
async def create_channel(
    request: ChannelConfigRequest,
    user_id: int = 1,  # TODO: Get from auth
    db: AsyncSession = Depends(get_db)
):
    """创建通知渠道配置"""
    try:
        config = NotificationChannelConfig(
            user_id=user_id,
            channel_type=request.channel_type,
            channel_name=request.channel_name,
            enabled=request.enabled,
            priority=request.priority,
            supported_priorities=request.supported_priorities,
            config=request.config,
            rate_limit_enabled=request.rate_limit_enabled,
            max_notifications_per_hour=request.max_notifications_per_hour,
            max_notifications_per_day=request.max_notifications_per_day
        )

        db.add(config)
        await db.commit()
        await db.refresh(config)

        logger.info(f"Created channel config {config.id} for user {user_id}")

        return {
            "success": True,
            "data": {
                "id": config.id,
                "message": "Channel configuration created successfully"
            }
        }
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create channel: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/channels/{channel_id}")
async def update_channel(
    channel_id: int,
    request: ChannelConfigRequest,
    db: AsyncSession = Depends(get_db)
):
    """更新通知渠道配置"""
    try:
        result = await db.execute(
            select(NotificationChannelConfig).where(NotificationChannelConfig.id == channel_id)
        )
        config = result.scalar_one_or_none()

        if not config:
            raise HTTPException(status_code=404, detail="Channel config not found")

        config.channel_name = request.channel_name
        config.enabled = request.enabled
        config.priority = request.priority
        config.supported_priorities = request.supported_priorities
        config.config = request.config
        config.rate_limit_enabled = request.rate_limit_enabled
        config.max_notifications_per_hour = request.max_notifications_per_hour
        config.max_notifications_per_day = request.max_notifications_per_day

        await db.commit()

        logger.info(f"Updated channel config {channel_id}")

        return {
            "success": True,
            "data": {
                "id": config.id,
                "message": "Channel configuration updated successfully"
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update channel: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/channels/{channel_id}")
async def delete_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_db)
):
    """删除通知渠道配置"""
    try:
        result = await db.execute(
            select(NotificationChannelConfig).where(NotificationChannelConfig.id == channel_id)
        )
        config = result.scalar_one_or_none()

        if not config:
            raise HTTPException(status_code=404, detail="Channel config not found")

        await db.delete(config)
        await db.commit()

        logger.info(f"Deleted channel config {channel_id}")

        return {
            "success": True,
            "data": {
                "id": channel_id,
                "message": "Channel configuration deleted successfully"
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete channel: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/channels/{channel_id}/test")
async def test_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_db)
):
    """测试通知渠道连接"""
    try:
        result = await db.execute(
            select(NotificationChannelConfig).where(NotificationChannelConfig.id == channel_id)
        )
        config = result.scalar_one_or_none()

        if not config:
            raise HTTPException(status_code=404, detail="Channel config not found")

        # 发送测试通知
        success = await notify_hub.notify(
            user_id=config.user_id,
            title="🔔 测试通知",
            message=f"这是一条来自 {config.channel_name} 的测试消息，用于验证通知渠道配置是否正确。",
            notification_type="info",
            priority="P1",
            metadata={"test": True}
        )

        return {
            "success": True,
            "data": {
                "test_result": "success" if success else "failed",
                "message": "Test notification queued" if success else "Failed to queue test notification"
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to test channel: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 频率限制配置 ====================

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
            return {
                "success": True,
                "data": {
                    "user_id": user_id,
                    "p2_min_interval": 0,
                    "p1_min_interval": 60,
                    "p0_batch_interval": 300,
                    "p0_batch_enabled": True,
                    "p0_batch_max_size": 10,
                    "enabled": True
                }
            }

        return {
            "success": True,
            "data": {
                "user_id": config.user_id,
                "p2_min_interval": config.p2_min_interval,
                "p1_min_interval": config.p1_min_interval,
                "p0_batch_interval": config.p0_batch_interval,
                "p0_batch_enabled": config.p0_batch_enabled,
                "p0_batch_max_size": config.p0_batch_max_size,
                "enabled": config.enabled,
                "created_at": config.created_at.isoformat() if config.created_at else None,
                "updated_at": config.updated_at.isoformat() if config.updated_at else None
            }
        }
    except Exception as e:
        logger.error(f"Failed to get frequency limits: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/frequency-limits")
async def update_frequency_limits(
    request: FrequencyLimitRequest,
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
            config = NotificationFrequencyLimit(
                user_id=user_id,
                p2_min_interval=request.p2_min_interval,
                p1_min_interval=request.p1_min_interval,
                p0_batch_interval=request.p0_batch_interval,
                p0_batch_enabled=request.p0_batch_enabled,
                p0_batch_max_size=request.p0_batch_max_size,
                enabled=request.enabled
            )
            db.add(config)
        else:
            config.p2_min_interval = request.p2_min_interval
            config.p1_min_interval = request.p1_min_interval
            config.p0_batch_interval = request.p0_batch_interval
            config.p0_batch_enabled = request.p0_batch_enabled
            config.p0_batch_max_size = request.p0_batch_max_size
            config.enabled = request.enabled

        await db.commit()
        await db.refresh(config)

        logger.info(f"Updated frequency limits for user {user_id}")

        return {
            "success": True,
            "data": {
                "id": config.id,
                "message": "Frequency limits updated successfully"
            }
        }
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update frequency limits: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 时间规则配置 ====================

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
            .order_by(desc(NotificationTimeRule.created_at))
        )
        rules = result.scalars().all()

        return {
            "success": True,
            "data": {
                "time_rules": [
                    {
                        "id": r.id,
                        "rule_name": r.rule_name,
                        "enabled": r.enabled,
                        "quiet_hours_enabled": r.quiet_hours_enabled,
                        "quiet_start_time": r.quiet_start_time,
                        "quiet_end_time": r.quiet_end_time,
                        "quiet_priority_filter": r.quiet_priority_filter,
                        "weekend_mode_enabled": r.weekend_mode_enabled,
                        "weekend_downgrade_p1_to_p0": r.weekend_downgrade_p1_to_p0,
                        "weekend_batch_p0": r.weekend_batch_p0,
                        "working_hours_enabled": r.working_hours_enabled,
                        "working_start_time": r.working_start_time,
                        "working_end_time": r.working_end_time,
                        "working_days": r.working_days,
                        "holiday_mode_enabled": r.holiday_mode_enabled,
                        "holiday_dates": r.holiday_dates,
                        "created_at": r.created_at.isoformat() if r.created_at else None
                    }
                    for r in rules
                ]
            }
        }
    except Exception as e:
        logger.error(f"Failed to list time rules: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/time-rules")
async def create_time_rule(
    request: TimeRuleRequest,
    user_id: int = 1,  # TODO: Get from auth
    db: AsyncSession = Depends(get_db)
):
    """创建时间规则配置"""
    try:
        rule = NotificationTimeRule(
            user_id=user_id,
            rule_name=request.rule_name,
            enabled=request.enabled,
            quiet_hours_enabled=request.quiet_hours_enabled,
            quiet_start_time=request.quiet_start_time,
            quiet_end_time=request.quiet_end_time,
            quiet_priority_filter=request.quiet_priority_filter,
            weekend_mode_enabled=request.weekend_mode_enabled,
            weekend_downgrade_p1_to_p0=request.weekend_downgrade_p1_to_p0,
            weekend_batch_p0=request.weekend_batch_p0,
            working_hours_enabled=request.working_hours_enabled,
            working_start_time=request.working_start_time,
            working_end_time=request.working_end_time,
            working_days=request.working_days,
            holiday_mode_enabled=request.holiday_mode_enabled,
            holiday_dates=request.holiday_dates
        )

        db.add(rule)
        await db.commit()
        await db.refresh(rule)

        logger.info(f"Created time rule {rule.id} for user {user_id}")

        return {
            "success": True,
            "data": {
                "id": rule.id,
                "message": "Time rule created successfully"
            }
        }
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create time rule: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/time-rules/{rule_id}")
async def update_time_rule(
    rule_id: int,
    request: TimeRuleRequest,
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

        rule.rule_name = request.rule_name
        rule.enabled = request.enabled
        rule.quiet_hours_enabled = request.quiet_hours_enabled
        rule.quiet_start_time = request.quiet_start_time
        rule.quiet_end_time = request.quiet_end_time
        rule.quiet_priority_filter = request.quiet_priority_filter
        rule.weekend_mode_enabled = request.weekend_mode_enabled
        rule.weekend_downgrade_p1_to_p0 = request.weekend_downgrade_p1_to_p0
        rule.weekend_batch_p0 = request.weekend_batch_p0
        rule.working_hours_enabled = request.working_hours_enabled
        rule.working_start_time = request.working_start_time
        rule.working_end_time = request.working_end_time
        rule.working_days = request.working_days
        rule.holiday_mode_enabled = request.holiday_mode_enabled
        rule.holiday_dates = request.holiday_dates

        await db.commit()

        logger.info(f"Updated time rule {rule_id}")

        return {
            "success": True,
            "data": {
                "id": rule.id,
                "message": "Time rule updated successfully"
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update time rule: {e}", exc_info=True)
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
            "success": True,
            "data": {
                "id": rule_id,
                "message": "Time rule deleted successfully"
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete time rule: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 通知历史查询 ====================

@router.get("/history")
async def get_notification_history(
    page: int = 1,
    page_size: int = 20,
    channel_type: Optional[str] = None,
    status: Optional[str] = None,
    notification_type: Optional[str] = None,
    priority: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    user_id: int = 1,  # TODO: Get from auth
    db: AsyncSession = Depends(get_db)
):
    """获取通知历史记录"""
    try:
        query = select(NotificationHistory).where(NotificationHistory.user_id == user_id)

        if channel_type:
            query = query.where(NotificationHistory.channel_type == channel_type)
        if status:
            query = query.where(NotificationHistory.status == status)
        if notification_type:
            query = query.where(NotificationHistory.notification_type == notification_type)
        if priority:
            query = query.where(NotificationHistory.priority == priority)
        if start_time:
            start_dt = datetime.fromisoformat(start_time)
            query = query.where(NotificationHistory.created_at >= start_dt)
        if end_time:
            end_dt = datetime.fromisoformat(end_time)
            query = query.where(NotificationHistory.created_at <= end_dt)

        # 总数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        # 分页
        query = query.order_by(desc(NotificationHistory.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        history = result.scalars().all()

        return {
            "success": True,
            "data": {
                "history": [
                    {
                        "id": h.id,
                        "user_id": h.user_id,
                        "title": h.title,
                        "message": h.message,
                        "notification_type": h.notification_type,
                        "priority": h.priority,
                        "channel_type": h.channel_type,
                        "status": h.status,
                        "sent_at": h.sent_at.isoformat() if h.sent_at else None,
                        "error_message": h.error_message,
                        "signal_id": h.signal_id,
                        "strategy_id": h.strategy_id,
                        "extra_data": h.extra_data,
                        "created_at": h.created_at.isoformat() if h.created_at else None
                    }
                    for h in history
                ]
            },
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size
            }
        }
    except Exception as e:
        logger.error(f"Failed to get notification history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 统计接口 ====================

@router.get("/stats")
async def get_notification_stats(
    period: str = "today",  # today/week/month
    user_id: int = 1,  # TODO: Get from auth
    db: AsyncSession = Depends(get_db)
):
    """获取通知统计信息"""
    try:
        # 计算时间范围
        now = datetime.now()
        if period == "today":
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            start_time = now - timedelta(days=7)
        elif period == "month":
            start_time = now - timedelta(days=30)
        else:
            start_time = now - timedelta(days=1)

        # 查询通知
        result = await db.execute(
            select(NotificationHistory).where(
                NotificationHistory.user_id == user_id,
                NotificationHistory.created_at >= start_time
            )
        )
        notifications = result.scalars().all()

        # 统计
        total = len(notifications)
        by_status = {}
        by_priority = {}
        by_channel = {}
        by_type = {}

        for notif in notifications:
            by_status[notif.status] = by_status.get(notif.status, 0) + 1
            by_priority[notif.priority] = by_priority.get(notif.priority, 0) + 1
            by_channel[notif.channel_type] = by_channel.get(notif.channel_type, 0) + 1
            by_type[notif.notification_type] = by_type.get(notif.notification_type, 0) + 1

        sent_count = by_status.get("sent", 0)
        success_rate = (sent_count / total * 100) if total > 0 else 100

        return {
            "success": True,
            "data": {
                "period": period,
                "total_notifications": total,
                "by_status": by_status,
                "by_priority": by_priority,
                "by_channel": by_channel,
                "by_type": by_type,
                "success_rate": round(success_rate, 2)
            }
        }
    except Exception as e:
        logger.error(f"Failed to get notification stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/channels")
async def get_channel_stats(
    user_id: int = 1,  # TODO: Get from auth
    db: AsyncSession = Depends(get_db)
):
    """获取各渠道的统计信息"""
    try:
        result = await db.execute(
            select(NotificationChannelConfig)
            .where(NotificationChannelConfig.user_id == user_id)
        )
        channels = result.scalars().all()

        return {
            "success": True,
            "data": {
                "channels": [
                    {
                        "channel_id": c.id,
                        "channel_type": c.channel_type,
                        "channel_name": c.channel_name,
                        "total_sent": c.total_sent or 0,
                        "total_failed": c.total_failed or 0,
                        "success_rate": round(
                            (c.total_sent / (c.total_sent + c.total_failed) * 100)
                            if (c.total_sent + c.total_failed) > 0 else 100,
                            2
                        ),
                        "last_sent_at": c.last_sent_at.isoformat() if c.last_sent_at else None,
                        "last_error": c.last_error,
                        "last_error_at": c.last_error_at.isoformat() if c.last_error_at else None
                    }
                    for c in channels
                ]
            }
        }
    except Exception as e:
        logger.error(f"Failed to get channel stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 系统管理接口 ====================

@router.get("/system/health")
async def get_system_health():
    """NotifyHub健康检查"""
    try:
        queue_status = await notify_hub.get_queue_status()

        return {
            "success": True,
            "data": {
                "status": "healthy" if queue_status["running"] else "stopped",
                "queue_size": queue_status["queue_size"],
                "worker_status": "running" if queue_status["running"] else "stopped",
                "batch_queues": queue_status["batch_queues"],
                "total_batched_notifications": queue_status["total_batched_notifications"]
            }
        }
    except Exception as e:
        logger.error(f"Failed to get system health: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system/queue")
async def get_queue_status():
    """查看当前通知队列状态"""
    try:
        queue_status = await notify_hub.get_queue_status()

        return {
            "success": True,
            "data": queue_status
        }
    except Exception as e:
        logger.error(f"Failed to get queue status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/system/flush-batch")
async def flush_batch_queue():
    """手动触发批量发送队列刷新"""
    try:
        async with SessionLocal() as db:
            await notify_hub._flush_all_batches(db)

        return {
            "success": True,
            "data": {
                "message": "Batch queues flushed successfully"
            }
        }
    except Exception as e:
        logger.error(f"Failed to flush batch queues: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
