"""
WebSocket推送服务
WebSocket Push Service

功能：
- 推送新信号到订阅客户端
- 推送策略状态更新
- 推送系统监控数据
- 推送容量信息
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from app.websocket.manager import manager

logger = logging.getLogger(__name__)


class WebSocketService:
    """WebSocket推送服务"""

    @staticmethod
    async def push_new_signal(signal_data: Dict[str, Any]):
        """
        推送新信号到订阅了signals主题的客户端

        Args:
            signal_data: 信号数据
        """
        try:
            message = {
                "type": "data",
                "topic": "signals",
                "data": {
                    "signals": [signal_data]
                },
                "timestamp": datetime.now().isoformat()
            }

            await manager.broadcast(message, topic="signals")
            logger.info(f"Pushed new signal: {signal_data.get('id')} to {len(manager.subscriptions['signals'])} clients")

        except Exception as e:
            logger.error(f"Failed to push signal: {e}", exc_info=True)

    @staticmethod
    async def push_strategy_status(strategy_id: int, status: str, data: Optional[Dict[str, Any]] = None):
        """
        推送策略状态更新

        Args:
            strategy_id: 策略ID
            status: 状态 (started, stopped, error, running)
            data: 额外数据
        """
        try:
            event_type_map = {
                "started": "strategy_started",
                "stopped": "strategy_stopped",
                "error": "strategy_error",
                "running": "strategy_running"
            }

            message = {
                "type": "event",
                "event_type": event_type_map.get(status, "strategy_update"),
                "data": {
                    "strategy_id": strategy_id,
                    "status": status,
                    **(data or {})
                },
                "timestamp": datetime.now().isoformat()
            }

            # 广播给订阅strategies主题的客户端
            await manager.broadcast(message, topic="strategies")
            logger.info(f"Pushed strategy status update: strategy_id={strategy_id}, status={status}")

        except Exception as e:
            logger.error(f"Failed to push strategy status: {e}", exc_info=True)

    @staticmethod
    async def push_monitoring_data(monitoring_data: Dict[str, Any]):
        """
        推送系统监控数据

        Args:
            monitoring_data: 监控数据
        """
        try:
            message = {
                "type": "data",
                "topic": "monitoring",
                "data": monitoring_data,
                "timestamp": datetime.now().isoformat()
            }

            await manager.broadcast(message, topic="monitoring")
            logger.debug(f"Pushed monitoring data to {len(manager.subscriptions['monitoring'])} clients")

        except Exception as e:
            logger.error(f"Failed to push monitoring data: {e}", exc_info=True)

    @staticmethod
    async def push_capacity_update(capacity_data: Dict[str, Any]):
        """
        推送容量信息更新

        Args:
            capacity_data: 容量数据
        """
        try:
            message = {
                "type": "data",
                "topic": "capacity",
                "data": capacity_data,
                "timestamp": datetime.now().isoformat()
            }

            await manager.broadcast(message, topic="capacity")
            logger.debug(f"Pushed capacity data to {len(manager.subscriptions['capacity'])} clients")

        except Exception as e:
            logger.error(f"Failed to push capacity update: {e}", exc_info=True)

    @staticmethod
    async def push_system_alert(alert_type: str, message: str, level: str = "warning", data: Optional[Dict] = None):
        """
        推送系统告警

        Args:
            alert_type: 告警类型 (capacity_warning, strategy_error, system_error等)
            message: 告警消息
            level: 告警级别 (info, warning, error, critical)
            data: 额外数据
        """
        try:
            notification = {
                "type": "notification",
                "data": {
                    "alert_type": alert_type,
                    "title": f"System Alert: {alert_type}",
                    "message": message,
                    "level": level,
                    **(data or {})
                },
                "timestamp": datetime.now().isoformat()
            }

            # 广播给所有连接的客户端（系统告警应该所有人都看到）
            await manager.broadcast(notification)
            logger.warning(f"Pushed system alert: {alert_type} - {message}")

        except Exception as e:
            logger.error(f"Failed to push system alert: {e}", exc_info=True)

    @staticmethod
    async def push_log_entry(log_data: Dict[str, Any]):
        """
        推送日志条目到订阅了logs主题的客户端

        Args:
            log_data: 日志数据
        """
        try:
            message = {
                "type": "data",
                "topic": "logs",
                "data": log_data,
                "timestamp": datetime.now().isoformat()
            }

            await manager.broadcast(message, topic="logs")
            logger.debug(f"Pushed log entry to {len(manager.subscriptions['logs'])} clients")

        except Exception as e:
            logger.error(f"Failed to push log entry: {e}", exc_info=True)

    @staticmethod
    async def push_strategy_log(strategy_id: int, log_entry: Dict[str, Any]):
        """
        推送策略日志到订阅了该策略的客户端

        Args:
            strategy_id: 策略ID
            log_entry: 日志条目 (包含timestamp, level, logger, message, raw)
        """
        try:
            message = {
                "type": "data",
                "topic": f"strategy_{strategy_id}_logs",
                "data": {
                    "strategy_id": strategy_id,
                    "log": log_entry
                },
                "timestamp": datetime.now().isoformat()
            }

            # 推送给订阅该策略日志的客户端
            await manager.broadcast(message, topic=f"strategy_{strategy_id}_logs")
            logger.debug(f"Pushed log for strategy {strategy_id}")

        except Exception as e:
            logger.error(f"Failed to push strategy log: {e}", exc_info=True)


# 创建全局实例
ws_service = WebSocketService()
