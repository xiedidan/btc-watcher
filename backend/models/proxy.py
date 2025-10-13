"""
Proxy model
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, Float
from sqlalchemy.sql import func
from database.session import Base


class Proxy(Base):
    """Proxy server configuration"""
    __tablename__ = "proxies"

    id = Column(Integer, primary_key=True, index=True)

    # Basic info
    name = Column(String(100), nullable=False)
    proxy_type = Column(String(20), nullable=False)  # http, https, socks5
    host = Column(String(100), nullable=False)
    port = Column(Integer, nullable=False)

    # Authentication
    username = Column(String(100), nullable=True)
    password = Column(String(255), nullable=True)

    # Health status
    is_active = Column(Boolean, default=True)
    is_healthy = Column(Boolean, default=True)
    health_check_url = Column(String(255), default="https://api.binance.com/api/v3/ping")

    # Performance metrics
    success_rate = Column(Float, default=100.0)  # percentage
    avg_latency_ms = Column(Float, nullable=True)  # milliseconds
    last_check_at = Column(DateTime(timezone=True), nullable=True)
    last_success_at = Column(DateTime(timezone=True), nullable=True)
    last_failure_at = Column(DateTime(timezone=True), nullable=True)

    # Statistics
    total_requests = Column(Integer, default=0)
    successful_requests = Column(Integer, default=0)
    failed_requests = Column(Integer, default=0)
    consecutive_failures = Column(Integer, default=0)

    # Configuration
    max_consecutive_failures = Column(Integer, default=3)
    health_check_interval = Column(Integer, default=3600)  # seconds

    # Proxy Metadata (renamed from 'metadata' to avoid SQLAlchemy reserved keyword)
    proxy_metadata = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Proxy(id={self.id}, name='{self.name}', host='{self.host}:{self.port}', healthy={self.is_healthy})>"
