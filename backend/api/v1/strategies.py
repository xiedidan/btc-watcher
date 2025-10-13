"""
Strategies API endpoints
管理交易策略的创建、启动、停止、查询等
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import logging

from database import get_db
from models.strategy import Strategy
from core.freqtrade_manager import FreqTradeGatewayManager

router = APIRouter()
logger = logging.getLogger(__name__)

# TODO: 在main.py中初始化并注入
_ft_manager: Optional[FreqTradeGatewayManager] = None


def get_ft_manager():
    """Get FreqTrade manager instance"""
    if _ft_manager is None:
        raise HTTPException(status_code=500, detail="FreqTrade manager not initialized")
    return _ft_manager


@router.get("/")
async def list_strategies(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """获取策略列表"""
    try:
        query = select(Strategy)

        if status:
            query = query.where(Strategy.status == status)

        query = query.offset(skip).limit(limit).order_by(Strategy.created_at.desc())

        result = await db.execute(query)
        strategies = result.scalars().all()

        return {
            "total": len(strategies),
            "skip": skip,
            "limit": limit,
            "strategies": [
                {
                    "id": s.id,
                    "name": s.name,
                    "strategy_class": s.strategy_class,
                    "exchange": s.exchange,
                    "status": s.status,
                    "port": s.port,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                    "started_at": s.started_at.isoformat() if s.started_at else None
                }
                for s in strategies
            ]
        }
    except Exception as e:
        logger.error(f"Failed to list strategies: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{strategy_id}")
async def get_strategy(
    strategy_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取策略详情"""
    try:
        result = await db.execute(
            select(Strategy).where(Strategy.id == strategy_id)
        )
        strategy = result.scalar_one_or_none()

        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        return {
            "id": strategy.id,
            "user_id": strategy.user_id,
            "name": strategy.name,
            "description": strategy.description,
            "strategy_class": strategy.strategy_class,
            "version": strategy.version,
            "exchange": strategy.exchange,
            "timeframe": strategy.timeframe,
            "pair_whitelist": strategy.pair_whitelist,
            "pair_blacklist": strategy.pair_blacklist,
            "dry_run": strategy.dry_run,
            "dry_run_wallet": strategy.dry_run_wallet,
            "stake_amount": strategy.stake_amount,
            "max_open_trades": strategy.max_open_trades,
            "signal_thresholds": strategy.signal_thresholds,
            "proxy_id": strategy.proxy_id,
            "status": strategy.status,
            "is_active": strategy.is_active,
            "port": strategy.port,
            "process_id": strategy.process_id,
            "created_at": strategy.created_at.isoformat() if strategy.created_at else None,
            "updated_at": strategy.updated_at.isoformat() if strategy.updated_at else None,
            "started_at": strategy.started_at.isoformat() if strategy.started_at else None,
            "stopped_at": strategy.stopped_at.isoformat() if strategy.stopped_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get strategy {strategy_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
async def create_strategy(
    strategy_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """创建新策略"""
    try:
        # 创建策略记录
        strategy = Strategy(
            user_id=strategy_data.get("user_id", 1),  # TODO: 从认证获取
            name=strategy_data["name"],
            description=strategy_data.get("description"),
            strategy_class=strategy_data["strategy_class"],
            version=strategy_data.get("version", "v1.0"),
            exchange=strategy_data["exchange"],
            timeframe=strategy_data["timeframe"],
            pair_whitelist=strategy_data["pair_whitelist"],
            pair_blacklist=strategy_data.get("pair_blacklist", []),
            dry_run=strategy_data.get("dry_run", True),
            dry_run_wallet=strategy_data.get("dry_run_wallet", 1000.0),
            stake_amount=strategy_data.get("stake_amount"),
            max_open_trades=strategy_data.get("max_open_trades", 3),
            signal_thresholds=strategy_data["signal_thresholds"],
            proxy_id=strategy_data.get("proxy_id"),
            status="stopped",
            is_active=True
        )

        db.add(strategy)
        await db.commit()
        await db.refresh(strategy)

        logger.info(f"Created strategy {strategy.id}: {strategy.name}")

        return {
            "id": strategy.id,
            "name": strategy.name,
            "status": strategy.status,
            "message": "Strategy created successfully"
        }
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create strategy: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{strategy_id}/start")
async def start_strategy(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
    ft_manager: FreqTradeGatewayManager = Depends(get_ft_manager)
):
    """启动策略"""
    try:
        # 获取策略
        result = await db.execute(
            select(Strategy).where(Strategy.id == strategy_id)
        )
        strategy = result.scalar_one_or_none()

        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        if strategy.status == "running":
            return {"message": "Strategy is already running", "status": "running"}

        # 准备策略配置
        strategy_config = {
            "id": strategy.id,
            "name": strategy.name,
            "strategy_class": strategy.strategy_class,
            "version": strategy.version,
            "exchange": strategy.exchange,
            "timeframe": strategy.timeframe,
            "pair_whitelist": strategy.pair_whitelist,
            "pair_blacklist": strategy.pair_blacklist,
            "dry_run": strategy.dry_run,
            "dry_run_wallet": strategy.dry_run_wallet,
            "stake_amount": strategy.stake_amount,
            "max_open_trades": strategy.max_open_trades,
            "proxy_id": strategy.proxy_id
        }

        # 启动FreqTrade实例
        success = await ft_manager.create_strategy(strategy_config)

        if success:
            # 更新数据库状态
            from datetime import datetime
            strategy.status = "running"
            strategy.started_at = datetime.now()
            strategy.port = ft_manager.strategy_ports.get(strategy_id)
            strategy.process_id = ft_manager.strategy_processes.get(strategy_id).pid if strategy_id in ft_manager.strategy_processes else None

            await db.commit()

            logger.info(f"Started strategy {strategy_id}: {strategy.name}")

            return {
                "id": strategy.id,
                "name": strategy.name,
                "status": "running",
                "port": strategy.port,
                "message": "Strategy started successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to start strategy")

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to start strategy {strategy_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{strategy_id}/stop")
async def stop_strategy(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
    ft_manager: FreqTradeGatewayManager = Depends(get_ft_manager)
):
    """停止策略"""
    try:
        # 获取策略
        result = await db.execute(
            select(Strategy).where(Strategy.id == strategy_id)
        )
        strategy = result.scalar_one_or_none()

        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        if strategy.status == "stopped":
            return {"message": "Strategy is already stopped", "status": "stopped"}

        # 停止FreqTrade实例
        success = await ft_manager.stop_strategy(strategy_id)

        if success:
            # 更新数据库状态
            from datetime import datetime
            strategy.status = "stopped"
            strategy.stopped_at = datetime.now()
            strategy.port = None
            strategy.process_id = None

            await db.commit()

            logger.info(f"Stopped strategy {strategy_id}: {strategy.name}")

            return {
                "id": strategy.id,
                "name": strategy.name,
                "status": "stopped",
                "message": "Strategy stopped successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to stop strategy")

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to stop strategy {strategy_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{strategy_id}")
async def delete_strategy(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
    ft_manager: FreqTradeGatewayManager = Depends(get_ft_manager)
):
    """删除策略"""
    try:
        # 获取策略
        result = await db.execute(
            select(Strategy).where(Strategy.id == strategy_id)
        )
        strategy = result.scalar_one_or_none()

        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        # 如果正在运行，先停止
        if strategy.status == "running":
            await ft_manager.stop_strategy(strategy_id)

        # 软删除：设置为不活跃
        strategy.is_active = False
        strategy.status = "stopped"

        await db.commit()

        logger.info(f"Deleted strategy {strategy_id}: {strategy.name}")

        return {
            "id": strategy.id,
            "message": "Strategy deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete strategy {strategy_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/overview")
async def get_strategies_overview(
    db: AsyncSession = Depends(get_db),
    ft_manager: FreqTradeGatewayManager = Depends(get_ft_manager)
):
    """获取策略概览"""
    try:
        # 获取数据库中的策略统计
        result = await db.execute(select(Strategy))
        all_strategies = result.scalars().all()

        total_strategies = len(all_strategies)
        running_strategies = len([s for s in all_strategies if s.status == "running"])
        stopped_strategies = len([s for s in all_strategies if s.status == "stopped"])

        # 获取系统容量信息
        capacity_info = ft_manager.get_capacity_info()

        return {
            "summary": {
                "total_strategies": total_strategies,
                "running_strategies": running_strategies,
                "stopped_strategies": stopped_strategies,
                "capacity_utilization": capacity_info["utilization_percent"],
                "available_slots": capacity_info["available_slots"]
            },
            "capacity": capacity_info,
            "strategies": [
                {
                    "id": s.id,
                    "name": s.name,
                    "status": s.status,
                    "exchange": s.exchange,
                    "port": s.port
                }
                for s in all_strategies if s.is_active
            ]
        }
    except Exception as e:
        logger.error(f"Failed to get strategies overview: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
