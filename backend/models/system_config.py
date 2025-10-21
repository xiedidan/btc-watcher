"""
System Configuration model
"""
from sqlalchemy import Column, Integer, CheckConstraint, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from database.session import Base


class SystemConfig(Base):
    """System configuration model (singleton)"""
    __tablename__ = "system_config"

    id = Column(Integer, primary_key=True, default=1)

    # Market data configuration
    market_data = Column(JSONB, nullable=False, default={
        "default_exchange": "binance",
        "enabled_exchanges": ["binance", "okx", "bybit", "bitget"],
        "default_klines_limit": 200,
        "cache_config": {
            "ttl": {
                "1m": 60,
                "5m": 300,
                "15m": 900,
                "1h": 3600,
                "4h": 14400,
                "1d": 86400
            },
            "max_size_mb": 512
        },
        "update_mode": "interval",  # "interval" or "n_periods"
        "update_interval_seconds": 5,
        "n_periods": 1,
        "auto_failover": True,
        "rate_limit_fallback": True,
        "historical_data_days": {
            "1m": 7,
            "5m": 30,
            "15m": 30,
            "1h": 90,
            "4h": 365,
            "1d": 365
        }
    })

    # Timestamps
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint('id = 1', name='single_row_constraint'),
    )

    def __repr__(self):
        return f"<SystemConfig(id={self.id}, updated_at='{self.updated_at}')>"
