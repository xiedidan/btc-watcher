"""
Technical Indicator model
"""
from sqlalchemy import Column, BigInteger, String, DateTime, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from database.session import Base


class TechnicalIndicator(Base):
    """Technical indicator data"""
    __tablename__ = "technical_indicators"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Trading pair info
    exchange = Column(String(20), nullable=False, index=True)  # binance, okx, bybit, bitget
    symbol = Column(String(20), nullable=False, index=True)  # BTC/USDT
    timeframe = Column(String(10), nullable=False, index=True)  # 1m, 5m, 15m, 1h, 4h, 1d

    # Indicator info
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    indicator_type = Column(String(20), nullable=False, index=True)  # MA, MACD, RSI, BOLL, VOL

    # Indicator parameters (e.g., {"period": 14, "type": "EMA"})
    indicator_params = Column(JSONB, nullable=True)

    # Indicator values (e.g., {"ma5": 45230.5, "ma10": 45100.2} or {"macd": 120.5, "signal": 115.3, "histogram": 5.2})
    indicator_values = Column(JSONB, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Composite indexes for efficient queries
    __table_args__ = (
        Index('idx_indicator_exchange_symbol_timeframe_time',
              'exchange', 'symbol', 'timeframe', 'timestamp'),
        Index('idx_indicator_type_time', 'indicator_type', 'timestamp'),
        UniqueConstraint('exchange', 'symbol', 'timeframe', 'timestamp', 'indicator_type',
                        name='uix_indicator_unique'),
    )

    def __repr__(self):
        return f"<TechnicalIndicator(id={self.id}, symbol='{self.symbol}', type='{self.indicator_type}', time='{self.timestamp}')>"
