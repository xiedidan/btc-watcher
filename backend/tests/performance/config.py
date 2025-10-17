"""
Performance Test Configuration
性能测试配置

此文件定义了性能测试的通用配置和设置。
"""
import os

# API基础URL
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_VERSION = "v1"
API_PREFIX = f"/api/{API_VERSION}"

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

# 性能测试目标
PERFORMANCE_TARGETS = {
    # 响应时间目标 (毫秒)
    "response_time": {
        "excellent": 100,    # < 100ms 优秀
        "good": 300,         # < 300ms 良好
        "acceptable": 1000,  # < 1000ms 可接受
        "poor": 3000        # < 3000ms 较差
    },

    # 吞吐量目标 (请求/秒)
    "throughput": {
        "read_operations": 1000,   # 读操作: 1000 req/s
        "write_operations": 100,   # 写操作: 100 req/s
        "auth_operations": 50      # 认证操作: 50 req/s
    },

    # 错误率目标
    "error_rate": {
        "acceptable": 0.01,  # < 1% 可接受
        "warning": 0.05,     # < 5% 警告
        "critical": 0.10     # < 10% 严重
    },

    # 并发用户目标
    "concurrent_users": {
        "smoke": 10,          # 冒烟测试: 10用户
        "load": 100,          # 负载测试: 100用户
        "stress": 500,        # 压力测试: 500用户
        "spike": 1000         # 峰值测试: 1000用户
    }
}

# 测试场景配置
TEST_SCENARIOS = {
    "smoke": {
        "users": 10,
        "spawn_rate": 2,
        "duration": "1m"
    },
    "load": {
        "users": 100,
        "spawn_rate": 10,
        "duration": "5m"
    },
    "stress": {
        "users": 500,
        "spawn_rate": 50,
        "duration": "10m"
    },
    "spike": {
        "users": 1000,
        "spawn_rate": 200,
        "duration": "3m"
    }
}

# 测试数据配置
TEST_DATA = {
    "strategy": {
        "name_prefix": "Perf Test Strategy",
        "config": {
            "pair": "BTC/USDT",
            "timeframe": "5m",
            "dry_run": True,
            "stake_amount": 10
        }
    },
    "signal": {
        "pairs": ["BTC/USDT", "ETH/USDT", "BNB/USDT"],
        "actions": ["buy", "sell"],
        "strengths": [0.9, 0.7, 0.5, 0.3]
    }
}

# 报告配置
REPORT_CONFIG = {
    "html_report": True,
    "csv_report": True,
    "output_dir": "tests/performance/reports",
    "screenshots_dir": "tests/performance/screenshots"
}

# Locust Web UI配置
WEB_UI_CONFIG = {
    "host": "0.0.0.0",
    "port": 8089,
    "modern_ui": True
}

# 日志配置
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s [%(levelname)s] %(message)s",
    "file": "tests/performance/logs/performance.log"
}

# 请求超时配置 (秒)
REQUEST_TIMEOUT = {
    "default": 30,
    "auth": 10,
    "read": 15,
    "write": 30,
    "heavy": 60
}

# 等待时间配置 (秒)
WAIT_TIME = {
    "min": 1,
    "max": 5,
    "think_time": 2  # 用户思考时间
}


def get_api_url(endpoint: str) -> str:
    """
    Get full API URL
    获取完整API URL

    Args:
        endpoint: API端点路径

    Returns:
        完整的API URL
    """
    if endpoint.startswith("/"):
        endpoint = endpoint[1:]
    return f"{API_BASE_URL}{API_PREFIX}/{endpoint}"


def get_test_scenario(scenario_name: str = "load") -> dict:
    """
    Get test scenario configuration
    获取测试场景配置

    Args:
        scenario_name: 场景名称 (smoke/load/stress/spike)

    Returns:
        场景配置字典
    """
    return TEST_SCENARIOS.get(scenario_name, TEST_SCENARIOS["load"])


def get_performance_target(category: str, metric: str) -> float:
    """
    Get performance target value
    获取性能目标值

    Args:
        category: 类别 (response_time/throughput/error_rate)
        metric: 指标名称

    Returns:
        目标值
    """
    return PERFORMANCE_TARGETS.get(category, {}).get(metric, 0)


if __name__ == "__main__":
    import json
    print("=== Performance Test Configuration ===")
    print(f"API Base URL: {API_BASE_URL}")
    print(f"API Prefix: {API_PREFIX}")
    print("\nTest Scenarios:")
    print(json.dumps(TEST_SCENARIOS, indent=2))
    print("\nPerformance Targets:")
    print(json.dumps(PERFORMANCE_TARGETS, indent=2))
