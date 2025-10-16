"""
Monitoring Data Broadcaster
监控数据广播服务

功能：
- 定期获取监控数据
- 通过WebSocket广播给订阅的客户端
- 支持不同频率的数据推送
- 支持不同主题的数据推送
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.websocket.manager import manager
from services.monitoring_service import MonitoringService
from database.session import SessionLocal
from models.signal import Signal
from models.strategy import Strategy

logger = logging.getLogger(__name__)


class MonitoringBroadcaster:
    """监控数据广播服务"""

    def __init__(self, monitoring_service: MonitoringService):
        """
        初始化广播服务

        Args:
            monitoring_service: 监控服务实例
        """
        self.monitoring_service = monitoring_service
        self.running = False
        self.broadcast_tasks = {}

        # 广播间隔配置（秒）
        self.intervals = {
            "monitoring": 5,      # 系统监控数据 - 每5秒
            "strategies": 10,     # 策略状态 - 每10秒
            "signals": 3,         # 新信号 - 每3秒
            "capacity": 60,       # 容量趋势 - 每60秒
        }

    async def start(self):
        """启动广播服务"""
        if self.running:
            logger.warning("Monitoring broadcaster is already running")
            return

        self.running = True
        logger.info("Starting monitoring broadcaster...")

        # 启动心跳检测
        await manager.start_heartbeat_checker()

        # 启动各个广播任务
        self.broadcast_tasks["monitoring"] = asyncio.create_task(
            self._broadcast_monitoring_data()
        )
        self.broadcast_tasks["strategies"] = asyncio.create_task(
            self._broadcast_strategies_status()
        )
        self.broadcast_tasks["signals"] = asyncio.create_task(
            self._broadcast_new_signals()
        )
        self.broadcast_tasks["capacity"] = asyncio.create_task(
            self._broadcast_capacity_data()
        )

        logger.info("Monitoring broadcaster started successfully")

    async def stop(self):
        """停止广播服务"""
        if not self.running:
            return

        logger.info("Stopping monitoring broadcaster...")
        self.running = False

        # 停止心跳检测
        await manager.stop_heartbeat_checker()

        # 取消所有广播任务
        for task_name, task in self.broadcast_tasks.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                logger.debug(f"Broadcast task {task_name} cancelled")

        self.broadcast_tasks.clear()
        logger.info("Monitoring broadcaster stopped")

    async def _broadcast_monitoring_data(self):
        """广播系统监控数据"""
        interval = self.intervals["monitoring"]

        while self.running:
            try:
                # 获取系统指标
                system_metrics = self.monitoring_service.get_system_metrics()

                if system_metrics:
                    # 获取健康状态
                    health_status = self.monitoring_service.get_health_status()

                    # 构建消息
                    message = {
                        "type": "data",
                        "topic": "monitoring",
                        "data": {
                            "system": system_metrics,
                            "health": health_status
                        },
                        "timestamp": datetime.now().isoformat()
                    }

                    # 广播给订阅monitoring主题的客户端
                    await manager.broadcast(message, topic="monitoring")

                    logger.debug(f"Broadcasted monitoring data to {len(manager.subscriptions['monitoring'])} clients")

            except Exception as e:
                logger.error(f"Error broadcasting monitoring data: {e}", exc_info=True)

            await asyncio.sleep(interval)

    async def _broadcast_strategies_status(self):
        """广播策略状态"""
        interval = self.intervals["strategies"]

        while self.running:
            try:
                # 获取策略指标
                strategy_metrics = self.monitoring_service.get_strategy_metrics()

                # 从数据库获取策略列表
                async with SessionLocal() as session:
                    result = await session.execute(select(Strategy))
                    strategies = result.scalars().all()

                    strategies_data = []
                    for strategy in strategies:
                        # 合并数据库信息和监控指标
                        strategy_data = {
                            "id": strategy.id,
                            "name": strategy.name,
                            "status": strategy.status,
                            "description": strategy.description,
                            "strategy_class": strategy.strategy_class,
                            "exchange": strategy.exchange,
                            "timeframe": strategy.timeframe,
                            "is_active": strategy.is_active,
                            "port": strategy.port,
                            "created_at": strategy.created_at.isoformat() if strategy.created_at else None,
                            "started_at": strategy.started_at.isoformat() if strategy.started_at else None,
                        }

                        # 添加监控指标
                        if strategy.id in strategy_metrics:
                            strategy_data["metrics"] = strategy_metrics[strategy.id]

                        strategies_data.append(strategy_data)

                # 构建消息
                message = {
                    "type": "data",
                    "topic": "strategies",
                    "data": {
                        "strategies": strategies_data,
                        "total": len(strategies_data),
                        "running": sum(1 for s in strategies_data if s["status"] == "running"),
                        "stopped": sum(1 for s in strategies_data if s["status"] == "stopped"),
                        "error": sum(1 for s in strategies_data if s["status"] == "error")
                    },
                    "timestamp": datetime.now().isoformat()
                }

                # 广播给订阅strategies主题的客户端
                await manager.broadcast(message, topic="strategies")

                logger.debug(f"Broadcasted strategies status to {len(manager.subscriptions['strategies'])} clients")

            except Exception as e:
                logger.error(f"Error broadcasting strategies status: {e}", exc_info=True)

            await asyncio.sleep(interval)

    async def _broadcast_new_signals(self):
        """广播新信号"""
        interval = self.intervals["signals"]
        last_signal_id = 0

        while self.running:
            try:
                async with SessionLocal() as session:
                    # 获取最新的信号（ID大于last_signal_id）
                    result = await session.execute(
                        select(Signal)
                        .where(Signal.id > last_signal_id)
                        .order_by(Signal.id.desc())
                        .limit(10)
                    )
                    new_signals = result.scalars().all()

                    if new_signals:
                        # 更新last_signal_id
                        last_signal_id = max(signal.id for signal in new_signals)

                        # 构建信号数据
                        signals_data = []
                        for signal in reversed(new_signals):  # 按时间正序
                            signals_data.append({
                                "id": signal.id,
                                "strategy_id": signal.strategy_id,
                                "pair": signal.pair,
                                "action": signal.action,
                                "current_rate": float(signal.current_rate) if signal.current_rate else None,
                                "amount": float(signal.amount) if signal.amount else None,
                                "stake_amount": float(signal.stake_amount) if signal.stake_amount else None,
                                "profit_ratio": float(signal.profit_ratio) if signal.profit_ratio else None,
                                "signal_strength": signal.signal_strength,
                                "indicators": signal.indicators,
                                "message": signal.message,
                                "created_at": signal.created_at.isoformat() if signal.created_at else None
                            })

                        # 构建消息
                        message = {
                            "type": "data",
                            "topic": "signals",
                            "data": {
                                "signals": signals_data,
                                "count": len(signals_data)
                            },
                            "timestamp": datetime.now().isoformat()
                        }

                        # 广播给订阅signals主题的客户端
                        await manager.broadcast(message, topic="signals")

                        logger.info(f"Broadcasted {len(signals_data)} new signals to {len(manager.subscriptions['signals'])} clients")

            except Exception as e:
                logger.error(f"Error broadcasting new signals: {e}", exc_info=True)

            await asyncio.sleep(interval)

    async def _broadcast_capacity_data(self):
        """广播容量数据"""
        interval = self.intervals["capacity"]

        while self.running:
            try:
                # 获取容量趋势（最近24小时）
                capacity_trend = self.monitoring_service.get_capacity_trend(hours=24)

                if capacity_trend:
                    # 获取最新的容量信息
                    latest_capacity = capacity_trend[-1] if capacity_trend else {}

                    # 构建消息
                    message = {
                        "type": "data",
                        "topic": "capacity",
                        "data": {
                            "current": latest_capacity,
                            "trend": capacity_trend,
                            "trend_count": len(capacity_trend)
                        },
                        "timestamp": datetime.now().isoformat()
                    }

                    # 广播给订阅capacity主题的客户端
                    await manager.broadcast(message, topic="capacity")

                    logger.debug(f"Broadcasted capacity data to {len(manager.subscriptions['capacity'])} clients")

            except Exception as e:
                logger.error(f"Error broadcasting capacity data: {e}", exc_info=True)

            await asyncio.sleep(interval)

    async def broadcast_event(self, event_type: str, data: dict, topic: Optional[str] = None):
        """
        广播事件消息

        Args:
            event_type: 事件类型 (strategy_started, strategy_stopped, signal_received, etc.)
            data: 事件数据
            topic: 主题（如果不指定，广播给所有连接）
        """
        try:
            message = {
                "type": "event",
                "event_type": event_type,
                "data": data,
                "timestamp": datetime.now().isoformat()
            }

            await manager.broadcast(message, topic=topic)
            logger.info(f"Broadcasted event '{event_type}' to topic '{topic or 'all'}'")

        except Exception as e:
            logger.error(f"Error broadcasting event: {e}", exc_info=True)

    async def send_notification(self, client_id: str, notification: dict):
        """
        发送个人通知

        Args:
            client_id: 客户端ID
            notification: 通知内容
        """
        try:
            message = {
                "type": "notification",
                "data": notification,
                "timestamp": datetime.now().isoformat()
            }

            await manager.send_personal_message(message, client_id)
            logger.info(f"Sent notification to client {client_id}")

        except Exception as e:
            logger.error(f"Error sending notification: {e}", exc_info=True)

    def get_stats(self) -> dict:
        """
        获取广播服务统计

        Returns:
            {
                "running": True,
                "active_tasks": 4,
                "websocket_connections": 10,
                "subscriptions": {...}
            }
        """
        return {
            "running": self.running,
            "active_tasks": len(self.broadcast_tasks),
            "websocket_stats": manager.get_stats()
        }


# 全局广播服务实例（将在main.py中初始化）
broadcaster: Optional[MonitoringBroadcaster] = None
