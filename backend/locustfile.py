"""
BTC Watcher Comprehensive Load Test
BTC Watcher综合负载测试

这是主要的Locust测试文件，包含完整的负载测试场景。

使用方式:
    locust -f locustfile.py --host=http://localhost:8000

Web UI:
    访问 http://localhost:8089 进行交互式测试
"""
from locust import HttpUser, task, between, events
import logging
import random
import time

# 导入所有测试用户类
from tests.performance.test_auth_performance import (
    AuthenticationUser,
    AuthenticatedReadUser
)
from tests.performance.test_strategy_performance import (
    StrategyReadUser,
    StrategyWriteUser,
    StrategyOperationsUser
)
from tests.performance.test_signal_performance import (
    SignalReadUser,
    SignalWebhookUser,
    SignalMixedUser
)
from tests.performance.config import (
    API_BASE_URL,
    PERFORMANCE_TARGETS,
    get_test_scenario
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================
# 综合场景用户类
# ============================================

class RealWorldUser(HttpUser):
    """
    真实世界用户模拟
    Simulates real-world user behavior

    结合认证、策略管理和信号监控的完整用户旅程
    """

    wait_time = between(3, 10)
    host = API_BASE_URL

    # 用户信息
    access_token = None
    user_credentials = {"username": "testuser", "password": "testpass123"}

    def on_start(self):
        """用户开始时登录"""
        self.login()

    def login(self):
        """用户登录"""
        try:
            response = self.client.post(
                "/api/v1/auth/token",
                data={
                    "username": self.user_credentials["username"],
                    "password": self.user_credentials["password"]
                },
                name="/auth/token [REAL USER LOGIN]"
            )

            if response.status_code == 200:
                self.access_token = response.json().get("access_token")
                logger.info("Real user logged in successfully")
            else:
                logger.error(f"Real user login failed: {response.status_code}")

        except Exception as e:
            logger.error(f"Real user login error: {e}")

    def get_headers(self):
        """获取认证头"""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    @task(10)
    def check_dashboard(self):
        """
        查看仪表盘（检查策略和信号概览）
        Check dashboard

        权重: 10 (最常见的操作)
        """
        try:
            # 获取策略概览
            self.client.get(
                "/api/v1/strategies/overview",
                headers=self.get_headers(),
                name="GET /strategies/overview [DASHBOARD]"
            )

            # 获取最近的信号
            self.client.get(
                "/api/v1/signals/?limit=10",
                headers=self.get_headers(),
                name="GET /signals/ [DASHBOARD SIGNALS]"
            )

            logger.debug("Real user checked dashboard")

        except Exception as e:
            logger.error(f"Check dashboard error: {e}")

    @task(8)
    def browse_strategies(self):
        """
        浏览策略列表
        Browse strategies

        权重: 8
        """
        try:
            response = self.client.get(
                "/api/v1/strategies/",
                headers=self.get_headers(),
                name="GET /strategies/ [REAL USER]"
            )

            if response.status_code == 200:
                strategies = response.json()
                logger.debug(f"Real user browsed {len(strategies)} strategies")

                # 可能会查看一个策略的详情
                if strategies and random.random() < 0.3:
                    strategy = random.choice(strategies)
                    self.client.get(
                        f"/api/v1/strategies/{strategy['id']}",
                        headers=self.get_headers(),
                        name="GET /strategies/{id} [REAL USER]"
                    )

        except Exception as e:
            logger.error(f"Browse strategies error: {e}")

    @task(8)
    def monitor_signals(self):
        """
        监控信号
        Monitor signals

        权重: 8
        """
        try:
            # 可能会应用一些过滤
            if random.random() < 0.5:
                pair = random.choice(["BTC/USDT", "ETH/USDT"])
                url = f"/api/v1/signals/?pair={pair}"
            else:
                url = "/api/v1/signals/?limit=20"

            response = self.client.get(
                url,
                headers=self.get_headers(),
                name="GET /signals/ [REAL USER]"
            )

            if response.status_code == 200:
                signals = response.json()
                logger.debug(f"Real user monitored {len(signals)} signals")

        except Exception as e:
            logger.error(f"Monitor signals error: {e}")

    @task(3)
    def manage_strategy(self):
        """
        管理策略（启动/停止）
        Manage strategy

        权重: 3 (较少执行)
        """
        try:
            # 获取策略列表
            response = self.client.get(
                "/api/v1/strategies/",
                headers=self.get_headers(),
                name="GET /strategies/ [FOR MANAGEMENT]"
            )

            if response.status_code == 200:
                strategies = response.json()

                if strategies:
                    strategy = random.choice(strategies)
                    status = strategy.get("status")

                    # 根据状态执行操作
                    if status == "stopped" and random.random() < 0.5:
                        # 启动策略
                        self.client.post(
                            f"/api/v1/strategies/{strategy['id']}/start",
                            json={},
                            headers=self.get_headers(),
                            name="POST /strategies/{id}/start [REAL USER]"
                        )
                        logger.debug(f"Real user started strategy {strategy['id']}")

                    elif status == "running" and random.random() < 0.3:
                        # 停止策略
                        self.client.post(
                            f"/api/v1/strategies/{strategy['id']}/stop",
                            json={},
                            headers=self.get_headers(),
                            name="POST /strategies/{id}/stop [REAL USER]"
                        )
                        logger.debug(f"Real user stopped strategy {strategy['id']}")

        except Exception as e:
            logger.error(f"Manage strategy error: {e}")

    @task(2)
    def check_statistics(self):
        """
        查看统计信息
        Check statistics

        权重: 2
        """
        try:
            self.client.get(
                "/api/v1/signals/statistics",
                headers=self.get_headers(),
                name="GET /signals/statistics [REAL USER]"
            )

            logger.debug("Real user checked statistics")

        except Exception as e:
            logger.error(f"Check statistics error: {e}")


class APIMonitorUser(HttpUser):
    """
    API监控用户
    API monitoring user

    持续检查关键API端点的健康状态和响应时间
    """

    wait_time = between(5, 15)
    host = API_BASE_URL

    access_token = None

    def on_start(self):
        """登录"""
        response = self.client.post(
            "/api/v1/auth/token",
            data={"username": "testuser", "password": "testpass123"},
            name="/auth/token [MONITOR]"
        )
        if response.status_code == 200:
            self.access_token = response.json().get("access_token")

    def get_headers(self):
        return {"Authorization": f"Bearer {self.access_token}"}

    @task(10)
    def health_check_strategies(self):
        """策略API健康检查"""
        self.client.get(
            "/api/v1/strategies/",
            headers=self.get_headers(),
            name="HEALTH CHECK /strategies/",
            catch_response=True
        ).success()

    @task(10)
    def health_check_signals(self):
        """信号API健康检查"""
        self.client.get(
            "/api/v1/signals/?limit=1",
            headers=self.get_headers(),
            name="HEALTH CHECK /signals/",
            catch_response=True
        ).success()

    @task(5)
    def health_check_overview(self):
        """概览API健康检查"""
        self.client.get(
            "/api/v1/strategies/overview",
            headers=self.get_headers(),
            name="HEALTH CHECK /strategies/overview",
            catch_response=True
        ).success()


# ============================================
# 事件监听器 - 用于自定义报告和监控
# ============================================

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """测试开始时执行"""
    logger.info("="*60)
    logger.info("BTC Watcher Performance Test Started")
    logger.info(f"Host: {API_BASE_URL}")
    logger.info(f"Performance Targets:")
    logger.info(f"  - Response Time: {PERFORMANCE_TARGETS['response_time']}")
    logger.info(f"  - Throughput: {PERFORMANCE_TARGETS['throughput']}")
    logger.info("="*60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """测试停止时执行"""
    logger.info("="*60)
    logger.info("BTC Watcher Performance Test Completed")

    # 获取统计信息
    stats = environment.stats
    logger.info(f"Total Requests: {stats.total.num_requests}")
    logger.info(f"Total Failures: {stats.total.num_failures}")
    logger.info(f"Average Response Time: {stats.total.avg_response_time:.2f}ms")
    logger.info(f"Max Response Time: {stats.total.max_response_time:.2f}ms")
    logger.info(f"Requests/sec: {stats.total.current_rps:.2f}")

    # 检查是否达到性能目标
    avg_response_time = stats.total.avg_response_time
    error_rate = stats.total.fail_ratio

    if avg_response_time < PERFORMANCE_TARGETS['response_time']['good']:
        logger.info("✅ Response time target achieved (< 300ms)")
    elif avg_response_time < PERFORMANCE_TARGETS['response_time']['acceptable']:
        logger.warning("⚠️  Response time acceptable (< 1000ms)")
    else:
        logger.error("❌ Response time target NOT met (> 1000ms)")

    if error_rate < PERFORMANCE_TARGETS['error_rate']['acceptable']:
        logger.info("✅ Error rate target achieved (< 1%)")
    elif error_rate < PERFORMANCE_TARGETS['error_rate']['warning']:
        logger.warning("⚠️  Error rate acceptable (< 5%)")
    else:
        logger.error("❌ Error rate target NOT met (> 5%)")

    logger.info("="*60)


# ============================================
# 默认导出
# ============================================

# 如果直接运行locustfile.py，使用RealWorldUser
__all__ = [
    "RealWorldUser",
    "APIMonitorUser",
    # 以下可以通过命令行指定
    "AuthenticationUser",
    "StrategyReadUser",
    "SignalReadUser"
]


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════╗
║           BTC Watcher Performance Test Suite                ║
╚══════════════════════════════════════════════════════════════╝

Run with Locust:
  locust -f locustfile.py --host=http://localhost:8000

Open Web UI:
  http://localhost:8089

Available Test Scenarios:
  1. Real World User (default) - 真实用户行为模拟
  2. API Monitor User - API健康监控
  3. Authentication Load - 认证负载测试
  4. Strategy Operations - 策略操作测试
  5. Signal Processing - 信号处理测试

Example Commands:
  # 快速测试 (10 users)
  locust -f locustfile.py --users 10 --spawn-rate 2 --run-time 1m

  # 负载测试 (100 users)
  locust -f locustfile.py --users 100 --spawn-rate 10 --run-time 5m

  # 压力测试 (500 users)
  locust -f locustfile.py --users 500 --spawn-rate 50 --run-time 10m

  # 无头模式 + CSV报告
  locust -f locustfile.py --headless --users 100 --spawn-rate 10 \\
         --run-time 5m --csv=reports/performance --html=reports/report.html

Performance Targets:
  - Response Time: < 300ms (good), < 1000ms (acceptable)
  - Throughput: 1000 req/s (read), 100 req/s (write)
  - Error Rate: < 1% (acceptable), < 5% (warning)
    """)
