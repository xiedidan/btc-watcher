"""
Strategy model
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, Text, Float, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database.session import Base


class Strategy(Base):
    """Trading strategy configuration"""
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Basic info
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    strategy_class = Column(String(100), nullable=False)  # FreqTrade strategy class name
    version = Column(String(20), default="v1.0")

    # Configuration
    exchange = Column(String(50), nullable=False)  # binance, okx, etc.
    timeframe = Column(String(10), nullable=False)  # 1m, 5m, 15m, 1h, etc.
    pair_whitelist = Column(JSON, nullable=False)  # ["BTC/USDT", "ETH/USDT"]
    pair_blacklist = Column(JSON, default=[])

    # FreqTrade settings
    dry_run = Column(Boolean, default=True)
    dry_run_wallet = Column(Float, default=1000.0)
    stake_amount = Column(Float, nullable=True)
    max_open_trades = Column(Integer, default=3)

    # Signal threshold configuration
    signal_thresholds = Column(JSON, nullable=False)
    # Example: {"strong": 0.8, "medium": 0.6, "weak": 0.4}

    # Proxy configuration
    proxy_id = Column(Integer, ForeignKey("proxies.id"), nullable=True)

    # Status
    status = Column(String(20), default="stopped")  # stopped, running, error
    is_active = Column(Boolean, default=True)

    # Runtime info (populated by FreqTrade manager)
    port = Column(Integer, nullable=True)  # Assigned port number
    process_id = Column(Integer, nullable=True)  # System process ID

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    stopped_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    # user = relationship("User", back_populates="strategies")
    # signals = relationship("Signal", back_populates="strategy")
    # proxy = relationship("Proxy", back_populates="strategies")

    def __repr__(self):
        return f"<Strategy(id={self.id}, name='{self.name}', status='{self.status}')>"
