# 实时数据通信Fallback设计方案 - 优化版

## 📋 文档信息
- **版本**: 2.0 (优化版)
- **更新日期**: 2025-10-29
- **优化重点**: 批量合并请求，降低服务器负载
- **状态**: 待确认

---

## 1. 问题背景

### 1.1 现状
当前系统实时数据推送采用 **WebSocket** 方式，但在某些网络环境下（FRP代理、防火墙等）WebSocket连接失败，导致前端无法获取实时数据。

### 1.2 设计目标
✅ WebSocket可用时：使用WebSocket实时推送（最佳体验）
✅ WebSocket不可用时：自动降级到HTTP轮询（保证可用性）
✅ **低服务器负载**：合并请求，减少API调用次数
✅ **按需轮询**：根据当前页面智能选择需要的数据

---

## 2. 优化方案：批量合并请求

### 2.1 请求优化对比

#### ❌ 原方案（分散请求）
```javascript
// 4个独立请求
setInterval(() => GET /api/v1/monitoring/system, 5000)    // 12次/分钟
setInterval(() => GET /api/v1/strategies/overview, 5000)  // 12次/分钟
setInterval(() => GET /api/v1/signals/?last_id=X, 10000)  // 6次/分钟
setInterval(() => GET /api/v1/system/capacity, 30000)     // 2次/分钟
```
**总计**: 32次/分钟（过多！）

#### ✅ 新方案（批量合并）
```javascript
// 方案A: 全部合并（简单但不够灵活）
setInterval(() => {
  GET /api/v1/realtime/batch?topics=monitoring,strategies,signals,capacity
}, 5000)
```
**总计**: 12次/分钟（降低62.5%）

```javascript
// 方案B: 按频率分组（推荐）
// 高频组（5秒）：核心数据
setInterval(() => {
  GET /api/v1/realtime/batch?topics=monitoring,strategies
}, 5000)  // 12次/分钟

// 中频组（10秒）：信号数据
setInterval(() => {
  GET /api/v1/realtime/batch?topics=signals
}, 10000)  // 6次/分钟

// 低频组（30秒）：容量数据
setInterval(() => {
  GET /api/v1/realtime/batch?topics=capacity
}, 30000)  // 2次/分钟
```
**总计**: 20次/分钟（降低37.5%）

```javascript
// 方案C: 按页面需求（最优）
// Dashboard页面：全部数据
setInterval(() => {
  GET /api/v1/realtime/batch?topics=monitoring,strategies,capacity
}, 5000)  // 12次/分钟

// Strategies页面：只需策略数据
setInterval(() => {
  GET /api/v1/realtime/batch?topics=strategies
}, 5000)  // 12次/分钟

// Signals页面：策略+信号
setInterval(() => {
  GET /api/v1/realtime/batch?topics=strategies,signals
}, 5000)  // 12次/分钟
```
**总计**: 根据页面，6-12次/分钟（降低62.5%-81.25%）

### 2.2 推荐方案：**混合策略**

结合方案B和方案C的优点：

```javascript
// 配置：不同页面的轮询策略
const POLLING_STRATEGIES = {
  dashboard: {
    high: ['monitoring', 'strategies'],     // 5秒
    medium: ['signals'],                     // 10秒
    low: ['capacity']                        // 30秒
  },
  strategies: {
    high: ['strategies'],                    // 5秒
    medium: [],
    low: []
  },
  signals: {
    high: ['strategies'],                    // 5秒
    medium: ['signals'],                     // 10秒
    low: []
  },
  monitoring: {
    high: ['monitoring', 'strategies'],      // 5秒
    medium: [],
    low: ['capacity']                        // 30秒
  }
}

// 实现
class RealtimeDataAdapter {
  startPolling(page = 'dashboard') {
    const strategy = POLLING_STRATEGIES[page] || POLLING_STRATEGIES.dashboard

    // 高频数据（5秒）
    if (strategy.high.length > 0) {
      this.highFreqTimer = setInterval(() => {
        this.fetchBatch(strategy.high)
      }, 5000)
    }

    // 中频数据（10秒）
    if (strategy.medium.length > 0) {
      this.mediumFreqTimer = setInterval(() => {
        this.fetchBatch(strategy.medium)
      }, 10000)
    }

    // 低频数据（30秒）
    if (strategy.low.length > 0) {
      this.lowFreqTimer = setInterval(() => {
        this.fetchBatch(strategy.low)
      }, 30000)
    }
  }

  async fetchBatch(topics) {
    const response = await axios.get('/api/v1/realtime/batch', {
      params: { topics: topics.join(',') }
    })
    // 更新store...
  }
}
```

