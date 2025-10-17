"""
Base User Class for Performance Tests
性能测试基础用户类

提供所有性能测试用户的通用功能和方法。
"""
from locust import HttpUser, between, task
from locust.exception import StopUser
import logging
from typing import Optional, Dict, Any
from .config import (
    API_PREFIX,
    TEST_USERS,
    WAIT_TIME,
    REQUEST_TIMEOUT,
    get_api_url
)

logger = logging.getLogger(__name__)


class BTCWatcherUser(HttpUser):
    """
    BTC Watcher基础用户类
    Base user class for BTC Watcher performance tests
    """

    # 用户等待时间（模拟真实用户的思考时间）
    wait_time = between(WAIT_TIME["min"], WAIT_TIME["max"])

    # 认证token
    access_token: Optional[str] = None

    # 用户信息
    user_credentials: Dict[str, str] = TEST_USERS["default"]

    def on_start(self):
        """
        测试开始时执行
        Called when a user starts
        """
        logger.info(f"User {self.user_credentials['username']} starting...")
        self.login()

    def on_stop(self):
        """
        测试停止时执行
        Called when a user stops
        """
        logger.info(f"User {self.user_credentials['username']} stopping...")
        if self.access_token:
            self.logout()

    def login(self):
        """
        用户登录
        User login
        """
        try:
            response = self.client.post(
                f"{API_PREFIX}/auth/token",
                data={
                    "username": self.user_credentials["username"],
                    "password": self.user_credentials["password"]
                },
                timeout=REQUEST_TIMEOUT["auth"],
                name="/auth/token [LOGIN]"
            )

            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                logger.info(f"User {self.user_credentials['username']} logged in successfully")
            else:
                logger.error(f"Login failed: {response.status_code} - {response.text}")
                raise StopUser(f"Login failed for user {self.user_credentials['username']}")

        except Exception as e:
            logger.error(f"Login error: {e}")
            raise StopUser(f"Login error: {e}")

    def logout(self):
        """
        用户登出
        User logout
        """
        # BTC Watcher可能没有显式的logout endpoint，
        # 这里只是清理token
        self.access_token = None
        logger.info(f"User {self.user_credentials['username']} logged out")

    def get_headers(self) -> Dict[str, str]:
        """
        获取请求头（包含认证token）
        Get request headers with auth token

        Returns:
            请求头字典
        """
        if not self.access_token:
            raise Exception("User not authenticated")

        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    def api_get(self, endpoint: str, name: Optional[str] = None, **kwargs) -> Any:
        """
        执行GET请求
        Perform authenticated GET request

        Args:
            endpoint: API端点
            name: 请求名称（用于统计）
            **kwargs: 其他请求参数

        Returns:
            Response object
        """
        if not endpoint.startswith("/"):
            endpoint = f"/{endpoint}"

        url = f"{API_PREFIX}{endpoint}"
        headers = self.get_headers()

        if "timeout" not in kwargs:
            kwargs["timeout"] = REQUEST_TIMEOUT["read"]

        if name is None:
            name = endpoint

        return self.client.get(
            url,
            headers=headers,
            name=name,
            **kwargs
        )

    def api_post(self, endpoint: str, data: Dict[str, Any], name: Optional[str] = None, **kwargs) -> Any:
        """
        执行POST请求
        Perform authenticated POST request

        Args:
            endpoint: API端点
            data: 请求数据
            name: 请求名称（用于统计）
            **kwargs: 其他请求参数

        Returns:
            Response object
        """
        if not endpoint.startswith("/"):
            endpoint = f"/{endpoint}"

        url = f"{API_PREFIX}{endpoint}"
        headers = self.get_headers()

        if "timeout" not in kwargs:
            kwargs["timeout"] = REQUEST_TIMEOUT["write"]

        if name is None:
            name = endpoint

        return self.client.post(
            url,
            json=data,
            headers=headers,
            name=name,
            **kwargs
        )

    def api_put(self, endpoint: str, data: Dict[str, Any], name: Optional[str] = None, **kwargs) -> Any:
        """
        执行PUT请求
        Perform authenticated PUT request

        Args:
            endpoint: API端点
            data: 请求数据
            name: 请求名称（用于统计）
            **kwargs: 其他请求参数

        Returns:
            Response object
        """
        if not endpoint.startswith("/"):
            endpoint = f"/{endpoint}"

        url = f"{API_PREFIX}{endpoint}"
        headers = self.get_headers()

        if "timeout" not in kwargs:
            kwargs["timeout"] = REQUEST_TIMEOUT["write"]

        if name is None:
            name = endpoint

        return self.client.put(
            url,
            json=data,
            headers=headers,
            name=name,
            **kwargs
        )

    def api_delete(self, endpoint: str, name: Optional[str] = None, **kwargs) -> Any:
        """
        执行DELETE请求
        Perform authenticated DELETE request

        Args:
            endpoint: API端点
            name: 请求名称（用于统计）
            **kwargs: 其他请求参数

        Returns:
            Response object
        """
        if not endpoint.startswith("/"):
            endpoint = f"/{endpoint}"

        url = f"{API_PREFIX}{endpoint}"
        headers = self.get_headers()

        if "timeout" not in kwargs:
            kwargs["timeout"] = REQUEST_TIMEOUT["write"]

        if name is None:
            name = endpoint

        return self.client.delete(
            url,
            headers=headers,
            name=name,
            **kwargs
        )

    def check_response(self, response: Any, expected_status: int = 200, name: str = "") -> bool:
        """
        检查响应状态
        Check response status

        Args:
            response: Response对象
            expected_status: 期望的状态码
            name: 请求名称（用于日志）

        Returns:
            是否成功
        """
        if response.status_code == expected_status:
            return True
        else:
            logger.warning(
                f"{name} failed: expected {expected_status}, got {response.status_code} - {response.text[:200]}"
            )
            return False
