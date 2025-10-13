"""
Monitoring API endpoints
监控数据查询
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from services.monitoring_service import MonitoringService
from api.v1.system import get_monitoring_service

router = APIRouter()


@router.get("/system")
async def get_system_metrics(
    monitoring: MonitoringService = Depends(get_monitoring_service)
):
    """获取系统监控指标"""
    try:
        metrics = monitoring.get_system_metrics()
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/strategies")
async def get_strategy_metrics(
    monitoring: MonitoringService = Depends(get_monitoring_service)
):
    """获取策略监控指标"""
    try:
        metrics = monitoring.get_strategy_metrics()
        return {
            "total_strategies": len(metrics),
            "strategies": metrics
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/capacity/trend")
async def get_capacity_trend(
    hours: int = 24,
    monitoring: MonitoringService = Depends(get_monitoring_service)
):
    """获取容量趋势数据"""
    try:
        trend_data = monitoring.get_capacity_trend(hours=hours)
        return {
            "period_hours": hours,
            "data_points": trend_data,
            "total_points": len(trend_data)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health-summary")
async def get_health_summary(
    monitoring: MonitoringService = Depends(get_monitoring_service)
):
    """获取健康状态摘要"""
    try:
        health = monitoring.get_health_status()
        system_metrics = monitoring.get_system_metrics()
        strategy_metrics = monitoring.get_strategy_metrics()

        return {
            "health": health,
            "system": {
                "cpu_percent": system_metrics.get("cpu", {}).get("percent", 0),
                "memory_percent": system_metrics.get("memory", {}).get("percent", 0),
                "disk_percent": system_metrics.get("disk", {}).get("percent", 0)
            },
            "strategies": {
                "total": len(strategy_metrics),
                "healthy": len([s for s in strategy_metrics.values() if s.get("is_alive")])
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
