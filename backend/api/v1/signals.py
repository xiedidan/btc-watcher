"""
Signals API endpoints
处理交易信号的接收、查询和管理
"""
from fastapi import APIRouter, HTTPException, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from typing import Optional
from datetime import datetime, timedelta
import logging

from database import get_db
from models.signal import Signal
from models.strategy import Strategy

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/")
async def list_signals(
    skip: int = 0,
    limit: int = 100,
    strategy_id: Optional[int] = None,
    pair: Optional[str] = None,
    action: Optional[str] = None,
    strength_level: Optional[str] = None,
    hours: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """获取信号列表"""
    try:
        query = select(Signal)

        # 过滤条件
        conditions = []
        if strategy_id:
            conditions.append(Signal.strategy_id == strategy_id)
        if pair:
            conditions.append(Signal.pair == pair)
        if action:
            conditions.append(Signal.action == action)
        if strength_level:
            conditions.append(Signal.strength_level == strength_level)
        if hours:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            conditions.append(Signal.created_at >= cutoff_time)

        if conditions:
            query = query.where(and_(*conditions))

        # 分页和排序
        query = query.offset(skip).limit(limit).order_by(desc(Signal.created_at))

        result = await db.execute(query)
        signals = result.scalars().all()

        return {
            "total": len(signals),
            "skip": skip,
            "limit": limit,
            "signals": [
                {
                    "id": s.id,
                    "strategy_id": s.strategy_id,
                    "pair": s.pair,
                    "action": s.action,
                    "signal_strength": s.signal_strength,
                    "strength_level": s.strength_level,
                    "current_rate": s.current_rate,
                    "profit_ratio": s.profit_ratio,
                    "created_at": s.created_at.isoformat() if s.created_at else None
                }
                for s in signals
            ]
        }
    except Exception as e:
        logger.error(f"Failed to list signals: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{signal_id}")
async def get_signal(
    signal_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取信号详情"""
    try:
        result = await db.execute(
            select(Signal).where(Signal.id == signal_id)
        )
        signal = result.scalar_one_or_none()

        if not signal:
            raise HTTPException(status_code=404, detail="Signal not found")

        return {
            "id": signal.id,
            "strategy_id": signal.strategy_id,
            "pair": signal.pair,
            "action": signal.action,
            "signal_strength": signal.signal_strength,
            "strength_level": signal.strength_level,
            "current_rate": signal.current_rate,
            "entry_price": signal.entry_price,
            "exit_price": signal.exit_price,
            "profit_ratio": signal.profit_ratio,
            "profit_abs": signal.profit_abs,
            "trade_duration": signal.trade_duration,
            "indicators": signal.indicators,
            "metadata": signal.signal_metadata,
            "notes": signal.notes,
            "freqtrade_trade_id": signal.freqtrade_trade_id,
            "open_date": signal.open_date.isoformat() if signal.open_date else None,
            "close_date": signal.close_date.isoformat() if signal.close_date else None,
            "created_at": signal.created_at.isoformat() if signal.created_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get signal {signal_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook/{strategy_id}")
async def receive_freqtrade_signal(
    strategy_id: int = Path(..., description="策略ID"),
    signal_data: dict = None,
    db: AsyncSession = Depends(get_db)
):
    """接收FreqTrade策略信号（Webhook）"""
    try:
        # 验证策略存在
        result = await db.execute(
            select(Strategy).where(Strategy.id == strategy_id)
        )
        strategy = result.scalar_one_or_none()

        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        # 计算信号强度等级
        signal_strength = signal_data.get("indicators", {}).get("signal_strength", 0.5)
        thresholds = strategy.signal_thresholds

        if signal_strength >= thresholds.get("strong", 0.8):
            strength_level = "strong"
        elif signal_strength >= thresholds.get("medium", 0.6):
            strength_level = "medium"
        elif signal_strength >= thresholds.get("weak", 0.4):
            strength_level = "weak"
        else:
            strength_level = "ignore"

        # 创建信号记录
        signal = Signal(
            strategy_id=strategy_id,
            pair=signal_data.get("pair"),
            action=signal_data.get("action", "hold"),
            signal_strength=signal_strength,
            strength_level=strength_level,
            current_rate=signal_data.get("current_rate"),
            entry_price=signal_data.get("entry_price"),
            exit_price=signal_data.get("exit_price"),
            profit_ratio=signal_data.get("profit_ratio"),
            profit_abs=signal_data.get("profit_abs"),
            trade_duration=signal_data.get("trade_duration"),
            indicators=signal_data.get("indicators"),
            metadata=signal_data.get("metadata"),
            freqtrade_trade_id=signal_data.get("trade_id"),
            open_date=datetime.fromisoformat(signal_data["open_date"]) if signal_data.get("open_date") else None,
            close_date=datetime.fromisoformat(signal_data["close_date"]) if signal_data.get("close_date") else None
        )

        db.add(signal)
        await db.commit()
        await db.refresh(signal)

        logger.info(f"Received signal {signal.id} from strategy {strategy_id}: {signal.pair} {signal.action}")

        # TODO: 触发通知（如果强度达到阈值）

        return {
            "status": "success",
            "signal_id": signal.id,
            "strength_level": strength_level
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to process signal webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics/summary")
async def get_signals_statistics(
    strategy_id: Optional[int] = None,
    hours: int = 24,
    db: AsyncSession = Depends(get_db)
):
    """获取信号统计"""
    try:
        cutoff_time = datetime.now() - timedelta(hours=hours)

        query = select(Signal).where(Signal.created_at >= cutoff_time)
        if strategy_id:
            query = query.where(Signal.strategy_id == strategy_id)

        result = await db.execute(query)
        signals = result.scalars().all()

        total_signals = len(signals)
        buy_signals = len([s for s in signals if s.action == "buy"])
        sell_signals = len([s for s in signals if s.action == "sell"])
        strong_signals = len([s for s in signals if s.strength_level == "strong"])
        medium_signals = len([s for s in signals if s.strength_level == "medium"])
        weak_signals = len([s for s in signals if s.strength_level == "weak"])

        # 计算平均信号强度
        avg_strength = sum([s.signal_strength for s in signals]) / total_signals if total_signals > 0 else 0

        return {
            "period_hours": hours,
            "total_signals": total_signals,
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
            "strong_signals": strong_signals,
            "medium_signals": medium_signals,
            "weak_signals": weak_signals,
            "average_strength": round(avg_strength, 3),
            "strategy_id": strategy_id
        }
    except Exception as e:
        logger.error(f"Failed to get signal statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics/trend")
async def get_signals_trend(
    hours: int = 24,
    group_by: str = "all",
    strategy_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """获取信号趋势数据"""
    try:
        cutoff_time = datetime.now() - timedelta(hours=hours)

        query = select(Signal).where(Signal.created_at >= cutoff_time)
        if strategy_id:
            query = query.where(Signal.strategy_id == strategy_id)

        query = query.order_by(Signal.created_at)

        result = await db.execute(query)
        signals = result.scalars().all()

        # 确定时间间隔
        if hours <= 24:
            interval_minutes = 60  # 1小时间隔
        elif hours <= 72:
            interval_minutes = 180  # 3小时间隔
        else:
            interval_minutes = 360  # 6小时间隔

        # 生成时间点
        data_points = []
        current_time = cutoff_time
        end_time = datetime.now()

        while current_time <= end_time:
            next_time = current_time + timedelta(minutes=interval_minutes)

            # 筛选该时间段内的信号
            period_signals = [
                s for s in signals
                if current_time <= s.created_at < next_time
            ]

            # 按分组统计
            if group_by == "all":
                strong = len([s for s in period_signals if s.strength_level == "strong"])
                medium = len([s for s in period_signals if s.strength_level == "medium"])
                weak = len([s for s in period_signals if s.strength_level == "weak"])

                data_points.append({
                    "timestamp": current_time.isoformat(),
                    "strong_signals": strong,
                    "medium_signals": medium,
                    "weak_signals": weak,
                    "total_signals": len(period_signals)
                })
            elif group_by == "pair":
                # 按货币对分组（这里简化为总体，可以扩展）
                strong = len([s for s in period_signals if s.strength_level == "strong"])
                medium = len([s for s in period_signals if s.strength_level == "medium"])
                weak = len([s for s in period_signals if s.strength_level == "weak"])

                data_points.append({
                    "timestamp": current_time.isoformat(),
                    "strong_signals": strong,
                    "medium_signals": medium,
                    "weak_signals": weak,
                    "total_signals": len(period_signals)
                })
            elif group_by == "strategy":
                # 按策略分组（这里简化为总体，可以扩展）
                strong = len([s for s in period_signals if s.strength_level == "strong"])
                medium = len([s for s in period_signals if s.strength_level == "medium"])
                weak = len([s for s in period_signals if s.strength_level == "weak"])

                data_points.append({
                    "timestamp": current_time.isoformat(),
                    "strong_signals": strong,
                    "medium_signals": medium,
                    "weak_signals": weak,
                    "total_signals": len(period_signals)
                })

            current_time = next_time

        return {
            "period_hours": hours,
            "group_by": group_by,
            "interval_minutes": interval_minutes,
            "data_points": data_points
        }
    except Exception as e:
        logger.error(f"Failed to get signal trend: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

