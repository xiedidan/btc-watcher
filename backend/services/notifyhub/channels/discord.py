"""
Discord Bot/Webhook 通知渠道
Discord Bot/Webhook Notification Channel
"""
import aiohttp
from typing import Dict, Any, Optional
from datetime import datetime
import logging
import os
from .base import NotificationChannel

logger = logging.getLogger(__name__)


class DiscordChannel(NotificationChannel):
    """Discord Bot/Webhook 通知渠道"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化Discord渠道

        支持两种模式：
        1. Webhook模式：只需要webhook_url
        2. Bot模式：需要bot_token和channel_id

        Args:
            config: 配置字典，可以包含：
                - webhook_url: Discord Webhook URL（Webhook模式）
                - bot_token: Discord Bot Token（Bot模式）
                - channel_id: Discord Channel ID（Bot模式）
        """
        super().__init__(config)
        self.webhook_url = config.get("webhook_url")
        self.bot_token = config.get("bot_token")
        self.channel_id = config.get("channel_id")

        if not self.webhook_url and not (self.bot_token and self.channel_id):
            raise ValueError(
                "Discord channel requires either 'webhook_url' or both 'bot_token' and 'channel_id' in config"
            )

    async def send(
        self,
        message: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        发送Discord消息

        Args:
            message: 消息内容
            title: 消息标题
            metadata: 元数据

        Returns:
            bool: 发送是否成功
        """
        if self.webhook_url:
            return await self._send_via_webhook(message, title, metadata)
        elif self.bot_token and self.channel_id:
            return await self._send_via_bot(message, title, metadata)
        else:
            logger.error("Discord channel not properly configured")
            return False

    async def _send_via_webhook(
        self,
        message: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """通过Webhook发送消息"""
        try:
            # 构建Discord Embed消息
            embed = {
                "title": title or "通知",
                "description": message,
                "color": self._get_discord_color(metadata),
                "timestamp": datetime.utcnow().isoformat()
            }

            # 添加元数据字段
            if metadata:
                fields = []
                priority = metadata.get("priority", "P1")
                notification_type = metadata.get("notification_type", "info")

                fields.append({
                    "name": "优先级",
                    "value": f"**{priority}**",
                    "inline": True
                })
                fields.append({
                    "name": "类型",
                    "value": notification_type,
                    "inline": True
                })

                embed["fields"] = fields

            payload = {
                "embeds": [embed]
            }

            # 获取代理配置
            proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
            if not proxy:
                proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")

            # 修正可能的代理URL格式问题（http:127.0.0.1 -> http://127.0.0.1）
            if proxy and not proxy.startswith(("http://", "https://", "socks://")):
                proxy = f"http://{proxy}"

            logger.info(f"Using proxy for Discord: {proxy}")

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    proxy=proxy,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 204:
                        logger.info("Discord webhook notification sent successfully")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Discord webhook error: {response.status}, {error_text}")
                        return False

        except Exception as e:
            logger.error(f"Failed to send Discord webhook notification: {e}", exc_info=True)
            return False

    async def _send_via_bot(
        self,
        message: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """通过Bot API发送消息"""
        try:
            url = f"https://discord.com/api/v10/channels/{self.channel_id}/messages"

            headers = {
                "Authorization": f"Bot {self.bot_token}",
                "Content-Type": "application/json"
            }

            # 构建Discord Embed消息
            embed = {
                "title": title or "通知",
                "description": message,
                "color": self._get_discord_color(metadata),
                "timestamp": datetime.utcnow().isoformat()
            }

            payload = {
                "embeds": [embed]
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        logger.info("Discord bot notification sent successfully")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Discord bot error: {response.status}, {error_text}")
                        return False

        except Exception as e:
            logger.error(f"Failed to send Discord bot notification: {e}", exc_info=True)
            return False

    def _get_discord_color(self, metadata: Optional[Dict[str, Any]] = None) -> int:
        """
        根据优先级和类型返回Discord颜色值

        Args:
            metadata: 元数据

        Returns:
            int: Discord颜色值
        """
        if not metadata:
            return 0x3498db  # 默认蓝色

        priority = metadata.get("priority", "P1")
        notification_type = metadata.get("notification_type", "info")

        # 根据优先级设置颜色
        if priority == "P2":
            return 0xe74c3c  # 红色（高优先级）
        elif priority == "P1":
            return 0xf39c12  # 橙色（中优先级）
        elif priority == "P0":
            return 0x95a5a6  # 灰色（低优先级）

        # 根据通知类型设置颜色
        if notification_type == "alert":
            return 0xe74c3c  # 红色
        elif notification_type == "signal":
            return 0x2ecc71  # 绿色
        elif notification_type == "info":
            return 0x3498db  # 蓝色

        return 0x3498db  # 默认蓝色

    async def test_connection(self) -> bool:
        """
        测试Discord连接

        Returns:
            bool: 连接是否正常
        """
        try:
            test_message = "🔔 Discord通知测试\n\n这是一条测试消息，用于验证Discord通知渠道配置是否正确。"
            return await self.send(
                test_message,
                "测试通知",
                {"priority": "P1", "notification_type": "info"}
            )
        except Exception as e:
            logger.error(f"Discord connection test failed: {e}", exc_info=True)
            return False
