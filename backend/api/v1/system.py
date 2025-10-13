# backend/api/v1/system.py
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from core.freqtrade_manager import FreqTradeGatewayManager
from core.api_gateway import FreqTradeAPIGateway
from core.config_manager import config_manager
from services.monitoring_service import MonitoringService

router = APIRouter()

# Module-level service instances (injected during startup)
_ft_manager: FreqTradeGatewayManager = None
_api_gateway: FreqTradeAPIGateway = None
_monitoring_service: MonitoringService = None


# Dependency provider functions
def get_ft_manager() -> FreqTradeGatewayManager:
    """Get FreqTrade manager dependency"""
    if _ft_manager is None:
        raise HTTPException(status_code=503, detail="FreqTrade manager not initialized")
    return _ft_manager


def get_api_gateway() -> FreqTradeAPIGateway:
    """Get API gateway dependency"""
    if _api_gateway is None:
        raise HTTPException(status_code=503, detail="API gateway not initialized")
    return _api_gateway


def get_monitoring_service() -> MonitoringService:
    """Get monitoring service dependency"""
    if _monitoring_service is None:
        raise HTTPException(status_code=503, detail="Monitoring service not initialized")
    return _monitoring_service


@router.get("/capacity")
async def get_system_capacity(
    ft_manager: FreqTradeGatewayManager = Depends(get_ft_manager)
):
    """获取系统容量信息

    Returns:
        {
            "max_strategies": 999,
            "running_strategies": 5,
            "available_slots": 994,
            "utilization_percent": 0.50,
            "port_range": "8081-9080",
            "can_start_more": true,
            "architecture": "multi_instance_reverse_proxy"
        }
    """
    try:
        capacity_info = ft_manager.get_capacity_info()
        return capacity_info
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get capacity info: {str(e)}"
        )


@router.get("/port-pool")
async def get_port_pool_status(
    ft_manager: FreqTradeGatewayManager = Depends(get_ft_manager)
):
    """获取端口池状态

    Returns:
        {
            "total_ports": 999,
            "available_ports": 994,
            "allocated_ports": 5,
            "running_strategies": 5,
            "port_range": "8081-9080",
            "max_concurrent": 999
        }
    """
    try:
        port_pool_status = ft_manager.get_port_pool_status()
        return port_pool_status
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get port pool status: {str(e)}"
        )


@router.get("/capacity/detailed")
async def get_detailed_capacity(
    ft_manager: FreqTradeGatewayManager = Depends(get_ft_manager),
    api_gateway: FreqTradeAPIGateway = Depends(get_api_gateway)
):
    """获取详细的系统容量和健康信息

    Returns:
        {
            "capacity": {...},
            "port_pool": {...},
            "gateway_health": {...},
            "recommendations": [...]
        }
    """
    try:
        # 获取容量信息
        capacity_info = ft_manager.get_capacity_info()

        # 获取端口池状态
        port_pool_status = ft_manager.get_port_pool_status()

        # 获取Gateway健康状态
        gateway_health = await api_gateway._gateway_health_check()

        # 生成容量建议
        recommendations = _generate_capacity_recommendations(capacity_info)

        return {
            "capacity": capacity_info,
            "port_pool": port_pool_status,
            "gateway_health": gateway_health,
            "recommendations": recommendations,
            "timestamp": capacity_info.get("timestamp", None)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get detailed capacity: {str(e)}"
        )


@router.get("/capacity/utilization-trend")
async def get_capacity_utilization_trend(
    hours: int = 24,
    ft_manager: FreqTradeGatewayManager = Depends(get_ft_manager)
):
    """获取容量使用率趋势（过去N小时）

    Args:
        hours: 查询的小时数，默认24小时

    Returns:
        {
            "period_hours": 24,
            "current_utilization": 0.50,
            "peak_utilization": 2.5,
            "average_utilization": 1.2,
            "trend": "stable|increasing|decreasing",
            "data_points": [...]
        }
    """
    try:
        # 从Redis或数据库获取历史容量数据
        trend_data = await _get_capacity_trend_from_cache(hours)

        current_capacity = ft_manager.get_capacity_info()

        return {
            "period_hours": hours,
            "current_utilization": current_capacity["utilization_percent"],
            "peak_utilization": trend_data.get("peak", 0),
            "average_utilization": trend_data.get("average", 0),
            "trend": trend_data.get("trend", "stable"),
            "data_points": trend_data.get("data_points", [])
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get utilization trend: {str(e)}"
        )


@router.post("/capacity/alert-threshold")
async def set_capacity_alert_threshold(
    threshold_percent: float,
    ft_manager: FreqTradeGatewayManager = Depends(get_ft_manager)
):
    """设置容量告警阈值

    Args:
        threshold_percent: 告警阈值百分比 (0-100)

    Returns:
        {"status": "success", "threshold": 80.0}
    """
    try:
        if threshold_percent < 0 or threshold_percent > 100:
            raise HTTPException(
                status_code=400,
                detail="Threshold must be between 0 and 100"
            )

        # 保存阈值到配置或数据库
        await _save_capacity_alert_threshold(threshold_percent)

        return {
            "status": "success",
            "threshold": threshold_percent,
            "message": f"Capacity alert threshold set to {threshold_percent}%"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to set alert threshold: {str(e)}"
        )


