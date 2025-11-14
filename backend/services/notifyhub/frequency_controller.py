"""
频率控制器
Frequency Controller - 防止通知轰炸
"""
import time
from typing import Dict, Tuple, List, Optional
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class FrequencyController:
    """
    频率控制器 - 防止通知轰炸

    功能：
    - P2：立即发送，无限制
    - P1：检查最小发送间隔（默认60秒）
    - P0：加入批量队列，定时批量发送（默认5分钟）
    """

    def __init__(self):
        # 记录每个渠道的最后发送时间 {(user_id, channel): timestamp}
        self.last_send_time: Dict[Tuple[int, str], float] = {}

        # P0通知批量缓冲区 {(user_id, channel): [notifications]}
        self.p0_batch_buffer: Dict[Tuple[int, str], List[Dict]] = defaultdict(list)

    async def should_send(
        self,
        user_id: int,
        channel: str,
        priority: str,
        frequency_config: Optional[Dict] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        判断是否应该发送通知

        Args:
            user_id: 用户ID
            channel: 渠道类型
            priority: 优先级 (P0/P1/P2)
            frequency_config: 频率配置

        Returns:
            Tuple[bool, Optional[str]]: (是否发送, 原因)
        """
        # 使用默认配置
        if not frequency_config:
            frequency_config = {
                "p2_min_interval": 0,
                "p1_min_interval": 60,
                "p0_batch_interval": 300,
                "p0_batch_enabled": True,
                "enabled": True
            }

        # 如果频率控制被禁用，直接发送
        if not frequency_config.get("enabled", True):
            return True, None

        # P2：最高优先级，立即发送
        if priority == "P2":
            self._update_last_send_time(user_id, channel)
            return True, None

        # P1：中等优先级，检查最小发送间隔
        if priority == "P1":
            min_interval = frequency_config.get("p1_min_interval", 60)
            last_time = self.last_send_time.get((user_id, channel), 0)
            current_time = time.time()

            if current_time - last_time >= min_interval:
                self._update_last_send_time(user_id, channel)
                return True, None
            else:
                remaining = min_interval - (current_time - last_time)
                return False, f"rate_limit_p1: {remaining:.0f}s remaining"

        # P0：最低优先级，批量发送
        if priority == "P0":
            if frequency_config.get("p0_batch_enabled", True):
                return False, "batched"  # 暂不发送，等待批量
            else:
                self._update_last_send_time(user_id, channel)
                return True, None  # 禁用批量则正常发送

        # 未知优先级，默认允许发送
        return True, None

    def add_to_batch(self, user_id: int, channel: str, notification: Dict):
        """
        将P0通知添加到批量队列

        Args:
            user_id: 用户ID
            channel: 渠道类型
            notification: 通知数据
        """
        batch_key = (user_id, channel)
        self.p0_batch_buffer[batch_key].append(notification)
        logger.debug(f"Added notification to batch queue for user {user_id}, channel {channel}")

    def get_batch_queue(self, user_id: int, channel: str) -> List[Dict]:
        """
        获取批量队列

        Args:
            user_id: 用户ID
            channel: 渠道类型

        Returns:
            List[Dict]: 批量队列中的通知列表
        """
        batch_key = (user_id, channel)
        return self.p0_batch_buffer.get(batch_key, [])

    def clear_batch_queue(self, user_id: int, channel: str):
        """
        清空批量队列

        Args:
            user_id: 用户ID
            channel: 渠道类型
        """
        batch_key = (user_id, channel)
        if batch_key in self.p0_batch_buffer:
            del self.p0_batch_buffer[batch_key]
            logger.debug(f"Cleared batch queue for user {user_id}, channel {channel}")

    def merge_p0_notifications(self, notifications: List[Dict]) -> Dict:
        """
        合并多条P0通知为一条

        Args:
            notifications: 通知列表

        Returns:
            Dict: 合并后的通知
        """
        if not notifications:
            return {}

        # 按通知类型分组
        grouped = defaultdict(list)
        for notif in notifications:
            notification_type = notif.get("notification_type", "info")
            grouped[notification_type].append(notif)

        # 构建合并消息
        total_count = len(notifications)
        title = f"📊 批量通知（{total_count}条）"

        message_parts = []
        for notif_type, notifs in grouped.items():
            type_emoji = self._get_type_emoji(notif_type)
            message_parts.append(f"\n**{type_emoji} {notif_type.upper()} ({len(notifs)}条)**")

            for idx, notif in enumerate(notifs[:10], 1):  # 只显示前10条
                notif_title = notif.get("title", "无标题")
                message_parts.append(f"{idx}. {notif_title}")

            if len(notifs) > 10:
                message_parts.append(f"... 还有 {len(notifs) - 10} 条")

        # 添加时间范围
        if notifications:
            first_time = notifications[0].get("created_at", "")
            last_time = notifications[-1].get("created_at", "")
            message_parts.append(f"\n⏰ 时间范围: {first_time} - {last_time}")

        message = "\n".join(message_parts)

        return {
            "title": title,
            "message": message,
            "notification_type": "info",
            "priority": "P0",
            "metadata": {
                "batch_count": total_count,
                "types": list(grouped.keys())
            }
        }

    def _update_last_send_time(self, user_id: int, channel: str):
        """更新最后发送时间"""
        self.last_send_time[(user_id, channel)] = time.time()

    def _get_type_emoji(self, notification_type: str) -> str:
        """获取通知类型的emoji"""
        type_map = {
            "signal": "📊",
            "alert": "🚨",
            "info": "ℹ️",
            "system": "⚙️"
        }
        return type_map.get(notification_type, "📢")

    def get_stats(self) -> Dict:
        """
        获取频率控制器统计信息

        Returns:
            Dict: 统计信息
        """
        total_batches = sum(len(v) for v in self.p0_batch_buffer.values())
        return {
            "active_channels": len(self.last_send_time),
            "batch_queues": len(self.p0_batch_buffer),
            "total_batched_notifications": total_batches
        }
