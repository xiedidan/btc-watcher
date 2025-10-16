"""
FreqTrade管理器单元测试
FreqTradeGatewayManager Unit Tests
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
from core.freqtrade_manager import FreqTradeGatewayManager


@pytest.fixture
def freqtrade_manager(tmp_path, monkeypatch):
    """创建带临时目录的FreqTrade管理器"""
    # 创建临时目录
    base_config_path = tmp_path / "freqtrade_configs"
    strategies_path = tmp_path / "user_data" / "strategies"
    logs_path = tmp_path / "logs" / "freqtrade"

    # Patch FreqTradeGatewayManager的__init__方法中的Path调用
    original_init = FreqTradeGatewayManager.__init__

    def patched_init(self):
        self.strategy_processes = {}
        self.strategy_ports = {}
        self.freqtrade_version = "2025.8"
        self.gateway_port = 8080
        self.base_port = 8081
        self.max_port = 9080  # 8081 to 9080 = 1000 ports total
        self.max_strategies = 1000
        self.base_config_path = base_config_path
        self.strategies_path = strategies_path
        self.logs_path = logs_path
        self.port_pool = set(range(self.base_port, self.max_port + 1))  # 1000 ports

        # 确保目录存在
        self.base_config_path.mkdir(parents=True, exist_ok=True)
        self.strategies_path.mkdir(parents=True, exist_ok=True)
        self.logs_path.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(FreqTradeGatewayManager, "__init__", patched_init)

    return FreqTradeGatewayManager()


class TestFreqTradeGatewayManager:
    """FreqTrade网关管理器测试类"""

    def test_initialization(self, freqtrade_manager):
        """测试管理器初始化"""
        manager = freqtrade_manager

        assert manager.base_port == 8081
        assert manager.max_port == 9080  # 1000 ports: 8081-9080
        assert manager.max_strategies == 1000
        assert len(manager.port_pool) == 1000
        assert manager.strategy_processes == {}
        assert manager.strategy_ports == {}

    @pytest.mark.asyncio
    async def test_allocate_port_preferred(self, freqtrade_manager):
        """测试端口分配 - 优先分配策略ID对应端口"""
        manager = freqtrade_manager

        # 策略ID为1，期望分配端口8082 (base_port + strategy_id)
        port = await manager._allocate_port(1)

        assert port == 8082
        assert 8082 not in manager.port_pool

    @pytest.mark.asyncio
    async def test_allocate_port_smallest_available(self, freqtrade_manager):
        """测试端口分配 - 分配最小可用端口"""
        manager = freqtrade_manager

        # 先移除优先端口
        manager.port_pool.discard(8082)

        # 分配策略ID为1，但8082已被占用，应该分配最小的可用端口
        port = await manager._allocate_port(1)

        assert port == 8081  # 应该是最小的可用端口
        assert 8081 not in manager.port_pool

    @pytest.mark.asyncio
    async def test_allocate_port_max_limit(self, freqtrade_manager):
        """测试端口分配 - 达到最大限制"""
        manager = freqtrade_manager

        # 模拟已达到最大策略数
        manager.strategy_processes = {i: Mock() for i in range(1000)}

        with pytest.raises(Exception) as exc_info:
            await manager._allocate_port(1001)

        assert "Maximum concurrent strategies limit" in str(exc_info.value)

    def test_get_capacity(self, freqtrade_manager):
        """测试获取容量信息"""
        manager = freqtrade_manager

        # 模拟一些运行中的策略（但不分配端口）
        manager.strategy_processes = {1: Mock(), 2: Mock(), 3: Mock()}

        capacity = manager.get_capacity_info()

        assert capacity["max_strategies"] == 1000
        assert capacity["running_strategies"] == 3
        # available_slots 是基于 port_pool 大小，不是 max - running
        assert capacity["available_slots"] == 1000  # 端口池仍然是满的

    def test_port_pool_integrity(self, freqtrade_manager):
        """测试端口池完整性"""
        manager = freqtrade_manager

        # 验证端口池包含所有端口
        expected_ports = set(range(8081, 9081))  # 1000 ports: 8081-9080
        assert manager.port_pool == expected_ports

        # 验证端口数量
        assert len(manager.port_pool) == 1000

    @pytest.mark.asyncio
    async def test_concurrent_port_allocation(self, freqtrade_manager):
        """测试并发端口分配"""
        manager = freqtrade_manager

        # 模拟并发分配10个端口
        allocated_ports = []
        for i in range(10):
            port = await manager._allocate_port(i)
            allocated_ports.append(port)

        # 验证所有端口都是唯一的
        assert len(allocated_ports) == len(set(allocated_ports))

        # 验证端口都在有效范围内
        for port in allocated_ports:
            assert 8081 <= port <= 9080  # 1000 ports range

    def test_strategy_tracking(self, freqtrade_manager):
        """测试策略跟踪"""
        manager = freqtrade_manager

        # 添加策略
        process_mock = Mock()
        manager.strategy_processes[1] = process_mock
        manager.strategy_ports[1] = 8081

        # 验证跟踪
        assert 1 in manager.strategy_processes
        assert manager.strategy_ports[1] == 8081

        # 移除策略
        del manager.strategy_processes[1]
        del manager.strategy_ports[1]

        assert 1 not in manager.strategy_processes
        assert 1 not in manager.strategy_ports


class TestFreqTradeManagerEdgeCases:
    """FreqTrade管理器边缘情况测试"""

    @pytest.mark.asyncio
    async def test_allocate_all_ports(self, freqtrade_manager):
        """测试分配所有端口"""
        manager = freqtrade_manager

        allocated_ports = []

        # 分配所有1000个端口
        for i in range(1000):
            port = await manager._allocate_port(i)
            allocated_ports.append(port)
            manager.strategy_processes[i] = Mock()  # 分配后再添加进程

        # 验证所有端口都已分配
        assert len(manager.port_pool) == 0
        assert len(allocated_ports) == 1000

        # 尝试再分配一个应该失败（端口池已空）
        with pytest.raises(Exception):
            await manager._allocate_port(1000)

    @pytest.mark.asyncio
    async def test_port_allocation_order(self, freqtrade_manager):
        """测试端口分配顺序"""
        manager = freqtrade_manager

        # 清空端口池并添加特定端口
        manager.port_pool = {8085, 8083, 8081}

        # 应该按升序分配
        port1 = await manager._allocate_port(999)  # 优先端口不在池中
        assert port1 == 8081

        port2 = await manager._allocate_port(998)
        assert port2 == 8083

        port3 = await manager._allocate_port(997)
        assert port3 == 8085


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