### 2.3 请求量对比表

| 页面 | 高频(5s) | 中频(10s) | 低频(30s) | 总计/分钟 |
|------|---------|----------|----------|----------|
| Dashboard | 2主题×12 | 1主题×6 | 1主题×2 | **3次×12+6+2 = 20次** |
| Strategies | 1主题×12 | 0 | 0 | **1次×12 = 12次** |
| Signals | 1主题×12 | 1主题×6 | 0 | **2次×12+6 = 18次** |
| Monitoring | 2主题×12 | 0 | 1主题×2 | **3次×12+2 = 14次** |

**优化效果**：
- 原方案：32次/分钟（固定）
- 新方案：12-20次/分钟（平均15次）
- **降低53%的请求量！**

---

## 3. 后端批量API设计

### 3.1 批量查询端点

**端点**: `GET /api/v1/realtime/batch`

**请求参数**:
```
topics: string (必填) - 逗号分隔的主题列表
  可选值: monitoring, strategies, signals, capacity
  示例: topics=monitoring,strategies

last_signal_id: int (可选) - 上次查询的信号ID（用于增量查询）
```

**响应格式**:
```json
{
  "success": true,
  "data": {
    "monitoring": {
      "system": {
        "cpu": {"percent": 35.2, "count": 8},
        "memory": {"percent": 62.5, "total": 16000000000},
        "disk": {"percent": 45.8, "total": 500000000000}
      },
      "timestamp": "2025-10-29T14:30:00Z"
    },
    "strategies": {
      "total": 8,
      "running": 3,
      "stopped": 4,
      "error": 1,
      "strategies": [
        {
          "id": 1,
          "name": "MA_Cross_BTC",
          "status": "running",
          "health_score": 95
        }
      ],
      "timestamp": "2025-10-29T14:30:00Z"
    },
    "signals": {
      "new_signals": [
        {
          "id": 156,
          "strategy_id": 1,
          "pair": "BTC/USDT",
          "action": "buy",
          "signal_strength": 85
        }
      ],
      "last_id": 156,
      "count": 1,
      "timestamp": "2025-10-29T14:30:00Z"
    },
    "capacity": {
      "used_ports": 3,
      "total_ports": 999,
      "usage_percent": 0.3,
      "timestamp": "2025-10-29T14:30:00Z"
    }
  },
  "timestamp": "2025-10-29T14:30:00Z"
}
```

### 3.2 实现代码

**新建文件**: `backend/api/v1/realtime.py`

