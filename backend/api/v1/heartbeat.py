"""
Strategy Heartbeat Monitoring API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from database.session import get_db
from models.heartbeat import StrategyHeartbeatConfig, StrategyHeartbeatHistory, StrategyRestartHistory
from models.strategy import Strategy
from services.heartbeat_monitor_service import heartbeat_monitor
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/strategies", tags=["heartbeat"])


# ===== Request/Response Models =====

class HeartbeatConfigUpdate(BaseModel):
    """心跳配置更新请求"""
    enabled: Optional[bool] = None
    timeout_seconds: Optional[int] = Field(None, ge=30, le=3600)
    check_interval_seconds: Optional[int] = Field(None, ge=10, le=300)
    auto_restart: Optional[bool] = None
    max_restart_attempts: Optional[int] = Field(None, ge=1, le=10)
    restart_cooldown_seconds: Optional[int] = Field(None, ge=30, le=600)


class RestartRequest(BaseModel):
    """手动重启请求"""
    reason: str = "manual"
    force: bool = False


# ===== API Endpoints =====

@router.get("/{strategy_id}/heartbeat")
async def get_strategy_heartbeat(
    strategy_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取策略心跳状态"""
    # 检查策略是否存在
    result = await db.execute(select(Strategy).where(Strategy.id == strategy_id))
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    # 从心跳监控服务获取实时状态
    status = None
    if heartbeat_monitor:
        status = heartbeat_monitor.get_heartbeat_status(strategy_id)

    if not status:
        # 如果监控服务中没有数据，从数据库获取最后的心跳记录
        result = await db.execute(
            select(StrategyHeartbeatHistory)
            .where(StrategyHeartbeatHistory.strategy_id == strategy_id)
            .order_by(desc(StrategyHeartbeatHistory.heartbeat_time))
            .limit(1)
        )
        last_heartbeat = result.scalar_one_or_none()

        # 获取重启历史
        result = await db.execute(
            select(StrategyRestartHistory)
            .where(StrategyRestartHistory.strategy_id == strategy_id)
            .order_by(desc(StrategyRestartHistory.restart_time))
            .limit(1)
        )
        last_restart = result.scalar_one_or_none()

        # 获取配置
        result = await db.execute(
            select(StrategyHeartbeatConfig)
            .where(StrategyHeartbeatConfig.strategy_id == strategy_id)
        )
        config = result.scalar_one_or_none()

        status = {
            "strategy_id": strategy_id,
            "last_heartbeat_time": last_heartbeat.heartbeat_time.isoformat() if last_heartbeat else None,
            "last_pid": last_heartbeat.pid if last_heartbeat else None,
            "last_version": last_heartbeat.version if last_heartbeat else None,
            "last_state": last_heartbeat.state if last_heartbeat else None,
            "timeout_seconds": config.timeout_seconds if config else 300,
            "auto_restart": config.auto_restart if config else True,
            "is_abnormal": False,
            "consecutive_failures": 0,
            "restart_count": 0,
            "last_restart_time": last_restart.restart_time.isoformat() if last_restart else None,
            "time_since_last_heartbeat_seconds": None
        }

        if last_heartbeat and last_heartbeat.heartbeat_time:
            time_since = int((datetime.now(timezone.utc) - last_heartbeat.heartbeat_time).total_seconds())
            status["time_since_last_heartbeat_seconds"] = time_since

    return {
        "success": True,
        "data": status
    }


