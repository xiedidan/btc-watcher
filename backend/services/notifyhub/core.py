"""
NotifyHub 核心服务
NotifyHub Core Service - 统一的通知入口
"""
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from database.session import SessionLocal
from models.notification import NotificationHistory, NotificationChannelConfig

from .router import NotifyRouter
from .frequency_controller import FrequencyController
from .time_rule_manager import TimeRuleManager
from .channels import TelegramChannel, DiscordChannel, FeishuChannel, NotificationChannel

logger = logging.getLogger(__name__)


class NotifyHub:
    """
    NotifyHub 通知中心

    统一的通知入口，业务代码只需要调用 notify() 方法

    特性：
    - 统一入口：业务代码只需调用一个API
    - 智能路由：根据用户配置自动选择通知渠道
    - 优先级管理：P0(低)/P1(中)/P2(高)三级优先级
    - 频率控制：防止通知轰炸
    - 时间规则：勿扰时段、工作时间等
    - 批量发送：低优先级通知自动批量合并
    """

    def __init__(self):
        self.frequency_controller = FrequencyController()
        self.time_rule_manager = TimeRuleManager()
        self.router = NotifyRouter(self.frequency_controller, self.time_rule_manager)

        self.queue: asyncio.Queue = asyncio.Queue()
        self.worker_task: Optional[asyncio.Task] = None
        self.batch_task: Optional[asyncio.Task] = None
        self.running = False

        # 渠道实例缓存 {(user_id, channel_type): channel_instance}
        self.channel_cache: Dict[tuple, NotificationChannel] = {}

    async def start(self):
        """启动NotifyHub服务"""
        if self.running:
            logger.warning("NotifyHub is already running")
            return

        self.running = True
        self.worker_task = asyncio.create_task(self._notification_worker())
        self.batch_task = asyncio.create_task(self._batch_worker())
        logger.info("NotifyHub started")

    async def stop(self):
        """停止NotifyHub服务"""
        if not self.running:
            return

        logger.info("Stopping NotifyHub...")
        self.running = False

        # 取消工作线程
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass

        if self.batch_task:
            self.batch_task.cancel()
            try:
                await self.batch_task
            except asyncio.CancelledError:
                pass

        # 清理缓存
        self.channel_cache.clear()

        logger.info("NotifyHub stopped")

    async def notify(
        self,
        user_id: int,
        title: str,
        message: str,
        notification_type: str,
        priority: str = "P1",
        metadata: Optional[Dict] = None,
        strategy_id: Optional[int] = None,
        signal_id: Optional[int] = None
    ) -> bool:
        """
        发送通知 - 统一入口

        Args:
            user_id: 用户ID
            title: 通知标题
            message: 通知内容
            notification_type: 通知类型 (signal/alert/info/system)
            priority: 优先级 (P0/P1/P2)
            metadata: 元数据
            strategy_id: 关联的策略ID（可选）
            signal_id: 关联的信号ID（可选）

        Returns:
            bool: 是否成功加入发送队列

        使用示例:
            await notify_hub.notify(
                user_id=1,
                title="强买入信号",
                message="BTC/USDT 出现强买入信号，信号强度85%",
                notification_type="signal",
                priority="P2",
                metadata={"pair": "BTC/USDT", "strength": 0.85},
                strategy_id=10,
                signal_id=12345
            )
        """
        try:
            notification_data = {
                "user_id": user_id,
                "title": title,
                "message": message,
                "notification_type": notification_type,
                "priority": priority,
                "metadata": metadata or {},
                "strategy_id": strategy_id,
                "signal_id": signal_id,
                "created_at": datetime.now().isoformat()
            }

            await self.queue.put(notification_data)
            logger.debug(f"Notification queued for user {user_id}, priority={priority}")
            return True

        except Exception as e:
            logger.error(f"Failed to queue notification: {e}", exc_info=True)
            return False

    async def _notification_worker(self):
        """通知工作线程 - 处理队列中的通知"""
        while self.running:
            try:
                notification_data = await asyncio.wait_for(
                    self.queue.get(),
                    timeout=1.0
                )

                async with SessionLocal() as db:
                    await self._process_notification(db, notification_data)

                self.queue.task_done()

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error in notification worker: {e}", exc_info=True)

    async def _batch_worker(self):
        """批量发送工作线程 - 定期发送P0通知"""
        while self.running:
            try:
                # 等待5分钟（默认批量间隔）
                await asyncio.sleep(300)

                async with SessionLocal() as db:
                    await self._flush_all_batches(db)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in batch worker: {e}", exc_info=True)

    async def _process_notification(self, db: AsyncSession, notification_data: Dict):
        """处理单个通知"""
        try:
            user_id = notification_data["user_id"]
            priority = notification_data["priority"]

            # 1. 路由：决定发送到哪些渠道
            channels = await self.router.route(db, notification_data)

            if not channels:
                logger.info(f"No channels selected for notification (user={user_id})")
                return

            # 2. 获取频率配置和时间规则
            frequency_config = await self.router.get_frequency_config(db, user_id)
            time_rule = await self.router.get_time_rule(db, user_id)

            # 3. 为每个渠道发送通知
            for channel_type in channels:
                await self._send_to_channel(
                    db,
                    channel_type,
                    notification_data,
                    frequency_config,
                    time_rule
                )

        except Exception as e:
            logger.error(f"Failed to process notification: {e}", exc_info=True)

    async def _send_to_channel(
        self,
        db: AsyncSession,
        channel_type: str,
        notification_data: Dict,
        frequency_config: Optional[Dict],
        time_rule: Optional[Dict]
    ):
        """发送通知到指定渠道"""
        try:
            user_id = notification_data["user_id"]
            priority = notification_data["priority"]

            # 1. 检查时间规则
            should_send_now, time_reason = await self.time_rule_manager.should_send_at_current_time(
                time_rule,
                priority
            )

            if not should_send_now:
                logger.info(
                    f"Notification blocked by time rule for user {user_id}, "
                    f"channel {channel_type}: {time_reason}"
                )
                return

            # 2. 检查频率限制
            should_send, freq_reason = await self.frequency_controller.should_send(
                user_id,
                channel_type,
                priority,
                frequency_config
            )

            if not should_send:
                if freq_reason == "batched":
                    # 加入批量队列
                    self.frequency_controller.add_to_batch(user_id, channel_type, notification_data)
                    logger.debug(f"Notification added to batch queue: user={user_id}, channel={channel_type}")
                else:
                    logger.info(
                        f"Notification blocked by frequency control: user={user_id}, "
                        f"channel={channel_type}, reason={freq_reason}"
                    )
                return

            # 3. 创建通知历史记录
            history_id = await self._create_notification_history(
                db,
                channel_type,
                notification_data
            )

            # 4. 获取渠道配置并发送
            channel_config = await self.router.get_channel_config(db, user_id, channel_type)

            if not channel_config:
                logger.error(f"No config found for channel {channel_type}, user {user_id}")
                await self._update_history_status(db, history_id, "failed", "Channel config not found")
                return

            # 5. 获取或创建渠道实例
            channel = await self._get_channel_instance(user_id, channel_type, channel_config)

            if not channel:
                logger.error(f"Failed to create channel instance: {channel_type}")
                await self._update_history_status(db, history_id, "failed", "Failed to create channel")
                return

            # 6. 发送通知
            success = await channel.send(
                message=notification_data["message"],
                title=notification_data["title"],
                metadata=notification_data.get("metadata", {})
            )

            # 7. 更新通知状态
            status = "sent" if success else "failed"
            await self._update_history_status(db, history_id, status)

            # 8. 更新渠道统计
            if success:
                await self._update_channel_stats(db, user_id, channel_type, success=True)
            else:
                await self._update_channel_stats(db, user_id, channel_type, success=False)

            logger.info(f"Notification {status} via {channel_type} (history_id={history_id})")

        except Exception as e:
            logger.error(f"Failed to send notification via {channel_type}: {e}", exc_info=True)

    async def _flush_all_batches(self, db: AsyncSession):
        """刷新所有批量队列"""
        try:
            stats = self.frequency_controller.get_stats()
            batch_count = stats.get("batch_queues", 0)

            if batch_count == 0:
                return

            logger.info(f"Flushing {batch_count} batch queues...")

            # 获取所有批量队列
            for (user_id, channel), notifications in self.frequency_controller.p0_batch_buffer.items():
                if not notifications:
                    continue

                # 合并通知
                merged = self.frequency_controller.merge_p0_notifications(notifications)

                if merged:
                    # 发送合并后的通知
                    await self._send_merged_notification(db, user_id, channel, merged)

                # 清空队列
                self.frequency_controller.clear_batch_queue(user_id, channel)

            logger.info(f"Flushed {batch_count} batch queues")

        except Exception as e:
            logger.error(f"Failed to flush batches: {e}", exc_info=True)

    async def _send_merged_notification(
        self,
        db: AsyncSession,
        user_id: int,
        channel_type: str,
        merged_data: Dict
    ):
        """发送合并后的批量通知"""
        try:
            # 获取渠道配置
            channel_config = await self.router.get_channel_config(db, user_id, channel_type)

            if not channel_config:
                logger.error(f"No config found for channel {channel_type}, user {user_id}")
                return

            # 获取或创建渠道实例
            channel = await self._get_channel_instance(user_id, channel_type, channel_config)

            if not channel:
                logger.error(f"Failed to create channel instance: {channel_type}")
                return

            # 发送通知
            success = await channel.send(
                message=merged_data.get("message", ""),
                title=merged_data.get("title", ""),
                metadata=merged_data.get("metadata", {})
            )

            if success:
                logger.info(f"Batch notification sent via {channel_type} for user {user_id}")
            else:
                logger.error(f"Failed to send batch notification via {channel_type}")

        except Exception as e:
            logger.error(f"Failed to send merged notification: {e}", exc_info=True)

    async def _get_channel_instance(
        self,
        user_id: int,
        channel_type: str,
        channel_config: Dict
    ) -> Optional[NotificationChannel]:
        """获取或创建渠道实例"""
        cache_key = (user_id, channel_type)

        # 检查缓存
        if cache_key in self.channel_cache:
            return self.channel_cache[cache_key]

        # 创建新实例
        try:
            if channel_type == "telegram":
                channel = TelegramChannel(channel_config)
            elif channel_type == "discord":
                channel = DiscordChannel(channel_config)
            elif channel_type == "feishu":
                channel = FeishuChannel(channel_config)
            else:
                logger.error(f"Unknown channel type: {channel_type}")
                return None

            # 缓存实例
            self.channel_cache[cache_key] = channel
            return channel

        except Exception as e:
            logger.error(f"Failed to create channel instance {channel_type}: {e}", exc_info=True)
            return None

    async def _create_notification_history(
        self,
        db: AsyncSession,
        channel_type: str,
        notification_data: Dict
    ) -> int:
        """创建通知历史记录"""
        try:
            history = NotificationHistory(
                user_id=notification_data["user_id"],
                title=notification_data["title"],
                message=notification_data["message"],
                notification_type=notification_data["notification_type"],
                priority=notification_data["priority"],
                channel_type=channel_type,
                status="pending",
                signal_id=notification_data.get("signal_id"),
                strategy_id=notification_data.get("strategy_id"),
                extra_data=notification_data.get("metadata")
            )

            db.add(history)
            await db.commit()
            await db.refresh(history)

            return history.id

        except Exception as e:
            logger.error(f"Failed to create notification history: {e}", exc_info=True)
            return 0

    async def _update_history_status(
        self,
        db: AsyncSession,
        history_id: int,
        status: str,
        error_message: Optional[str] = None
    ):
        """更新通知历史状态"""
        try:
            from sqlalchemy import select

            result = await db.execute(
                select(NotificationHistory).where(NotificationHistory.id == history_id)
            )
            history = result.scalar_one_or_none()

            if history:
                history.status = status
                if status == "sent":
                    history.sent_at = datetime.now()
                if error_message:
                    history.error_message = error_message

                await db.commit()

        except Exception as e:
            logger.error(f"Failed to update notification history status: {e}", exc_info=True)

    async def _update_channel_stats(
        self,
        db: AsyncSession,
        user_id: int,
        channel_type: str,
        success: bool
    ):
        """更新渠道统计信息"""
        try:
            from sqlalchemy import select

            result = await db.execute(
                select(NotificationChannelConfig).where(
                    NotificationChannelConfig.user_id == user_id,
                    NotificationChannelConfig.channel_type == channel_type
                ).limit(1)
            )
            channel_config = result.scalar_one_or_none()

            if channel_config:
                if success:
                    channel_config.total_sent = (channel_config.total_sent or 0) + 1
                    channel_config.last_sent_at = datetime.now()
                else:
                    channel_config.total_failed = (channel_config.total_failed or 0) + 1
                    channel_config.last_error_at = datetime.now()

                await db.commit()

        except Exception as e:
            logger.error(f"Failed to update channel stats: {e}", exc_info=True)

    async def get_queue_status(self) -> Dict:
        """获取队列状态"""
        stats = self.frequency_controller.get_stats()
        return {
            "queue_size": self.queue.qsize(),
            "running": self.running,
            "batch_queues": stats.get("batch_queues", 0),
            "total_batched_notifications": stats.get("total_batched_notifications", 0)
        }


# 全局单例
notify_hub = NotifyHub()