```python
"""
Realtime data batch API
实时数据批量查询接口
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
import logging

from database import get_db
from services.monitoring_service import MonitoringService
from api.v1.system import get_monitoring_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/batch")
async def get_realtime_batch(
    topics: str = Query(
        ...,
        description="逗号分隔的主题列表 (monitoring,strategies,signals,capacity)"
    ),
    last_signal_id: Optional[int] = Query(
        None,
        description="上次查询的最后信号ID（增量查询）"
    ),
    db: AsyncSession = Depends(get_db),
    monitoring: MonitoringService = Depends(get_monitoring_service)
):
    """
    批量获取多个主题的实时数据

    优化请求次数，一次调用获取多个主题数据

    示例:
    - /api/v1/realtime/batch?topics=monitoring,strategies
    - /api/v1/realtime/batch?topics=signals&last_signal_id=150
    """
    try:
        topic_list = [t.strip() for t in topics.split(',')]
        valid_topics = {'monitoring', 'strategies', 'signals', 'capacity'}

        # 验证主题
        invalid_topics = set(topic_list) - valid_topics
        if invalid_topics:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid topics: {invalid_topics}"
            )

        result = {}

        # 监控数据
        if 'monitoring' in topic_list:
            system_metrics = monitoring.get_system_metrics()
            result['monitoring'] = {
                'system': system_metrics,
                'timestamp': datetime.now().isoformat()
            }

        # 策略状态
        if 'strategies' in topic_list:
            from sqlalchemy import select, func
            from models.strategy import Strategy

            # 统计查询
            total_query = await db.execute(select(func.count(Strategy.id)))
            total = total_query.scalar()

            running_query = await db.execute(
                select(func.count(Strategy.id)).where(Strategy.status == 'running')
            )
            running = running_query.scalar()

            stopped_query = await db.execute(
                select(func.count(Strategy.id)).where(Strategy.status == 'stopped')
            )
            stopped = stopped_query.scalar()

            error_query = await db.execute(
                select(func.count(Strategy.id)).where(Strategy.status == 'error')
            )
            error = error_query.scalar()

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
                        'port': s.port
                    }
                    for s in running_strategies
                ],
                'timestamp': datetime.now().isoformat()
            }

        # 信号数据（增量查询）
        if 'signals' in topic_list:
            from sqlalchemy import select
            from models.signal import Signal

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
                        'created_at': s.created_at.isoformat()
                    }
                    for s in signals
                ],
                'last_id': signals[0].id if signals else last_signal_id,
                'count': len(signals),
                'timestamp': datetime.now().isoformat()
            }

        # 容量数据
        if 'capacity' in topic_list:
            from core.freqtrade_manager import FreqTradeGatewayManager
            from api.v1.system import get_freqtrade_manager

            ft_manager = get_freqtrade_manager()

            used_ports = len(ft_manager.port_manager.allocated_ports)
            total_ports = ft_manager.port_manager.max_port - ft_manager.port_manager.base_port + 1

            result['capacity'] = {
                'used_ports': used_ports,
                'total_ports': total_ports,
                'available_ports': total_ports - used_ports,
                'usage_percent': round(used_ports / total_ports * 100, 2),
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
        raise HTTPException(status_code=500, detail=str(e))


# 导入datetime
from datetime import datetime
```

### 3.3 注册路由

**修改文件**: `backend/main.py`

```python
# 在现有导入中添加
from api.v1 import realtime

# 在路由注册部分添加
app.include_router(
    realtime.router,
    prefix="/api/v1/realtime",
    tags=["realtime"]
)
```

---

## 4. 前端实现优化

### 4.1 配置文件

**新建文件**: `frontend/src/config/realtime.js`

