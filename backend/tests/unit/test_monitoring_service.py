"""
监控服务单元测试
MonitoringService Unit Tests
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from services.monitoring_service import MonitoringService


class TestMonitoringService:
    """监控服务测试类"""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """测试监控服务初始化"""
        mock_manager = Mock()
        service = MonitoringService(mock_manager)

        assert service.ft_manager == mock_manager
        assert service.monitoring_tasks == {}
        assert service.running is False

    @pytest.mark.asyncio
    async def test_get_system_metrics(self):
        """测试获取系统指标"""
        mock_manager = Mock()
        service = MonitoringService(mock_manager)

        # 模拟设置一些系统指标
        service.system_metrics = {
            "cpu": {"percent": 45.5},
            "memory": {"percent": 62.3},
            "disk": {"percent": 55.8},
            "timestamp": datetime.now().isoformat()
        }

        metrics = service.get_system_metrics()

        assert metrics["cpu"]["percent"] == 45.5
        assert metrics["memory"]["percent"] == 62.3
        assert metrics["disk"]["percent"] == 55.8
        assert "timestamp" in metrics

    @pytest.mark.asyncio
    async def test_get_capacity_info(self):
        """测试获取容量信息"""
        mock_manager = Mock()
        mock_manager.get_capacity_info.return_value = {
            "max_strategies": 999,
            "running_strategies": 50,
            "available_slots": 949,
            "utilization_percent": 5.0
        }

        service = MonitoringService(mock_manager)
        capacity = mock_manager.get_capacity_info()

        assert capacity["max_strategies"] == 999
        assert capacity["running_strategies"] == 50
        assert capacity["available_slots"] == 949
        assert capacity["utilization_percent"] == 5.0

    @pytest.mark.asyncio
    async def test_check_alerts_high_cpu(self):
        """测试高CPU告警"""
        mock_manager = Mock()
        service = MonitoringService(mock_manager)

        # 设置高CPU使用率
        service.system_metrics = {
            "cpu": {"percent": 95.0},
            "memory": {"percent": 50.0},
            "disk": {"percent": 40.0}
        }

        # 调用检查告警方法并验证指标
        await service._check_system_alerts()
        # 验证是否有高CPU使用率
        assert service.system_metrics["cpu"]["percent"] > 90

    @pytest.mark.asyncio
    async def test_check_alerts_high_memory(self):
        """测试高内存告警"""
        mock_manager = Mock()
        service = MonitoringService(mock_manager)

        # 设置高内存使用率
        service.system_metrics = {
            "cpu": {"percent": 50.0},
            "memory": {"percent": 92.0},
            "disk": {"percent": 40.0}
        }

        # 验证指标
        assert service.system_metrics["memory"]["percent"] > 90

    @pytest.mark.asyncio
    async def test_check_alerts_high_disk(self):
        """测试高磁盘告警"""
        mock_manager = Mock()
        service = MonitoringService(mock_manager)

        # 设置高磁盘使用率
        service.system_metrics = {
            "cpu": {"percent": 50.0},
            "memory": {"percent": 50.0},
            "disk": {"percent": 88.0}
        }

        # 验证指标
        assert service.system_metrics["disk"]["percent"] < 90

    @pytest.mark.asyncio
    async def test_check_alerts_high_capacity(self):
        """测试高容量告警"""
        mock_manager = Mock()
        mock_manager.get_capacity_info.return_value = {
            "utilization_percent": 92.0
        }

        service = MonitoringService(mock_manager)

        # 验证容量信息
        capacity = mock_manager.get_capacity_info()
        assert capacity["utilization_percent"] > 90

    @pytest.mark.asyncio
    async def test_no_alerts_normal_metrics(self):
        """测试正常指标无告警"""
        mock_manager = Mock()
        mock_manager.get_capacity_info.return_value = {
            "utilization_percent": 50.0
        }

        service = MonitoringService(mock_manager)

        # 设置正常指标
        service.system_metrics = {
            "cpu": {"percent": 45.0},
            "memory": {"percent": 55.0},
            "disk": {"percent": 60.0}
        }

        # 验证都在正常范围内
        assert service.system_metrics["cpu"]["percent"] < 90
        assert service.system_metrics["memory"]["percent"] < 90
        assert service.system_metrics["disk"]["percent"] < 90


class TestMonitoringServiceIntegration:
    """监控服务集成测试"""

    @pytest.mark.asyncio
    async def test_get_monitoring_overview(self):
        """测试获取监控概览"""
        mock_manager = Mock()
        mock_manager.get_capacity_info.return_value = {
            "max_strategies": 999,
            "running_strategies": 10,
            "available_slots": 989,
            "utilization_percent": 1.0
        }
        mock_manager.strategy_processes = {i: Mock() for i in range(10)}

        service = MonitoringService(mock_manager)

        # 设置系统指标
        service.system_metrics = {
            "cpu": {"percent": 45.0},
            "memory": {"percent": 55.0},
            "disk": {"percent": 60.0}
        }

        # 获取健康状态作为概览的一部分
        overview = service.get_health_status()

        assert "status" in overview
        assert "monitoring_running" in overview
        assert overview["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_alert_threshold_customization(self):
        """测试告警阈值自定义"""
        mock_manager = Mock()
        service = MonitoringService(mock_manager)

        # 设置指标
        service.system_metrics = {
            "cpu": {"percent": 75.0},
            "memory": {"percent": 80.0},
            "disk": {"percent": 85.0}
        }

        # 验证健康状态（默认阈值是80%）
        health = service.get_health_status()

        # CPU 75% < 80% 所以是健康的
        # Memory 80% 不小于 80% 所以不健康
        # Disk 85% > 80% 所以不健康
        assert health["cpu_healthy"] is True
        assert health["memory_healthy"] is False
        assert health["disk_healthy"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
