"""
飞书 Webhook 通知渠道
Feishu Webhook Notification Channel
"""
import aiohttp
from typing import Dict, Any, Optional
import logging
from .base import NotificationChannel

logger = logging.getLogger(__name__)


class FeishuChannel(NotificationChannel):
    """飞书 Webhook 通知渠道"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化飞书渠道

        Args:
            config: 配置字典，必须包含：
                - webhook_url: 飞书Webhook URL
        """
        super().__init__(config)
        self.webhook_url = config.get("webhook_url")

        if not self.webhook_url:
            raise ValueError("Feishu channel requires 'webhook_url' in config")

    async def send(
        self,
        message: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        发送飞书消息（使用卡片消息格式）

        Args:
            message: 消息内容
            title: 消息标题
            metadata: 元数据

        Returns:
            bool: 发送是否成功
        """
        try:
            # 构建飞书卡片消息
            card_content = self._build_card_content(message, title, metadata)

            payload = {
                "msg_type": "interactive",
                "card": card_content
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("code") == 0:
                            logger.info("Feishu notification sent successfully")
                            return True
                        else:
                            logger.error(f"Feishu API error: {result.get('msg')}")
                            return False
                    else:
                        error_text = await response.text()
                        logger.error(f"Feishu webhook error: {response.status}, {error_text}")
                        return False

        except Exception as e:
            logger.error(f"Failed to send Feishu notification: {e}", exc_info=True)
            return False

    def _build_card_content(
        self,
        message: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        构建飞书卡片消息内容

        Args:
            message: 消息内容
            title: 标题
            metadata: 元数据

        Returns:
            Dict: 卡片内容
        """
        # 获取颜色模板
        template = self._get_feishu_template(metadata)

        # 构建卡片标题
        card_title = title or "通知"
        if metadata:
            type_emoji = self._get_type_emoji(metadata.get("notification_type", "info"))
            priority_emoji = self._get_priority_color(metadata.get("priority", "P1"))
            card_title = f"{type_emoji} {priority_emoji} {card_title}"

        card = {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": card_title
                },
                "template": template
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "plain_text",
                        "content": message
                    }
                }
            ]
        }

        # 添加元数据字段
        if metadata:
            fields = []
            priority = metadata.get("priority", "P1")
            notification_type = metadata.get("notification_type", "info")

            fields.append({
                "is_short": True,
                "text": {
                    "tag": "lark_md",
                    "content": f"**优先级**\n{priority}"
                }
            })
            fields.append({
                "is_short": True,
                "text": {
                    "tag": "lark_md",
                    "content": f"**类型**\n{notification_type}"
                }
            })

            card["elements"].append({
                "tag": "div",
                "fields": fields
            })

        return card

    def _get_feishu_template(self, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        根据优先级和类型返回飞书卡片模板颜色

        Args:
            metadata: 元数据

        Returns:
            str: 飞书模板颜色 (red/orange/grey/blue/green等)
        """
        if not metadata:
            return "blue"

        priority = metadata.get("priority", "P1")
        notification_type = metadata.get("notification_type", "info")

        # 根据优先级设置颜色
        if priority == "P2":
            return "red"  # 高优先级
        elif priority == "P1":
            return "orange"  # 中优先级
        elif priority == "P0":
            return "grey"  # 低优先级

        # 根据通知类型设置颜色
        if notification_type == "alert":
            return "red"
        elif notification_type == "signal":
            return "green"
        elif notification_type == "info":
            return "blue"

        return "blue"

    async def test_connection(self) -> bool:
        """
        测试飞书连接

        Returns:
            bool: 连接是否正常
        """
        try:
            test_message = "🔔 飞书通知测试\n\n这是一条测试消息，用于验证飞书通知渠道配置是否正确。"
            return await self.send(
                test_message,
                "测试通知",
                {"priority": "P1", "notification_type": "info"}
            )
        except Exception as e:
            logger.error(f"Feishu connection test failed: {e}", exc_info=True)
            return False
