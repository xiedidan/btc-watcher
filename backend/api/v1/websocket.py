"""
WebSocket API endpoints
WebSocket实时通信端点

功能：
- WebSocket连接管理
- 用户认证
- 主题订阅/取消订阅
- 心跳检测
- 实时消息推送
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError, jwt
import logging
import json
from typing import Optional
from datetime import datetime
import uuid

from app.websocket.manager import manager
from models.user import User
from database import get_db
from config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


async def verify_websocket_token(token: str, db: AsyncSession) -> Optional[User]:
    """
    验证WebSocket连接的JWT Token

    Args:
        token: JWT token
        db: 数据库会话

    Returns:
        User对象，如果验证失败返回None
    """
    try:
        # 解码JWT token
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        username: str = payload.get("sub")

        if username is None:
            logger.warning("Token payload missing 'sub' field")
            return None

        # 从数据库获取用户
        result = await db.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()

        if user is None:
            logger.warning(f"User not found: {username}")
            return None

        if not user.is_active:
            logger.warning(f"User is not active: {username}")
            return None

        return user

    except JWTError as e:
        logger.warning(f"JWT validation failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Error verifying token: {e}", exc_info=True)
        return None


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token for authentication")
):
    """
    WebSocket连接端点

    连接URL: ws://host/api/v1/ws?token=<jwt_token>

    消息格式：

    客户端 -> 服务器:
    {
        "type": "subscribe",
        "topic": "monitoring|strategies|signals|logs|capacity"
    }
    {
        "type": "unsubscribe",
        "topic": "monitoring|strategies|signals|logs|capacity"
    }
    {
        "type": "pong",
        "timestamp": "2025-10-14T10:30:00"
    }
    {
        "type": "request",
        "endpoint": "strategies|signals|monitoring",
        "data": {}
    }

    服务器 -> 客户端:
    {
        "type": "ping",
        "timestamp": "2025-10-14T10:30:00"
    }
    {
        "type": "connected",
        "client_id": "user123_uuid",
        "timestamp": "2025-10-14T10:30:00"
    }
    {
        "type": "subscribed",
        "topic": "monitoring",
        "timestamp": "2025-10-14T10:30:00"
    }
    {
        "type": "data",
        "topic": "monitoring",
        "data": {...},
        "timestamp": "2025-10-14T10:30:00"
    }
    {
        "type": "error",
        "message": "Error message",
        "timestamp": "2025-10-14T10:30:00"
    }
    """
    client_id = None
    db = None

    try:
        # 获取数据库会话
        async for session in get_db():
            db = session
            break

        # 验证token
        user = await verify_websocket_token(token, db)

        if user is None:
            # 认证失败，关闭连接
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            logger.warning("WebSocket connection rejected: authentication failed")
            return

        # 生成客户端ID (用户名 + UUID)
        client_id = f"{user.username}_{uuid.uuid4().hex[:8]}"

        # 接受连接
        await manager.connect(websocket, client_id)

        # 发送连接成功消息
        await manager.send_personal_message(
            {
                "type": "connected",
                "client_id": client_id,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email
                },
                "timestamp": datetime.now().isoformat(),
                "available_topics": list(manager.subscriptions.keys())
            },
            client_id
        )

        logger.info(f"WebSocket client {client_id} connected (user: {user.username})")

        # 消息循环
        while True:
            try:
                # 接收消息
                data = await websocket.receive_text()

                # 解析消息
                try:
                    message = json.loads(data)
                    message_type = message.get("type")

                    # 处理不同类型的消息
                    if message_type == "subscribe":
                        # 订阅主题
                        topic = message.get("topic")

                        if topic in manager.subscriptions:
                            manager.subscribe(client_id, topic)
                            await manager.send_personal_message(
                                {
                                    "type": "subscribed",
                                    "topic": topic,
                                    "timestamp": datetime.now().isoformat()
                                },
                                client_id
                            )
                            logger.info(f"Client {client_id} subscribed to {topic}")
                        else:
                            await manager.send_personal_message(
                                {
                                    "type": "error",
                                    "message": f"Unknown topic: {topic}",
                                    "available_topics": list(manager.subscriptions.keys()),
                                    "timestamp": datetime.now().isoformat()
                                },
                                client_id
                            )

                    elif message_type == "unsubscribe":
                        # 取消订阅
                        topic = message.get("topic")
                        manager.unsubscribe(client_id, topic)
                        await manager.send_personal_message(
                            {
                                "type": "unsubscribed",
                                "topic": topic,
                                "timestamp": datetime.now().isoformat()
                            },
                            client_id
                        )
                        logger.info(f"Client {client_id} unsubscribed from {topic}")

                    elif message_type == "pong":
                        # 心跳响应
                        manager.update_heartbeat(client_id)
                        logger.debug(f"Received pong from client {client_id}")

                    elif message_type == "request":
                        # 数据请求（用于主动拉取数据）
                        endpoint = message.get("endpoint")
                        request_data = message.get("data", {})

                        # 根据endpoint返回相应数据
                        # 这里可以扩展为调用相应的service获取数据
                        await manager.send_personal_message(
                            {
                                "type": "response",
                                "endpoint": endpoint,
                                "data": {},  # TODO: 实现具体数据查询
                                "timestamp": datetime.now().isoformat()
                            },
                            client_id
                        )
                        logger.debug(f"Client {client_id} requested data from {endpoint}")

                    else:
                        # 未知消息类型
                        await manager.send_personal_message(
                            {
                                "type": "error",
                                "message": f"Unknown message type: {message_type}",
                                "timestamp": datetime.now().isoformat()
                            },
                            client_id
                        )

                except json.JSONDecodeError:
                    # JSON解析失败
                    await manager.send_personal_message(
                        {
                            "type": "error",
                            "message": "Invalid JSON format",
                            "timestamp": datetime.now().isoformat()
                        },
                        client_id
                    )
                except Exception as e:
                    # 消息处理失败
                    logger.error(f"Error processing message from {client_id}: {e}", exc_info=True)
                    await manager.send_personal_message(
                        {
                            "type": "error",
                            "message": f"Error processing message: {str(e)}",
                            "timestamp": datetime.now().isoformat()
                        },
                        client_id
                    )

            except WebSocketDisconnect:
                # 客户端断开连接
                logger.info(f"Client {client_id} disconnected normally")
                break

            except Exception as e:
                # 其他异常
                logger.error(f"Error in WebSocket loop for {client_id}: {e}", exc_info=True)
                break

    except Exception as e:
        logger.error(f"Error in WebSocket endpoint: {e}", exc_info=True)

    finally:
        # 清理连接
        if client_id:
            manager.disconnect(client_id)
            logger.info(f"Client {client_id} connection cleaned up")


@router.get("/stats")
async def get_websocket_stats():
    """
    获取WebSocket连接统计

    Returns:
        {
            "total_connections": 10,
            "subscriptions": {
                "monitoring": 5,
                "strategies": 3,
                "signals": 7,
                "logs": 2,
                "capacity": 4
            }
        }
    """
    return manager.get_stats()
