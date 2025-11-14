"""
Strategies API endpoints
管理交易策略的创建、启动、停止、查询等
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel
import logging
import ast
import tempfile
from pathlib import Path
import asyncio

from database import get_db
from models.strategy import Strategy
from models.user import User
from core.freqtrade_manager import FreqTradeGatewayManager
from services.websocket_service import ws_service
from services.log_monitor_service import log_monitor_service
from services.heartbeat_monitor_service import heartbeat_monitor
from api.v1.auth import get_current_active_user

router = APIRouter()
logger = logging.getLogger(__name__)

# TODO: 在main.py中初始化并注入
_ft_manager: Optional[FreqTradeGatewayManager] = None


# Pydantic模型用于策略更新
class StrategyUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    pair_whitelist: Optional[List[str]] = None
    pair_blacklist: Optional[List[str]] = None
    dry_run_wallet: Optional[float] = None
    stake_amount: Optional[float] = None
    max_open_trades: Optional[int] = None
    signal_thresholds: Optional[dict] = None
    proxy_id: Optional[int] = None


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
        query = select(Strategy).where(Strategy.is_active == True)

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
                    "process_id": s.process_id,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                    "started_at": s.started_at.isoformat() if s.started_at else None
                }
                for s in strategies
            ]
        }
    except Exception as e:
        logger.error(f"Failed to list strategies: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/overview")
async def get_strategies_overview(
    db: AsyncSession = Depends(get_db),
    ft_manager: FreqTradeGatewayManager = Depends(get_ft_manager)
):
    """获取策略概览"""
    try:
        # 获取数据库中的策略统计 (仅活跃策略)
        result = await db.execute(select(Strategy).where(Strategy.is_active == True))
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
                    "port": s.port,
                    "started_at": s.started_at.isoformat() if s.started_at else None
                }
                for s in all_strategies if s.is_active
            ]
        }
    except Exception as e:
        logger.error(f"Failed to get strategies overview: {e}", exc_info=True)
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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """创建新策略"""
    try:
        # 使用当前登录用户的 ID
        logger.info(f"User {current_user.username} (ID: {current_user.id}) creating strategy: {strategy_data.get('name')}")

        # 创建策略记录
        strategy = Strategy(
            user_id=current_user.id,  # 使用当前登录用户的 ID
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

        logger.info(f"Created strategy {strategy.id}: {strategy.name} for user {current_user.username}")

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


async def _start_strategy_background(strategy_id: int, strategy_config: dict, ft_manager: FreqTradeGatewayManager):
    """
    后台任务：执行策略启动

    处理流程：
    1. 调用FreqTrade管理器启动策略
    2. 根据结果更新数据库状态
    3. 推送WebSocket消息通知前端
    4. 启动日志监控服务
    """
    from database.session import SessionLocal
    from datetime import datetime

    async with SessionLocal() as db:
        try:
            logger.info(f"[BG Task] Starting strategy {strategy_id}: {strategy_config.get('name')}")

            # 执行启动
            success = await ft_manager.create_strategy(strategy_config, db)

            # 获取策略以更新状态
            result = await db.execute(
                select(Strategy).where(Strategy.id == strategy_id)
            )
            strategy = result.scalar_one_or_none()

            if not strategy:
                logger.error(f"[BG Task] Strategy {strategy_id} not found in database after starting attempt")
                return

            if success:
                # ✅ 启动成功：更新为running状态
                strategy.status = "running"
                strategy.started_at = datetime.now()
                strategy.port = ft_manager.strategy_ports.get(strategy_id)
                strategy.process_id = ft_manager.strategy_processes.get(strategy_id).pid if strategy_id in ft_manager.strategy_processes else None

                await db.commit()

                logger.info(
                    f"[BG Task] ✅ Strategy {strategy_id} started successfully "
                    f"(Port: {strategy.port}, PID: {strategy.process_id})"
                )

                # 启动日志监控
                if log_monitor_service:
                    await log_monitor_service.start_monitoring_strategy(strategy_id)
                    logger.info(f"[BG Task] Started log monitoring for strategy {strategy_id}")

                # 注册心跳监控
                if heartbeat_monitor:
                    log_file_path = str(ft_manager.logs_path / f"strategy_{strategy_id}.log")
                    await heartbeat_monitor.register_strategy(
                        strategy_id=strategy_id,
                        log_file_path=log_file_path
                    )
                    logger.info(f"[BG Task] Registered heartbeat monitoring for strategy {strategy_id}")

                # 推送成功状态
                await ws_service.push_strategy_status(
                    strategy_id=strategy.id,
                    status="started",
                    data={
                        "name": strategy.name,
                        "exchange": strategy.exchange,
                        "port": strategy.port,
                        "process_id": strategy.process_id,
                        "started_at": strategy.started_at.isoformat() if strategy.started_at else None
                    }
                )
            else:
                # ❌ 启动失败：恢复为stopped
                strategy.status = "stopped"
                await db.commit()

                logger.error(f"[BG Task] ❌ Failed to start strategy {strategy_id}: create_strategy returned False")

                # 推送失败状态（通用错误）
                await ws_service.push_strategy_status(
                    strategy_id=strategy.id,
                    status="start_failed",
                    data={
                        "name": strategy.name,
                        "error": "Failed to start FreqTrade instance (unknown reason)",
                        "error_type": "startup_failure"
                    }
                )

        except Exception as e:
            error_message = str(e)
            logger.error(f"[BG Task] ❌ Exception starting strategy {strategy_id}: {error_message}", exc_info=True)

            # 🔍 分析错误类型并生成友好的错误消息
            error_info = _analyze_startup_error(error_message, strategy_config)

            # 尝试恢复状态
            try:
                result = await db.execute(
                    select(Strategy).where(Strategy.id == strategy_id)
                )
                strategy = result.scalar_one_or_none()
                if strategy:
                    strategy.status = "stopped"
                    await db.commit()

                    # 推送详细的错误信息
                    await ws_service.push_strategy_status(
                        strategy_id=strategy.id,
                        status="start_failed",
                        data={
                            "name": strategy.name,
                            "error": error_info["message"],
                            "error_type": error_info["type"],
                            "suggestion": error_info.get("suggestion"),
                            "raw_error": error_message[:200]  # 保留原始错误（截取前200字符）
                        }
                    )

                    logger.info(f"[BG Task] Strategy {strategy_id} status reset to 'stopped'")
            except Exception as inner_e:
                logger.error(f"[BG Task] Failed to recover strategy {strategy_id} status: {inner_e}")


def _analyze_startup_error(error_message: str, strategy_config: dict) -> dict:
    """
    分析启动错误并返回友好的错误信息

    Args:
        error_message: 原始错误消息
        strategy_config: 策略配置

    Returns:
        dict: {
            "type": 错误类型,
            "message": 友好的错误消息,
            "suggestion": 解决建议（可选）
        }
    """
    error_lower = error_message.lower()
    port = strategy_config.get("port", "unknown")

    # 1. 端口冲突
    if "address already in use" in error_lower or "errno 98" in error_lower:
        return {
            "type": "port_conflict",
            "message": f"端口冲突：端口 {port} 已被其他进程占用",
            "suggestion": "请停止占用该端口的进程，或者等待片刻后重试"
        }

    # 2. 进程异常退出
    if "process exited" in error_lower:
        # 尝试提取退出码
        import re
        exit_code_match = re.search(r'code (\d+)', error_message)
        exit_code = exit_code_match.group(1) if exit_code_match else "unknown"

        return {
            "type": "process_exit",
            "message": f"FreqTrade进程异常退出（退出码: {exit_code}）",
            "suggestion": "请查看策略日志了解详细原因"
        }

    # 3. API超时
    if "failed to start within" in error_lower or "timeout" in error_lower:
        return {
            "type": "api_timeout",
            "message": f"FreqTrade API启动超时（端口: {port}）",
            "suggestion": "进程可能仍在运行但API未响应，请检查系统资源或策略配置"
        }

    # 4. 配置错误
    if "config" in error_lower or "invalid" in error_lower:
        return {
            "type": "config_error",
            "message": "策略配置错误",
            "suggestion": "请检查策略配置文件是否正确"
        }

    # 5. 代理错误
    if "proxy" in error_lower or "connection" in error_lower:
        proxy_id = strategy_config.get("proxy_id")
        if proxy_id:
            return {
                "type": "proxy_error",
                "message": f"代理连接失败（代理ID: {proxy_id}）",
                "suggestion": "请检查代理配置是否正确，或尝试使用其他代理"
            }

    # 6. 权限错误
    if "permission" in error_lower or "access denied" in error_lower:
        return {
            "type": "permission_error",
            "message": "权限不足：无法启动FreqTrade进程",
            "suggestion": "请检查FreqTrade可执行文件权限"
        }

    # 7. 容量不足
    if "maximum" in error_lower or "limit" in error_lower:
        return {
            "type": "capacity_error",
            "message": "系统容量不足：已达到最大策略数量或端口限制",
            "suggestion": "请停止其他策略后重试"
        }

    # 8. 未知错误（默认）
    return {
        "type": "unknown",
        "message": f"启动失败：{error_message[:100]}",  # 截取前100字符
        "suggestion": "请查看后端日志了解详细错误信息"
    }


@router.post("/{strategy_id}/start", status_code=202)
async def start_strategy(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
    ft_manager: FreqTradeGatewayManager = Depends(get_ft_manager)
):
    """启动策略 - 异步模式，立即返回"""
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

        if strategy.status == "starting":
            return {"message": "Strategy is already starting", "status": "starting"}

        # 立即设置状态为"正在启动"
        strategy.status = "starting"
        await db.commit()

        # 推送"正在启动"状态到WebSocket订阅客户端
        await ws_service.push_strategy_status(
            strategy_id=strategy.id,
            status="starting",
            data={
                "name": strategy.name,
                "exchange": strategy.exchange
            }
        )

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

        # 启动后台任务执行实际启动操作
        asyncio.create_task(_start_strategy_background(strategy_id, strategy_config, ft_manager))

        logger.info(f"Strategy {strategy_id} start request accepted, executing in background")

        # 立即返回202 Accepted
        return {
            "id": strategy.id,
            "name": strategy.name,
            "status": "starting",
            "message": "Strategy start request accepted, executing in background"
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to accept start request for strategy {strategy_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def _stop_strategy_background(strategy_id: int, ft_manager: FreqTradeGatewayManager):
    """后台任务：执行策略停止"""
    from database.session import SessionLocal
    from datetime import datetime

    async with SessionLocal() as db:
        try:
            # 执行停止
            success = await ft_manager.stop_strategy(strategy_id)

            # 获取策略以更新状态
            result = await db.execute(
                select(Strategy).where(Strategy.id == strategy_id)
            )
            strategy = result.scalar_one_or_none()

            if not strategy:
                logger.error(f"Strategy {strategy_id} not found after stopping")
                return

            if success:
                # 停止日志监控
                if log_monitor_service:
                    await log_monitor_service.stop_monitoring_strategy(strategy_id)
                    logger.info(f"Stopped log monitoring for strategy {strategy_id}")

                # 取消心跳监控注册
                if heartbeat_monitor:
                    await heartbeat_monitor.unregister_strategy(strategy_id)
                    logger.info(f"Unregistered heartbeat monitoring for strategy {strategy_id}")

                # 更新为stopped状态
                strategy.status = "stopped"
                strategy.stopped_at = datetime.now()
                strategy.port = None
                strategy.process_id = None

                await db.commit()

                logger.info(f"Background task: Strategy {strategy_id} stopped successfully")

                # 推送成功状态
                await ws_service.push_strategy_status(
                    strategy_id=strategy.id,
                    status="stopped",
                    data={
                        "name": strategy.name,
                        "stopped_at": strategy.stopped_at.isoformat() if strategy.stopped_at else None
                    }
                )
            else:
                # 停止失败，恢复为running
                strategy.status = "running"
                await db.commit()

                logger.error(f"Background task: Failed to stop strategy {strategy_id}")

                # 推送失败状态
                await ws_service.push_strategy_status(
                    strategy_id=strategy.id,
                    status="stop_failed",
                    data={
                        "name": strategy.name,
                        "error": "Failed to stop FreqTrade instance"
                    }
                )
        except Exception as e:
            logger.error(f"Background task error for stopping strategy {strategy_id}: {e}", exc_info=True)
            # 尝试恢复状态
            try:
                result = await db.execute(
                    select(Strategy).where(Strategy.id == strategy_id)
                )
                strategy = result.scalar_one_or_none()
                if strategy:
                    strategy.status = "running"
                    await db.commit()

                    await ws_service.push_strategy_status(
                        strategy_id=strategy.id,
                        status="stop_failed",
                        data={
                            "name": strategy.name,
                            "error": str(e)
                        }
                    )
            except Exception as inner_e:
                logger.error(f"Failed to recover strategy {strategy_id} status: {inner_e}")


@router.post("/{strategy_id}/stop", status_code=202)
async def stop_strategy(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
    ft_manager: FreqTradeGatewayManager = Depends(get_ft_manager)
):
    """停止策略 - 异步模式，立即返回"""
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

        if strategy.status == "stopping":
            return {"message": "Strategy is already stopping", "status": "stopping"}

        # 立即设置状态为"正在停止"
        strategy.status = "stopping"
        await db.commit()

        # 推送"正在停止"状态到WebSocket订阅客户端
        await ws_service.push_strategy_status(
            strategy_id=strategy.id,
            status="stopping",
            data={
                "name": strategy.name
            }
        )

        # 启动后台任务执行实际停止操作
        asyncio.create_task(_stop_strategy_background(strategy_id, ft_manager))

        logger.info(f"Strategy {strategy_id} stop request accepted, executing in background")

        # 立即返回202 Accepted
        return {
            "id": strategy.id,
            "name": strategy.name,
            "status": "stopping",
            "message": "Strategy stop request accepted, executing in background"
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to accept stop request for strategy {strategy_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{strategy_id}/restart")
async def restart_strategy(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
    ft_manager: FreqTradeGatewayManager = Depends(get_ft_manager)
):
    """重启策略

    先停止策略，然后重新启动。适用于应用配置更改。
    """
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

            # 更新状态
            strategy.status = "stopped"
            strategy.port = None
            strategy.process_id = None
            await db.commit()

            # 等待一小段时间确保进程完全停止
            import asyncio
            await asyncio.sleep(2)

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

        # 重新启动
        success = await ft_manager.create_strategy(strategy_config, db)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to restart strategy")

        # 更新数据库
        from datetime import datetime
        strategy.status = "running"
        strategy.started_at = datetime.now()

        await db.commit()

        # 重新获取策略以获取更新后的port和process_id
        await db.refresh(strategy)

        logger.info(f"Restarted strategy {strategy_id}: {strategy.name} on port {strategy.port}")

        # 推送策略重启事件
        await ws_service.push_strategy_status(
            strategy_id=strategy.id,
            status="running",
            data={
                "name": strategy.name,
                "port": strategy.port,
                "process_id": strategy.process_id,
                "started_at": strategy.started_at.isoformat() if strategy.started_at else None
            }
        )

        return {
            "id": strategy.id,
            "name": strategy.name,
            "status": "running",
            "port": strategy.port,
            "process_id": strategy.process_id,
            "message": "Strategy restarted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to restart strategy {strategy_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{strategy_id}/logs")
async def get_strategy_logs(
    strategy_id: int,
    lines: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """获取策略运行日志（结构化）

    Parameters:
    - lines: 返回最后N行日志，默认100行

    返回格式：
    {
        "strategy_id": 10,
        "strategy_name": "pt1",
        "logs": [
            {
                "timestamp": "2025-10-27 16:55:41,203",
                "logger": "freqtrade.freqtradebot",
                "level": "INFO",
                "message": "Bot heartbeat. PID=258926...",
                "raw": "2025-10-27 16:55:41,203 - freqtrade.freqtradebot - INFO - Bot heartbeat..."
            }
        ]
    }
    """
    try:
        # 验证策略存在
        result = await db.execute(
            select(Strategy).where(Strategy.id == strategy_id)
        )
        strategy = result.scalar_one_or_none()

        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        # 使用日志监控服务获取结构化日志
        if log_monitor_service:
            logger.debug(f"Using log_monitor_service for strategy {strategy_id}")
            logs = await log_monitor_service.get_recent_logs(strategy_id, lines)

            return {
                "strategy_id": strategy_id,
                "strategy_name": strategy.name,
                "logs": logs,
                "total_returned": len(logs)
            }
        else:
            # 降级方案：直接读取文件并解析
            logger.debug(f"Using fallback method for strategy {strategy_id} logs")
            from pathlib import Path
            import re

            log_path = Path(__file__).parent.parent.parent / "logs" / "freqtrade" / f"strategy_{strategy_id}.log"

            if not log_path.exists():
                return {
                    "strategy_id": strategy_id,
                    "strategy_name": strategy.name,
                    "logs": [],
                    "total_returned": 0,
                    "message": "Log file not found - strategy may not have been started yet"
                }

            # 读取最后N行
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = f.readlines()
                log_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

            # 解析日志格式
            log_pattern = re.compile(
                r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - ([\w\.]+) - (\w+) - (.+)'
            )

            parsed_logs = []
            for line in log_lines:
                line = line.strip()
                if not line:
                    continue

                match = log_pattern.match(line)
                if match:
                    timestamp_str, logger_name, level, message = match.groups()
                    parsed_logs.append({
                        "timestamp": timestamp_str,
                        "logger": logger_name,
                        "level": level,
                        "message": message,
                        "raw": line
                    })
                else:
                    # 无法解析的行，作为原始内容
                    parsed_logs.append({
                        "timestamp": "",
                        "logger": "unknown",
                        "level": "INFO",
                        "message": line,
                        "raw": line
                    })

            return {
                "strategy_id": strategy_id,
                "strategy_name": strategy.name,
                "logs": parsed_logs,
                "total_returned": len(parsed_logs)
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get logs for strategy {strategy_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{strategy_id}")
async def update_strategy(
    strategy_id: int,
    update_data: StrategyUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """更新策略配置

    注意：运行中的策略需要先停止才能更新，或者更新后需要重启才能生效
    """
    try:
        # 获取策略
        result = await db.execute(
            select(Strategy).where(
                Strategy.id == strategy_id,
                Strategy.is_active == True
            )
        )
        strategy = result.scalar_one_or_none()

        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        # 如果策略正在运行，警告用户
        is_running = strategy.status == "running"

        # 更新字段
        updated_fields = []

        if update_data.name is not None and update_data.name != strategy.name:
            strategy.name = update_data.name
            updated_fields.append("name")

        if update_data.description is not None and update_data.description != strategy.description:
            strategy.description = update_data.description
            updated_fields.append("description")

        if update_data.pair_whitelist is not None and update_data.pair_whitelist != strategy.pair_whitelist:
            strategy.pair_whitelist = update_data.pair_whitelist
            updated_fields.append("pair_whitelist")

        if update_data.pair_blacklist is not None and update_data.pair_blacklist != strategy.pair_blacklist:
            strategy.pair_blacklist = update_data.pair_blacklist
            updated_fields.append("pair_blacklist")

        if update_data.dry_run_wallet is not None and update_data.dry_run_wallet != strategy.dry_run_wallet:
            strategy.dry_run_wallet = update_data.dry_run_wallet
            updated_fields.append("dry_run_wallet")

        if update_data.stake_amount is not None and update_data.stake_amount != strategy.stake_amount:
            strategy.stake_amount = update_data.stake_amount
            updated_fields.append("stake_amount")

        if update_data.max_open_trades is not None and update_data.max_open_trades != strategy.max_open_trades:
            strategy.max_open_trades = update_data.max_open_trades
            updated_fields.append("max_open_trades")

        if update_data.signal_thresholds is not None and update_data.signal_thresholds != strategy.signal_thresholds:
            strategy.signal_thresholds = update_data.signal_thresholds
            updated_fields.append("signal_thresholds")

        if update_data.proxy_id is not None and update_data.proxy_id != strategy.proxy_id:
            strategy.proxy_id = update_data.proxy_id
            updated_fields.append("proxy_id")

        if not updated_fields:
            return {
                "id": strategy.id,
                "message": "No changes detected"
            }

        # 更新时间戳
        from datetime import datetime, timezone
        strategy.updated_at = datetime.now(timezone.utc)

        await db.commit()

        logger.info(f"Updated strategy {strategy_id}: {', '.join(updated_fields)}")

        message = f"Strategy updated successfully. Fields updated: {', '.join(updated_fields)}"
        if is_running:
            message += ". Note: Strategy is running - restart required for changes to take effect."

        return {
            "id": strategy.id,
            "name": strategy.name,
            "updated_fields": updated_fields,
            "requires_restart": is_running,
            "message": message
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update strategy {strategy_id}: {e}", exc_info=True)
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


@router.get("/{strategy_id}/health")
async def check_strategy_health(
    strategy_id: int,
    ft_manager: FreqTradeGatewayManager = Depends(get_ft_manager)
):
    """检查策略健康状态"""
    try:
        health_status = await ft_manager.check_strategy_health(strategy_id)
        return health_status
    except Exception as e:
        logger.error(f"Failed to check strategy {strategy_id} health: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health/all")
async def check_all_strategies_health(
    ft_manager: FreqTradeGatewayManager = Depends(get_ft_manager)
):
    """检查所有策略的健康状态"""
    try:
        health_report = await ft_manager.check_all_strategies_health()
        return health_report
    except Exception as e:
        logger.error(f"Failed to check all strategies health: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload")
async def upload_strategy_file(
    file: UploadFile = File(...),
    ft_manager: FreqTradeGatewayManager = Depends(get_ft_manager)
):
    """
    上传策略文件并扫描可用的策略类
    Upload strategy file and scan for available strategy classes
    """
    try:
        # 1. 验证文件类型
        if not file.filename.endswith('.py'):
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Only .py files are accepted"
            )

        # 2. 验证文件大小 (限制为1MB)
        content = await file.read()
        if len(content) > 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail="File too large. Maximum size is 1MB"
            )

        # 3. 保存文件到临时目录
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.py', delete=False) as tmp_file:
            tmp_file.write(content)
            tmp_path = tmp_file.name

        # 4. 使用AST解析Python代码
        try:
            with open(tmp_path, 'r', encoding='utf-8') as f:
                file_content = f.read()

            tree = ast.parse(file_content, filename=file.filename)
        except SyntaxError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid Python syntax: {str(e)}"
            )

        # 5. 扫描策略类（查找继承自IStrategy的类）
        strategy_classes = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # 检查是否继承自IStrategy或其他策略基类
                inherits_from_strategy = False
                base_classes = []

                for base in node.bases:
                    if isinstance(base, ast.Name):
                        base_name = base.id
                        base_classes.append(base_name)
                        # 检查常见的策略基类名称
                        if base_name in ['IStrategy', 'Strategy', 'StrategyBase']:
                            inherits_from_strategy = True

                # 如果找到策略类，提取信息
                if inherits_from_strategy or len(node.bases) > 0:
                    # 提取docstring
                    docstring = ast.get_docstring(node) or "No description available"

                    # 提取类方法
                    methods = [
                        item.name for item in node.body
                        if isinstance(item, ast.FunctionDef)
                    ]

                    strategy_classes.append({
                        "class_name": node.name,
                        "description": docstring.split('\n')[0][:200],  # 取第一行，限制200字符
                        "base_classes": base_classes,
                        "methods": methods,
                        "has_populate_indicators": "populate_indicators" in methods,
                        "has_populate_entry": "populate_entry_trend" in methods or "populate_buy_trend" in methods,
                        "has_populate_exit": "populate_exit_trend" in methods or "populate_sell_trend" in methods,
                        "is_valid_strategy": inherits_from_strategy
                    })

        # 6. 如果文件有效，保存到策略目录
        if strategy_classes:
            strategies_path = ft_manager.strategies_path
            target_path = strategies_path / file.filename

            # 检查文件是否已存在
            if target_path.exists():
                logger.warning(f"Strategy file {file.filename} already exists, will be overwritten")

            # 复制文件到策略目录
            with open(target_path, 'wb') as f:
                f.write(content)

            logger.info(f"Uploaded strategy file {file.filename} with {len(strategy_classes)} classes")

        # 7. 清理临时文件
        Path(tmp_path).unlink(missing_ok=True)

        # 转换策略类对象，使用前端期望的字段名
        frontend_strategy_classes = [
            {
                "name": sc["class_name"],  # 前端期望的字段名
                "description": sc["description"],
                "base_classes": sc["base_classes"],
                "methods": sc["methods"],
                "has_populate_indicators": sc["has_populate_indicators"],
                "has_populate_entry": sc["has_populate_entry"],
                "has_populate_exit": sc["has_populate_exit"],
                "is_valid_strategy": sc["is_valid_strategy"]
            }
            for sc in strategy_classes
        ]

        return {
            "success": True,  # 添加 success 字段供前端判断
            "filename": file.filename,
            "file_id": file.filename.replace('.py', ''),  # 添加 file_id
            "file_path": str(strategies_path / file.filename),  # 添加 file_path
            "size_bytes": len(content),
            "strategy_classes": frontend_strategy_classes,  # 使用转换后的对象
            "total_classes": len(strategy_classes),
            "valid_strategies": len([s for s in strategy_classes if s["is_valid_strategy"]]),
            "message": f"文件上传成功，发现 {len(strategy_classes)} 个策略类"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload strategy file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
