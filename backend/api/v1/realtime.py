"""
Realtime data batch API
实时数据批量查询接口（用于WebSocket降级时的轮询）
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from datetime import datetime
import logging

from database import get_db
from models.strategy import Strategy
from models.signal import Signal

router = APIRouter()
logger = logging.getLogger(__name__)


# Dependency functions (moved here to avoid circular import)
def get_monitoring_service():
    """Get monitoring service instance"""
    from api.v1 import system
    return system._monitoring_service


def get_freqtrade_manager():
    """Get FreqTrade manager instance"""
    from api.v1 import system
    return system._ft_manager


@router.get("/batch")
async def get_realtime_batch(
    topics: str = Query(
        ...,
        description="逗号分隔的主题列表，可选: monitoring,strategies,signals,capacity"
    ),
    last_signal_id: Optional[int] = Query(
        None,
        description="上次查询的最后信号ID（用于增量查询signals）"
    ),
    db: AsyncSession = Depends(get_db),
    monitoring = Depends(get_monitoring_service),
    ft_manager = Depends(get_freqtrade_manager)
):
    """
    批量获取多个主题的实时数据

    优化轮询模式的请求次数，一次调用可获取多个主题的数据

    **主题说明**:
    - monitoring: 系统监控数据（CPU、内存、磁盘）
    - strategies: 策略状态概览
    - signals: 信号数据（支持增量查询）
    - capacity: 容量数据（端口使用情况）

    **示例**:
    - `/api/v1/realtime/batch?topics=monitoring,strategies`
    - `/api/v1/realtime/batch?topics=signals&last_signal_id=150`
    - `/api/v1/realtime/batch?topics=monitoring,strategies,signals,capacity`

    **返回格式**:
    ```json
    {
      "success": true,
      "data": {
        "monitoring": {...},
        "strategies": {...},
        "signals": {...},
        "capacity": {...}
      },
      "timestamp": "2025-10-29T14:30:00Z"
    }
    ```
    """
    try:
        # 解析主题列表
        topic_list = [t.strip() for t in topics.split(',')]
        valid_topics = {'monitoring', 'strategies', 'signals', 'capacity'}

        # 验证主题
        invalid_topics = set(topic_list) - valid_topics
        if invalid_topics:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid topics: {', '.join(invalid_topics)}. Valid topics: {', '.join(valid_topics)}"
            )

        result = {}

        # 1. 监控数据
        if 'monitoring' in topic_list:
            try:
                system_metrics = monitoring.get_system_metrics()
                result['monitoring'] = {
                    'system': system_metrics,
                    'timestamp': datetime.now().isoformat()
                }
            except Exception as e:
                logger.error(f"Failed to get monitoring data: {e}")
                result['monitoring'] = {
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }

        # 2. 策略状态
        if 'strategies' in topic_list:
            try:
                # 统计查询
                total_query = await db.execute(select(func.count(Strategy.id)))
                total = total_query.scalar() or 0

                running_query = await db.execute(
                    select(func.count(Strategy.id)).where(Strategy.status == 'running')
                )
                running = running_query.scalar() or 0

                stopped_query = await db.execute(
                    select(func.count(Strategy.id)).where(Strategy.status == 'stopped')
                )
                stopped = stopped_query.scalar() or 0

                error_query = await db.execute(
                    select(func.count(Strategy.id)).where(Strategy.status == 'error')
                )
                error = error_query.scalar() or 0

                # 获取运行中的策略详情
                strategies_query = await db.execute(
                    select(Strategy)
                    .where(Strategy.status == 'running')
                    .order_by(Strategy.id)
                )
                running_strategies = strategies_query.scalars().all()

                result['strategies'] = {
                    'total': total,
                    'running': running,
                    'stopped': stopped,
                    'error': error,
                    'strategies': [
                        {
                            'id': s.id,
                            'name': s.name,
                            'status': s.status,
                            'is_active': s.is_active,
                            'port': s.port,
                            'process_id': s.process_id,
                            'started_at': s.started_at.isoformat() if s.started_at else None
                        }
                        for s in running_strategies
                    ],
                    'timestamp': datetime.now().isoformat()
                }
            except Exception as e:
                logger.error(f"Failed to get strategies data: {e}")
                result['strategies'] = {
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }

        # 3. 信号数据（支持增量查询）
        if 'signals' in topic_list:
            try:
                query = select(Signal).order_by(Signal.id.desc()).limit(10)

                if last_signal_id:
                    # 增量查询：只获取新信号
                    query = query.where(Signal.id > last_signal_id)

                signals_query = await db.execute(query)
                signals = signals_query.scalars().all()

                result['signals'] = {
                    'new_signals': [
                        {
                            'id': s.id,
                            'strategy_id': s.strategy_id,
                            'pair': s.pair,
                            'action': s.action,
                            'signal_strength': s.signal_strength,
                            'strength_level': s.strength_level,
                            'current_rate': float(s.current_rate) if s.current_rate else None,
                            'entry_price': float(s.entry_price) if s.entry_price else None,
                            'indicators': s.indicators,
                            'created_at': s.created_at.isoformat() if s.created_at else None
                        }
                        for s in signals
                    ],
                    'last_id': signals[0].id if signals else (last_signal_id or 0),
                    'count': len(signals),
                    'timestamp': datetime.now().isoformat()
                }
            except Exception as e:
                logger.error(f"Failed to get signals data: {e}")
                result['signals'] = {
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }

        # 4. 容量数据
        if 'capacity' in topic_list:
            try:
                if ft_manager:
                    used_ports = len(ft_manager.strategy_ports)
                    total_ports = ft_manager.max_port - ft_manager.base_port + 1

                    result['capacity'] = {
                        'used_ports': used_ports,
                        'total_ports': total_ports,
                        'available_ports': total_ports - used_ports,
                        'usage_percent': round(used_ports / total_ports * 100, 2) if total_ports > 0 else 0,
                        'timestamp': datetime.now().isoformat()
                    }
                else:
                    result['capacity'] = {
                        'error': 'FreqTrade manager not available',
                        'timestamp': datetime.now().isoformat()
                    }
            except Exception as e:
                logger.error(f"Failed to get capacity data: {e}")
                result['capacity'] = {
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }

        return {
            'success': True,
            'data': result,
            'timestamp': datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch query failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch query failed: {str(e)}")
