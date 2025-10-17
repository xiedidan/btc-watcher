"""
Signal API Performance Tests
信号监控API性能测试

测试信号监控相关的API性能：
- 信号列表查询
- 信号过滤
- 信号详情查询
- Webhook接收
- 统计信息查询
"""
from locust import task, between
import logging
import random
import time
from .base_user import BTCWatcherUser
from .config import TEST_DATA, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


class SignalReadUser(BTCWatcherUser):
    """
    信号读操作用户
    User for signal read operations
    """

    wait_time = between(1, 4)

    @task(25)
    def get_signals_list(self):
        """
        获取信号列表
        Get signals list

        权重: 25 (最常用的操作)
        """
        try:
            response = self.api_get(
                "/signals/",
                name="GET /signals/ [LIST]"
            )

            if self.check_response(response, 200, "Get signals list"):
                data = response.json()
                logger.debug(f"Retrieved {len(data)} signals")

        except Exception as e:
            logger.error(f"Get signals list error: {e}")

    @task(15)
    def get_signals_with_pagination(self):
        """
        带分页的信号列表查询
        Get signals list with pagination

        权重: 15
        """
        try:
            skip = random.randint(0, 100)
            limit = random.choice([20, 50, 100])

            response = self.api_get(
                f"/signals/?skip={skip}&limit={limit}",
                name="GET /signals/ [PAGINATED]"
            )

            if self.check_response(response, 200, "Get paginated signals"):
                data = response.json()
                logger.debug(f"Retrieved page: skip={skip}, limit={limit}, count={len(data)}")

        except Exception as e:
            logger.error(f"Get paginated signals error: {e}")

    @task(10)
    def filter_signals_by_pair(self):
        """
        按交易对过滤信号
        Filter signals by pair

        权重: 10
        """
        try:
            pair = random.choice(TEST_DATA['signal']['pairs'])

            response = self.api_get(
                f"/signals/?pair={pair}",
                name="GET /signals/ [FILTER BY PAIR]"
            )

            if self.check_response(response, 200, f"Filter signals by {pair}"):
                data = response.json()
                logger.debug(f"Found {len(data)} signals for {pair}")

        except Exception as e:
            logger.error(f"Filter signals by pair error: {e}")

    @task(8)
    def filter_signals_by_action(self):
        """
        按操作类型过滤信号
        Filter signals by action

        权重: 8
        """
        try:
            action = random.choice(TEST_DATA['signal']['actions'])

            response = self.api_get(
                f"/signals/?action={action}",
                name="GET /signals/ [FILTER BY ACTION]"
            )

            if self.check_response(response, 200, f"Filter signals by {action}"):
                data = response.json()
                logger.debug(f"Found {len(data)} {action} signals")

        except Exception as e:
            logger.error(f"Filter signals by action error: {e}")

    @task(5)
    def filter_signals_by_strength(self):
        """
        按强度过滤信号
        Filter signals by strength

        权重: 5
        """
        try:
            strength_level = random.choice(["strong", "medium", "weak"])

            response = self.api_get(
                f"/signals/?strength_level={strength_level}",
                name="GET /signals/ [FILTER BY STRENGTH]"
            )

            if self.check_response(response, 200, f"Filter signals by {strength_level}"):
                data = response.json()
                logger.debug(f"Found {len(data)} {strength_level} signals")

        except Exception as e:
            logger.error(f"Filter signals by strength error: {e}")

    @task(8)
    def get_signal_detail(self):
        """
        获取信号详情
        Get signal detail

        权重: 8
        """
        try:
            # 首先获取信号列表
            list_response = self.api_get("/signals/?limit=10", name="GET /signals/ [FOR DETAIL]")

            if list_response.status_code == 200:
                signals = list_response.json()

                if signals and len(signals) > 0:
                    # 随机选择一个信号
                    signal = random.choice(signals)
                    signal_id = signal.get("id")

                    # 获取详情
                    detail_response = self.api_get(
                        f"/signals/{signal_id}",
                        name="GET /signals/{id} [DETAIL]"
                    )

                    self.check_response(detail_response, 200, f"Get signal {signal_id} detail")
                else:
                    logger.debug("No signals available for detail query")

        except Exception as e:
            logger.error(f"Get signal detail error: {e}")

    @task(5)
    def get_signals_statistics(self):
        """
        获取信号统计信息
        Get signals statistics

        权重: 5
        """
        try:
            response = self.api_get(
                "/signals/statistics",
                name="GET /signals/statistics [STATS]"
            )

            if self.check_response(response, 200, "Get signals statistics"):
                data = response.json()
                logger.debug(f"Statistics: {data}")

        except Exception as e:
            logger.error(f"Get signals statistics error: {e}")


