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
        assert service.is_running is False

    @pytest.mark.asyncio
    async def test_get_system_metrics(self):
        """测试获取系统指标"""
        mock_manager = Mock()
        service = MonitoringService(mock_manager)

        with patch('psutil.cpu_percent', return_value=45.5):
            with patch('psutil.virtual_memory') as mock_memory:
                mock_memory.return_value.percent = 62.3
                with patch('psutil.disk_usage') as mock_disk:
                    mock_disk.return_value.percent = 55.8

                    metrics = await service._get_system_metrics()

                    assert metrics["cpu_usage"] == 45.5
                    assert metrics["memory_usage"] == 62.3
                    assert metrics["disk_usage"] == 55.8
                    assert "timestamp" in metrics

    @pytest.mark.asyncio
    async def test_get_capacity_info(self):
        """测试获取容量信息"""
        mock_manager = Mock()
        mock_manager.get_capacity.return_value = {
            "total_slots": 999,
            "used_slots": 50,
            "available_slots": 949,
            "utilization_percent": 5.0
        }

        service = MonitoringService(mock_manager)
        capacity = await service._get_capacity_info()

        assert capacity["total_slots"] == 999
        assert capacity["used_slots"] == 50
        assert capacity["available_slots"] == 949
        assert capacity["utilization_percent"] == 5.0

    @pytest.mark.asyncio
    async def test_check_alerts_high_cpu(self):
        """测试高CPU告警"""
        mock_manager = Mock()
        service = MonitoringService(mock_manager)

        metrics = {
            "cpu_usage": 95.0,
            "memory_usage": 50.0,
            "disk_usage": 40.0
        }

        alerts = await service._check_alerts(metrics)

        # 应该有CPU告警
        cpu_alerts = [a for a in alerts if "CPU" in a["message"]]
        assert len(cpu_alerts) > 0
        assert cpu_alerts[0]["level"] == "warning"

    @pytest.mark.asyncio
    async def test_check_alerts_high_memory(self):
        """测试高内存告警"""
        mock_manager = Mock()
        service = MonitoringService(mock_manager)

        metrics = {
            "cpu_usage": 50.0,
            "memory_usage": 92.0,
            "disk_usage": 40.0
        }

        alerts = await service._check_alerts(metrics)

        # 应该有内存告警
        memory_alerts = [a for a in alerts if "Memory" in a["message"]]
        assert len(memory_alerts) > 0
        assert memory_alerts[0]["level"] == "warning"

    @pytest.mark.asyncio
    async def test_check_alerts_high_disk(self):
        """测试高磁盘告警"""
        mock_manager = Mock()
        service = MonitoringService(mock_manager)

        metrics = {
            "cpu_usage": 50.0,
            "memory_usage": 50.0,
            "disk_usage": 88.0
        }

        alerts = await service._check_alerts(metrics)

        # 应该有磁盘告警
        disk_alerts = [a for a in alerts if "Disk" in a["message"]]
        assert len(disk_alerts) > 0
        assert disk_alerts[0]["level"] == "warning"

    @pytest.mark.asyncio
    async def test_check_alerts_high_capacity(self):
        """测试高容量告警"""
        mock_manager = Mock()
        mock_manager.get_capacity.return_value = {
            "utilization_percent": 92.0
        }

        service = MonitoringService(mock_manager)

        metrics = {
            "cpu_usage": 50.0,
            "memory_usage": 50.0,
            "disk_usage": 50.0
        }

        alerts = await service._check_alerts(metrics)

        # 应该有容量告警
        capacity_alerts = [a for a in alerts if "capacity" in a["message"].lower()]
        assert len(capacity_alerts) > 0

    @pytest.mark.asyncio
    async def test_no_alerts_normal_metrics(self):
        """测试正常指标无告警"""
        mock_manager = Mock()
        mock_manager.get_capacity.return_value = {
            "utilization_percent": 50.0
        }

        service = MonitoringService(mock_manager)

        metrics = {
            "cpu_usage": 45.0,
            "memory_usage": 55.0,
            "disk_usage": 60.0
        }

        alerts = await service._check_alerts(metrics)

        # 正常情况下不应该有告警
        assert len(alerts) == 0


class TestMonitoringServiceIntegration:
    """监控服务集成测试"""

    @pytest.mark.asyncio
    async def test_get_monitoring_overview(self):
        """测试获取监控概览"""
        mock_manager = Mock()
        mock_manager.get_capacity.return_value = {
            "total_slots": 999,
            "used_slots": 10,
            "available_slots": 989,
            "utilization_percent": 1.0
        }
        mock_manager.strategy_processes = {i: Mock() for i in range(10)}

        service = MonitoringService(mock_manager)

        with patch('psutil.cpu_percent', return_value=45.0):
            with patch('psutil.virtual_memory') as mock_memory:
                mock_memory.return_value.percent = 55.0
                with patch('psutil.disk_usage') as mock_disk:
                    mock_disk.return_value.percent = 60.0

                    overview = await service.get_monitoring_overview()

                    assert "system_metrics" in overview
                    assert "capacity" in overview
                    assert "active_strategies" in overview
                    assert overview["active_strategies"] == 10

    @pytest.mark.asyncio
    async def test_alert_threshold_customization(self):
        """测试告警阈值自定义"""
        mock_manager = Mock()
        service = MonitoringService(mock_manager)

        # 自定义阈值
        service.cpu_threshold = 70.0
        service.memory_threshold = 85.0
        service.disk_threshold = 90.0

        metrics = {
            "cpu_usage": 75.0,  # 超过70
            "memory_usage": 80.0,  # 未超过85
            "disk_usage": 85.0  # 未超过90
        }

        alerts = await service._check_alerts(metrics)

        # 只有CPU应该告警
        assert len(alerts) == 1
        assert "CPU" in alerts[0]["message"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