```javascript
/**
 * 实时数据配置
 * Realtime data configuration
 */

// 轮询策略：按页面定义需要的数据和频率
export const POLLING_STRATEGIES = {
  dashboard: {
    high: ['monitoring', 'strategies'],     // 5秒
    medium: ['signals'],                     // 10秒
    low: ['capacity']                        // 30秒
  },
  strategies: {
    high: ['strategies'],                    // 5秒
    medium: [],
    low: []
  },
  signals: {
    high: ['strategies'],                    // 5秒  (需要知道策略状态)
    medium: ['signals'],                     // 10秒
    low: []
  },
  monitoring: {
    high: ['monitoring', 'strategies'],      // 5秒
    medium: [],
    low: ['capacity']                        // 30秒
  },
  settings: {
    high: [],
    medium: [],
    low: ['capacity']                        // 30秒 (设置页面只需容量)
  }
}

export const REALTIME_CONFIG = {
  // WebSocket配置
  websocket: {
    enabled: true,
    retryAttempts: 3,
    retryDelay: 3000,
    heartbeatInterval: 25000,
    connectionTimeout: 10000
  },

  // 轮询配置
  polling: {
    enabled: true,
    fallbackDelay: 10000,

    // 轮询间隔（毫秒）
    intervals: {
      high: 5000,      // 高频：5秒
      medium: 10000,   // 中频：10秒
      low: 30000       // 低频：30秒
    },

    // 页面不可见时的优化
    backgroundMultiplier: 2,  // 后台时间隔翻倍

    // 智能降频：连续N次数据无变化时降低频率
    adaptivePolling: {
      enabled: true,
      unchangedThreshold: 3,    // 3次无变化
      maxInterval: 60000        // 最长60秒
    }
  },

  // 调试选项
  debug: {
    forcePolling: false,        // 强制轮询模式
    logConnections: true,       // 记录连接日志
    logPolling: false           // 记录轮询日志
  }
}
```

### 4.2 实时数据适配器

**新建文件**: `frontend/src/utils/realtimeDataAdapter.js`

