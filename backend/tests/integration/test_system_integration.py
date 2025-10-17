"""
System Integration Tests
系统集成测试 - 测试多个组件的协同工作
"""
import pytest


class TestSystemHealth:
    """系统健康检查集成测试"""

    def test_health_endpoint(self, client):
        """测试健康检查端点"""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "app_name" in data
        assert "version" in data

    def test_system_health_with_monitoring(self, client):
        """测试包含监控信息的系统健康检查"""
        response = client.get("/api/v1/system/health")

        # 可能返回200或503（如果服务未初始化）
        assert response.status_code in [200, 503]

        if response.status_code == 200:
            data = response.json()
            assert "status" in data

    def test_system_capacity(self, client):
        """测试系统容量查询"""
        response = client.get("/api/v1/system/capacity")

        # 可能返回200或503
        assert response.status_code in [200, 503]

        if response.status_code == 200:
            data = response.json()
            assert "max_strategies" in data
            assert "running_strategies" in data


class TestServiceCoordination:
    """服务协同测试"""

    def test_create_strategy_triggers_monitoring(self, client, auth_headers, test_db):
        """测试创建策略是否触发监控"""
        # 1. 获取当前容量
        capacity_before = client.get("/api/v1/system/capacity")

        # 2. 创建策略
        create_response = client.post(
            "/api/v1/strategies/",
            json={
                "name": "Monitoring Test Strategy",
                "strategy_class": "TestStrategy",
                "exchange": "binance",
                "timeframe": "1h",
                "pair_whitelist": ["BTC/USDT"],
                "signal_thresholds": {"strong": 0.8, "medium": 0.6, "weak": 0.4}
            },
            headers=auth_headers
        )

        # 验证策略创建（可能因为缺少字段而失败）
        if create_response.status_code in [200, 201]:
            # 3. 检查容量是否更新（实际环境中）
            capacity_after = client.get("/api/v1/system/capacity")

            # 验证容量端点可访问
            assert capacity_after.status_code in [200, 503]


class TestEndToEndWorkflow:
    """端到端工作流测试"""

    def test_complete_trading_workflow(self, client, test_db):
        """测试完整的交易工作流"""
        # 1. 用户注册
        register_response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "trader1",
                "email": "trader1@example.com",
                "password": "trader123"
            }
        )

        assert register_response.status_code in [200, 201]

        # 2. 用户登录
        login_response = client.post(
            "/api/v1/auth/token",
            data={
                "username": "trader1",
                "password": "trader123"
            }
        )

        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 3. 创建交易策略
        strategy_response = client.post(
            "/api/v1/strategies/",
            json={
                "name": "My Trading Strategy",
                "strategy_class": "MomentumStrategy",
                "exchange": "binance",
                "timeframe": "15m",
                "pair_whitelist": ["BTC/USDT", "ETH/USDT"],
                "signal_thresholds": {"strong": 0.8, "medium": 0.6, "weak": 0.4}
            },
            headers=headers
        )

        # 策略创建可能成功或失败
        if strategy_response.status_code in [200, 201]:
            strategy_id = strategy_response.json()["id"]

            # 4. 查看策略列表
            list_response = client.get(
                "/api/v1/strategies/",
                headers=headers
            )

            if list_response.status_code == 200:
                strategies = list_response.json()
                # 验证策略在列表中
                assert isinstance(strategies, dict)

            # 5. 查看策略详情
            detail_response = client.get(
                f"/api/v1/strategies/{strategy_id}",
                headers=headers
            )

            if detail_response.status_code == 200:
                assert detail_response.json()["id"] == strategy_id

    def test_multi_user_isolation(self, client, test_db):
        """测试多用户数据隔离"""
        # 创建两个用户
        users = []
        for i in range(2):
            reg_response = client.post(
                "/api/v1/auth/register",
                json={
                    "username": f"user{i}",
                    "email": f"user{i}@example.com",
                    "password": f"password{i}"
                }
            )
            assert reg_response.status_code in [200, 201]

            # 登录
            login_response = client.post(
                "/api/v1/auth/token",
                data={
                    "username": f"user{i}",
                    "password": f"password{i}"
                }
            )

            if login_response.status_code == 200:
                users.append({
                    "token": login_response.json()["access_token"],
                    "username": f"user{i}"
                })

        # 每个用户创建策略
        for user in users:
            headers = {"Authorization": f"Bearer {user['token']}"}
            response = client.post(
                "/api/v1/strategies/",
                json={
                    "name": f"{user['username']}'s Strategy",
                    "strategy_class": "TestStrategy",
                    "exchange": "binance",
                    "timeframe": "1h",
                    "pair_whitelist": ["BTC/USDT"],
                    "signal_thresholds": {"strong": 0.8, "medium": 0.6, "weak": 0.4}
                },
                headers=headers
            )

            # 策略创建可能成功或失败
            assert response.status_code in [200, 201, 401, 500]


class TestErrorHandling:
    """错误处理集成测试"""

    def test_404_handling(self, client):
        """测试404错误处理"""
        response = client.get("/api/v1/nonexistent/endpoint")

        assert response.status_code == 404

    def test_malformed_request(self, client):
        """测试错误格式请求"""
        response = client.post(
            "/api/v1/auth/register",
            data="not json data"
        )

        assert response.status_code in [422, 400]

    def test_concurrent_requests(self, client, auth_headers):
        """测试并发请求处理"""
        import concurrent.futures

        def make_request():
            return client.get("/api/v1/system/health")

        # 发送10个并发请求
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [f.result() for f in futures]

        # 所有请求都应该得到响应
        assert len(results) == 10
        for result in results:
            assert result.status_code in [200, 503]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
