"""
Notification configuration models
通知配置数据模型
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, Float
from sqlalchemy.sql import func
from database.session import Base


class NotificationChannelConfig(Base):
    """通知渠道配置"""
    __tablename__ = "notification_channel_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)

    # Channel info
    channel_type = Column(String(50), nullable=False)  # telegram, wechat, feishu, email, sms
    channel_name = Column(String(100), nullable=False)
    enabled = Column(Boolean, default=True)
    priority = Column(Integer, default=1)  # 优先级，数字越小优先级越高

    # Priority levels supported by this channel
    supported_priorities = Column(JSON, default=["P2", "P1", "P0"])  # Which priority levels this channel handles

    # Channel-specific configuration
    config = Column(JSON, nullable=True)  # bot_token, webhook_url, etc.

    # Template configuration
    templates = Column(JSON, nullable=True)  # p2, p1, p0 message templates

    # Rate limiting
    rate_limit_enabled = Column(Boolean, default=True)
    max_notifications_per_hour = Column(Integer, default=60)
    max_notifications_per_day = Column(Integer, default=500)

    # Statistics
    total_sent = Column(Integer, default=0)
    total_failed = Column(Integer, default=0)
    last_sent_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(String(500), nullable=True)
    last_error_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<NotificationChannelConfig(id={self.id}, user_id={self.user_id}, type='{self.channel_type}', enabled={self.enabled})>"


class NotificationFrequencyLimit(Base):
    """通知频率限制配置"""
    __tablename__ = "notification_frequency_limits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)

    # Priority-based frequency limits (seconds)
    p2_min_interval = Column(Integer, default=0)  # P2 - 最高优先级，立即发送
    p1_min_interval = Column(Integer, default=60)  # P1 - 中等优先级，最少间隔60秒
    p0_batch_interval = Column(Integer, default=300)  # P0 - 最低优先级，批量发送间隔300秒

    # Batch settings for P0
    p0_batch_enabled = Column(Boolean, default=True)
    p0_batch_max_size = Column(Integer, default=10)  # Maximum notifications per batch

    # Global limits
    enabled = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<NotificationFrequencyLimit(id={self.id}, user_id={self.user_id})>"


class NotificationTimeRule(Base):
    """通知时间规则配置"""
    __tablename__ = "notification_time_rules"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    rule_name = Column(String(100), nullable=False)
    enabled = Column(Boolean, default=True)

    # Quiet hours (勿扰时段)
    quiet_hours_enabled = Column(Boolean, default=False)
    quiet_start_time = Column(String(5), default="22:00")  # HH:MM format
    quiet_end_time = Column(String(5), default="08:00")  # HH:MM format
    quiet_priority_filter = Column(String(10), default="P2")  # Only send >= P2 during quiet hours

    # Weekend mode (周末模式)
    weekend_mode_enabled = Column(Boolean, default=False)
    weekend_downgrade_p1_to_p0 = Column(Boolean, default=True)  # 周末将P1降级为P0
    weekend_batch_p0 = Column(Boolean, default=True)  # 周末批量发送P0

    # Working hours (工作时段)
    working_hours_enabled = Column(Boolean, default=False)
    working_start_time = Column(String(5), default="09:00")
    working_end_time = Column(String(5), default="18:00")
    working_days = Column(JSON, default=[1, 2, 3, 4, 5])  # 1=Monday, 7=Sunday

    # Holiday mode (假期模式)
    holiday_mode_enabled = Column(Boolean, default=False)
    holiday_dates = Column(JSON, default=[])  # List of dates in "YYYY-MM-DD" format

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<NotificationTimeRule(id={self.id}, user_id={self.user_id}, name='{self.rule_name}')>"


class NotificationHistory(Base):
    """通知历史记录"""
    __tablename__ = "notification_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)

    # Notification content
    title = Column(String(200), nullable=False)
    message = Column(String(2000), nullable=False)
    notification_type = Column(String(50), nullable=False)  # signal, system, alert, etc.
    priority = Column(String(10), nullable=False)  # P2, P1, P0

    # Channel info
    channel_type = Column(String(50), nullable=False)
    channel_config_id = Column(Integer, nullable=True)

    # Status
    status = Column(String(20), default="pending")  # pending, sent, failed, batched
    sent_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(String(500), nullable=True)

    # Metadata
    signal_id = Column(Integer, nullable=True)  # If related to a signal
    strategy_id = Column(Integer, nullable=True)  # If related to a strategy
    extra_data = Column(JSON, nullable=True)  # Additional metadata (renamed from metadata to avoid SQLAlchemy reserved word)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    def __repr__(self):
        return f"<NotificationHistory(id={self.id}, user_id={self.user_id}, type='{self.notification_type}', status='{self.status}')>"
