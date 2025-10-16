"""
WebSocket连接管理器
WebSocket Connection Manager

功能：
- 管理WebSocket连接
- 广播消息
- 心跳检测
- 断线处理
"""
from typing import Dict, Set
from fastapi import WebSocket
import asyncio
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket连接管理器"""

    def __init__(self):
        # 活跃连接：{client_id: WebSocket}
        self.active_connections: Dict[str, WebSocket] = {}

        # 心跳状态：{client_id: last_heartbeat_time}
        self.heartbeat_status: Dict[str, datetime] = {}

        # 订阅主题：{topic: Set[client_id]}
        self.subscriptions: Dict[str, Set[str]] = {
            "monitoring": set(),      # 系统监控
            "strategies": set(),      # 策略状态
            "signals": set(),         # 信号推送
            "logs": set(),           # 日志流
            "capacity": set(),       # 容量监控
        }

        # 心跳超时时间（秒）
        self.heartbeat_timeout = 30

        # 心跳检测任务
        self.heartbeat_task = None

    async def connect(self, websocket: WebSocket, client_id: str):
        """接受WebSocket连接"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.heartbeat_status[client_id] = datetime.now()
        logger.info(f"Client {client_id} connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, client_id: str):
        """断开连接"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]

        if client_id in self.heartbeat_status:
            del self.heartbeat_status[client_id]

        # 从所有订阅中移除
        for topic in self.subscriptions:
            self.subscriptions[topic].discard(client_id)

        logger.info(f"Client {client_id} disconnected. Total connections: {len(self.active_connections)}")

    def subscribe(self, client_id: str, topic: str):
        """订阅主题"""
        if topic in self.subscriptions:
            self.subscriptions[topic].add(client_id)
            logger.info(f"Client {client_id} subscribed to {topic}")
        else:
            logger.warning(f"Topic {topic} does not exist")

    def unsubscribe(self, client_id: str, topic: str):
        """取消订阅"""
        if topic in self.subscriptions:
            self.subscriptions[topic].discard(client_id)
            logger.info(f"Client {client_id} unsubscribed from {topic}")

    async def send_personal_message(self, message: dict, client_id: str):
        """发送个人消息"""
        if client_id in self.active_connections:
            try:
                websocket = self.active_connections[client_id]
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to {client_id}: {e}")
                self.disconnect(client_id)

    async def broadcast(self, message: dict, topic: str = None):
        """
        广播消息

        Args:
            message: 消息内容
            topic: 主题（如果指定，只发送给订阅该主题的客户端）
        """
        # 确定接收者
        if topic and topic in self.subscriptions:
            recipients = self.subscriptions[topic]
        else:
            recipients = self.active_connections.keys()

        # 发送消息
        disconnected_clients = []
        for client_id in recipients:
            if client_id in self.active_connections:
                try:
                    websocket = self.active_connections[client_id]
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to {client_id}: {e}")
                    disconnected_clients.append(client_id)

        # 清理断开的连接
        for client_id in disconnected_clients:
            self.disconnect(client_id)

    def update_heartbeat(self, client_id: str):
        """更新心跳时间"""
        if client_id in self.heartbeat_status:
            self.heartbeat_status[client_id] = datetime.now()
            logger.debug(f"Heartbeat updated for {client_id}")

    async def check_heartbeats(self):
        """检查心跳超时"""
        while True:
            try:
                await asyncio.sleep(10)  # 每10秒检查一次

                now = datetime.now()
                timeout_clients = []

                for client_id, last_heartbeat in self.heartbeat_status.items():
                    elapsed = (now - last_heartbeat).total_seconds()

                    if elapsed > self.heartbeat_timeout:
                        logger.warning(f"Client {client_id} heartbeat timeout ({elapsed}s)")
                        timeout_clients.append(client_id)
                    elif elapsed > self.heartbeat_timeout * 0.7:
                        # 70%超时时发送ping
                        await self.send_personal_message(
                            {"type": "ping", "timestamp": now.isoformat()},
                            client_id
                        )

                # 断开超时的客户端
                for client_id in timeout_clients:
                    if client_id in self.active_connections:
                        try:
                            await self.active_connections[client_id].close()
                        except:
                            pass
                        self.disconnect(client_id)

            except Exception as e:
                logger.error(f"Error in heartbeat check: {e}")

    async def start_heartbeat_checker(self):
        """启动心跳检测任务"""
        if self.heartbeat_task is None:
            self.heartbeat_task = asyncio.create_task(self.check_heartbeats())
            logger.info("Heartbeat checker started")

    async def stop_heartbeat_checker(self):
        """停止心跳检测任务"""
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
            self.heartbeat_task = None
            logger.info("Heartbeat checker stopped")

    def get_stats(self) -> dict:
        """获取连接统计"""
        return {
            "total_connections": len(self.active_connections),
            "subscriptions": {
                topic: len(clients)
                for topic, clients in self.subscriptions.items()
            }
        }


# 全局连接管理器实例
manager = ConnectionManager()
