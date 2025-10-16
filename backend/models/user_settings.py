"""
User Settings Model
用户设置数据模型
"""
from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey
from sqlalchemy.sql import func
from database import Base


class UserSettings(Base):
    """用户设置"""
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)

    # 设置数据（JSON格式存储）
    notifications = Column(JSON, default={
        "browser_enabled": True,
        "signal_enabled": True,
        "strategy_enabled": True,
        "system_enabled": True,
        "sound_enabled": False
    })

    websocket = Column(JSON, default={
        "max_reconnect_attempts": 5,
        "reconnect_delay": 3,
        "heartbeat_interval": 25,
        "subscribed_topics": ["monitoring", "strategies", "signals", "capacity"]
    })

    display = Column(JSON, default={
        "refresh_interval": 30,
        "page_size": 20,
        "date_format": "YYYY-MM-DD HH:mm:ss",
        "number_format": "en-US",
        "show_charts": True,
        "show_trends": True,
        "enable_animations": True
    })

    advanced = Column(JSON, default={
        "debug_mode": False,
        "api_timeout": 30,
        "cache_strategy": "memory"
    })

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
