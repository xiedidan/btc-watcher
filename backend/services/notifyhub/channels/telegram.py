"""
Telegram Bot 通知渠道
Telegram Bot Notification Channel
"""
import aiohttp
from typing import Dict, Any, Optional
import logging
from .base import NotificationChannel

logger = logging.getLogger(__name__)


class TelegramChannel(NotificationChannel):
    """Telegram Bot 通知渠道"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化Telegram渠道

        Args:
            config: 配置字典，必须包含：
                - bot_token: Telegram Bot Token
                - chat_id: Chat ID
        """
        super().__init__(config)
        self.bot_token = config.get("bot_token")
        self.chat_id = config.get("chat_id")

        if not self.bot_token or not self.chat_id:
            raise ValueError("Telegram channel requires 'bot_token' and 'chat_id' in config")

    async def send(
        self,
        message: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        发送Telegram消息

        Args:
            message: 消息内容
            title: 消息标题
            metadata: 元数据

        Returns:
            bool: 发送是否成功
        """
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

            # 格式化消息
            formatted_message = self._format_message_with_metadata(message, title, metadata)

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json={
                        "chat_id": self.chat_id,
                        "text": formatted_message,
                        "parse_mode": "Markdown"
                    },
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        logger.info(f"Telegram notification sent successfully to chat_id {self.chat_id}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Telegram API error: {response.status}, {error_text}")
                        return False

        except aiohttp.ClientError as e:
            logger.error(f"Telegram client error: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}", exc_info=True)
            return False

    async def test_connection(self) -> bool:
        """
        测试Telegram连接

        Returns:
            bool: 连接是否正常
        """
        try:
            test_message = "🔔 Telegram通知测试\n\n这是一条测试消息，用于验证Telegram通知渠道配置是否正确。"
            return await self.send(
                test_message,
                "测试通知",
                {"priority": "P1", "notification_type": "info"}
            )
        except Exception as e:
            logger.error(f"Telegram connection test failed: {e}", exc_info=True)
            return False
