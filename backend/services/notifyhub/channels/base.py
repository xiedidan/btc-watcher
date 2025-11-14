"""
通知渠道抽象基类
Notification Channel Base Class
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class NotificationChannel(ABC):
    """通知渠道抽象基类"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化通知渠道

        Args:
            config: 渠道配置字典
        """
        self.config = config
        self.channel_type = self.__class__.__name__.replace("Channel", "").lower()

    @abstractmethod
    async def send(
        self,
        message: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        发送通知

        Args:
            message: 通知内容
            title: 通知标题（可选）
            metadata: 元数据（可选），包含priority、notification_type等信息

        Returns:
            bool: 发送是否成功
        """
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """
        测试渠道连接

        Returns:
            bool: 连接是否正常
        """
        pass

    def _get_priority_color(self, priority: str) -> str:
        """
        根据优先级获取颜色代码

        Args:
            priority: 优先级 (P0/P1/P2)

        Returns:
            str: 颜色代码或emoji
        """
        priority_map = {
            "P2": "🔴",  # 最高优先级 - 红色
            "P1": "🟠",  # 中等优先级 - 橙色
            "P0": "⚪"   # 最低优先级 - 白色
        }
        return priority_map.get(priority, "🔵")

    def _get_type_emoji(self, notification_type: str) -> str:
        """
        根据通知类型获取emoji

        Args:
            notification_type: 通知类型 (signal/alert/info/system)

        Returns:
            str: emoji图标
        """
        type_map = {
            "signal": "📊",
            "alert": "🚨",
            "info": "ℹ️",
            "system": "⚙️"
        }
        return type_map.get(notification_type, "📢")

    def _format_message_with_metadata(
        self,
        message: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        使用元数据格式化消息

        Args:
            message: 原始消息
            title: 标题
            metadata: 元数据

        Returns:
            str: 格式化后的消息
        """
        if not metadata:
            return f"**{title}**\n\n{message}" if title else message

        priority = metadata.get("priority", "P1")
        notification_type = metadata.get("notification_type", "info")

        priority_emoji = self._get_priority_color(priority)
        type_emoji = self._get_type_emoji(notification_type)

        formatted = f"{type_emoji} {priority_emoji} **{title}**\n\n{message}" if title else f"{type_emoji} {message}"
        return formatted

    def __repr__(self):
        return f"<{self.__class__.__name__}(type='{self.channel_type}')>"