```javascript
/**
 * 实时数据适配器
 * Realtime Data Adapter
 *
 * 统一WebSocket和HTTP轮询的数据获取接口
 */
import wsClient from './websocket'
import { REALTIME_CONFIG, POLLING_STRATEGIES } from '@/config/realtime'
import { monitoringAPI, strategyAPI, signalAPI, systemAPI } from '@/api'
import axios from 'axios'

class RealtimeDataAdapter {
  constructor() {
    this.mode = 'websocket'  // 'websocket' | 'polling'
    this.timers = {
      high: null,
      medium: null,
      low: null
    }
    this.currentPage = 'dashboard'
    this.isConnected = false
    this.wsRetryCount = 0
    this.lastSignalId = 0

    // 数据变化���测（用于智能降频）
    this.dataHashes = {
      monitoring: null,
      strategies: null,
      signals: null,
      capacity: null
    }
    this.unchangedCounts = {
      high: 0,
      medium: 0,
      low: 0
    }

    // 回调函数
    this.callbacks = {
      onData: null,
      onModeChange: null,
      onError: null
    }
  }

  /**
   * 连接（优先WebSocket）
   */
  async connect(token, page = 'dashboard') {
    this.currentPage = page

    if (REALTIME_CONFIG.debug.forcePolling) {
      console.log('[Realtime] Force polling mode enabled')
      this.fallbackToPolling()
      return
    }

    if (!REALTIME_CONFIG.websocket.enabled) {
      this.fallbackToPolling()
      return
    }

    try {
      await this.tryWebSocket(token)
    } catch (error) {
      console.warn('[Realtime] WebSocket failed, fallback to polling:', error)
      this.fallbackToPolling()
    }
  }

  /**
   * 尝试WebSocket连接
   */
  async tryWebSocket(token) {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error('WebSocket connection timeout'))
      }, REALTIME_CONFIG.websocket.connectionTimeout)

      wsClient.on('open', () => {
        clearTimeout(timeout)
        this.mode = 'websocket'
        this.isConnected = true
        this.wsRetryCount = 0

        console.log('[Realtime] WebSocket connected')
        this.callbacks.onModeChange?.('websocket')
        resolve()
      })

      wsClient.on('connected', (data) => {
        clearTimeout(timeout)
        console.log('[Realtime] WebSocket ready')

        // 订阅当前页面需要的主题
        this.subscribeTopics()
        resolve()
      })

      wsClient.on('close', (event) => {
        clearTimeout(timeout)
        this.isConnected = false

        if (event.code !== 1000 && this.wsRetryCount < REALTIME_CONFIG.websocket.retryAttempts) {
          // 非正常关闭，重试
          this.wsRetryCount++
          console.log(`[Realtime] Retry WebSocket (${this.wsRetryCount}/${REALTIME_CONFIG.websocket.retryAttempts})`)

          setTimeout(() => {
            this.tryWebSocket(token).catch(() => {
              if (this.wsRetryCount >= REALTIME_CONFIG.websocket.retryAttempts) {
                this.fallbackToPolling()
              }
            })
          }, REALTIME_CONFIG.websocket.retryDelay)
        } else if (this.wsRetryCount >= REALTIME_CONFIG.websocket.retryAttempts) {
          reject(new Error('Max retry attempts reached'))
        }
      })

      wsClient.on('error', (error) => {
        clearTimeout(timeout)
        console.error('[Realtime] WebSocket error:', error)
        this.callbacks.onError?.(error)
        reject(error)
      })

      wsClient.on('data', (message) => {
        this.callbacks.onData?.(message)
      })

      // 开始连接
      wsClient.connect(token)
    })
  }

  /**
   * 订阅WebSocket主题
   */
  subscribeTopics() {
    const strategy = POLLING_STRATEGIES[this.currentPage] || POLLING_STRATEGIES.dashboard
    const allTopics = [...strategy.high, ...strategy.medium, ...strategy.low]

    allTopics.forEach(topic => {
      wsClient.subscribe(topic)
    })
  }

  /**
   * 降级到轮询模式
   */
  fallbackToPolling() {
    console.log('[Realtime] Switching to polling mode')

    this.mode = 'polling'
    this.isConnected = false

    // 断开WebSocket
    if (wsClient.isConnected) {
      wsClient.disconnect()
    }

    // 启动轮询
    this.startPolling()

    this.callbacks.onModeChange?.('polling')
  }

  /**
   * 启动轮询
   */
  startPolling(page) {
    if (page) {
      this.currentPage = page
    }

    this.stopPolling()

    const strategy = POLLING_STRATEGIES[this.currentPage] || POLLING_STRATEGIES.dashboard

    // 高频轮询
    if (strategy.high.length > 0) {
      this.startFrequencyPolling('high', strategy.high, REALTIME_CONFIG.polling.intervals.high)
    }

    // 中频轮询
    if (strategy.medium.length > 0) {
      this.startFrequencyPolling('medium', strategy.medium, REALTIME_CONFIG.polling.intervals.medium)
    }

    // 低频轮询
    if (strategy.low.length > 0) {
      this.startFrequencyPolling('low', strategy.low, REALTIME_CONFIG.polling.intervals.low)
    }

    // 立即执行一次
    if (strategy.high.length > 0) this.fetchBatch(strategy.high)
    if (strategy.medium.length > 0) this.fetchBatch(strategy.medium)
    if (strategy.low.length > 0) this.fetchBatch(strategy.low)
  }

  /**
   * 启动特定频率的轮询
   */
  startFrequencyPolling(frequency, topics, baseInterval) {
    let interval = baseInterval

    // 页面不可见时降低频率
    if (document.hidden) {
      interval *= REALTIME_CONFIG.polling.backgroundMultiplier
    }

    this.timers[frequency] = setInterval(() => {
      // 检查页面可见性
      if (document.hidden) {
        return  // 后台时跳过
      }

      this.fetchBatch(topics, frequency)
    }, interval)
  }

  /**
   * 批量获取数据
   */
  async fetchBatch(topics, frequency = null) {
    if (REALTIME_CONFIG.debug.logPolling) {
      console.log('[Realtime] Polling:', topics)
    }

    try {
      const params = {
        topics: topics.join(',')
      }

      // 信号增量查询
      if (topics.includes('signals') && this.lastSignalId > 0) {
        params.last_signal_id = this.lastSignalId
      }

      const response = await axios.get('/api/v1/realtime/batch', { params })

      if (response.data.success) {
        const data = response.data.data

        // 更新最后信号ID
        if (data.signals) {
          this.lastSignalId = data.signals.last_id || this.lastSignalId
        }

        // 智能降频检测
        if (frequency && REALTIME_CONFIG.polling.adaptivePolling.enabled) {
          this.detectDataChange(data, frequency)
        }

        // 触发数据回调
        topics.forEach(topic => {
          if (data[topic]) {
            this.callbacks.onData?.({
              type: 'data',
              topic: topic,
              data: data[topic],
              timestamp: data[topic].timestamp
            })
          }
        })
      }
    } catch (error) {
      console.error('[Realtime] Polling error:', error)
      this.callbacks.onError?.(error)
    }
  }

  /**
   * 检测数据变化（智能降频）
   */
  detectDataChange(data, frequency) {
    const config = REALTIME_CONFIG.polling.adaptivePolling
    let hasChange = false

    Object.keys(data).forEach(topic => {
      const hash = JSON.stringify(data[topic])
      if (this.dataHashes[topic] !== hash) {
        hasChange = true
        this.dataHashes[topic] = hash
      }
    })

    if (!hasChange) {
      this.unchangedCounts[frequency]++

      // 连续N次无变化，降低频率
      if (this.unchangedCounts[frequency] >= config.unchangedThreshold) {
        const timer = this.timers[frequency]
        if (timer) {
          const currentInterval = timer._idleTimeout || REALTIME_CONFIG.polling.intervals[frequency]
          const newInterval = Math.min(currentInterval * 1.5, config.maxInterval)

          if (newInterval !== currentInterval) {
            console.log(`[Realtime] Adaptive polling: ${frequency} ${currentInterval}ms -> ${newInterval}ms`)
            clearInterval(timer)

            const strategy = POLLING_STRATEGIES[this.currentPage]
            const topics = strategy[frequency]
            this.startFrequencyPolling(frequency, topics, newInterval)
          }
        }
      }
    } else {
      this.unchangedCounts[frequency] = 0
    }
  }

  /**
   * 停止轮询
   */
  stopPolling() {
    Object.values(this.timers).forEach(timer => {
      if (timer) clearInterval(timer)
    })
    this.timers = { high: null, medium: null, low: null }
  }

  /**
   * 断开连接
   */
  disconnect() {
    if (this.mode === 'websocket') {
      wsClient.disconnect()
    } else {
      this.stopPolling()
    }

    this.isConnected = false
  }

  /**
   * 切换页面
   */
  switchPage(page) {
    if (this.currentPage === page) return

    this.currentPage = page

    if (this.mode === 'websocket') {
      // TODO: 取消订阅旧主题，订阅新主题
      this.subscribeTopics()
    } else {
      // 重启轮询
      this.startPolling(page)
    }
  }

  /**
   * 手动重试WebSocket
   */
  async retryWebSocket(token) {
    if (this.mode === 'websocket') {
      console.log('[Realtime] Already in WebSocket mode')
      return
    }

    console.log('[Realtime] Manual retry WebSocket')
    this.stopPolling()
    this.wsRetryCount = 0

    try {
      await this.tryWebSocket(token)
    } catch (error) {
      console.error('[Realtime] Retry failed:', error)
      this.fallbackToPolling()
      throw error
    }
  }

  /**
   * 注册回调
   */
  on(event, callback) {
    if (event === 'data') this.callbacks.onData = callback
    if (event === 'modeChange') this.callbacks.onModeChange = callback
    if (event === 'error') this.callbacks.onError = callback
  }

  /**
   * 获取当前状态
   */
  getStatus() {
    return {
      mode: this.mode,
      isConnected: this.isConnected,
      currentPage: this.currentPage,
      wsRetryCount: this.wsRetryCount
    }
  }
}

// 全局单例
const realtimeAdapter = new RealtimeDataAdapter()

// 页面可见性监听
document.addEventListener('visibilitychange', () => {
  if (realtimeAdapter.mode === 'polling') {
    if (document.hidden) {
      console.log('[Realtime] Page hidden, reducing polling frequency')
      // 降低频率的逻辑在startFrequencyPolling中处理
    } else {
      console.log('[Realtime] Page visible, restoring polling frequency')
      realtimeAdapter.startPolling()
    }
  }
})

export default realtimeAdapter
```

