"""
Authentication API Performance Tests
认证API性能测试

测试认证相关的API性能：
- 用户登录
- Token验证
- 并发登录
"""
from locust import task, between
from locust.exception import RescheduleTask
import logging
from .base_user import BTCWatcherUser
from .config import API_PREFIX, TEST_USERS, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


class AuthenticationUser(BTCWatcherUser):
    """
    认证性能测试用户
    User for authentication performance testing
    """

    wait_time = between(2, 5)

    def on_start(self):
        """
        不自动登录，因为我们要测试登录性能
        Don't auto-login since we're testing login performance
        """
        logger.info("AuthenticationUser starting (no auto-login)...")

    @task(10)
    def test_login(self):
        """
        测试登录性能
        Test login performance

        权重: 10 (最频繁的任务)
        """
        try:
            response = self.client.post(
                f"{API_PREFIX}/auth/token",
                data={
                    "username": TEST_USERS["default"]["username"],
                    "password": TEST_USERS["default"]["password"]
                },
                timeout=REQUEST_TIMEOUT["auth"],
                name="POST /auth/token [LOGIN]"
            )

            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                logger.debug(f"Login successful, token length: {len(self.access_token) if self.access_token else 0}")
            else:
                logger.warning(f"Login failed: {response.status_code}")

        except Exception as e:
            logger.error(f"Login error: {e}")

    @task(5)
    def test_login_with_different_credentials(self):
        """
        测试使用不同凭证登录
        Test login with different credentials

        权重: 5
        """
        # 使用admin用户
        try:
            response = self.client.post(
                f"{API_PREFIX}/auth/token",
                data={
                    "username": TEST_USERS["admin"]["username"],
                    "password": TEST_USERS["admin"]["password"]
                },
                timeout=REQUEST_TIMEOUT["auth"],
                name="POST /auth/token [ADMIN LOGIN]"
            )

            if response.status_code == 200:
                logger.debug("Admin login successful")
            else:
                logger.warning(f"Admin login failed: {response.status_code}")

        except Exception as e:
            logger.error(f"Admin login error: {e}")

    @task(3)
    def test_invalid_login(self):
        """
        测试无效凭证登录
        Test login with invalid credentials

        权重: 3 (测试错误处理性能)
        """
        try:
            response = self.client.post(
                f"{API_PREFIX}/auth/token",
                data={
                    "username": "invaliduser",
                    "password": "wrongpassword"
                },
                timeout=REQUEST_TIMEOUT["auth"],
                name="POST /auth/token [INVALID LOGIN]",
                catch_response=True
            )

            if response.status_code in [400, 401, 422]:
                # 预期的错误响应
                response.success()
                logger.debug(f"Invalid login handled correctly: {response.status_code}")
            else:
                response.failure(f"Unexpected status code: {response.status_code}")

        except Exception as e:
            logger.error(f"Invalid login test error: {e}")

    @task(2)
    def test_empty_credentials(self):
        """
        测试空凭证
        Test with empty credentials

        权重: 2
        """
        try:
            response = self.client.post(
                f"{API_PREFIX}/auth/token",
                data={
                    "username": "",
                    "password": ""
                },
                timeout=REQUEST_TIMEOUT["auth"],
                name="POST /auth/token [EMPTY CREDENTIALS]",
                catch_response=True
            )

            if response.status_code in [400, 422]:
                # 预期的验证错误
                response.success()
                logger.debug(f"Empty credentials validation passed: {response.status_code}")
            else:
                response.failure(f"Unexpected status code: {response.status_code}")

        except Exception as e:
            logger.error(f"Empty credentials test error: {e}")


class AuthenticatedReadUser(BTCWatcherUser):
    """
    已认证读操作用户
    Authenticated user performing read operations
    """

    wait_time = between(1, 3)

    @task(10)
    def test_get_current_user(self):
        """
        测试获取当前用户信息
        Test get current user info

        权重: 10
        """
        try:
            response = self.api_get(
                "/auth/me",
                name="GET /auth/me [CURRENT USER]"
            )

            self.check_response(response, expected_status=200, name="Get current user")

        except Exception as e:
            logger.error(f"Get current user error: {e}")

    @task(5)
    def test_verify_token(self):
        """
        测试Token验证
        Test token verification

        权重: 5
        """
        try:
            # 尝试访问需要认证的端点来验证token
            response = self.api_get(
                "/strategies/",
                name="GET /strategies/ [TOKEN VERIFY]"
            )

            if response.status_code in [200, 404]:
                # 200或404都表示token有效
                logger.debug("Token verification successful")
            elif response.status_code == 401:
                logger.warning("Token expired or invalid")
                # 重新登录
                self.login()
            else:
                logger.warning(f"Unexpected status: {response.status_code}")

        except Exception as e:
            logger.error(f"Token verification error: {e}")


class HighConcurrencyAuthUser(BTCWatcherUser):
    """
    高并发认证用户
    High concurrency authentication user

    用于压力测试和峰值负载测试
    """

    wait_time = between(0.5, 2)  # 更短的等待时间，增加压力

    def on_start(self):
        """不自动登录"""
        logger.info("HighConcurrencyAuthUser starting...")

    @task
    def rapid_login_logout(self):
        """
        快速登录登出循环
        Rapid login-logout cycle
        """
        try:
            # 登录
            response = self.client.post(
                f"{API_PREFIX}/auth/token",
                data={
                    "username": TEST_USERS["default"]["username"],
                    "password": TEST_USERS["default"]["password"]
                },
                timeout=REQUEST_TIMEOUT["auth"],
                name="POST /auth/token [RAPID LOGIN]"
            )

            if response.status_code == 200:
                data = response.json()
                token = data.get("access_token")

                # 使用token执行一次API调用
                self.client.get(
                    f"{API_PREFIX}/strategies/",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=REQUEST_TIMEOUT["read"],
                    name="GET /strategies/ [RAPID VERIFY]"
                )

                logger.debug("Rapid login-logout cycle completed")
            else:
                logger.warning(f"Rapid login failed: {response.status_code}")

        except Exception as e:
            logger.error(f"Rapid login-logout error: {e}")


# 用于命令行直接运行
if __name__ == "__main__":
    import sys
    print("This is a Locust test file. Run it with:")
    print(f"  locust -f {__file__} --host=http://localhost:8000")
    print("\nAvailable user classes:")
    print("  - AuthenticationUser (default)")
    print("  - AuthenticatedReadUser")
    print("  - HighConcurrencyAuthUser")
    print("\nExample:")
    print(f"  locust -f {__file__} AuthenticationUser --users 100 --spawn-rate 10")