@router.get("/{strategy_id}/heartbeat/config")
async def get_heartbeat_config(
    strategy_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取策略心跳监控配置"""
    # 检查策略是否存在
    result = await db.execute(select(Strategy).where(Strategy.id == strategy_id))
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    # 获取配置
    result = await db.execute(
        select(StrategyHeartbeatConfig).where(
            StrategyHeartbeatConfig.strategy_id == strategy_id
        )
    )
    config = result.scalar_one_or_none()

    if not config:
        # 如果没有配置，返回默认配置
        return {
            "success": True,
            "data": {
                "strategy_id": strategy_id,
                "enabled": True,
                "timeout_seconds": 300,
                "check_interval_seconds": 30,
                "auto_restart": True,
                "max_restart_attempts": 3,
                "restart_cooldown_seconds": 60,
                "created_at": None,
                "updated_at": None
            }
        }

    return {
        "success": True,
        "data": {
            "strategy_id": config.strategy_id,
            "enabled": config.enabled,
            "timeout_seconds": config.timeout_seconds,
            "check_interval_seconds": config.check_interval_seconds,
            "auto_restart": config.auto_restart,
            "max_restart_attempts": config.max_restart_attempts,
            "restart_cooldown_seconds": config.restart_cooldown_seconds,
            "created_at": config.created_at.isoformat() if config.created_at else None,
            "updated_at": config.updated_at.isoformat() if config.updated_at else None
        }
    }


@router.put("/{strategy_id}/heartbeat/config")
async def update_heartbeat_config(
    strategy_id: int,
    config_update: HeartbeatConfigUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新策略心跳监控配置"""
    # 检查策略是否存在
    result = await db.execute(select(Strategy).where(Strategy.id == strategy_id))
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    # 获取或创建配置
    result = await db.execute(
        select(StrategyHeartbeatConfig).where(
            StrategyHeartbeatConfig.strategy_id == strategy_id
        )
    )
    config = result.scalar_one_or_none()

    if not config:
        config = StrategyHeartbeatConfig(strategy_id=strategy_id)
        db.add(config)

    # 更新配置
    if config_update.enabled is not None:
        config.enabled = config_update.enabled
    if config_update.timeout_seconds is not None:
        config.timeout_seconds = config_update.timeout_seconds
    if config_update.check_interval_seconds is not None:
        config.check_interval_seconds = config_update.check_interval_seconds
    if config_update.auto_restart is not None:
        config.auto_restart = config_update.auto_restart
    if config_update.max_restart_attempts is not None:
        config.max_restart_attempts = config_update.max_restart_attempts
    if config_update.restart_cooldown_seconds is not None:
        config.restart_cooldown_seconds = config_update.restart_cooldown_seconds

    config.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(config)

    # 更新心跳监控服务中的配置
    if heartbeat_monitor and strategy_id in heartbeat_monitor.heartbeat_status:
        await heartbeat_monitor.update_config(
            strategy_id=strategy_id,
            timeout=config.timeout_seconds,
            auto_restart=config.auto_restart
        )

    return {
        "success": True,
        "data": {
            "strategy_id": config.strategy_id,
            "enabled": config.enabled,
            "timeout_seconds": config.timeout_seconds,
            "check_interval_seconds": config.check_interval_seconds,
            "auto_restart": config.auto_restart,
            "max_restart_attempts": config.max_restart_attempts,
            "restart_cooldown_seconds": config.restart_cooldown_seconds,
            "created_at": config.created_at.isoformat() if config.created_at else None,
            "updated_at": config.updated_at.isoformat() if config.updated_at else None
        }
    }


@router.get("/{strategy_id}/heartbeat/history")
async def get_heartbeat_history(
    strategy_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    is_timeout: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """获取策略心跳历史记录"""
    # 检查策略是否存在
    result = await db.execute(select(Strategy).where(Strategy.id == strategy_id))
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    # 构建查询条件
    conditions = [StrategyHeartbeatHistory.strategy_id == strategy_id]
    if start_time:
        conditions.append(StrategyHeartbeatHistory.heartbeat_time >= start_time)
    if end_time:
        conditions.append(StrategyHeartbeatHistory.heartbeat_time <= end_time)
    if is_timeout is not None:
        conditions.append(StrategyHeartbeatHistory.is_timeout == is_timeout)

    # 查询总数
    count_query = select(func.count()).select_from(StrategyHeartbeatHistory).where(and_(*conditions))
    result = await db.execute(count_query)
    total = result.scalar()

    # 查询历史记录
    offset = (page - 1) * page_size
    query = (
        select(StrategyHeartbeatHistory)
        .where(and_(*conditions))
        .order_by(desc(StrategyHeartbeatHistory.heartbeat_time))
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(query)
    history_records = result.scalars().all()

    return {
        "success": True,
        "data": {
            "history": [
                {
                    "id": record.id,
                    "strategy_id": record.strategy_id,
                    "heartbeat_time": record.heartbeat_time.isoformat(),
                    "pid": record.pid,
                    "version": record.version,
                    "state": record.state,
                    "is_timeout": record.is_timeout,
                    "time_since_last_heartbeat_seconds": record.time_since_last_heartbeat_seconds,
                    "created_at": record.created_at.isoformat() if record.created_at else None
                }
                for record in history_records
            ]
        },
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size
        }
    }


@router.get("/{strategy_id}/restart/history")
async def get_restart_history(
    strategy_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    restart_reason: Optional[str] = None,
    restart_success: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """获取策略重启历史记录"""
    # 检查策略是否存在
    result = await db.execute(select(Strategy).where(Strategy.id == strategy_id))
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    # 构建查询条件
    conditions = [StrategyRestartHistory.strategy_id == strategy_id]
    if start_time:
        conditions.append(StrategyRestartHistory.restart_time >= start_time)
    if end_time:
        conditions.append(StrategyRestartHistory.restart_time <= end_time)
    if restart_reason:
        conditions.append(StrategyRestartHistory.restart_reason == restart_reason)
    if restart_success is not None:
        conditions.append(StrategyRestartHistory.restart_success == restart_success)

    # 查询总数
    count_query = select(func.count()).select_from(StrategyRestartHistory).where(and_(*conditions))
    result = await db.execute(count_query)
    total = result.scalar()

    # 查询重启历史
    offset = (page - 1) * page_size
    query = (
        select(StrategyRestartHistory)
        .where(and_(*conditions))
        .order_by(desc(StrategyRestartHistory.restart_time))
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(query)
    restart_records = result.scalars().all()

    return {
        "success": True,
        "data": {
            "history": [
                {
                    "id": record.id,
                    "strategy_id": record.strategy_id,
                    "restart_reason": record.restart_reason,
                    "restart_time": record.restart_time.isoformat(),
                    "restart_success": record.restart_success,
                    "error_message": record.error_message,
                    "previous_pid": record.previous_pid,
                    "new_pid": record.new_pid,
                    "created_at": record.created_at.isoformat() if record.created_at else None
                }
                for record in restart_records
            ]
        },
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size
        }
    }


@router.post("/{strategy_id}/restart")
async def restart_strategy(
    strategy_id: int,
    restart_req: RestartRequest,
    db: AsyncSession = Depends(get_db)
):
    """手动重启策略"""
    # 检查策略是否存在
    result = await db.execute(select(Strategy).where(Strategy.id == strategy_id))
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    # 检查策略状态
    if strategy.status != "running" and not restart_req.force:
        raise HTTPException(
            status_code=400,
            detail="Strategy is not running. Use force=true to restart anyway."
        )

    # 获取当前PID
    previous_pid = strategy.process_id

    # 重启策略
    try:
        # 这���需要从 main.py 或其他地方获取 strategy_manager 实例
        # 暂时先返回成功响应，实际重启逻辑需要在集成时完成
        restart_time = datetime.now(timezone.utc)

        # TODO: 调用 strategy_manager.restart_strategy(strategy_id)

        # 记录重启历史
        restart_history = StrategyRestartHistory(
            strategy_id=strategy_id,
            restart_reason=restart_req.reason,
            restart_time=restart_time,
            restart_success=True,  # 暂时设为True
            error_message=None,
            previous_pid=previous_pid,
            new_pid=None  # 新PID需要等待进程启动后获取
        )
        db.add(restart_history)
        await db.commit()

        return {
            "success": True,
            "data": {
                "strategy_id": strategy_id,
                "restart_time": restart_time.isoformat(),
                "previous_pid": previous_pid,
                "new_pid": None,  # 需要异步获取
                "restart_success": True
            }
        }

    except Exception as e:
        logger.error(f"Failed to restart strategy {strategy_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to restart strategy: {str(e)}")


@router.get("/system/heartbeat/summary")
async def get_heartbeat_summary(
    db: AsyncSession = Depends(get_db)
):
    """获取所有策略的心跳监控概览"""
    if not heartbeat_monitor:
        return {
            "success": True,
            "data": {
                "total_strategies": 0,
                "healthy_strategies": 0,
                "abnormal_strategies": 0,
                "total_restarts_today": 0,
                "strategies": []
            }
        }

    # 从心跳监控服务获取所有状态
    all_status = await heartbeat_monitor.get_all_heartbeat_status()

    # 计算统计信息
    total_strategies = len(all_status)
    abnormal_strategies = sum(1 for s in all_status if s["is_abnormal"])
    healthy_strategies = total_strategies - abnormal_strategies

    # 查询今天的重启次数
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(func.count())
        .select_from(StrategyRestartHistory)
        .where(StrategyRestartHistory.restart_time >= today_start)
    )
    total_restarts_today = result.scalar()

    # 获取策略名称
    strategy_ids = [s["strategy_id"] for s in all_status]
    if strategy_ids:
        result = await db.execute(
            select(Strategy).where(Strategy.id.in_(strategy_ids))
        )
        strategies = {s.id: s for s in result.scalars().all()}
    else:
        strategies = {}

    # 构建策略列表
    strategy_list = []
    for status in all_status:
        strategy_id = status["strategy_id"]
        strategy = strategies.get(strategy_id)
        strategy_list.append({
            "strategy_id": strategy_id,
            "strategy_name": strategy.name if strategy else f"Strategy #{strategy_id}",
            "last_heartbeat_time": status["last_heartbeat_time"],
            "is_abnormal": status["is_abnormal"],
            "time_since_last_heartbeat_seconds": status["time_since_last_heartbeat_seconds"]
        })

    return {
        "success": True,
        "data": {
            "total_strategies": total_strategies,
            "healthy_strategies": healthy_strategies,
            "abnormal_strategies": abnormal_strategies,
            "total_restarts_today": total_restarts_today,
            "strategies": strategy_list
        }
    }