---

## 5. 优化后的性能对比

### 5.1 请求量对比

| 场景 | 原方案 | 优化方案 | 降低 |
|------|--------|---------|------|
| Dashboard页面 | 32次/分钟 | **20次/分钟** | 37.5% |
| Strategies页面 | 32次/分钟 | **12次/分钟** | 62.5% |
| Signals页面 | 32次/分钟 | **18次/分钟** | 43.8% |
| Settings页面 | 32次/分钟 | **2次/分钟** | 93.8% |

**平均优化**: **53% 请求量降低**

### 5.2 批量API优势

1. **单个请求合并**：
   - 原：4个独立HTTP请求
   - 新：1个批量请求
   - 减少3次TCP连接建立

2. **数据库查询优化**：
   - 原：4个独立事务
   - 新：1个事务批量查询
   - 减少数据库连接开销

3. **网络传输优化**：
   - HTTP头复用
   - 压缩效率提升

### 5.3 智能优化特性

#### 页面可见性优化
```javascript
// 页面隐藏时
if (document.hidden) {
  interval *= 2  // 间隔翻倍：5秒 → 10秒
}
```

#### 自适应轮询
```javascript
// 数据3次无变化时
if (unchangedCount >= 3) {
  interval *= 1.5  // 逐步降低频率：5s → 7.5s → 11.25s ...
  interval = Math.min(interval, 60000)  // 最长60秒
}

// 数据有变化时
if (dataChanged) {
  interval = baseInterval  // 恢复正常间隔
}
```

