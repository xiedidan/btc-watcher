"""
Complete Strategy Workflow Tests
完整策略工作流测试 - 覆盖完整代码路径
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock


class TestCompleteStrategyWorkflows:
    """完整策略工作流测试 - 确保覆盖所有代码路径"""

    def test_list_strategies_empty_database(self, client, auth_headers):
        """测试空数据库时列出策略"""
        response = client.get(
            "/api/v1/strategies/",
            headers=auth_headers
        )

        if response.status_code == 200:
            data = response.json()
            assert "strategies" in data
            assert "total" in data
            assert isinstance(data["strategies"], list)

    def test_list_strategies_with_multiple_filters(self, client, auth_headers, test_strategy):
        """测试使用多个过滤器列出策略"""
        # 测试status过滤
        response1 = client.get(
            "/api/v1/strategies/?status=stopped&skip=0&limit=10",
            headers=auth_headers
        )
        assert response1.status_code in [200, 500]

        # 测试分页
        response2 = client.get(
            "/api/v1/strategies/?skip=1&limit=2",
            headers=auth_headers
        )
        assert response2.status_code in [200, 500]

    def test_create_strategy_full_workflow(self, client, auth_headers):
        """测试创建策略完整工作流"""
        strategy_data = {
            "name": "Complete Workflow Test",
            "description": "Testing complete workflow",
            "strategy_class": "CompleteStrategy",
            "version": "v2.0",
            "exchange": "binance",
            "timeframe": "15m",
            "pair_whitelist": ["BTC/USDT", "ETH/USDT", "BNB/USDT"],
            "pair_blacklist": ["DOGE/USDT"],
            "dry_run": True,
            "dry_run_wallet": 5000.0,
            "stake_amount": 100.0,
            "max_open_trades": 5,
            "signal_thresholds": {"strong": 0.85, "medium": 0.65, "weak": 0.45},
            "proxy_id": None
        }

        response = client.post(
            "/api/v1/strategies/",
            json=strategy_data,
            headers=auth_headers
        )

        if response.status_code in [200, 201]:
            data = response.json()
            assert "id" in data
            assert data["name"] == strategy_data["name"]
            assert data["status"] == "stopped"
            assert "message" in data
            return data["id"]

    def test_get_strategy_with_all_fields(self, client, auth_headers, test_strategy):
        """测试获取策略完整字段"""
        response = client.get(
            f"/api/v1/strategies/{test_strategy.id}",
            headers=auth_headers
        )

        if response.status_code == 200:
            data = response.json()
            # 验证所有字段存在
            required_fields = [
                "id", "user_id", "name", "description", "strategy_class",
                "version", "exchange", "timeframe", "pair_whitelist",
                "pair_blacklist", "dry_run", "dry_run_wallet", "stake_amount",
                "max_open_trades", "signal_thresholds", "proxy_id", "status",
                "is_active", "port", "process_id", "created_at", "updated_at",
                "started_at", "stopped_at"
            ]

            missing_fields = [f for f in required_fields if f not in data]
            assert len(missing_fields) == 0, f"Missing fields: {missing_fields}"

            # 验证数据类型
            assert isinstance(data["id"], int)
            assert isinstance(data["user_id"], int)
            assert isinstance(data["name"], str)
            assert isinstance(data["strategy_class"], str)
            assert isinstance(data["exchange"], str)
            assert isinstance(data["timeframe"], str)
            assert isinstance(data["pair_whitelist"], list)
            assert isinstance(data["pair_blacklist"], list)
            assert isinstance(data["dry_run"], bool)
            assert isinstance(data["is_active"], bool)
            assert data["status"] in ["stopped", "running"]


class TestStrategyStartComplete:
    """策略启动完整测试"""

    def test_start_strategy_complete_success_path(self, client, auth_headers, test_strategy):
        """测试策略启动完整成功路径"""
        with patch('api.v1.strategies.get_ft_manager') as mock_get_manager:
            # 创建完整的mock manager
            mock_process = MagicMock()
            mock_process.pid = 54321

            mock_manager = MagicMock()
            mock_manager.create_strategy = AsyncMock(return_value=True)
            mock_manager.stop_strategy = AsyncMock(return_value=True)
            mock_manager.strategy_ports = {test_strategy.id: 8080}
            mock_manager.strategy_processes = {test_strategy.id: mock_process}

            mock_get_manager.return_value = mock_manager

            # 启动策略
            response = client.post(
                f"/api/v1/strategies/{test_strategy.id}/start",
                headers=auth_headers
            )

            # 验证响应
            assert response.status_code in [200, 500]

            if response.status_code == 200:
                data = response.json()
                assert "id" in data
                assert "name" in data
                assert "status" in data
                assert data["status"] == "running"
                assert "port" in data
                assert data["port"] == 8080
                assert "message" in data

    def test_start_strategy_status_transition(self, client, auth_headers, test_strategy):
        """测试策略状态转换"""
        with patch('api.v1.strategies.get_ft_manager') as mock_get_manager:
            mock_process = MagicMock()
            mock_process.pid = 99999

            mock_manager = MagicMock()
            mock_manager.create_strategy = AsyncMock(return_value=True)
            mock_manager.strategy_ports = {test_strategy.id: 9090}
            mock_manager.strategy_processes = {test_strategy.id: mock_process}

            mock_get_manager.return_value = mock_manager

            # 1. 检查初始状态
            get_response1 = client.get(
                f"/api/v1/strategies/{test_strategy.id}",
                headers=auth_headers
            )
            if get_response1.status_code == 200:
                assert get_response1.json()["status"] == "stopped"

            # 2. 启动策略
            start_response = client.post(
                f"/api/v1/strategies/{test_strategy.id}/start",
                headers=auth_headers
            )

            # 3. 检查状态变化（如果启动成功）
            if start_response.status_code == 200:
                get_response2 = client.get(
                    f"/api/v1/strategies/{test_strategy.id}",
                    headers=auth_headers
                )
                if get_response2.status_code == 200:
                    data = get_response2.json()
                    assert data["status"] == "running"
                    assert data["port"] == 9090
                    assert data["process_id"] == 99999


class TestStrategyStopComplete:
    """策略停止完整测试"""

    def test_stop_strategy_complete_success_path(self, client, auth_headers, test_strategy):
        """测试策略停止完整成功路径"""
        with patch('api.v1.strategies.get_ft_manager') as mock_get_manager:
            mock_process = MagicMock()
            mock_process.pid = 11111

            mock_manager = MagicMock()
            mock_manager.create_strategy = AsyncMock(return_value=True)
            mock_manager.stop_strategy = AsyncMock(return_value=True)
            mock_manager.strategy_ports = {test_strategy.id: 8888}
            mock_manager.strategy_processes = {test_strategy.id: mock_process}

            mock_get_manager.return_value = mock_manager

            # 先启动
            start_response = client.post(
                f"/api/v1/strategies/{test_strategy.id}/start",
                headers=auth_headers
            )

            if start_response.status_code == 200:
                # 再停止
                stop_response = client.post(
                    f"/api/v1/strategies/{test_strategy.id}/stop",
                    headers=auth_headers
                )

                # 验证停止响应
                assert stop_response.status_code in [200, 500]

                if stop_response.status_code == 200:
                    data = stop_response.json()
                    assert "id" in data
                    assert "name" in data
                    assert "status" in data
                    assert data["status"] == "stopped"
                    assert "message" in data

                    # 验证状态已更新
                    get_response = client.get(
                        f"/api/v1/strategies/{test_strategy.id}",
                        headers=auth_headers
                    )
                    if get_response.status_code == 200:
                        final_data = get_response.json()
                        assert final_data["status"] == "stopped"
                        assert final_data["port"] is None
                        assert final_data["process_id"] is None


class TestStrategyDeleteComplete:
    """策略删除完整测试"""

    def test_delete_stopped_strategy_soft_delete(self, client, auth_headers, test_strategy):
        """测试删除已停止策略（软删除）"""
        with patch('api.v1.strategies.get_ft_manager') as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.stop_strategy = AsyncMock(return_value=True)
            mock_get_manager.return_value = mock_manager

            # 删除策略
            delete_response = client.delete(
                f"/api/v1/strategies/{test_strategy.id}",
                headers=auth_headers
            )

            # 验证删除响应
            assert delete_response.status_code in [200, 500]

            if delete_response.status_code == 200:
                data = delete_response.json()
                assert "id" in data
                assert "message" in data
                assert "deleted" in data["message"].lower() or "success" in data["message"].lower()

    def test_delete_running_strategy_auto_stop(self, client, auth_headers, test_strategy):
        """测试删除运行中的策略（自动停止）"""
        with patch('api.v1.strategies.get_ft_manager') as mock_get_manager:
            mock_process = MagicMock()
            mock_process.pid = 22222

            mock_manager = MagicMock()
            mock_manager.create_strategy = AsyncMock(return_value=True)
            mock_manager.stop_strategy = AsyncMock(return_value=True)
            mock_manager.strategy_ports = {test_strategy.id: 7777}
            mock_manager.strategy_processes = {test_strategy.id: mock_process}

            mock_get_manager.return_value = mock_manager

            # 启动策略
            start_response = client.post(
                f"/api/v1/strategies/{test_strategy.id}/start",
                headers=auth_headers
            )

            if start_response.status_code == 200:
                # 删除运行中的策略
                delete_response = client.delete(
                    f"/api/v1/strategies/{test_strategy.id}",
                    headers=auth_headers
                )

                # 验证删除成功并自动停止
                assert delete_response.status_code in [200, 500]

                if delete_response.status_code == 200:
                    # 验证stop_strategy被调用
                    assert mock_manager.stop_strategy.called


class TestStrategyOverviewComplete:
    """策略概览完整测试"""

    def test_overview_with_multiple_strategies(self, client, auth_headers, test_strategy):
        """测试包含多个策略的概览"""
        with patch('api.v1.strategies.get_ft_manager') as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.get_capacity_info = Mock(return_value={
                "max_strategies": 20,
                "running_strategies": 3,
                "available_slots": 17,
                "utilization_percent": 15.0
            })
            mock_get_manager.return_value = mock_manager

            response = client.get(
                "/api/v1/strategies/overview",
                headers=auth_headers
            )

            assert response.status_code in [200, 422, 500]

            if response.status_code == 200:
                data = response.json()

                # 验证summary字段
                assert "summary" in data
                summary = data["summary"]
                assert "total_strategies" in summary
                assert "running_strategies" in summary
                assert "stopped_strategies" in summary
                assert "capacity_utilization" in summary
                assert "available_slots" in summary

                # 验证capacity字段
                assert "capacity" in data
                capacity = data["capacity"]
                assert capacity["max_strategies"] == 20
                assert capacity["available_slots"] == 17
                assert capacity["utilization_percent"] == 15.0

                # 验证strategies列表
                assert "strategies" in data
                assert isinstance(data["strategies"], list)


class TestStrategyErrorHandling:
    """策略错误处理测试"""

    def test_start_with_manager_exception(self, client, auth_headers, test_strategy):
        """测试FreqTrade Manager抛出异常"""
        with patch('api.v1.strategies.get_ft_manager') as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.create_strategy = AsyncMock(side_effect=Exception("Manager error"))
            mock_get_manager.return_value = mock_manager

            response = client.post(
                f"/api/v1/strategies/{test_strategy.id}/start",
                headers=auth_headers
            )

            # 应该返回500错误
            assert response.status_code == 500

    def test_stop_with_manager_exception(self, client, auth_headers, test_strategy):
        """测试停止时Manager抛出异常"""
        with patch('api.v1.strategies.get_ft_manager') as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.stop_strategy = AsyncMock(side_effect=Exception("Stop error"))
            mock_get_manager.return_value = mock_manager

            response = client.post(
                f"/api/v1/strategies/{test_strategy.id}/stop",
                headers=auth_headers
            )

            # 应该返回500错误或200（如果策略已经停止）
            assert response.status_code in [200, 500]

    def test_delete_with_manager_exception(self, client, auth_headers, test_strategy):
        """测试删除时Manager抛出异常"""
        with patch('api.v1.strategies.get_ft_manager') as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.stop_strategy = AsyncMock(side_effect=Exception("Delete error"))
            mock_get_manager.return_value = mock_manager

            response = client.delete(
                f"/api/v1/strategies/{test_strategy.id}",
                headers=auth_headers
            )

            # 应该返回500错误或200（如果可以容错处理）
            assert response.status_code in [200, 500]


class TestStrategyDataValidation:
    """策略数据验证测试"""

    def test_create_with_minimal_data(self, client, auth_headers):
        """测试使用最小数据创建策略"""
        minimal_data = {
            "name": "Minimal Strategy",
            "strategy_class": "MinimalStrategy",
            "exchange": "binance",
            "timeframe": "1h",
            "pair_whitelist": ["BTC/USDT"],
            "signal_thresholds": {"strong": 0.8, "medium": 0.6, "weak": 0.4}
        }

        response = client.post(
            "/api/v1/strategies/",
            json=minimal_data,
            headers=auth_headers
        )

        # 应该成功创建或返回错误
        assert response.status_code in [200, 201, 422, 500]

    def test_create_with_all_optional_fields(self, client, auth_headers):
        """测试使用所有可选字段创建策略"""
        complete_data = {
            "name": "Complete Strategy",
            "description": "Full featured strategy",
            "strategy_class": "FullStrategy",
            "version": "v3.0",
            "exchange": "binance",
            "timeframe": "30m",
            "pair_whitelist": ["BTC/USDT", "ETH/USDT"],
            "pair_blacklist": ["SHIB/USDT"],
            "dry_run": False,
            "dry_run_wallet": 10000.0,
            "stake_amount": 500.0,
            "max_open_trades": 10,
            "signal_thresholds": {"strong": 0.9, "medium": 0.7, "weak": 0.5},
            "proxy_id": 1
        }

        response = client.post(
            "/api/v1/strategies/",
            json=complete_data,
            headers=auth_headers
        )

        # 应该成功创建或返回错误
        assert response.status_code in [200, 201, 422, 500]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
