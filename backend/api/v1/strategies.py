"""
Strategies API endpoints
管理交易策略的创建、启动、停止、查询等
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import logging
import ast
import tempfile
from pathlib import Path

from database import get_db
from models.strategy import Strategy
from core.freqtrade_manager import FreqTradeGatewayManager
from services.websocket_service import ws_service

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

        # 启动FreqTrade实例（传递db session用于查询代理）
        success = await ft_manager.create_strategy(strategy_config, db)

        if success:
            # 更新数据库状态
            from datetime import datetime
            strategy.status = "running"
            strategy.started_at = datetime.now()
            strategy.port = ft_manager.strategy_ports.get(strategy_id)
            strategy.process_id = ft_manager.strategy_processes.get(strategy_id).pid if strategy_id in ft_manager.strategy_processes else None

            await db.commit()

            logger.info(f"Started strategy {strategy_id}: {strategy.name}")

            # 推送策略启动事件到WebSocket订阅客户端
            await ws_service.push_strategy_status(
                strategy_id=strategy.id,
                status="started",
                data={
                    "name": strategy.name,
                    "exchange": strategy.exchange,
                    "port": strategy.port,
                    "started_at": strategy.started_at.isoformat() if strategy.started_at else None
                }
            )

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

            # 推送策略停止事件到WebSocket订阅客户端
            await ws_service.push_strategy_status(
                strategy_id=strategy.id,
                status="stopped",
                data={
                    "name": strategy.name,
                    "stopped_at": strategy.stopped_at.isoformat() if strategy.stopped_at else None
                }
            )

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

        return {
            "filename": file.filename,
            "size_bytes": len(content),
            "strategy_classes": strategy_classes,
            "total_classes": len(strategy_classes),
            "valid_strategies": len([s for s in strategy_classes if s["is_valid_strategy"]]),
            "message": f"File uploaded successfully. Found {len(strategy_classes)} strategy classe(s)."
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload strategy file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
