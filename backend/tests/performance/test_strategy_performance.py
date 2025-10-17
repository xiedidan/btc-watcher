"""
Strategy API Performance Tests
策略管理API性能测试

测试策略管理相关的API性能：
- 策略列表查询
- 策略创建
- 策略启动/停止
- 策略删除
- 策略详情查询
"""
from locust import task, between
import logging
import random
import time
from .base_user import BTCWatcherUser
from .config import TEST_DATA

logger = logging.getLogger(__name__)


class StrategyReadUser(BTCWatcherUser):
    """
    策略读操作用户
    User for strategy read operations
    """

    wait_time = between(1, 3)

    @task(20)
    def get_strategies_list(self):
        """
        获取策略列表
        Get strategies list

        权重: 20 (最常用的操作)
        """
        try:
            response = self.api_get(
                "/strategies/",
                name="GET /strategies/ [LIST]"
            )

            if self.check_response(response, 200, "Get strategies list"):
                data = response.json()
                logger.debug(f"Retrieved {len(data)} strategies")

        except Exception as e:
            logger.error(f"Get strategies list error: {e}")

    @task(10)
    def get_strategies_with_pagination(self):
        """
        带分页的策略列表查询
        Get strategies list with pagination

        权重: 10
        """
        try:
            skip = random.randint(0, 50)
            limit = random.choice([10, 20, 50])

            response = self.api_get(
                f"/strategies/?skip={skip}&limit={limit}",
                name="GET /strategies/ [PAGINATED]"
            )

            if self.check_response(response, 200, "Get paginated strategies"):
                data = response.json()
                logger.debug(f"Retrieved page: skip={skip}, limit={limit}, count={len(data)}")

        except Exception as e:
            logger.error(f"Get paginated strategies error: {e}")

    @task(5)
    def get_strategy_detail(self):
        """
        获取策略详情
        Get strategy detail

        权重: 5
        """
        try:
            # 首先获取策略列表
            list_response = self.api_get("/strategies/", name="GET /strategies/ [FOR DETAIL]")

            if list_response.status_code == 200:
                strategies = list_response.json()

                if strategies and len(strategies) > 0:
                    # 随机选择一个策略
                    strategy = random.choice(strategies)
                    strategy_id = strategy.get("id")

                    # 获取详情
                    detail_response = self.api_get(
                        f"/strategies/{strategy_id}",
                        name="GET /strategies/{id} [DETAIL]"
                    )

                    self.check_response(detail_response, 200, f"Get strategy {strategy_id} detail")
                else:
                    logger.debug("No strategies available for detail query")

        except Exception as e:
            logger.error(f"Get strategy detail error: {e}")

    @task(3)
    def get_strategy_overview(self):
        """
        获取策略概览
        Get strategy overview

        权重: 3
        """
        try:
            response = self.api_get(
                "/strategies/overview",
                name="GET /strategies/overview [OVERVIEW]"
            )

            if self.check_response(response, 200, "Get strategies overview"):
                data = response.json()
                logger.debug(f"Overview: {data}")

        except Exception as e:
            logger.error(f"Get strategy overview error: {e}")


class StrategyWriteUser(BTCWatcherUser):
    """
    策略写操作用户
    User for strategy write operations
    """

    wait_time = between(2, 5)

    # 保存创建的策略ID，用于后续操作
    created_strategy_ids = []

    @task(10)
    def create_strategy(self):
        """
        创建策略
        Create strategy

        权重: 10
        """
        try:
            strategy_name = f"{TEST_DATA['strategy']['name_prefix']} {int(time.time())}"

            strategy_data = {
                "name": strategy_name,
                "description": "Performance test strategy",
                "config": TEST_DATA['strategy']['config']
            }

            response = self.api_post(
                "/strategies/",
                data=strategy_data,
                name="POST /strategies/ [CREATE]"
            )

            if response.status_code in [200, 201]:
                data = response.json()
                strategy_id = data.get("id")
                self.created_strategy_ids.append(strategy_id)
                logger.info(f"Strategy created: {strategy_id}")
            else:
                logger.warning(f"Create strategy failed: {response.status_code}")

        except Exception as e:
            logger.error(f"Create strategy error: {e}")

    @task(5)
    def update_strategy(self):
        """
        更新策略
        Update strategy

        权重: 5
        """
        if not self.created_strategy_ids:
            logger.debug("No strategies to update")
            return

        try:
            strategy_id = random.choice(self.created_strategy_ids)

            update_data = {
                "description": f"Updated at {int(time.time())}",
                "config": TEST_DATA['strategy']['config']
            }

            response = self.api_put(
                f"/strategies/{strategy_id}",
                data=update_data,
                name="PUT /strategies/{id} [UPDATE]"
            )

            self.check_response(response, 200, f"Update strategy {strategy_id}")

        except Exception as e:
            logger.error(f"Update strategy error: {e}")

    @task(3)
    def delete_strategy(self):
        """
        删除策略
        Delete strategy

        权重: 3
        """
        if not self.created_strategy_ids:
            logger.debug("No strategies to delete")
            return

        try:
            strategy_id = self.created_strategy_ids.pop(0)

            response = self.api_delete(
                f"/strategies/{strategy_id}",
                name="DELETE /strategies/{id} [DELETE]"
            )

            if response.status_code in [200, 204]:
                logger.info(f"Strategy deleted: {strategy_id}")
            else:
                logger.warning(f"Delete strategy failed: {response.status_code}")

        except Exception as e:
            logger.error(f"Delete strategy error: {e}")


