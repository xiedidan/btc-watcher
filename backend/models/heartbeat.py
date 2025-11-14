"""
Strategy heartbeat monitoring models
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database.session import Base


class StrategyHeartbeatConfig(Base):
    """Strategy heartbeat monitoring configuration"""
    __tablename__ = "strategy_heartbeat_configs"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Monitoring settings
    enabled = Column(Boolean, default=True, nullable=False)
    timeout_seconds = Column(Integer, default=300, nullable=False)  # 5分钟默认超时
    check_interval_seconds = Column(Integer, default=30, nullable=False)  # 30秒检查间隔

    # Auto-restart settings
    auto_restart = Column(Boolean, default=True, nullable=False)  # 默认开启自动重启
    max_restart_attempts = Column(Integer, default=3, nullable=False)  # 最大重启次数
    restart_cooldown_seconds = Column(Integer, default=60, nullable=False)  # 重启冷却时间

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    # strategy = relationship("Strategy", back_populates="heartbeat_config")

    def __repr__(self):
        return f"<StrategyHeartbeatConfig(strategy_id={self.strategy_id}, enabled={self.enabled}, timeout={self.timeout_seconds}s)>"


class StrategyHeartbeatHistory(Base):
    """Strategy heartbeat history records"""
    __tablename__ = "strategy_heartbeat_history"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False, index=True)

    # Heartbeat info
    heartbeat_time = Column(DateTime(timezone=True), nullable=False, index=True)
    pid = Column(Integer, nullable=True)
    version = Column(String(50), nullable=True)
    state = Column(String(20), nullable=True)  # RUNNING, STOPPED, etc.

    # Timeout info
    is_timeout = Column(Boolean, default=False, nullable=False)
    time_since_last_heartbeat_seconds = Column(Integer, nullable=True)

    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    # strategy = relationship("Strategy", back_populates="heartbeat_history")

    def __repr__(self):
        return f"<StrategyHeartbeatHistory(strategy_id={self.strategy_id}, heartbeat_time={self.heartbeat_time}, is_timeout={self.is_timeout})>"


class StrategyRestartHistory(Base):
    """Strategy restart history records"""
    __tablename__ = "strategy_restart_history"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False, index=True)

    # Restart info
    restart_reason = Column(String(50), nullable=False)  # heartbeat_timeout, manual, error
    restart_time = Column(DateTime(timezone=True), nullable=False, index=True)
    restart_success = Column(Boolean, nullable=True)
    error_message = Column(Text, nullable=True)

    # Process info
    previous_pid = Column(Integer, nullable=True)
    new_pid = Column(Integer, nullable=True)

    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    # strategy = relationship("Strategy", back_populates="restart_history")

    def __repr__(self):
        return f"<StrategyRestartHistory(strategy_id={self.strategy_id}, reason={self.restart_reason}, success={self.restart_success})>"
