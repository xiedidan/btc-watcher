"""Database models package"""
# Import all models here for Alembic auto-detection
from .user import User
from .strategy import Strategy
from .signal import Signal
from .notification import NotificationChannelConfig, NotificationFrequencyLimit, NotificationTimeRule, NotificationHistory
from .proxy import Proxy
from .user_settings import UserSettings

__all__ = ["User", "Strategy", "Signal", "NotificationChannelConfig", "NotificationFrequencyLimit", "NotificationTimeRule", "NotificationHistory", "Proxy", "UserSettings"]