@router.get("/config/{config_name}")
async def get_config(config_name: str):
    """获取配置信息

    Args:
        config_name: 配置名称 (monitoring, notifications, proxy)

    Returns:
        配置信息字典
    """
    try:
        if config_name == "monitoring":
            return config_manager.get_monitoring_config()
        elif config_name == "notifications":
            return config_manager.get_notification_config()
        elif config_name == "proxy":
            return config_manager.get_proxy_config()
        else:
            raise HTTPException(status_code=404, detail="Config not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get config: {str(e)}"
        )


@router.post("/config/reload")
async def reload_config(
    config_name: Optional[str] = None,
    monitoring_service: MonitoringService = Depends(get_monitoring_service)
):
    """重新加载配置

    Args:
        config_name: 配置名称，不指定则重载所有配置

    Returns:
        {"status": "success", "message": "Config reloaded"}
    """
    try:
        config_manager.reload_config(config_name)

        # 通知相关服务重新加载配置
        if config_name in ["system", None]:
            await monitoring_service.reload_config()

        return {
            "status": "success",
            "message": f"Config {'reloaded' if config_name else 'all configs reloaded'}",
            "config_name": config_name
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reload config: {str(e)}"
        )


@router.get("/health")
async def system_health_check(
    monitoring: MonitoringService = Depends(get_monitoring_service)
):
    """系统健康检查

    Returns:
        {
            "status": "healthy",
            "architecture": "multi_instance_reverse_proxy",
            "services": {...},
            "metrics": {...}
        }
    """
    try:
        # 获取监控服务的健康状态
        health_status = monitoring.get_health_status()

        # 获取系统指标
        system_metrics = monitoring.get_system_metrics()

        return {
            **health_status,
            "metrics": {
                "cpu_percent": system_metrics.get("cpu", {}).get("percent", 0),
                "memory_percent": system_metrics.get("memory", {}).get("percent", 0),
                "disk_percent": system_metrics.get("disk", {}).get("percent", 0)
            }
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "architecture": "multi_instance_reverse_proxy"
        }


@router.get("/statistics")
async def get_system_statistics(
    ft_manager: FreqTradeGatewayManager = Depends(get_ft_manager),
    api_gateway: FreqTradeAPIGateway = Depends(get_api_gateway)
):
    """获取系统统计信息

    Returns:
        {
            "total_strategies": 5,
            "healthy_strategies": 4,
            "capacity_utilization": 0.50,
            "uptime_seconds": 86400,
            "architecture_mode": "multi_instance_reverse_proxy"
        }
    """
    try:
        # 获取容量信息
        capacity_info = ft_manager.get_capacity_info()

        # 获取Gateway统计
        gateway_health = await api_gateway._gateway_health_check()

        # 获取系统运行时间
        import psutil
        import time
        uptime_seconds = time.time() - psutil.boot_time()

        return {
            "total_strategies": capacity_info["running_strategies"],
            "max_strategies": capacity_info["max_strategies"],
            "healthy_strategies": gateway_health.get("healthy_strategies", 0),
            "capacity_utilization": capacity_info["utilization_percent"],
            "port_range": capacity_info["port_range"],
            "uptime_seconds": uptime_seconds,
            "architecture_mode": "multi_instance_reverse_proxy",
            "can_start_more": capacity_info["can_start_more"]
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get statistics: {str(e)}"
        )


# Helper functions

def _generate_capacity_recommendations(capacity_info: dict) -> list:
    """生成容量建议"""
    recommendations = []
    utilization = capacity_info["utilization_percent"]
    running = capacity_info["running_strategies"]
    max_strategies = capacity_info["max_strategies"]

    if utilization > 90:
        recommendations.append({
            "level": "critical",
            "message": f"系统容量使用率超过90% ({utilization:.2f}%)，建议立即停止部分策略或升级硬件资源",
            "action": "stop_strategies_or_upgrade"
        })
    elif utilization > 80:
        recommendations.append({
            "level": "warning",
            "message": f"系统容量使用率超过80% ({utilization:.2f}%)，建议规划资源升级",
            "action": "plan_upgrade"
        })
    elif utilization > 50:
        recommendations.append({
            "level": "info",
            "message": f"系统容量使用正常 ({utilization:.2f}%)，可继续添加策略",
            "action": "normal_operation"
        })
    else:
        recommendations.append({
            "level": "info",
            "message": f"系统容量充足 ({utilization:.2f}%)，大量可用槽位",
            "action": "normal_operation"
        })

    # 根据当前使用量推荐硬件配置
    if running <= 5:
        recommendations.append({
            "level": "info",
            "message": "当前配置建议: 4核CPU + 8GB内存 (个人使用级别)",
            "action": "hardware_recommendation"
        })
    elif running <= 20:
        recommendations.append({
            "level": "info",
            "message": "当前配置建议: 8核CPU + 16GB内存 (小团队级别)",
            "action": "hardware_recommendation"
        })
    elif running <= 100:
        recommendations.append({
            "level": "info",
            "message": "当前配置建议: 16核CPU + 64GB内存 (专业团队级别)",
            "action": "hardware_recommendation"
        })
    else:
        recommendations.append({
            "level": "info",
            "message": "当前配置建议: 32核CPU + 128GB+内存 (机构级别)",
            "action": "hardware_recommendation"
        })

    return recommendations


async def _get_capacity_trend_from_cache(hours: int) -> dict:
    """从缓存获取容量趋势数据"""
    # TODO: 实现从Redis或数据库获取历史数据
    # 这里返回模拟数据
    return {
        "peak": 5.0,
        "average": 2.5,
        "trend": "stable",
        "data_points": []
    }


async def _save_capacity_alert_threshold(threshold: float):
    """保存容量告警阈值"""
    # TODO: 保存到Redis或数据库
    pass