class StrategyOperationsUser(BTCWatcherUser):
    """
    策略操作用户（启动/停止）
    User for strategy operations (start/stop)
    """

    wait_time = between(3, 8)

    @task(10)
    def start_strategy(self):
        """
        启动策略
        Start strategy

        权重: 10
        """
        try:
            # 获取停止状态的策略
            list_response = self.api_get("/strategies/", name="GET /strategies/ [FOR START]")

            if list_response.status_code == 200:
                strategies = list_response.json()
                # 过滤出停止状态的策略
                stopped_strategies = [s for s in strategies if s.get("status") == "stopped"]

                if stopped_strategies:
                    strategy = random.choice(stopped_strategies)
                    strategy_id = strategy.get("id")

                    # 启动策略
                    response = self.api_post(
                        f"/strategies/{strategy_id}/start",
                        data={},
                        name="POST /strategies/{id}/start [START]"
                    )

                    if response.status_code in [200, 201]:
                        logger.info(f"Strategy started: {strategy_id}")
                    else:
                        logger.warning(f"Start strategy failed: {response.status_code}")
                else:
                    logger.debug("No stopped strategies to start")

        except Exception as e:
            logger.error(f"Start strategy error: {e}")

    @task(8)
    def stop_strategy(self):
        """
        停止策略
        Stop strategy

        权重: 8
        """
        try:
            # 获取运行中的策略
            list_response = self.api_get("/strategies/", name="GET /strategies/ [FOR STOP]")

            if list_response.status_code == 200:
                strategies = list_response.json()
                # 过滤出运行中的策略
                running_strategies = [s for s in strategies if s.get("status") == "running"]

                if running_strategies:
                    strategy = random.choice(running_strategies)
                    strategy_id = strategy.get("id")

                    # 停止策略
                    response = self.api_post(
                        f"/strategies/{strategy_id}/stop",
                        data={},
                        name="POST /strategies/{id}/stop [STOP]"
                    )

                    if response.status_code in [200, 201]:
                        logger.info(f"Strategy stopped: {strategy_id}")
                    else:
                        logger.warning(f"Stop strategy failed: {response.status_code}")
                else:
                    logger.debug("No running strategies to stop")

        except Exception as e:
            logger.error(f"Stop strategy error: {e}")

    @task(2)
    def get_strategy_logs(self):
        """
        获取策略日志
        Get strategy logs

        权重: 2
        """
        try:
            # 获取策略列表
            list_response = self.api_get("/strategies/", name="GET /strategies/ [FOR LOGS]")

            if list_response.status_code == 200:
                strategies = list_response.json()

                if strategies:
                    strategy = random.choice(strategies)
                    strategy_id = strategy.get("id")

                    # 获取日志
                    response = self.api_get(
                        f"/strategies/{strategy_id}/logs",
                        name="GET /strategies/{id}/logs [LOGS]"
                    )

                    if response.status_code == 200:
                        logger.debug(f"Retrieved logs for strategy {strategy_id}")
                    elif response.status_code == 404:
                        logger.debug(f"No logs found for strategy {strategy_id}")

        except Exception as e:
            logger.error(f"Get strategy logs error: {e}")


class StrategyMixedUser(BTCWatcherUser):
    """
    策略混合操作用户
    User with mixed strategy operations

    模拟真实用户的行为模式
    """

    wait_time = between(2, 6)

    created_strategies = []

    @task(15)
    def browse_strategies(self):
        """浏览策略列表"""
        response = self.api_get("/strategies/", name="GET /strategies/ [BROWSE]")
        self.check_response(response, 200, "Browse strategies")

    @task(5)
    def create_and_manage_strategy(self):
        """创建并管理策略的完整流程"""
        try:
            # 1. 创建策略
            strategy_name = f"Mixed User Strategy {int(time.time())}"
            create_response = self.api_post(
                "/strategies/",
                data={
                    "name": strategy_name,
                    "description": "Mixed user test strategy",
                    "config": TEST_DATA['strategy']['config']
                },
                name="POST /strategies/ [MIXED CREATE]"
            )

            if create_response.status_code in [200, 201]:
                strategy_id = create_response.json().get("id")
                logger.info(f"Mixed user created strategy: {strategy_id}")

                # 2. 等待一下（模拟用户思考）
                time.sleep(2)

                # 3. 查看详情
                self.api_get(f"/strategies/{strategy_id}", name="GET /strategies/{id} [MIXED DETAIL]")

                # 4. 等待
                time.sleep(1)

                # 5. 启动策略
                self.api_post(f"/strategies/{strategy_id}/start", data={}, name="POST /strategies/{id}/start [MIXED START]")

                # 6. 等待
                time.sleep(3)

                # 7. 停止策略
                self.api_post(f"/strategies/{strategy_id}/stop", data={}, name="POST /strategies/{id}/stop [MIXED STOP]")

                # 8. 等待
                time.sleep(1)

                # 9. 删除策略
                self.api_delete(f"/strategies/{strategy_id}", name="DELETE /strategies/{id} [MIXED DELETE]")

                logger.info(f"Mixed user completed full lifecycle for strategy: {strategy_id}")

        except Exception as e:
            logger.error(f"Mixed user workflow error: {e}")


# 用于命令行直接运行
if __name__ == "__main__":
    print("This is a Locust test file. Run it with:")
    print(f"  locust -f {__file__} --host=http://localhost:8000")
    print("\nAvailable user classes:")
    print("  - StrategyReadUser (default)")
    print("  - StrategyWriteUser")
    print("  - StrategyOperationsUser")
    print("  - StrategyMixedUser")
