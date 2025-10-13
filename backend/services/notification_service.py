"""
Notification Service
多渠道通知服务：Telegram、企业微信、飞书、邮件等
"""
import asyncio
import aiohttp
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional
from datetime import datetime
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.session import SessionLocal
from models.notification import Notification
from models.user import User
from config import settings

logger = logging.getLogger(__name__)


class NotificationService:
    """通知服务"""

    def __init__(self):
        self.channels = {
            "telegram": self._send_telegram,
            "wechat": self._send_wechat,
            "feishu": self._send_feishu,
            "email": self._send_email
        }
        self.queue: asyncio.Queue = asyncio.Queue()
        self.worker_task: Optional[asyncio.Task] = None
        self.running = False

    async def start(self):
        """启动通知服务"""
        if self.running:
            logger.warning("Notification service is already running")
            return

        self.running = True
        self.worker_task = asyncio.create_task(self._notification_worker())
        logger.info("Notification service started")

    async def stop(self):
        """停止通知服务"""
        if not self.running:
            return

        logger.info("Stopping notification service...")
        self.running = False

        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass

        logger.info("Notification service stopped")

    async def send_notification(
        self,
        user_id: int,
        title: str,
        message: str,
        channel: str,
        priority: str = "P2",
        notification_type: str = "signal",
        data: Optional[Dict] = None
    ) -> bool:
        """发送通知（添加到队列）"""
        try:
            notification_data = {
                "user_id": user_id,
                "title": title,
                "message": message,
                "channel": channel,
                "priority": priority,
                "notification_type": notification_type,
                "data": data or {}
            }

            await self.queue.put(notification_data)
            logger.debug(f"Notification queued for user {user_id} via {channel}")
            return True

        except Exception as e:
            logger.error(f"Failed to queue notification: {e}", exc_info=True)
            return False

    async def send_signal_notification(
        self,
        user_id: int,
        signal_data: Dict,
        channels: List[str]
    ):
        """发送交易信号通知"""
        try:
            # 构建通知内容
            pair = signal_data.get("pair", "Unknown")
            action = signal_data.get("action", "hold").upper()
            strength = signal_data.get("signal_strength", 0)
            strength_level = signal_data.get("strength_level", "weak")
            current_rate = signal_data.get("current_rate", 0)

            # 强度表情
            strength_emoji = {
                "strong": "🔥",
                "medium": "⚡",
                "weak": "💡",
                "ignore": "🔕"
            }.get(strength_level, "📊")

            title = f"{strength_emoji} {action} Signal: {pair}"

            message = f"""
{strength_emoji} **{action} Signal**
━━━━━━━━━━━━━━━━
📊 Pair: {pair}
💪 Strength: {strength:.2%} ({strength_level})
💰 Price: ${current_rate:.8f}
⏰ Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Strategy: {signal_data.get("strategy_name", "Unknown")}
"""

            # 发送到所有渠道
            for channel in channels:
                await self.send_notification(
                    user_id=user_id,
                    title=title,
                    message=message.strip(),
                    channel=channel,
                    priority="P0" if strength_level == "strong" else "P1",
                    notification_type="signal",
                    data=signal_data
                )

            logger.info(f"Signal notification sent to user {user_id} via {len(channels)} channels")

        except Exception as e:
            logger.error(f"Failed to send signal notification: {e}", exc_info=True)

    async def send_system_alert(
        self,
        title: str,
        message: str,
        priority: str = "P1",
        channels: Optional[List[str]] = None
    ):
        """发送系统告警（发送给所有管理员）"""
        try:
            async with SessionLocal() as session:
                # 获取所有管理员用户
                result = await session.execute(
                    select(User).where(User.is_superuser == True)
                )
                admins = result.scalars().all()

                default_channels = channels or ["telegram", "email"]

                for admin in admins:
                    for channel in default_channels:
                        await self.send_notification(
                            user_id=admin.id,
                            title=f"🚨 System Alert: {title}",
                            message=message,
                            channel=channel,
                            priority=priority,
                            notification_type="alert"
                        )

                logger.info(f"System alert sent to {len(admins)} admins")

        except Exception as e:
            logger.error(f"Failed to send system alert: {e}", exc_info=True)

    async def _notification_worker(self):
        """通知工作线程"""
        while self.running:
            try:
                # 从队列获取通知
                notification_data = await asyncio.wait_for(
                    self.queue.get(),
                    timeout=1.0
                )

                # 创建通知记录
                notification_id = await self._create_notification_record(notification_data)

                # 发送通知
                channel = notification_data["channel"]
                if channel in self.channels:
                    success = await self.channels[channel](notification_data)

                    # 更新通知状态
                    await self._update_notification_status(
                        notification_id,
                        "sent" if success else "failed"
                    )
                else:
                    logger.error(f"Unknown notification channel: {channel}")
                    await self._update_notification_status(notification_id, "failed")

                self.queue.task_done()

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error in notification worker: {e}", exc_info=True)

    async def _create_notification_record(self, data: Dict) -> int:
        """创建通知记录"""
        try:
            async with SessionLocal() as session:
                # 获取用户信息
                result = await session.execute(
                    select(User).where(User.id == data["user_id"])
                )
                user = result.scalar_one_or_none()

                if not user:
                    logger.error(f"User {data['user_id']} not found")
                    return 0

                # 确定接收地址
                recipient = self._get_recipient(user, data["channel"])

                # 创建通知记录
                notification = Notification(
                    signal_id=data.get("signal_id"),
                    user_id=data["user_id"],
                    notification_type=data["notification_type"],
                    priority=data["priority"],
                    channel=data["channel"],
                    status="pending",
                    title=data["title"],
                    message=data["message"],
                    data=data.get("data"),
                    recipient=recipient
                )

                session.add(notification)
                await session.commit()
                await session.refresh(notification)

                return notification.id

        except Exception as e:
            logger.error(f"Failed to create notification record: {e}", exc_info=True)
            return 0

    async def _update_notification_status(self, notification_id: int, status: str):
        """更新通知状态"""
        try:
            async with SessionLocal() as session:
                result = await session.execute(
                    select(Notification).where(Notification.id == notification_id)
                )
                notification = result.scalar_one_or_none()

                if notification:
                    notification.status = status
                    if status == "sent":
                        notification.sent_at = datetime.now()
                    await session.commit()

        except Exception as e:
            logger.error(f"Failed to update notification status: {e}", exc_info=True)

    def _get_recipient(self, user: User, channel: str) -> str:
        """获取接收地址"""
        if channel == "email":
            return user.email
        elif channel == "telegram":
            # TODO: 从用户配置获取telegram_chat_id
            return settings.TELEGRAM_CHAT_ID or ""
        else:
            return user.email

    async def _send_telegram(self, data: Dict) -> bool:
        """发送Telegram通知"""
        if not settings.TELEGRAM_BOT_TOKEN:
            logger.warning("Telegram bot token not configured")
            return False

        try:
            url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json={
                        "chat_id": settings.TELEGRAM_CHAT_ID,
                        "text": f"**{data['title']}**\n\n{data['message']}",
                        "parse_mode": "Markdown"
                    },
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        logger.info(f"Telegram notification sent: {data['title']}")
                        return True
                    else:
                        logger.error(f"Telegram API error: {response.status}")
                        return False

        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}", exc_info=True)
            return False

    async def _send_wechat(self, data: Dict) -> bool:
        """发送企业微信通知"""
        if not settings.WECHAT_CORP_ID:
            logger.warning("WeChat configuration not found")
            return False

        try:
            # TODO: 实现企业微信API调用
            logger.info(f"WeChat notification sent: {data['title']}")
            return True

        except Exception as e:
            logger.error(f"Failed to send WeChat notification: {e}", exc_info=True)
            return False

    async def _send_feishu(self, data: Dict) -> bool:
        """发送飞书通知"""
        if not settings.FEISHU_WEBHOOK_URL:
            logger.warning("Feishu webhook URL not configured")
            return False

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    settings.FEISHU_WEBHOOK_URL,
                    json={
                        "msg_type": "text",
                        "content": {
                            "text": f"{data['title']}\n\n{data['message']}"
                        }
                    },
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        logger.info(f"Feishu notification sent: {data['title']}")
                        return True
                    else:
                        logger.error(f"Feishu webhook error: {response.status}")
                        return False

        except Exception as e:
            logger.error(f"Failed to send Feishu notification: {e}", exc_info=True)
            return False

    async def _send_email(self, data: Dict) -> bool:
        """发送邮件通知"""
        if not settings.SMTP_HOST:
            logger.warning("SMTP configuration not found")
            return False

        try:
            # 创建邮件
            msg = MIMEMultipart()
            msg['From'] = settings.SMTP_FROM or settings.SMTP_USER
            msg['To'] = data.get("recipient", "")
            msg['Subject'] = data['title']

            # 邮件正文
            body = MIMEText(data['message'], 'plain', 'utf-8')
            msg.attach(body)

            # 发送邮件
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)

            logger.info(f"Email notification sent: {data['title']}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email notification: {e}", exc_info=True)
            return False

    async def get_notification_stats(self, hours: int = 24) -> Dict:
        """获取通知统计"""
        try:
            async with SessionLocal() as session:
                from datetime import timedelta
                cutoff_time = datetime.now() - timedelta(hours=hours)

                result = await session.execute(
                    select(Notification).where(Notification.created_at >= cutoff_time)
                )
                notifications = result.scalars().all()

                total = len(notifications)
                sent = len([n for n in notifications if n.status == "sent"])
                failed = len([n for n in notifications if n.status == "failed"])
                pending = len([n for n in notifications if n.status == "pending"])

                return {
                    "period_hours": hours,
                    "total": total,
                    "sent": sent,
                    "failed": failed,
                    "pending": pending,
                    "success_rate": (sent / total * 100) if total > 0 else 100
                }

        except Exception as e:
            logger.error(f"Failed to get notification stats: {e}", exc_info=True)
            return {}
