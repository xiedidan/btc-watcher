"""
K-line (OHLCV) Data Model
"""
from sqlalchemy import Column, BigInteger, String, Float, DateTime, Index, UniqueConstraint
from sqlalchemy.sql import func
from database.session import Base


class Kline(Base):
    """K-line (candlestick) OHLCV data"""
    __tablename__ = "klines"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Trading pair info
    exchange = Column(String(20), nullable=False, index=True)  # binance, okx, bybit, bitget
    symbol = Column(String(20), nullable=False, index=True)  # BTC/USDT
    timeframe = Column(String(10), nullable=False, index=True)  # 1m, 5m, 15m, 1h, 4h, 1d

    # K-line data
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Composite indexes for efficient queries
    __table_args__ = (
        Index('idx_kline_exchange_symbol_timeframe_time',
              'exchange', 'symbol', 'timeframe', 'timestamp'),
        UniqueConstraint('exchange', 'symbol', 'timeframe', 'timestamp',
                        name='uix_kline_unique'),
    )

    def __repr__(self):
        return (
            f"<Kline(id={self.id}, exchange='{self.exchange}', "
            f"symbol='{self.symbol}', timeframe='{self.timeframe}', "
            f"timestamp='{self.timestamp}', close={self.close})>"
        )

    def to_ohlcv_list(self) -> list:
        """
        Convert to OHLCV list format [timestamp_ms, open, high, low, close, volume]

        Returns:
            OHLCV data as list
        """
        timestamp_ms = int(self.timestamp.timestamp() * 1000)
        return [timestamp_ms, self.open, self.high, self.low, self.close, self.volume]