class SignalWebhookUser(BTCWatcherUser):
    """
    信号Webhook用户
    User for signal webhook operations

    模拟FreqTrade发送信号
    """

    wait_time = between(2, 10)  # Webhook可能不那么频繁

    @task(10)
    def send_buy_signal(self):
        """
        发送买入信号
        Send buy signal

        权重: 10
        """
        try:
            # 获取可用策略
            strategies_response = self.api_get("/strategies/?limit=1", name="GET /strategies/ [FOR WEBHOOK]")

            if strategies_response.status_code == 200:
                strategies = strategies_response.json()

                if strategies:
                    strategy_id = strategies[0].get("id")
                    pair = random.choice(TEST_DATA['signal']['pairs'])
                    current_rate = random.uniform(40000, 50000)
                    signal_strength = random.choice(TEST_DATA['signal']['strengths'])

                    signal_data = {
                        "pair": pair,
                        "action": "buy",
                        "current_rate": current_rate,
                        "indicators": {
                            "signal_strength": signal_strength,
                            "rsi": random.uniform(30, 70),
                            "macd": random.uniform(-100, 100)
                        },
                        "metadata": {
                            "exchange": "binance",
                            "timeframe": "5m"
                        }
                    }

                    response = self.api_post(
                        f"/signals/webhook/{strategy_id}",
                        data=signal_data,
                        name="POST /signals/webhook/{id} [BUY]"
                    )

                    if response.status_code in [200, 201]:
                        logger.info(f"Buy signal sent for {pair} at {current_rate}")
                    else:
                        logger.warning(f"Send buy signal failed: {response.status_code}")
                else:
                    logger.debug("No strategies available for webhook")

        except Exception as e:
            logger.error(f"Send buy signal error: {e}")

    @task(8)
    def send_sell_signal(self):
        """
        发送卖出信号
        Send sell signal

        权重: 8
        """
        try:
            # 获取可用策略
            strategies_response = self.api_get("/strategies/?limit=1", name="GET /strategies/ [FOR WEBHOOK]")

            if strategies_response.status_code == 200:
                strategies = strategies_response.json()

                if strategies:
                    strategy_id = strategies[0].get("id")
                    pair = random.choice(TEST_DATA['signal']['pairs'])
                    current_rate = random.uniform(40000, 50000)
                    signal_strength = random.choice(TEST_DATA['signal']['strengths'])

                    signal_data = {
                        "pair": pair,
                        "action": "sell",
                        "current_rate": current_rate,
                        "indicators": {
                            "signal_strength": signal_strength,
                            "rsi": random.uniform(30, 70),
                            "macd": random.uniform(-100, 100)
                        },
                        "metadata": {
                            "exchange": "binance",
                            "timeframe": "5m"
                        }
                    }

                    response = self.api_post(
                        f"/signals/webhook/{strategy_id}",
                        data=signal_data,
                        name="POST /signals/webhook/{id} [SELL]"
                    )

                    if response.status_code in [200, 201]:
                        logger.info(f"Sell signal sent for {pair} at {current_rate}")
                    else:
                        logger.warning(f"Send sell signal failed: {response.status_code}")

        except Exception as e:
            logger.error(f"Send sell signal error: {e}")

    @task(2)
    def send_rapid_signals(self):
        """
        快速发送多个信号（峰值测试）
        Send rapid signals (spike test)

        权重: 2
        """
        try:
            # 获取可用策略
            strategies_response = self.api_get("/strategies/?limit=1", name="GET /strategies/ [FOR RAPID]")

            if strategies_response.status_code == 200:
                strategies = strategies_response.json()

                if strategies:
                    strategy_id = strategies[0].get("id")

                    # 快速发送5个信号
                    for i in range(5):
                        pair = random.choice(TEST_DATA['signal']['pairs'])
                        action = random.choice(TEST_DATA['signal']['actions'])
                        current_rate = random.uniform(40000, 50000)

                        signal_data = {
                            "pair": pair,
                            "action": action,
                            "current_rate": current_rate,
                            "indicators": {"signal_strength": 0.8}
                        }

                        self.api_post(
                            f"/signals/webhook/{strategy_id}",
                            data=signal_data,
                            name="POST /signals/webhook/{id} [RAPID]"
                        )

                        # 短暂延迟
                        time.sleep(0.1)

                    logger.info(f"Sent 5 rapid signals for strategy {strategy_id}")

        except Exception as e:
            logger.error(f"Send rapid signals error: {e}")


