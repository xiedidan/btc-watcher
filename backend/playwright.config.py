"""
Playwright Configuration
Playwright测试配置
"""
import os
from typing import Dict, Any

# 基础URL配置
BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:3000")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# 浏览器配置
BROWSERS = ["chromium"]  # 可选: firefox, webkit
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"
SLOW_MO = int(os.getenv("SLOW_MO", "0"))

# 视口配置
VIEWPORT_SIZES = {
    "desktop": {"width": 1920, "height": 1080},
    "laptop": {"width": 1366, "height": 768},
    "tablet": {"width": 768, "height": 1024},
    "mobile": {"width": 375, "height": 667},
}

DEFAULT_VIEWPORT = VIEWPORT_SIZES["desktop"]

# 超时配置（毫秒）
TIMEOUTS = {
    "default": 30000,  # 30秒
    "navigation": 60000,  # 60秒
    "action": 15000,  # 15秒
}

# 截图和视频配置
SCREENSHOT_ON_FAILURE = True
VIDEO_ON_FAILURE = True
VIDEO_SIZE = {"width": 1920, "height": 1080}

# 输出目录
OUTPUT_DIRS = {
    "screenshots": "tests/e2e/screenshots",
    "videos": "tests/e2e/videos",
    "reports": "tests/e2e/reports",
}

# 重试配置
MAX_RETRIES = 2  # 失败后最多重试次数

# 浏览器上下文配置
BROWSER_CONTEXT_OPTIONS: Dict[str, Any] = {
    "viewport": DEFAULT_VIEWPORT,
    "locale": "zh-CN",
    "timezone_id": "Asia/Shanghai",
    "permissions": ["notifications"],
    "has_touch": False,
    "is_mobile": False,
    "color_scheme": "light",  # or "dark"
}

# 测试用户配置
TEST_USERS = {
    "default": {
        "username": "testuser",
        "password": "testpass123",
        "email": "testuser@example.com"
    },
    "admin": {
        "username": "admin",
        "password": "admin123",
        "email": "admin@example.com"
    }
}

# 设备模拟（移动端测试）
DEVICES = {
    "iPhone 12": {
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15",
        "viewport": {"width": 390, "height": 844},
        "device_scale_factor": 3,
        "is_mobile": True,
        "has_touch": True,
    },
    "iPad Pro": {
        "user_agent": "Mozilla/5.0 (iPad; CPU OS 14_0 like Mac OS X) AppleWebKit/605.1.15",
        "viewport": {"width": 1024, "height": 1366},
        "device_scale_factor": 2,
        "is_mobile": False,
        "has_touch": True,
    }
}


def get_config() -> Dict[str, Any]:
    """
    获取完整配置

    Returns:
        配置字典
    """
    return {
        "base_url": BASE_URL,
        "api_base_url": API_BASE_URL,
        "browsers": BROWSERS,
        "headless": HEADLESS,
        "slow_mo": SLOW_MO,
        "viewport": DEFAULT_VIEWPORT,
        "timeouts": TIMEOUTS,
        "screenshot_on_failure": SCREENSHOT_ON_FAILURE,
        "video_on_failure": VIDEO_ON_FAILURE,
        "output_dirs": OUTPUT_DIRS,
        "max_retries": MAX_RETRIES,
        "browser_context_options": BROWSER_CONTEXT_OPTIONS,
        "test_users": TEST_USERS,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(get_config(), indent=2, ensure_ascii=False))
