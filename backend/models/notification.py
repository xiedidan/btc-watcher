"""
Notification model
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, Text, ForeignKey, Index
from sqlalchemy.sql import func
from database.session import Base


class Notification(Base):
    """Notification record"""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Notification type and priority
    notification_type = Column(String(20), nullable=False)  # signal, system, alert
    priority = Column(String(10), nullable=False, index=True)  # P0, P1, P2

    # Channel and status
    channel = Column(String(20), nullable=False)  # telegram, wechat, feishu, email, sms
    status = Column(String(20), default="pending", index=True)  # pending, sent, failed, cancelled

    # Content
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    data = Column(JSON, nullable=True)  # Additional structured data

    # Delivery info
    recipient = Column(String(100), nullable=False)  # phone number, email, chat_id, etc.
    sent_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)

    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Composite indexes
    __table_args__ = (
        Index('idx_status_priority_created', 'status', 'priority', 'created_at'),
        Index('idx_user_created', 'user_id', 'created_at'),
    )

    def __repr__(self):
        return f"<Notification(id={self.id}, type='{self.notification_type}', priority='{self.priority}', status='{self.status}')>"