#### 按页面需求
```javascript
// Dashboard: 全部数据
topics = ['monitoring', 'strategies', 'signals', 'capacity']

// Settings: 仅容量
topics = ['capacity']  // 减少93.8%请求！
```

---

## 6. 修改文件清单

### 6.1 后端（3个文件）

| 文件 | 类型 | 代码量 | 说明 |
|------|------|-------|------|
| `api/v1/realtime.py` | 新建 | ~200行 | 批量查询端点 |
| `main.py` | 修改 | +5行 | 注册路由 |
| `api/v1/signals.py` | 修改 | +10行 | 支持last_id参数 |

### 6.2 前端（5个文件）

| 文件 | 类型 | 代码量 | 说明 |
|------|------|-------|------|
| `config/realtime.js` | 新建 | ~80行 | 配置管理 |
| `utils/realtimeDataAdapter.js` | 新建 | ~400行 | 核心适配器 |
| `stores/websocket.js` | 修改 | +100行 | 集成adapter |
| `stores/user.js` | 修改 | +20行 | 使用adapter |
| `components/ConnectionStatus.vue` | 新建 | ~150行 | 状态指示器 |

### 6.3 设计文档（2个文件）

| 文件 | 修改内容 |
|------|---------|
| `API_DESIGN.md` | 新增3.4节"批量查询与降级机制" |
| `DESIGN.md` | 更新实时通信架构说明 |

---

## 7. 实施计划（优化版）

### Phase 1: 后端批量API（1天）
- [x] 设计批量查询端点
- [ ] 实现 `GET /api/v1/realtime/batch`
- [ ] 优化signals增量查询
- [ ] 单元测试
- [ ] API文档

### Phase 2: 前端配置和适配器（2天）
- [ ] 实现 `config/realtime.js`
- [ ] 实现 `realtimeDataAdapter.js`
- [ ] 页面可见性优化
- [ ] 智能降频逻辑
- [ ] 单元测试

### Phase 3: Store集成（1天）
- [ ] 改造 `stores/websocket.js`
- [ ] 更新 `stores/user.js`
- [ ] 各页面集成adapter
- [ ] 数据流测试

