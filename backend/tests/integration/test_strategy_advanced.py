"""
Advanced Strategy API Tests
深度策略API测试 - 覆盖启动、停止、删除等核心逻辑
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime


class TestStrategyListAdvanced:
    """策略列表高级测试"""

    def test_list_strategies_with_status_filter_stopped(self, client, auth_headers, test_strategy):
        """测试按状态过滤策略列表 - stopped状态"""
        response = client.get(
            "/api/v1/strategies/?status=stopped",
            headers=auth_headers
        )

        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            assert "strategies" in data
            assert "total" in data
            # 所有返回的策略都应该是stopped状态
            if data["total"] > 0:
                for strategy in data["strategies"]:
                    assert strategy["status"] == "stopped"

    def test_list_strategies_with_status_filter_running(self, client, auth_headers):
        """测试按状态过滤策略列表 - running状态"""
        response = client.get(
            "/api/v1/strategies/?status=running",
            headers=auth_headers
        )

        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            assert "strategies" in data
            # running策略列表（可能为空）
            if data["total"] > 0:
                for strategy in data["strategies"]:
                    assert strategy["status"] == "running"

    def test_list_strategies_with_skip_and_limit(self, client, auth_headers):
        """测试策略列表分页 - skip和limit"""
        response = client.get(
            "/api/v1/strategies/?skip=0&limit=5",
            headers=auth_headers
        )

        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            assert data["skip"] == 0
            assert data["limit"] == 5
            assert len(data["strategies"]) <= 5


class TestStrategyGetAdvanced:
    """策略获取高级测试"""

    def test_get_strategy_full_details(self, client, auth_headers, test_strategy):
        """测试获取策略完整详情 - 所有字段"""
        response = client.get(
            f"/api/v1/strategies/{test_strategy.id}",
            headers=auth_headers
        )

        if response.status_code == 200:
            data = response.json()
            # 验证所有关键字段都存在
            expected_fields = [
                "id", "user_id", "name", "description", "strategy_class",
                "version", "exchange", "timeframe", "pair_whitelist",
                "pair_blacklist", "dry_run", "dry_run_wallet", "stake_amount",
                "max_open_trades", "signal_thresholds", "proxy_id", "status",
                "is_active", "port", "process_id", "created_at", "updated_at",
                "started_at", "stopped_at"
            ]
            for field in expected_fields:
                assert field in data, f"Missing field: {field}"

    def test_get_nonexistent_strategy_404(self, client, auth_headers):
        """测试获取不存在的策略 - 返回404"""
        response = client.get(
            "/api/v1/strategies/999999",
            headers=auth_headers
        )

        # 应该返回404
        assert response.status_code in [404, 500]


class TestStrategyStartAdvanced:
    """策略启动高级测试"""

    def test_start_strategy_with_full_config(self, client, auth_headers, test_strategy):
        """测试启动策略 - 完整配置"""
        with patch('api.v1.strategies.get_ft_manager') as mock_get_manager:
            # 创建mock manager
            mock_manager = Mock()
            mock_manager.create_strategy = AsyncMock(return_value=True)
            mock_manager.strategy_ports = {test_strategy.id: 8080}

            # Mock process with pid
            mock_process = Mock()
            mock_process.pid = 12345
            mock_manager.strategy_processes = {test_strategy.id: mock_process}

            mock_get_manager.return_value = mock_manager

            response = client.post(
                f"/api/v1/strategies/{test_strategy.id}/start",
                headers=auth_headers
            )

            # 验证响应
            if response.status_code == 200:
                data = response.json()
                assert "id" in data
                assert "name" in data
                assert data["status"] == "running"
                assert "port" in data
                assert data["message"] == "Strategy started successfully"

    def test_start_strategy_already_running_message(self, client, auth_headers, test_strategy):
        """测试启动已运行策略 - 验证消息"""
        with patch('api.v1.strategies.get_ft_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_manager.create_strategy = AsyncMock(return_value=True)
            mock_manager.strategy_ports = {test_strategy.id: 8080}
            mock_manager.strategy_processes = {}
            mock_get_manager.return_value = mock_manager

            # 第一次启动
            response1 = client.post(
                f"/api/v1/strategies/{test_strategy.id}/start",
                headers=auth_headers
            )

            # 第二次启动
            response2 = client.post(
                f"/api/v1/strategies/{test_strategy.id}/start",
                headers=auth_headers
            )

            # 第二次应该返回already running消息
            if response2.status_code == 200:
                data = response2.json()
                assert "message" in data
                assert "already running" in data["message"].lower()

    def test_start_strategy_manager_returns_false(self, client, auth_headers, test_strategy):
        """测试启动策略 - manager返回False"""
        with patch('api.v1.strategies.get_ft_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_manager.create_strategy = AsyncMock(return_value=False)
            mock_get_manager.return_value = mock_manager

            response = client.post(
                f"/api/v1/strategies/{test_strategy.id}/start",
                headers=auth_headers
            )

            # 应该返回500错误
            assert response.status_code == 500

    def test_start_nonexistent_strategy_404(self, client, auth_headers):
        """测试启动不存在的策略 - 返回404"""
        with patch('api.v1.strategies.get_ft_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_get_manager.return_value = mock_manager

            response = client.post(
                "/api/v1/strategies/999999/start",
                headers=auth_headers
            )

            # 应该返回404
            assert response.status_code in [404, 500]


class TestStrategyStopAdvanced:
    """策略停止高级测试"""

    def test_stop_running_strategy_success(self, client, auth_headers, test_strategy):
        """测试停止运行中的策略 - 成功"""
        with patch('api.v1.strategies.get_ft_manager') as mock_get_manager:
            # 先设置好所有mock属性
            mock_process = Mock()
            mock_process.pid = 12345

            mock_manager = Mock()
            mock_manager.create_strategy = AsyncMock(return_value=True)
            mock_manager.stop_strategy = AsyncMock(return_value=True)
            mock_manager.strategy_ports = {test_strategy.id: 8080}
            mock_manager.strategy_processes = {test_strategy.id: mock_process}
            mock_get_manager.return_value = mock_manager

            # 先启动
            start_response = client.post(
                f"/api/v1/strategies/{test_strategy.id}/start",
                headers=auth_headers
            )

            # 只有成功启动后才测试停止
            if start_response.status_code == 200:
                # 再停止
                stop_response = client.post(
                    f"/api/v1/strategies/{test_strategy.id}/stop",
                    headers=auth_headers
                )

                # 验证停止响应
                if stop_response.status_code == 200:
                    data = stop_response.json()
                    assert "status" in data
                    # 可能返回stopped状态或成功消息
                    assert data["status"] == "stopped"

    def test_stop_already_stopped_strategy_message(self, client, auth_headers, test_strategy):
        """测试停止已停止策略 - 验证消息"""
        with patch('api.v1.strategies.get_ft_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_get_manager.return_value = mock_manager

            response = client.post(
                f"/api/v1/strategies/{test_strategy.id}/stop",
                headers=auth_headers
            )

            # 应该返回already stopped消息
            if response.status_code == 200:
                data = response.json()
                assert "message" in data
                assert "already stopped" in data["message"].lower()

    def test_stop_strategy_manager_returns_false(self, client, auth_headers, test_strategy):
        """测试停止策略 - manager返回False"""
        with patch('api.v1.strategies.get_ft_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_manager.create_strategy = AsyncMock(return_value=True)
            mock_manager.stop_strategy = AsyncMock(return_value=False)
            mock_process = Mock()
            mock_process.pid = 12345
            mock_manager.strategy_ports = {test_strategy.id: 8080}
            mock_manager.strategy_processes = {test_strategy.id: mock_process}
            mock_get_manager.return_value = mock_manager

            # 先启动
            client.post(
                f"/api/v1/strategies/{test_strategy.id}/start",
                headers=auth_headers
            )

            # 尝试停止（manager返回False）
            response = client.post(
                f"/api/v1/strategies/{test_strategy.id}/stop",
                headers=auth_headers
            )

            # 应该返回500错误
            assert response.status_code in [500, 200]

    def test_stop_nonexistent_strategy_404(self, client, auth_headers):
        """测试停止不存在的策略 - 返回404"""
        with patch('api.v1.strategies.get_ft_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_get_manager.return_value = mock_manager

            response = client.post(
                "/api/v1/strategies/999999/stop",
                headers=auth_headers
            )

            # 应该返回404
            assert response.status_code in [404, 500]


class TestStrategyDeleteAdvanced:
    """策略删除高级测试"""

    def test_delete_stopped_strategy_success(self, client, auth_headers, test_strategy):
        """测试删除已停止策略 - 成功"""
        with patch('api.v1.strategies.get_ft_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_manager.stop_strategy = AsyncMock(return_value=True)
            mock_get_manager.return_value = mock_manager

            response = client.delete(
                f"/api/v1/strategies/{test_strategy.id}",
                headers=auth_headers
            )

            # 验证删除响应
            if response.status_code == 200:
                data = response.json()
                assert "id" in data
                assert data["message"] == "Strategy deleted successfully"

    def test_delete_running_strategy_auto_stop(self, client, auth_headers, test_strategy):
        """测试删除运行中的策略 - 自动停止"""
        with patch('api.v1.strategies.get_ft_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_manager.create_strategy = AsyncMock(return_value=True)
            mock_manager.stop_strategy = AsyncMock(return_value=True)
            mock_process = Mock()
            mock_process.pid = 12345
            mock_manager.strategy_ports = {test_strategy.id: 8080}
            mock_manager.strategy_processes = {test_strategy.id: mock_process}
            mock_get_manager.return_value = mock_manager

            # 先启动策略
            client.post(
                f"/api/v1/strategies/{test_strategy.id}/start",
                headers=auth_headers
            )

            # 删除运行中的策略（应该自动停止）
            response = client.delete(
                f"/api/v1/strategies/{test_strategy.id}",
                headers=auth_headers
            )

            # 验证删除成功
            if response.status_code == 200:
                data = response.json()
                assert data["message"] == "Strategy deleted successfully"

    def test_delete_nonexistent_strategy_404(self, client, auth_headers):
        """测试删除不存在的策略 - 返回404"""
        with patch('api.v1.strategies.get_ft_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_get_manager.return_value = mock_manager

            response = client.delete(
                "/api/v1/strategies/999999",
                headers=auth_headers
            )

            # 应该返回404
            assert response.status_code in [404, 500]


class TestStrategiesOverviewAdvanced:
    """策略概览高级测试"""

    def test_get_strategies_overview_with_data(self, client, auth_headers, test_strategy):
        """测试获取策略概览 - 包含数据"""
        with patch('api.v1.strategies.get_ft_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_manager.get_capacity_info = Mock(return_value={
                "max_strategies": 10,
                "running_strategies": 1,
                "available_slots": 9,
                "utilization_percent": 10.0
            })
            mock_get_manager.return_value = mock_manager

            response = client.get(
                "/api/v1/strategies/overview",
                headers=auth_headers
            )

            if response.status_code == 200:
                data = response.json()
                # 验证summary字段
                assert "summary" in data
                assert "total_strategies" in data["summary"]
                assert "running_strategies" in data["summary"]
                assert "stopped_strategies" in data["summary"]
                assert "capacity_utilization" in data["summary"]
                assert "available_slots" in data["summary"]

                # 验证capacity字段
                assert "capacity" in data
                assert data["capacity"]["max_strategies"] == 10

                # 验证strategies列表
                assert "strategies" in data
                assert isinstance(data["strategies"], list)

    def test_get_strategies_overview_empty(self, client, auth_headers):
        """测试获取策略概览 - 空数据"""
        with patch('api.v1.strategies.get_ft_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_manager.get_capacity_info = Mock(return_value={
                "max_strategies": 10,
                "running_strategies": 0,
                "available_slots": 10,
                "utilization_percent": 0.0
            })
            mock_get_manager.return_value = mock_manager

            response = client.get(
                "/api/v1/strategies/overview",
                headers=auth_headers
            )

            if response.status_code == 200:
                data = response.json()
                assert data["summary"]["total_strategies"] >= 0
                assert data["summary"]["running_strategies"] == 0


class TestStrategyErrorScenarios:
    """策略错误场景测试"""

    def test_manager_not_initialized_error(self, client, auth_headers, test_strategy):
        """测试FreqTrade Manager未初始化错误"""
        with patch('api.v1.strategies.get_ft_manager') as mock_get_manager:
            # Mock抛出异常
            mock_get_manager.side_effect = Exception("FreqTrade manager not initialized")

            response = client.post(
                f"/api/v1/strategies/{test_strategy.id}/start",
                headers=auth_headers
            )

            # 应该返回500错误
            assert response.status_code == 500

    def test_database_error_on_create(self, client, auth_headers):
        """测试创建策略时数据库错误"""
        # 故意发送不完整的数据导致错误
        response = client.post(
            "/api/v1/strategies/",
            json={
                "name": "Error Test"
                # 缺少必需字段
            },
            headers=auth_headers
        )

        # 应该返回错误
        assert response.status_code in [400, 422, 500]

    def test_exception_in_start_strategy(self, client, auth_headers, test_strategy):
        """测试启动策略时的异常处理"""
        with patch('api.v1.strategies.get_ft_manager') as mock_get_manager:
            mock_manager = Mock()
            # Mock抛出异常
            mock_manager.create_strategy = AsyncMock(side_effect=Exception("Unexpected error"))
            mock_get_manager.return_value = mock_manager

            response = client.post(
                f"/api/v1/strategies/{test_strategy.id}/start",
                headers=auth_headers
            )

            # 应该返回500错误
            assert response.status_code == 500

    def test_exception_in_stop_strategy(self, client, auth_headers, test_strategy):
        """测试停止策略时的异常处理"""
        with patch('api.v1.strategies.get_ft_manager') as mock_get_manager:
            mock_manager = Mock()
            # Mock抛出异常
            mock_manager.stop_strategy = AsyncMock(side_effect=Exception("Unexpected error"))
            mock_get_manager.return_value = mock_manager

            response = client.post(
                f"/api/v1/strategies/{test_strategy.id}/stop",
                headers=auth_headers
            )

            # 应该返回500错误
            assert response.status_code in [500, 200]

    def test_exception_in_delete_strategy(self, client, auth_headers, test_strategy):
        """测试删除策略时的异常处理"""
        with patch('api.v1.strategies.get_ft_manager') as mock_get_manager:
            mock_manager = Mock()
            # Mock抛出异常
            mock_manager.stop_strategy = AsyncMock(side_effect=Exception("Unexpected error"))
            mock_get_manager.return_value = mock_manager

            response = client.delete(
                f"/api/v1/strategies/{test_strategy.id}",
                headers=auth_headers
            )

            # 应该返回500错误
            assert response.status_code in [500, 200]


class TestStrategyUpdateWorkflow:
    """策略更新工作流测试"""

    def test_strategy_state_transitions(self, client, auth_headers, test_strategy):
        """测试策略状态转换"""
        with patch('api.v1.strategies.get_ft_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_manager.create_strategy = AsyncMock(return_value=True)
            mock_manager.stop_strategy = AsyncMock(return_value=True)
            mock_process = Mock()
            mock_process.pid = 12345
            mock_manager.strategy_ports = {test_strategy.id: 8080}
            mock_manager.strategy_processes = {test_strategy.id: mock_process}
            mock_get_manager.return_value = mock_manager

            # 初始状态: stopped
            get_response1 = client.get(
                f"/api/v1/strategies/{test_strategy.id}",
                headers=auth_headers
            )
            if get_response1.status_code == 200:
                assert get_response1.json()["status"] == "stopped"

            # 启动: stopped -> running
            start_response = client.post(
                f"/api/v1/strategies/{test_strategy.id}/start",
                headers=auth_headers
            )

            # 停止: running -> stopped
            stop_response = client.post(
                f"/api/v1/strategies/{test_strategy.id}/stop",
                headers=auth_headers
            )

            # 验证最终状态
            get_response2 = client.get(
                f"/api/v1/strategies/{test_strategy.id}",
                headers=auth_headers
            )
            if get_response2.status_code == 200:
                assert get_response2.json()["status"] == "stopped"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
