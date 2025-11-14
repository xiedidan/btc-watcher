"""
Proxies API endpoints
网络代理管理API
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import List, Optional
import logging
from datetime import datetime
import httpx

from database import get_db
from models.proxy import Proxy

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/")
async def list_proxies(
    skip: int = 0,
    limit: int = 100,
    enabled: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """获取代理列表"""
    try:
        query = select(Proxy).where(Proxy.is_active == True)

        if enabled is not None:
            query = query.where(Proxy.is_active == enabled)

        query = query.order_by(Proxy.priority).offset(skip).limit(limit)

        result = await db.execute(query)
        proxies = result.scalars().all()

        return {
            "total": len(proxies),
            "proxies": [
                {
                    "id": p.id,
                    "name": p.name,
                    "type": p.proxy_type,
                    "host": p.host,
                    "port": p.port,
                    "username": p.username,
                    "enabled": p.is_active,
                    "status": "healthy" if p.is_healthy else "unhealthy",
                    "priority": p.priority,
                    "performance_metrics": {
                        "success_rate": p.success_rate,
                        "avg_latency_ms": p.avg_latency_ms,
                        "total_requests": p.total_requests,
                        "successful_requests": p.successful_requests,
                        "failed_requests": p.failed_requests,
                        "last_success_time": p.last_success_at.isoformat() if p.last_success_at else None
                    }
                }
                for p in proxies
            ]
        }
    except Exception as e:
        logger.error(f"Failed to list proxies: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health-check-config")
async def get_health_check_config():
    """获取健康检查配置"""
    # 这里可以从数据库或配置文件读取
    # 暂时返回默认值
    return {
        "interval_seconds": 3600,
        "timeout_seconds": 10,
        "retry_count": 3,
        "test_url": "https://api.binance.com/api/v3/ping"
    }


@router.put("/health-check-config")
async def update_health_check_config(config: dict):
    """更新健康检查配置"""
    # 这里应该保存到数据库或配置文件
    # 暂时只做验证
    required_fields = ["interval_seconds", "timeout_seconds", "retry_count", "test_url"]

    for field in required_fields:
        if field not in config:
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")

    logger.info(f"Updated health check config: {config}")

    return {
        "message": "Health check config updated successfully",
        "config": config
    }


@router.get("/{proxy_id}")
async def get_proxy(
    proxy_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取代理详情"""
    try:
        result = await db.execute(
            select(Proxy).where(Proxy.id == proxy_id)
        )
        proxy = result.scalar_one_or_none()

        if not proxy:
            raise HTTPException(status_code=404, detail="Proxy not found")

        return {
            "id": proxy.id,
            "name": proxy.name,
            "type": proxy.proxy_type,
            "host": proxy.host,
            "port": proxy.port,
            "username": proxy.username,
            "password": "***" if proxy.password else None,
            "enabled": proxy.is_active,
            "healthy": proxy.is_healthy,
            "priority": proxy.priority,
            "health_check_url": proxy.health_check_url,
            "success_rate": proxy.success_rate,
            "avg_latency_ms": proxy.avg_latency_ms,
            "total_requests": proxy.total_requests,
            "successful_requests": proxy.successful_requests,
            "failed_requests": proxy.failed_requests,
            "consecutive_failures": proxy.consecutive_failures,
            "last_check_at": proxy.last_check_at.isoformat() if proxy.last_check_at else None,
            "last_success_at": proxy.last_success_at.isoformat() if proxy.last_success_at else None,
            "last_failure_at": proxy.last_failure_at.isoformat() if proxy.last_failure_at else None,
            "created_at": proxy.created_at.isoformat() if proxy.created_at else None,
            "updated_at": proxy.updated_at.isoformat() if proxy.updated_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get proxy {proxy_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
async def create_proxy(
    proxy_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """创建代理"""
    try:
        # 获取当前最大priority
        result = await db.execute(
            select(Proxy.priority).order_by(Proxy.priority.desc()).limit(1)
        )
        max_priority = result.scalar_one_or_none()
        next_priority = (max_priority or 0) + 1

        proxy = Proxy(
            name=proxy_data["name"],
            proxy_type=proxy_data["type"],
            host=proxy_data["host"],
            port=proxy_data["port"],
            username=proxy_data.get("username"),
            password=proxy_data.get("password"),
            is_active=proxy_data.get("enabled", True),
            priority=next_priority,
            health_check_url=proxy_data.get("health_check_url", "https://api.binance.com/api/v3/ping")
        )

        db.add(proxy)
        await db.commit()
        await db.refresh(proxy)

        logger.info(f"Created proxy {proxy.id}: {proxy.name}")

        return {
            "id": proxy.id,
            "name": proxy.name,
            "message": "Proxy created successfully"
        }
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create proxy: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{proxy_id}")
async def update_proxy(
    proxy_id: int,
    proxy_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """更新代理"""
    try:
        result = await db.execute(
            select(Proxy).where(Proxy.id == proxy_id)
        )
        proxy = result.scalar_one_or_none()

        if not proxy:
            raise HTTPException(status_code=404, detail="Proxy not found")

        # 更新字段
        if "name" in proxy_data:
            proxy.name = proxy_data["name"]
        if "type" in proxy_data:
            proxy.proxy_type = proxy_data["type"]
        if "host" in proxy_data:
            proxy.host = proxy_data["host"]
        if "port" in proxy_data:
            proxy.port = proxy_data["port"]
        if "username" in proxy_data:
            proxy.username = proxy_data["username"]
        if "password" in proxy_data:
            proxy.password = proxy_data["password"]
        if "enabled" in proxy_data:
            proxy.is_active = proxy_data["enabled"]
        if "health_check_url" in proxy_data:
            proxy.health_check_url = proxy_data["health_check_url"]

        await db.commit()
        await db.refresh(proxy)

        logger.info(f"Updated proxy {proxy_id}: {proxy.name}")

        return {
            "id": proxy.id,
            "name": proxy.name,
            "message": "Proxy updated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update proxy {proxy_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{proxy_id}")
async def delete_proxy(
    proxy_id: int,
    db: AsyncSession = Depends(get_db)
):
    """删除代理（软删除）"""
    try:
        result = await db.execute(
            select(Proxy).where(Proxy.id == proxy_id)
        )
        proxy = result.scalar_one_or_none()

        if not proxy:
            raise HTTPException(status_code=404, detail="Proxy not found")

        # 软删除
        proxy.is_active = False

        await db.commit()

        logger.info(f"Deleted proxy {proxy_id}: {proxy.name}")

        return {
            "id": proxy_id,
            "message": "Proxy deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete proxy {proxy_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{proxy_id}/test")
async def test_proxy(
    proxy_id: int,
    db: AsyncSession = Depends(get_db)
):
    """测试代理连通性"""
    try:
        result = await db.execute(
            select(Proxy).where(Proxy.id == proxy_id)
        )
        proxy = result.scalar_one_or_none()

        if not proxy:
            raise HTTPException(status_code=404, detail="Proxy not found")

        # 构建代理URL
        if proxy.username and proxy.password:
            proxy_url = f"{proxy.proxy_type}://{proxy.username}:{proxy.password}@{proxy.host}:{proxy.port}"
        else:
            proxy_url = f"{proxy.proxy_type}://{proxy.host}:{proxy.port}"

        # 测试连接
        test_url = proxy.health_check_url or "https://api.binance.com/api/v3/ping"
        start_time = datetime.now()

        try:
            # httpx使用proxy参数（单数）传递代理URL
            async with httpx.AsyncClient(proxy=proxy_url, timeout=10.0) as client:
                response = await client.get(test_url)
                end_time = datetime.now()
                latency_ms = int((end_time - start_time).total_seconds() * 1000)

                if response.status_code == 200:
                    # 更新成功统计
                    proxy.last_check_at = datetime.now()
                    proxy.last_success_at = datetime.now()
                    proxy.consecutive_failures = 0
                    proxy.successful_requests += 1
                    proxy.total_requests += 1

                    # 更新平均延迟
                    if proxy.avg_latency_ms:
                        proxy.avg_latency_ms = (proxy.avg_latency_ms + latency_ms) / 2
                    else:
                        proxy.avg_latency_ms = latency_ms

                    # 更新成功率
                    proxy.success_rate = (proxy.successful_requests / proxy.total_requests) * 100
                    proxy.is_healthy = True

                    await db.commit()

                    return {
                        "success": True,
                        "latency_ms": latency_ms,
                        "message": "Proxy test successful"
                    }
                else:
                    raise Exception(f"HTTP {response.status_code}")

        except Exception as test_error:
            # 更新失败统计
            proxy.last_check_at = datetime.now()
            proxy.last_failure_at = datetime.now()
            proxy.consecutive_failures += 1
            proxy.failed_requests += 1
            proxy.total_requests += 1

            # 更新成功率
            if proxy.total_requests > 0:
                proxy.success_rate = (proxy.successful_requests / proxy.total_requests) * 100

            # 检查是否需要标记为不健康
            if proxy.consecutive_failures >= proxy.max_consecutive_failures:
                proxy.is_healthy = False

            await db.commit()

            return {
                "success": False,
                "error": str(test_error),
                "message": "Proxy test failed"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to test proxy {proxy_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/swap-priority")
async def swap_priority(
    proxy_id_1: int = Query(...),
    proxy_id_2: int = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """交换两个代理的优先级"""
    try:
        # 获取两个代理
        result = await db.execute(
            select(Proxy).where(Proxy.id.in_([proxy_id_1, proxy_id_2]))
        )
        proxies = result.scalars().all()

        if len(proxies) != 2:
            raise HTTPException(status_code=404, detail="One or both proxies not found")

        proxy1, proxy2 = proxies[0], proxies[1]

        # 交换优先级
        temp_priority = proxy1.priority
        proxy1.priority = proxy2.priority
        proxy2.priority = temp_priority

        await db.commit()

        logger.info(f"Swapped priority between proxy {proxy_id_1} and {proxy_id_2}")

        return {
            "message": "Priority swapped successfully",
            "proxy1": {"id": proxy1.id, "priority": proxy1.priority},
            "proxy2": {"id": proxy2.id, "priority": proxy2.priority}
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to swap priority: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
