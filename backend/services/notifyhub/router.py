"""
通知路由引擎
Notification Router - 根据规则决定通知去向
"""
from typing import List, Dict, Optional
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.notification import NotificationChannelConfig
from .frequency_controller import FrequencyController
from .time_rule_manager import TimeRuleManager

logger = logging.getLogger(__name__)


class NotifyRouter:
    """
    通知路由器 - 根据规则决定通知去向

    功能：
    - 根据用户配置选择渠道
    - 检查渠道是否启用
    - 检查渠道是否支持该优先级
    - 检查频率限制
    - 检查时间规则
    """

    def __init__(
        self,
        frequency_controller: FrequencyController,
        time_rule_manager: TimeRuleManager
    ):
        self.frequency_controller = frequency_controller
        self.time_rule_manager = time_rule_manager

    async def route(
        self,
        db: AsyncSession,
        notification: Dict
    ) -> List[str]:
        """
        根据通知内容和用户配置决定发送渠道

        Args:
            db: 数据库会话
            notification: 通知数据

        Returns:
            List[str]: 应该发送的渠道类型列表
        """
        user_id = notification.get("user_id")
        priority = notification.get("priority", "P1")

        if not user_id:
            logger.error("Notification missing user_id")
            return []

        # 获取用户的渠道配置
        channel_configs = await self._get_user_channel_configs(db, user_id)

        if not channel_configs:
            logger.warning(f"No channel configs found for user {user_id}")
            return []

        selected_channels = []

        for channel_config in channel_configs:
            # 1. 检查渠道是否启用
            if not channel_config.enabled:
                logger.debug(f"Channel {channel_config.channel_type} disabled for user {user_id}")
                continue

            # 2. 检查渠道是否支持该优先级
            supported_priorities = channel_config.supported_priorities or ["P2", "P1", "P0"]
            if priority not in supported_priorities:
                logger.debug(
                    f"Channel {channel_config.channel_type} does not support priority {priority}"
                )
                continue

            # 3. 检查频率限制
            # 注意：频率检查在实际发送时进行，这里只记录

            # 4. 检查时间规则
            # 注意：时间规则检查在实际发送时进行，这里只记录

            selected_channels.append(channel_config.channel_type)

        logger.info(
            f"Routed notification for user {user_id} to channels: {selected_channels}"
        )
        return selected_channels

    async def _get_user_channel_configs(
        self,
        db: AsyncSession,
        user_id: int
    ) -> List[NotificationChannelConfig]:
        """
        获取用户的渠道配置

        Args:
            db: 数据库会话
            user_id: 用户ID

        Returns:
            List[NotificationChannelConfig]: 渠道配置列表
        """
        try:
            result = await db.execute(
                select(NotificationChannelConfig)
                .where(NotificationChannelConfig.user_id == user_id)
                .order_by(NotificationChannelConfig.priority)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Failed to get channel configs for user {user_id}: {e}", exc_info=True)
            return []

    async def get_frequency_config(
        self,
        db: AsyncSession,
        user_id: int
    ) -> Optional[Dict]:
        """
        获取用户的频率限制配置

        Args:
            db: 数据库会话
            user_id: 用户ID

        Returns:
            Optional[Dict]: 频率配置
        """
        try:
            from models.notification import NotificationFrequencyLimit

            result = await db.execute(
                select(NotificationFrequencyLimit)
                .where(NotificationFrequencyLimit.user_id == user_id)
                .limit(1)
            )
            config = result.scalar_one_or_none()

            if not config:
                # 返回默认配置
                return {
                    "p2_min_interval": 0,
                    "p1_min_interval": 60,
                    "p0_batch_interval": 300,
                    "p0_batch_enabled": True,
                    "p0_batch_max_size": 10,
                    "enabled": True
                }

            return {
                "p2_min_interval": config.p2_min_interval,
                "p1_min_interval": config.p1_min_interval,
                "p0_batch_interval": config.p0_batch_interval,
                "p0_batch_enabled": config.p0_batch_enabled,
                "p0_batch_max_size": config.p0_batch_max_size,
                "enabled": config.enabled
            }
        except Exception as e:
            logger.error(f"Failed to get frequency config for user {user_id}: {e}", exc_info=True)
            return None

    async def get_time_rule(
        self,
        db: AsyncSession,
        user_id: int
    ) -> Optional[Dict]:
        """
        获取用户的时间规则配置（取第一个启用的规则）

        Args:
            db: 数据库会话
            user_id: 用户ID

        Returns:
            Optional[Dict]: 时间规则配置
        """
        try:
            from models.notification import NotificationTimeRule

            result = await db.execute(
                select(NotificationTimeRule)
                .where(
                    NotificationTimeRule.user_id == user_id,
                    NotificationTimeRule.enabled == True
                )
                .limit(1)
            )
            rule = result.scalar_one_or_none()

            if not rule:
                return None

            return {
                "enabled": rule.enabled,
                "quiet_hours_enabled": rule.quiet_hours_enabled,
                "quiet_start_time": rule.quiet_start_time,
                "quiet_end_time": rule.quiet_end_time,
                "quiet_priority_filter": rule.quiet_priority_filter,
                "weekend_mode_enabled": rule.weekend_mode_enabled,
                "weekend_downgrade_p1_to_p0": rule.weekend_downgrade_p1_to_p0,
                "weekend_batch_p0": rule.weekend_batch_p0,
                "working_hours_enabled": rule.working_hours_enabled,
                "working_start_time": rule.working_start_time,
                "working_end_time": rule.working_end_time,
                "working_days": rule.working_days,
                "holiday_mode_enabled": rule.holiday_mode_enabled,
                "holiday_dates": rule.holiday_dates
            }
        except Exception as e:
            logger.error(f"Failed to get time rule for user {user_id}: {e}", exc_info=True)
            return None

    async def get_channel_config(
        self,
        db: AsyncSession,
        user_id: int,
        channel_type: str
    ) -> Optional[Dict]:
        """
        获取指定渠道的配置

        Args:
            db: 数据库会话
            user_id: 用户ID
            channel_type: 渠道类型

        Returns:
            Optional[Dict]: 渠道配置
        """
        try:
            result = await db.execute(
                select(NotificationChannelConfig)
                .where(
                    NotificationChannelConfig.user_id == user_id,
                    NotificationChannelConfig.channel_type == channel_type,
                    NotificationChannelConfig.enabled == True
                )
                .limit(1)
            )
            channel_config = result.scalar_one_or_none()

            if not channel_config:
                return None

            return channel_config.config

        except Exception as e:
            logger.error(
                f"Failed to get channel config for user {user_id}, channel {channel_type}: {e}",
                exc_info=True
            )
            return None
