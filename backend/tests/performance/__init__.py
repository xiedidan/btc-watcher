"""
Performance Tests Package
性能测试包

包含Locust性能测试的所有模块。
"""
from .base_user import BTCWatcherUser
from .config import (
    API_BASE_URL,
    API_PREFIX,
    TEST_USERS,
    PERFORMANCE_TARGETS,
    get_api_url,
    get_test_scenario,
    get_performance_target
)

__all__ = [
    "BTCWatcherUser",
    "API_BASE_URL",
    "API_PREFIX",
    "TEST_USERS",
    "PERFORMANCE_TARGETS",
    "get_api_url",
    "get_test_scenario",
    "get_performance_target"
]