class SignalComplexQueryUser(BTCWatcherUser):
    """
    信号复杂查询用户
    User for complex signal queries

    执行复杂的过滤和查询组合
    """

    wait_time = between(2, 6)

    @task(10)
    def complex_filter_query(self):
        """
        复杂过滤查询
        Complex filter query

        权重: 10
        """
        try:
            pair = random.choice(TEST_DATA['signal']['pairs'])
            action = random.choice(TEST_DATA['signal']['actions'])
            strength = random.choice(["strong", "medium"])
            limit = random.choice([10, 20, 50])

            response = self.api_get(
                f"/signals/?pair={pair}&action={action}&strength_level={strength}&limit={limit}",
                name="GET /signals/ [COMPLEX FILTER]"
            )

            if self.check_response(response, 200, "Complex filter query"):
                data = response.json()
                logger.debug(f"Complex filter result: {len(data)} signals")

        except Exception as e:
            logger.error(f"Complex filter query error: {e}")

    @task(5)
    def date_range_query(self):
        """
        日期范围查询
        Date range query

        权重: 5
        """
        try:
            # 获取最近7天的信号
            import datetime
            end_date = datetime.datetime.now()
            start_date = end_date - datetime.timedelta(days=7)

            response = self.api_get(
                f"/signals/?start_date={start_date.isoformat()}&end_date={end_date.isoformat()}",
                name="GET /signals/ [DATE RANGE]"
            )

            if self.check_response(response, 200, "Date range query"):
                data = response.json()
                logger.debug(f"Date range result: {len(data)} signals")

        except Exception as e:
            logger.error(f"Date range query error: {e}")

    @task(3)
    def aggregation_query(self):
        """
        聚合查询
        Aggregation query

        权重: 3
        """
        try:
            # 按交易对统计
            response = self.api_get(
                "/signals/statistics?group_by=pair",
                name="GET /signals/statistics [AGGREGATION]"
            )

            if self.check_response(response, 200, "Aggregation query"):
                data = response.json()
                logger.debug(f"Aggregation result: {data}")

        except Exception as e:
            logger.error(f"Aggregation query error: {e}")


class SignalMixedUser(BTCWatcherUser):
    """
    信号混合操作用户
    User with mixed signal operations

    模拟真实用户的行为：查看、过滤、详情
    """

    wait_time = between(2, 5)

    @task(20)
    def browse_signals(self):
        """浏览信号列表"""
        response = self.api_get("/signals/?limit=20", name="GET /signals/ [BROWSE]")
        self.check_response(response, 200, "Browse signals")

    @task(10)
    def filter_and_view_details(self):
        """过滤并查看详情"""
        try:
            # 1. 按交易对过滤
            pair = random.choice(TEST_DATA['signal']['pairs'])
            filter_response = self.api_get(
                f"/signals/?pair={pair}&limit=10",
                name="GET /signals/ [MIXED FILTER]"
            )

            if filter_response.status_code == 200:
                signals = filter_response.json()

                if signals:
                    # 2. 查看第一个信号的详情
                    signal_id = signals[0].get("id")
                    self.api_get(
                        f"/signals/{signal_id}",
                        name="GET /signals/{id} [MIXED DETAIL]"
                    )

                    logger.debug(f"Mixed user: filtered {pair} and viewed signal {signal_id}")

        except Exception as e:
            logger.error(f"Filter and view details error: {e}")

    @task(5)
    def check_statistics_workflow(self):
        """查看统计信息工作流程"""
        try:
            # 1. 查看总体统计
            self.api_get("/signals/statistics", name="GET /signals/statistics [MIXED STATS]")

            # 2. 等待
            time.sleep(1)

            # 3. 查看最近的信号
            self.api_get("/signals/?limit=5", name="GET /signals/ [MIXED RECENT]")

            logger.debug("Mixed user: checked statistics workflow")

        except Exception as e:
            logger.error(f"Check statistics workflow error: {e}")


# 用于命令行直接运行
if __name__ == "__main__":
    print("This is a Locust test file. Run it with:")
    print(f"  locust -f {__file__} --host=http://localhost:8000")
    print("\nAvailable user classes:")
    print("  - SignalReadUser (default)")
    print("  - SignalWebhookUser")
    print("  - SignalComplexQueryUser")
    print("  - SignalMixedUser")
