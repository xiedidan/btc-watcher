"""
Signal model
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Text, ForeignKey, Index
from sqlalchemy.sql import func
from database.session import Base


class Signal(Base):
    """Trading signal from FreqTrade"""
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=False, index=True)

    # Signal info
    pair = Column(String(20), nullable=False, index=True)  # BTC/USDT
    action = Column(String(10), nullable=False)  # buy, sell, hold
    signal_strength = Column(Float, nullable=False)  # 0.0 - 1.0
    strength_level = Column(String(10), nullable=False)  # strong, medium, weak, ignore

    # Price info
    current_rate = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=True)
    exit_price = Column(Float, nullable=True)

    # Trade info
    profit_ratio = Column(Float, nullable=True)
    profit_abs = Column(Float, nullable=True)
    trade_duration = Column(Integer, nullable=True)  # seconds

    # Indicators (custom data from strategy)
    indicators = Column(JSON, nullable=True)
    # Example: {"rsi": 70, "macd": 0.5, "volume": 1000000}

    # Signal Metadata (renamed from 'metadata' to avoid SQLAlchemy reserved keyword)
    signal_metadata = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)

    # FreqTrade specific
    freqtrade_trade_id = Column(Integer, nullable=True)
    open_date = Column(DateTime(timezone=True), nullable=True)
    close_date = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Composite indexes for efficient queries
    __table_args__ = (
        Index('idx_strategy_pair_created', 'strategy_id', 'pair', 'created_at'),
        Index('idx_pair_action_created', 'pair', 'action', 'created_at'),
        Index('idx_strength_created', 'strength_level', 'created_at'),
    )

    def __repr__(self):
        return f"<Signal(id={self.id}, pair='{self.pair}', action='{self.action}', strength={self.signal_strength})>"