### Phase 4: UI组件（0.5天）
- [ ] 连接状态指示器
- [ ] 降级提示组件
- [ ] 手动重试按钮

### Phase 5: 测试和优化（1天）
- [ ] 功能测试
- [ ] 性能测试（请求量监控）
- [ ] 压力测试
- [ ] 文档完善

### Phase 6: 上线监控（0.5天）
- [ ] 灰度发布
- [ ] 监控指标
- [ ] 收集反馈

**总工期**: 6天（含优化和测试）

---

## 8. 监控指标

### 8.1 关键指标

上线后需要监控：

1. **连接模式分布**：
   - WebSocket使用率：目标 >80%
   - 轮询使用率：<20%

2. **API请求量**：
   - 批量端点调用次数：Dashboard ~12次/分钟
   - 平均响应时间：<200ms
   - 错误率：<0.1%

3. **降级触发率**：
   - 自动降级次数：<5%登录会话
   - 手动重试成功率：>90%

4. **性能影响**：
   - 服务器CPU：增加<5%
   - 内存占用：增加<50MB
   - 数据库连接：无明显增加

### 8.2 告警规则

```yaml
- alert: PollingModeHighUsage
  expr: polling_mode_ratio > 0.3
  for: 10m
  annotations:
    summary: "轮询模式使用率过高 (>30%)"
    description: "可能WebSocket配置有问题"

- alert: BatchAPISlowResponse
  expr: batch_api_p95_latency > 500ms
  for: 5m
  annotations:
    summary: "批量API响应慢"
    description: "P95延迟 >500ms，需优化"

- alert: BatchAPIHighError
  expr: batch_api_error_rate > 0.05
  for: 5m
  annotations:
    summary: "批量API错误率高 (>5%)"
```

---

## 9. 用户文档

### 9.1 连接状态说明

**状态指示器**（页面右上角）：

```
🟢 实时推送 (WebSocket)
   ↓ 最佳体验，数据延迟<100ms

🟡 轮询模式 (5-30秒刷新)
   ↓ 降级模式，数据延迟3-30秒
   ↓ 点击可重试WebSocket

🔴 离线
   ↓ 无网络连接
```

### 9.2 常见问题

**Q: 为什么会切换到轮询模式？**
A: 可能原因：
- 网络环境不支持WebSocket（公司防火墙）
- 代理服务器配置问题
- Token过期

**Q: 轮询模式会影响使用吗？**
A: 影响��小：
- Dashboard数据每5秒刷新
- 信号数据每10秒刷新
- 仍然可以正常使用所有功能

**Q: 如何切换回WebSocket？**
A: 点击状态指示器，选择"重试WebSocket"

**Q: 可以强制使用某种模式吗？**
A: 可以在设置页面选择：
- 自动选择（推荐）
- 仅WebSocket
- 仅轮询

---

## 10. 总结

### 10.1 核心优化

✅ **请求量降低53%**：通过批量API合并
✅ **按页面优化**：不同页面不同策略
✅ **智能降频**：数据无变化时自动降低频率
✅ **页面可见性**：后台时降低刷新频率

### 10.2 预期效果

| 指标 | 优化前 | 优化后 | 改善 |
|------|--------|--------|------|
| API请求/分钟 | 32次 | 12-20次 | ↓ 53% |
| 服务器负载 | 基准 | +3% | 可接受 |
| 数据延迟 | 5-30秒 | 5-30秒 | 保持 |
| 用户体验 | ⭐⭐⭐ | ⭐⭐⭐⭐ | 提升 |

### 10.3 下一步

**请确认**：

1. ✅ 批量API设计是否合理？
2. ✅ 按页面轮询策略是否满足需求？
3. ✅ 智能降频是否需要？
4. ✅ 6天工期是否可接受？

**确认后立即开始实施！** 🚀
