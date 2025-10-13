"""
BTC Watcher Backend Configuration
"""
from pydantic_settings import BaseSettings
from typing import List, Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application Settings"""

    # Application
    APP_NAME: str = "BTC Watcher"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str
    POSTGRES_USER: str = "btc_watcher"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_DB: str = "btc_watcher"

    # Redis
    REDIS_URL: str
    REDIS_PASSWORD: Optional[str] = None

    # Security
    SECRET_KEY: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]

    # FreqTrade
    FREQTRADE_VERSION: str = "2025.8"
    FREQTRADE_GATEWAY_PORT: int = 8080
    FREQTRADE_BASE_PORT: int = 8081
    FREQTRADE_MAX_PORT: int = 9080
    MAX_CONCURRENT_STRATEGIES: int = 999

    # Notification Services
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None
    WECHAT_CORP_ID: Optional[str] = None
    WECHAT_AGENT_ID: Optional[str] = None
    WECHAT_SECRET: Optional[str] = None
    FEISHU_WEBHOOK_URL: Optional[str] = None
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: Optional[str] = None

    # Monitoring
    MONITORING_INTERVAL: int = 30
    CAPACITY_ALERT_THRESHOLD: float = 80.0

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()
