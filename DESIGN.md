# BTC Watcher 系统设计文档

## 1. 系统总体架构

### 1.1 架构概览
```
远程价格服务器                     本地BTC Watcher系统
┌─────────────────┐             ┌─────────────────────────────────────────┐
│  Price Service  │────────────▶│              Web UI                     │
│  (数据采集)      │   HTTP API  │           (Vue.js + TS)                 │
└─────────────────┘             └─────────────────────────────────────────┘
│                                        │                   │
├─ PostgreSQL                            │ HTTP/WebSocket    │
├─ Redis Cache                           │                   │
└─ Export API                            ▼                   ▼
                              ┌─────────────────┐  ┌─────────────────┐
                              │  Backend API    │  │  Notification   │
                              │   (FastAPI)     │  │    Service      │
                              └─────────────────┘  └─────────────────┘
                                        │                   │
                              ┌─────────┼─────────┐         │
                              │         │         │         │
                              ▼         ▼         ▼         ▼
                    ┌─────────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
                    │ Price Data  │ │FreqTrade│ │  Sync   │ │ Redis   │
                    │ PostgreSQL  │ │Strategies│ │Service │ │ Cache   │
                    └─────────────┘ └─────────┘ └─────────┘ └─────────┘
```

### 1.2 核心组件

#### 1.2.1 前端 Web UI
- **技术选型**: Vue.js 3 + TypeScript + Vite
- **UI框架**: Element Plus / Ant Design Vue
- **图表组件**: TradingView Lightweight Charts / ECharts
- **状态管理**: Pinia
- **HTTP客户端**: Axios

#### 1.2.2 后端 API 服务
- **技术选型**: FastAPI + Python 3.11
- **异步框架**: async/await + uvicorn
- **API文档**: 自动生成OpenAPI/Swagger文档
- **身份认证**: JWT Token认证

#### 1.2.3 价格数据服务 (新增)
- **数据采集**: 多交易所WebSocket实时数据收集
- **数据存储**: 高性能时间序列数据存储
- **批量处理**: 异步批量写入，Redis缓存加速
- **API导出**: RESTful API提供历史数据导出

#### 1.2.4 数据同步服务 (新增)
- **增量同步**: 基于时间戳的智能增量同步
- **多源支持**: 支持多个远程数据源节点
- **状态追踪**: 详细的同步状态监控和管理
- **容错机制**: 自动重连和失败重试

#### 1.2.5 数据存储层
- **主数据库**: PostgreSQL 15+
  - 策略配置、信号记录、用户数据
  - 价格数据（分区表优化）
  - 同步状态和节点配置
- **缓存层**: Redis 7+
  - 实时价格数据缓存
  - 会话缓存和消息队列
  - 热点数据加速访问

#### 1.2.6 FreqTrade 集成
- **版本**: FreqTrade 2024.x
- **运行模式**: Dry-run模式（不执行实际交易）
- **通信方式**: 信号文件输出 + API监控
- **策略存储**: 独立Python模块，支持热更新

#### 1.2.7 通知服务
- **架构**: 独立微服务
- **消息队列**: Redis/File Queue
- **通知渠道**: 多渠道适配器模式（微信/Telegram/邮件等）

## 2. 详细设计

### 2.1 数据库设计

#### 2.1.1 核心业务表
```sql
-- 交易所配置表 (新增)
CREATE TABLE exchanges (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    api_base_url VARCHAR(255) NOT NULL,
    websocket_url VARCHAR(255),
    is_active BOOLEAN DEFAULT true
);

-- 交易对配置表 (更新)
CREATE TABLE trading_pairs (
    id SERIAL PRIMARY KEY,
    exchange_id INTEGER REFERENCES exchanges(id),
    symbol VARCHAR(20) NOT NULL,
    base_asset VARCHAR(10) NOT NULL,
    quote_asset VARCHAR(10) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(exchange_id, symbol)
);

-- 策略配置表
CREATE TABLE strategies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    config_json JSONB NOT NULL,
    status VARCHAR(20) DEFAULT 'stopped',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 2.1.2 价格数据表 (新增)
```sql
-- 实时价格数据表（支持分区）
CREATE TABLE price_tickers (
    id BIGSERIAL PRIMARY KEY,
    trading_pair_id INTEGER REFERENCES trading_pairs(id),
    price DECIMAL(20,8) NOT NULL,
    bid_price DECIMAL(20,8),
    ask_price DECIMAL(20,8),
    volume_24h DECIMAL(30,8),
    price_change_percent_24h DECIMAL(10,4),
    high_24h DECIMAL(20,8),
    low_24h DECIMAL(20,8),
    timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) PARTITION BY RANGE (timestamp);

-- K线数据表（支持分区）
CREATE TABLE klines (
    id BIGSERIAL PRIMARY KEY,
    trading_pair_id INTEGER REFERENCES trading_pairs(id),
    timeframe VARCHAR(10) NOT NULL,
    open_time TIMESTAMP NOT NULL,
    close_time TIMESTAMP NOT NULL,
    open_price DECIMAL(20,8) NOT NULL,
    high_price DECIMAL(20,8) NOT NULL,
    low_price DECIMAL(20,8) NOT NULL,
    close_price DECIMAL(20,8) NOT NULL,
    volume DECIMAL(30,8) NOT NULL,
    quote_volume DECIMAL(30,8),
    trade_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(trading_pair_id, timeframe, open_time)
) PARTITION BY LIST (timeframe);
```

#### 2.1.3 数据同步表 (新增)
```sql
-- 数据源节点配置表
CREATE TABLE data_source_nodes (
    id SERIAL PRIMARY KEY,
    node_id VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    api_endpoint VARCHAR(255) NOT NULL,
    api_key VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    sync_interval_minutes INTEGER DEFAULT 5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 数据同步状态表
CREATE TABLE sync_status (
    id SERIAL PRIMARY KEY,
    source_node_id VARCHAR(100) NOT NULL,
    trading_pair_id INTEGER REFERENCES trading_pairs(id),
    data_type VARCHAR(20) NOT NULL, -- ticker, kline_1m, kline_5m, etc.
    last_sync_timestamp TIMESTAMP,
    sync_status VARCHAR(20) DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_node_id, trading_pair_id, data_type)
);
```

#### 2.1.4 信号和通知表
```sql
-- 信号记录表
CREATE TABLE signals (
    id SERIAL PRIMARY KEY,
    strategy_id INTEGER REFERENCES strategies(id),
    trading_pair_id INTEGER REFERENCES trading_pairs(id),
    signal_type VARCHAR(20) NOT NULL,
    price DECIMAL(20,8) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 通知配置表
CREATE TABLE notification_configs (
    id SERIAL PRIMARY KEY,
    channel_type VARCHAR(20) NOT NULL,
    config_json JSONB NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 通知记录表
CREATE TABLE notification_logs (
    id SERIAL PRIMARY KEY,
    signal_id INTEGER REFERENCES signals(id),
    channel_type VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    error_message TEXT,
    sent_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2.2 API设计

#### 2.2.1 核心业务API
```python
# 交易对管理
GET    /api/v1/exchanges                # 获取交易所列表
GET    /api/v1/trading-pairs            # 获取交易对列表
POST   /api/v1/trading-pairs            # 创建交易对
PUT    /api/v1/trading-pairs/{id}       # 更新交易对
DELETE /api/v1/trading-pairs/{id}       # 删除交易对

# 策略管理
GET    /api/v1/strategies               # 获取策略列表
POST   /api/v1/strategies               # 创建策略
PUT    /api/v1/strategies/{id}          # 更新策略
DELETE /api/v1/strategies/{id}          # 删除策略
POST   /api/v1/strategies/{id}/start    # 启动策略
POST   /api/v1/strategies/{id}/stop     # 停止策略

# 信号查询
GET    /api/v1/signals                  # 获取信号列表
GET    /api/v1/signals/recent           # 获取最近信号
```

#### 2.2.2 价格数据API (新增)
```python
# 实时价格数据
GET    /api/v1/prices/tickers          # 获取实时价格
GET    /api/v1/prices/ticker/{symbol}  # 获取单个ticker
GET    /api/v1/prices/klines           # 获取K线数据
GET    /api/v1/prices/history          # 获取历史价格数据

# 数据导出API (用于数据同步)
GET    /api/v1/data/tickers/export     # 导出ticker数据
GET    /api/v1/data/klines/export      # 导出K线数据
GET    /api/v1/data/sync/status        # 获取数据同步状态
```

#### 2.2.3 数据同步API (新增)
```python
# 同步节点管理
GET    /api/v1/sync/nodes              # 获取同步节点列表
POST   /api/v1/sync/nodes              # 创建同步节点
PUT    /api/v1/sync/nodes/{id}         # 更新同步节点
DELETE /api/v1/sync/nodes/{id}         # 删除同步节点

# 同步操作
POST   /api/v1/sync/nodes/{id}/test    # 测试节点连接
POST   /api/v1/sync/nodes/{id}/sync    # 手动触发同步
GET    /api/v1/sync/status             # 获取同步状态
```

#### 2.2.4 通知管理API
```python
# 通知配置
GET    /api/v1/notifications/config    # 获取通知配置
PUT    /api/v1/notifications/config    # 更新通知配置
POST   /api/v1/notifications/test      # 测试通知发送
GET    /api/v1/notifications/logs      # 获取通知日志
```

#### 2.2.5 WebSocket接口
```python
# 实时数据推送
WS     /ws/prices                      # 价格数据推送
WS     /ws/signals                     # 信号实时推送
WS     /ws/strategy-status             # 策略状态推送
WS     /ws/sync-status                 # 同步状态推送
```

### 2.3 FreqTrade 集成方案

#### 2.3.1 策略基类设计
```python
from freqtrade.strategy import IStrategy
import json
from datetime import datetime

class BaseMonitorStrategy(IStrategy):
    """监控策略基类"""

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self.signal_file = config.get('signal_file', '/app/signals/signals.json')

    def emit_signal(self, signal_type: str, pair: str, price: float, metadata: dict = None):
        """发出信号"""
        signal = {
            'timestamp': datetime.utcnow().isoformat(),
            'strategy': self.__class__.__name__,
            'signal_type': signal_type,
            'pair': pair,
            'price': price,
            'metadata': metadata or {}
        }

        # 写入信号文件，由主应用监控
        with open(self.signal_file, 'a') as f:
            f.write(json.dumps(signal) + '\n')
```

#### 2.3.2 策略管理器
```python
import subprocess
import os
from typing import Dict, List

class StrategyManager:
    """策略进程管理器"""

    def __init__(self):
        self.processes: Dict[int, subprocess.Popen] = {}
        self.config_dir = '/app/strategies/configs'

    def start_strategy(self, strategy_id: int, strategy_config: dict) -> bool:
        """启动策略进程"""
        if strategy_id in self.processes:
            return False

        config_file = f"{self.config_dir}/strategy_{strategy_id}.json"
        with open(config_file, 'w') as f:
            json.dump(strategy_config, f)

        cmd = [
            'freqtrade', 'trade',
            '--config', config_file,
            '--strategy', strategy_config['strategy_class']
        ]

        process = subprocess.Popen(cmd)
        self.processes[strategy_id] = process
        return True

    def stop_strategy(self, strategy_id: int) -> bool:
        """停止策略进程"""
        if strategy_id not in self.processes:
            return False

        process = self.processes[strategy_id]
        process.terminate()
        del self.processes[strategy_id]
        return True
```

#### 2.3.3 策略日志心跳监控服务

**设计目标**:
- 实时监控FreqTrade策略进程的日志输出
- 检测心跳日志，判断策略进程是否正常运行
- 心跳超时时发送告警通知
- 支持配置自动重启（可选功能，默认开启）
- 记录心跳异常和重启历史

**心跳日志格式**:
```
2025-11-04 21:19:01,013 - freqtrade.worker - INFO - Bot heartbeat. PID=872423, version='2025.9.1', state='RUNNING'
```

**日志监控服务设计**:

```python
import asyncio
import re
from datetime import datetime, timedelta
from typing import Dict, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class StrategyHeartbeatMonitor:
    """策略心跳监控服务"""

    # 心跳日志正则表达式
    HEARTBEAT_PATTERN = re.compile(
        r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ - freqtrade\.worker - INFO - '
        r'Bot heartbeat\. PID=(\d+), version=\'([^\']+)\', state=\'(\w+)\''
    )

    def __init__(
        self,
        strategy_manager,
        notify_hub,
        check_interval: int = 30,  # 检查间隔（秒）
        default_timeout: int = 300  # 默认超时时间（秒，5分钟）
    ):
        """
        初始化心跳监控服务

        Args:
            strategy_manager: 策略管理器实例
            notify_hub: 通知中心实例
            check_interval: 心跳检查间隔（秒）
            default_timeout: 默认心跳超时时间（秒）
        """
        self.strategy_manager = strategy_manager
        self.notify_hub = notify_hub
        self.check_interval = check_interval
        self.default_timeout = default_timeout

        # 存储每个策略的心跳状态
        self.heartbeat_status: Dict[int, HeartbeatStatus] = {}

        # 监控任务
        self.monitor_task: Optional[asyncio.Task] = None
        self.running = False

    async def start(self):
        """启动心跳监控服务"""
        if self.running:
            logger.warning("Heartbeat monitor already running")
            return

        self.running = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Heartbeat monitor started")

    async def stop(self):
        """停止心跳监控服务"""
        self.running = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Heartbeat monitor stopped")

    def register_strategy(
        self,
        strategy_id: int,
        log_file_path: str,
        timeout: Optional[int] = None
    ):
        """
        注册需要监控的策略

        Args:
            strategy_id: 策略ID
            log_file_path: 策略日志文件路径
            timeout: 心跳超时时间（秒），None则使用默认值
        """
        self.heartbeat_status[strategy_id] = HeartbeatStatus(
            strategy_id=strategy_id,
            log_file_path=log_file_path,
            timeout=timeout or self.default_timeout
        )
        logger.info(f"Registered strategy {strategy_id} for heartbeat monitoring")

    def unregister_strategy(self, strategy_id: int):
        """取消注册策略"""
        if strategy_id in self.heartbeat_status:
            del self.heartbeat_status[strategy_id]
            logger.info(f"Unregistered strategy {strategy_id} from heartbeat monitoring")

    def update_timeout(self, strategy_id: int, timeout: int):
        """更新策略的心跳超时配置"""
        if strategy_id in self.heartbeat_status:
            self.heartbeat_status[strategy_id].timeout = timeout
            logger.info(f"Updated timeout for strategy {strategy_id}: {timeout}s")

    async def _monitor_loop(self):
        """心跳监控主循环"""
        while self.running:
            try:
                await self._check_all_strategies()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in heartbeat monitor loop: {e}", exc_info=True)
                await asyncio.sleep(self.check_interval)

    async def _check_all_strategies(self):
        """检查所有策略的心跳状态"""
        for strategy_id, status in list(self.heartbeat_status.items()):
            try:
                await self._check_strategy_heartbeat(strategy_id, status)
            except Exception as e:
                logger.error(
                    f"Error checking heartbeat for strategy {strategy_id}: {e}",
                    exc_info=True
                )

    async def _check_strategy_heartbeat(
        self,
        strategy_id: int,
        status: 'HeartbeatStatus'
    ):
        """检查单个策略的心跳状态"""
        # 读取日志文件，查找最新的心跳记录
        latest_heartbeat = await self._read_latest_heartbeat(status.log_file_path)

        if latest_heartbeat:
            # 更新心跳时间
            status.last_heartbeat_time = latest_heartbeat['timestamp']
            status.last_pid = latest_heartbeat['pid']
            status.last_version = latest_heartbeat['version']
            status.last_state = latest_heartbeat['state']
            status.consecutive_failures = 0

            # 检查心跳是否超时
            time_since_heartbeat = (datetime.now() - status.last_heartbeat_time).total_seconds()

            if time_since_heartbeat > status.timeout:
                # 心跳超时
                await self._handle_heartbeat_timeout(strategy_id, status, time_since_heartbeat)
            else:
                # 心跳正常
                if status.is_abnormal:
                    # 从异常状态恢复
                    await self._handle_heartbeat_recovered(strategy_id, status)
        else:
            # 没有读取到心跳记录
            if status.last_heartbeat_time:
                time_since_heartbeat = (datetime.now() - status.last_heartbeat_time).total_seconds()
                if time_since_heartbeat > status.timeout:
                    await self._handle_heartbeat_timeout(strategy_id, status, time_since_heartbeat)

    async def _read_latest_heartbeat(self, log_file_path: str) -> Optional[dict]:
        """
        读取日志文件中最新的心跳记录

        Returns:
            心跳信息字典，包含 timestamp, pid, version, state
        """
        try:
            log_path = Path(log_file_path)
            if not log_path.exists():
                return None

            # 读取日志文件最后N行（避免读取整个大文件）
            last_lines = await self._read_last_lines(log_path, lines=100)

            # 从后往前查找心跳日志
            for line in reversed(last_lines):
                match = self.HEARTBEAT_PATTERN.search(line)
                if match:
                    timestamp_str, pid, version, state = match.groups()
                    return {
                        'timestamp': datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S'),
                        'pid': int(pid),
                        'version': version,
                        'state': state
                    }

            return None

        except Exception as e:
            logger.error(f"Error reading heartbeat from {log_file_path}: {e}")
            return None

    async def _read_last_lines(self, file_path: Path, lines: int = 100) -> list:
        """读取文件的最后N行"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                # 使用简单的方法读取最后N行
                return f.readlines()[-lines:]
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return []

    async def _handle_heartbeat_timeout(
        self,
        strategy_id: int,
        status: 'HeartbeatStatus',
        time_since_heartbeat: float
    ):
        """处理心跳超时"""
        status.consecutive_failures += 1
        status.is_abnormal = True

        logger.warning(
            f"Strategy {strategy_id} heartbeat timeout: "
            f"{time_since_heartbeat:.0f}s since last heartbeat "
            f"(timeout: {status.timeout}s, failures: {status.consecutive_failures})"
        )

        # 发送告警通知
        await self.notify_hub.notify(
            user_id=1,  # 管理员
            title=f"🚨 策略心跳超时告警",
            message=(
                f"策略 #{strategy_id} 心跳超时\n"
                f"最后心跳时间: {status.last_heartbeat_time.strftime('%Y-%m-%d %H:%M:%S') if status.last_heartbeat_time else '无'}\n"
                f"超时时长: {time_since_heartbeat:.0f}秒\n"
                f"配置超时: {status.timeout}秒\n"
                f"连续失败次数: {status.consecutive_failures}"
            ),
            notification_type="alert",
            priority="P2",  # 高优先级
            metadata={
                "strategy_id": strategy_id,
                "time_since_heartbeat": time_since_heartbeat,
                "timeout": status.timeout,
                "consecutive_failures": status.consecutive_failures
            },
            strategy_id=strategy_id
        )

        # 尝试重启策略
        try:
            logger.info(f"Attempting to restart strategy {strategy_id}")
            success = await self.strategy_manager.restart_strategy(strategy_id)

            if success:
                # 重置心跳状态
                status.last_restart_time = datetime.now()
                status.restart_count += 1

                logger.info(f"Strategy {strategy_id} restarted successfully")

                # 发送重启成功通知
                await self.notify_hub.notify(
                    user_id=1,
                    title=f"✅ 策略已自动重启",
                    message=(
                        f"策略 #{strategy_id} 因心跳超时已自动重启\n"
                        f"重启次数: {status.restart_count}\n"
                        f"重启时间: {status.last_restart_time.strftime('%Y-%m-%d %H:%M:%S')}"
                    ),
                    notification_type="info",
                    priority="P1",
                    metadata={
                        "strategy_id": strategy_id,
                        "restart_count": status.restart_count
                    },
                    strategy_id=strategy_id
                )
            else:
                logger.error(f"Failed to restart strategy {strategy_id}")

                # 发送重启失败通知
                await self.notify_hub.notify(
                    user_id=1,
                    title=f"❌ 策略重启失败",
                    message=f"策略 #{strategy_id} 自动重启失败，请手动检查",
                    notification_type="alert",
                    priority="P2",
                    metadata={"strategy_id": strategy_id},
                    strategy_id=strategy_id
                )

        except Exception as e:
            logger.error(f"Error restarting strategy {strategy_id}: {e}", exc_info=True)

    async def _handle_heartbeat_recovered(self, strategy_id: int, status: 'HeartbeatStatus'):
        """处理心跳恢复正常"""
        status.is_abnormal = False

        logger.info(f"Strategy {strategy_id} heartbeat recovered")

        # 发送恢复通知
        await self.notify_hub.notify(
            user_id=1,
            title=f"✅ 策略心跳恢复正常",
            message=(
                f"策略 #{strategy_id} 心跳已恢复正常\n"
                f"最后心跳: {status.last_heartbeat_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"状态: {status.last_state}"
            ),
            notification_type="info",
            priority="P1",
            metadata={
                "strategy_id": strategy_id,
                "last_heartbeat": status.last_heartbeat_time.isoformat()
            },
            strategy_id=strategy_id
        )

    def get_heartbeat_status(self, strategy_id: int) -> Optional[dict]:
        """获取策略的心跳状态"""
        if strategy_id not in self.heartbeat_status:
            return None

        status = self.heartbeat_status[strategy_id]
        return {
            "strategy_id": strategy_id,
            "last_heartbeat_time": status.last_heartbeat_time.isoformat() if status.last_heartbeat_time else None,
            "last_pid": status.last_pid,
            "last_version": status.last_version,
            "last_state": status.last_state,
            "timeout": status.timeout,
            "is_abnormal": status.is_abnormal,
            "consecutive_failures": status.consecutive_failures,
            "restart_count": status.restart_count,
            "last_restart_time": status.last_restart_time.isoformat() if status.last_restart_time else None
        }


class HeartbeatStatus:
    """心跳状态数据类"""

    def __init__(self, strategy_id: int, log_file_path: str, timeout: int):
        self.strategy_id = strategy_id
        self.log_file_path = log_file_path
        self.timeout = timeout

        # 心跳状态
        self.last_heartbeat_time: Optional[datetime] = None
        self.last_pid: Optional[int] = None
        self.last_version: Optional[str] = None
        self.last_state: Optional[str] = None

        # 异常状态
        self.is_abnormal = False
        self.consecutive_failures = 0

        # 重启记录
        self.restart_count = 0
        self.last_restart_time: Optional[datetime] = None
```

**数据库表设计** (添加到现有数据库设计中):

```sql
-- 策略心跳监控配置表
CREATE TABLE strategy_heartbeat_configs (
    id SERIAL PRIMARY KEY,
    strategy_id INTEGER REFERENCES strategies(id) ON DELETE CASCADE,
    enabled BOOLEAN DEFAULT true,
    timeout_seconds INTEGER DEFAULT 300,
    check_interval_seconds INTEGER DEFAULT 30,
    auto_restart BOOLEAN DEFAULT true,
    max_restart_attempts INTEGER DEFAULT 3,
    restart_cooldown_seconds INTEGER DEFAULT 60,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(strategy_id)
);

-- 策略心跳历史记录表
CREATE TABLE strategy_heartbeat_history (
    id BIGSERIAL PRIMARY KEY,
    strategy_id INTEGER REFERENCES strategies(id) ON DELETE CASCADE,
    heartbeat_time TIMESTAMP NOT NULL,
    pid INTEGER,
    version VARCHAR(50),
    state VARCHAR(20),
    is_timeout BOOLEAN DEFAULT false,
    time_since_last_heartbeat_seconds INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 策略重启历史记录表
CREATE TABLE strategy_restart_history (
    id BIGSERIAL PRIMARY KEY,
    strategy_id INTEGER REFERENCES strategies(id) ON DELETE CASCADE,
    restart_reason VARCHAR(50) NOT NULL,  -- heartbeat_timeout, manual, error
    restart_time TIMESTAMP NOT NULL,
    restart_success BOOLEAN,
    error_message TEXT,
    previous_pid INTEGER,
    new_pid INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX idx_heartbeat_history_strategy_time ON strategy_heartbeat_history(strategy_id, heartbeat_time DESC);
CREATE INDEX idx_restart_history_strategy_time ON strategy_restart_history(strategy_id, restart_time DESC);
```

**使用示例**:

```python
# 初始化心跳监控服务
heartbeat_monitor = StrategyHeartbeatMonitor(
    strategy_manager=strategy_manager,
    notify_hub=notify_hub,
    check_interval=30,  # 每30秒检查一次
    default_timeout=300  # 默认5分钟超时
)

# 启动监控服务
await heartbeat_monitor.start()

# 启动策略时注册心跳监控
strategy_id = 123
log_file_path = f"/app/logs/strategy_{strategy_id}.log"
heartbeat_monitor.register_strategy(
    strategy_id=strategy_id,
    log_file_path=log_file_path,
    timeout=300  # 5分钟超时
)

# 停止策略时取消注册
heartbeat_monitor.unregister_strategy(strategy_id)

# 获取心跳状态
status = heartbeat_monitor.get_heartbeat_status(strategy_id)
```

### 2.4 NotifyHub 通知中心设计

#### 2.4.1 NotifyHub 架构总览

NotifyHub是一个统一的通知管理中心，提供集中式的通知路由、频率控制、优先级管理和多渠道分发功能。

```
业务代码                   NotifyHub核心                    通知渠道
┌──────────┐            ┌─────────────────┐           ┌────────────┐
│ 策略引擎  │───────────▶│                 │──────────▶│  Telegram  │
├──────────┤            │  NotifyHub      │           ├────────────┤
│ 系统监控  │───────────▶│                 │──────────▶│  Discord   │
├──────────┤            │  - 路由规则      │           ├────────────┤
│ 告警模块  │───────────▶│  - 优先级管理   │──────────▶│  企业微信   │
├──────────┤            │  - 频率控制      │           ├────────────┤
│ 数据同步  │───────────▶│  - 时间规则      │──────────▶│   飞书     │
└──────────┘            │  - 批量发送      │           ├────────────┤
                        │  - 模板渲染      │──────────▶│   邮件     │
                        └─────────────────┘           ├────────────┤
                                 │                     │   短信     │
                                 ▼                     └────────────┘
                        ┌─────────────────┐
                        │ 通知历史记录      │
                        │ (PostgreSQL)    │
                        └─────────────────┘
```

**核心特性**：
- ✅ **统一入口**：业务代码只需调用一个API发送通知
- ✅ **智能路由**：根据用户配置自动选择通知渠道
- ✅ **优先级管理**：P0(最高)/P1(中)/P2(低)三级优先级
- ✅ **频率控制**：防止通知轰炸，支持按优先级配置发送间隔
- ✅ **时间规则**：勿扰时段、工作时间、周末模式、假期模式
- ✅ **批量发送**：低优先级通知自动批量合并
- ✅ **模板系统**：支持自定义通知模板
- ✅ **失败重试**：自动重试失败的通知

#### 2.4.2 优先级定义

```python
# 优先级级别定义
P0 = "P0"  # 最低优先级 - 批量发送
P1 = "P1"  # 中等优先级 - 限频发送
P2 = "P2"  # 最高优先级 - 立即发送

# 使用场景示例
优先级映射 = {
    "系统崩溃": P2,
    "策略异常停止": P2,
    "强买入信号(strength>=80%)": P2,

    "中等买入信号(50%<=strength<80%)": P1,
    "策略状态变化": P1,
    "代理连接失败": P1,

    "弱买入信号(strength<50%)": P0,
    "策略心跳": P0,
    "数据同步完成": P0
}
```

#### 2.4.3 通知路由规则引擎

```python
class NotifyRouter:
    """通知路由器 - 根据规则决定通知去向"""

    async def route(self, notification: NotificationMessage) -> List[str]:
        """
        根据通知内容和用户配置决定发送渠道

        Returns:
            List[str]: 应该发送的渠道列表，如 ["telegram", "feishu"]
        """
        channels = []

        # 获取用户的渠道配置
        user_channels = await self._get_user_channel_configs(notification.user_id)

        for channel_config in user_channels:
            # 检查渠道是否启用
            if not channel_config.enabled:
                continue

            # 检查渠道是否支持该优先级
            if notification.priority not in channel_config.supported_priorities:
                continue

            # 检查频率限制
            if not await self._check_rate_limit(channel_config, notification):
                continue

            # 检查时间规则
            if not await self._check_time_rules(channel_config, notification):
                continue

            channels.append(channel_config.channel_type)

        return channels
```

#### 2.4.4 频率控制器

```python
class FrequencyController:
    """频率控制器 - 防止通知轰炸"""

    def __init__(self):
        self.last_send_time = {}  # 记录每个渠道的最后发送时间
        self.p0_batch_buffer = {}  # P0通知批量缓冲区

    async def should_send(
        self,
        user_id: int,
        channel: str,
        priority: str,
        frequency_config: NotificationFrequencyLimit
    ) -> bool:
        """
        判断是否应该发送通知

        规则：
        - P2: 立即发送，无限制
        - P1: 检查最小发送间隔（默认60秒）
        - P0: 加入批量队列，定时批量发送（默认5分钟）
        """
        if priority == "P2":
            return True  # 最高优先级，立即发送

        if priority == "P1":
            # 检查距离上次发送的时间间隔
            last_time = self.last_send_time.get((user_id, channel), 0)
            current_time = time.time()

            if current_time - last_time >= frequency_config.p1_min_interval:
                self.last_send_time[(user_id, channel)] = current_time
                return True
            return False

        if priority == "P0":
            # P0消息加入批量队列
            if frequency_config.p0_batch_enabled:
                return False  # 暂不发送，等待批量
            return True  # 禁用批量则正常发送

    async def flush_batch_queue(self, user_id: int, channel: str):
        """批量发送P0通知队列"""
        batch_key = (user_id, channel)
        if batch_key not in self.p0_batch_buffer:
            return

        notifications = self.p0_batch_buffer[batch_key]
        if not notifications:
            return

        # 合并多条P0通知为一条
        merged_message = self._merge_p0_notifications(notifications)
        await self._send_notification(channel, merged_message)

        # 清空队列
        self.p0_batch_buffer[batch_key] = []
```

#### 2.4.5 时间规则管理器

```python
class TimeRuleManager:
    """时间规则管理器 - 管理勿扰时段、工作时间等"""

    async def should_send_at_current_time(
        self,
        time_rule: NotificationTimeRule,
        priority: str
    ) -> Tuple[bool, Optional[str]]:
        """
        检查当前时间是否应该发送通知

        Returns:
            (should_send, reason)
        """
        now = datetime.now()

        # 1. 勿扰时段检查
        if time_rule.quiet_hours_enabled:
            if self._is_in_quiet_hours(now, time_rule):
                # 勿扰时段只发送高优先级通知
                if priority < time_rule.quiet_priority_filter:
                    return False, "quiet_hours"

        # 2. 工作时间检查
        if time_rule.working_hours_enabled:
            if not self._is_in_working_hours(now, time_rule):
                return False, "outside_working_hours"

        # 3. 周末模式检查
        if time_rule.weekend_mode_enabled:
            if self._is_weekend(now):
                # 周末降级P1到P0
                if time_rule.weekend_downgrade_p1_to_p0 and priority == "P1":
                    return False, "weekend_downgrade"

        # 4. 假期模式检查
        if time_rule.holiday_mode_enabled:
            if self._is_holiday(now, time_rule.holiday_dates):
                return False, "holiday"

        return True, None

    def _is_in_quiet_hours(self, now: datetime, rule: NotificationTimeRule) -> bool:
        """检查是否在勿扰时段"""
        current_time = now.time()
        start_time = datetime.strptime(rule.quiet_start_time, "%H:%M").time()
        end_time = datetime.strptime(rule.quiet_end_time, "%H:%M").time()

        if start_time < end_time:
            # 正常时间段：如 09:00 - 18:00
            return start_time <= current_time <= end_time
        else:
            # 跨天时间段：如 22:00 - 08:00
            return current_time >= start_time or current_time <= end_time
```

#### 2.4.6 通知渠道适配器

```python
from abc import ABC, abstractmethod
from typing import Dict, Any

class NotificationChannel(ABC):
    """通知渠道抽象基类"""

    @abstractmethod
    async def send(
        self,
        message: str,
        title: str = None,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """发送通知"""
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """测试渠道连接"""
        pass

class TelegramChannel(NotificationChannel):
    """Telegram Bot 通知渠道"""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id

    async def send(self, message: str, title: str = None, metadata: Dict = None) -> bool:
        """发送Telegram消息"""
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

        # 格式化消息
        formatted_message = f"**{title}**\n\n{message}" if title else message

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json={
                    "chat_id": self.chat_id,
                    "text": formatted_message,
                    "parse_mode": "Markdown"
                },
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                return response.status == 200

class FeishuChannel(NotificationChannel):
    """飞书 Webhook 通知渠道"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    async def send(self, message: str, title: str = None, metadata: Dict = None) -> bool:
        """发送飞书消息"""
        content = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": title or "通知"
                    },
                    "template": self._get_color_by_priority(metadata)
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "plain_text",
                            "content": message
                        }
                    }
                ]
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(self.webhook_url, json=content) as response:
                return response.status == 200

class WeChatWorkChannel(NotificationChannel):
    """企业微信通知渠道"""

    def __init__(self, corp_id: str, corp_secret: str, agent_id: str):
        self.corp_id = corp_id
        self.corp_secret = corp_secret
        self.agent_id = agent_id
        self.access_token = None

    async def send(self, message: str, title: str = None, metadata: Dict = None) -> bool:
        """发送企业微信消息"""
        # 获取access_token
        if not self.access_token:
            await self._refresh_access_token()

        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={self.access_token}"

        content = {
            "touser": "@all",
            "msgtype": "text",
            "agentid": self.agent_id,
            "text": {
                "content": f"{title}\n\n{message}" if title else message
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=content) as response:
                return response.status == 200

class DiscordChannel(NotificationChannel):
    """Discord Bot 通知渠道"""

    def __init__(self, webhook_url: str = None, bot_token: str = None, channel_id: str = None):
        """
        Discord通知渠道初始化

        支持两种模式：
        1. Webhook模式：只需要webhook_url
        2. Bot模式：需要bot_token和channel_id
        """
        self.webhook_url = webhook_url
        self.bot_token = bot_token
        self.channel_id = channel_id

    async def send(self, message: str, title: str = None, metadata: Dict = None) -> bool:
        """发送Discord消息"""
        if self.webhook_url:
            return await self._send_via_webhook(message, title, metadata)
        elif self.bot_token and self.channel_id:
            return await self._send_via_bot(message, title, metadata)
        else:
            logger.error("Discord channel not properly configured")
            return False

    async def _send_via_webhook(self, message: str, title: str = None, metadata: Dict = None) -> bool:
        """通过Webhook发送消息"""
        # 构建Discord Embed消息
        embed = {
            "title": title or "通知",
            "description": message,
            "color": self._get_color_by_priority(metadata),
            "timestamp": datetime.utcnow().isoformat()
        }

        # 添加元数据字段
        if metadata:
            fields = []
            priority = metadata.get("priority", "P1")
            notification_type = metadata.get("notification_type", "info")

            fields.append({
                "name": "优先级",
                "value": f"**{priority}**",
                "inline": True
            })
            fields.append({
                "name": "类型",
                "value": notification_type,
                "inline": True
            })

            embed["fields"] = fields

        payload = {
            "embeds": [embed]
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.webhook_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 204:
                    logger.info("Discord webhook notification sent successfully")
                    return True
                else:
                    logger.error(f"Discord webhook error: {response.status}")
                    return False

    async def _send_via_bot(self, message: str, title: str = None, metadata: Dict = None) -> bool:
        """通过Bot API发送消息"""
        url = f"https://discord.com/api/v10/channels/{self.channel_id}/messages"

        headers = {
            "Authorization": f"Bot {self.bot_token}",
            "Content-Type": "application/json"
        }

        # 构建Discord Embed消息
        embed = {
            "title": title or "通知",
            "description": message,
            "color": self._get_color_by_priority(metadata),
            "timestamp": datetime.utcnow().isoformat()
        }

        payload = {
            "embeds": [embed]
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    logger.info("Discord bot notification sent successfully")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Discord bot error: {response.status}, {error_text}")
                    return False

    def _get_color_by_priority(self, metadata: Dict = None) -> int:
        """根据优先级返回Discord颜色值"""
        if not metadata:
            return 0x3498db  # 默认蓝色

        priority = metadata.get("priority", "P1")
        notification_type = metadata.get("notification_type", "info")

        # 根据优先级设置颜色
        if priority == "P2":
            return 0xe74c3c  # 红色（高优先级）
        elif priority == "P1":
            return 0xf39c12  # 橙色（中优先级）
        elif priority == "P0":
            return 0x95a5a6  # 灰色（低优先级）

        # 根据通知类型设置颜色
        if notification_type == "alert":
            return 0xe74c3c  # 红色
        elif notification_type == "signal":
            return 0x2ecc71  # 绿色
        elif notification_type == "info":
            return 0x3498db  # 蓝色

        return 0x3498db  # 默认蓝色

    async def test_connection(self) -> bool:
        """测试Discord连接"""
        test_message = "🔔 Discord通知测试\n\n这是一条测试消息，用于验证Discord通知渠道配置是否正确。"
        return await self.send(test_message, "测试通知", {"priority": "P1", "notification_type": "info"})

class EmailChannel(NotificationChannel):
    """邮件通知渠道"""

    def __init__(self, smtp_host: str, smtp_port: int, smtp_user: str, smtp_password: str, from_email: str):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.from_email = from_email

    async def send(self, message: str, title: str = None, metadata: Dict = None) -> bool:
        """发送邮件通知"""
        # 邮件实现
        pass

class SMSChannel(NotificationChannel):
    """短信通知渠道"""

    def __init__(self, api_key: str, api_secret: str, phone_numbers: list):
        self.api_key = api_key
        self.api_secret = api_secret
        self.phone_numbers = phone_numbers

    async def send(self, message: str, title: str = None, metadata: Dict = None) -> bool:
        """发送短信通知"""
        # 短信实现
        pass
```

#### 2.4.7 NotifyHub 核心服务

```python
class NotifyHub:
    """
    NotifyHub 通知中心

    统一的通知入口，业务代码只需要调用 notify() 方法
    """

    def __init__(self):
        self.router = NotifyRouter()
        self.frequency_controller = FrequencyController()
        self.time_rule_manager = TimeRuleManager()
        self.channels: Dict[str, NotificationChannel] = {}
        self.queue = asyncio.Queue()
        self.worker_task = None

    async def notify(
        self,
        user_id: int,
        title: str,
        message: str,
        notification_type: str,
        priority: str = "P1",
        metadata: Dict = None,
        strategy_id: int = None,
        signal_id: int = None
    ) -> bool:
        """
        发送通知 - 统一入口

        Args:
            user_id: 用户ID
            title: 通知标题
            message: 通知内容
            notification_type: 通知类型 (signal/alert/info/system)
            priority: 优先级 (P0/P1/P2)
            metadata: 元数据
            strategy_id: 关联的策略ID（可选）
            signal_id: 关联的信号ID（可选）

        Returns:
            bool: 是否成功加入发送队列

        使用示例:
            # 业务代码中发送通知
            await notify_hub.notify(
                user_id=1,
                title="强买入信号",
                message="BTC/USDT 出现强买入信号，信号强度85%",
                notification_type="signal",
                priority="P2",  # 最高优先级，立即发送
                metadata={"pair": "BTC/USDT", "strength": 0.85},
                strategy_id=10,
                signal_id=12345
            )
        """
        notification_data = {
            "user_id": user_id,
            "title": title,
            "message": message,
            "notification_type": notification_type,
            "priority": priority,
            "metadata": metadata or {},
            "strategy_id": strategy_id,
            "signal_id": signal_id,
            "created_at": datetime.now()
        }

        await self.queue.put(notification_data)
        logger.debug(f"Notification queued for user {user_id}, priority={priority}")
        return True

    async def _notification_worker(self):
        """通知工作线程 - 处理队列中的通知"""
        while True:
            try:
                notification_data = await self.queue.get()

                # 1. 路由：决定发送到哪些渠道
                channels = await self.router.route(notification_data)

                if not channels:
                    logger.info(f"No channels selected for notification (user={notification_data['user_id']})")
                    continue

                # 2. 为每个渠道发送通知
                for channel_type in channels:
                    await self._send_to_channel(channel_type, notification_data)

                self.queue.task_done()

            except Exception as e:
                logger.error(f"Error in notification worker: {e}", exc_info=True)

    async def _send_to_channel(self, channel_type: str, notification_data: Dict):
        """发送通知到指定渠道"""
        try:
            # 创建通知历史记录
            history_id = await self._create_notification_history(
                channel_type,
                notification_data
            )

            # 获取渠道实例
            channel = self.channels.get(channel_type)
            if not channel:
                logger.error(f"Channel {channel_type} not found")
                await self._update_history_status(history_id, "failed", "Channel not found")
                return

            # 渲染通知模板
            formatted_message = await self._render_template(channel_type, notification_data)

            # 发送通知
            success = await channel.send(
                message=formatted_message,
                title=notification_data["title"],
                metadata=notification_data["metadata"]
            )

            # 更新通知状态
            status = "sent" if success else "failed"
            await self._update_history_status(history_id, status)

            logger.info(f"Notification {status} via {channel_type} (history_id={history_id})")

        except Exception as e:
            logger.error(f"Failed to send notification via {channel_type}: {e}", exc_info=True)
            await self._update_history_status(history_id, "failed", str(e))

# 全局单例
notify_hub = NotifyHub()
```

#### 2.4.8 使用示例

```python
# ===== 业务代码中使用NotifyHub =====

# 示例1: 策略引擎发送交易信号通知
async def on_new_signal(signal_data: Dict):
    """当产生新交易信号时"""
    strength = signal_data['signal_strength']

    # 根据信号强度决定优先级
    if strength >= 0.8:
        priority = "P2"  # 强信号，立即发送
    elif strength >= 0.5:
        priority = "P1"  # 中等信号，限频发送
    else:
        priority = "P0"  # 弱信号，批量发送

    await notify_hub.notify(
        user_id=signal_data['user_id'],
        title=f"📊 {signal_data['action']} 信号: {signal_data['pair']}",
        message=f"信号强度: {strength:.1%}\n价格: ${signal_data['price']:.2f}",
        notification_type="signal",
        priority=priority,
        metadata=signal_data,
        strategy_id=signal_data['strategy_id'],
        signal_id=signal_data['signal_id']
    )

# 示例2: 系统监控模块发送告警
async def on_strategy_error(strategy_id: int, error_message: str):
    """当策略异常时"""
    await notify_hub.notify(
        user_id=1,  # 管理员
        title="🚨 策略异常告警",
        message=f"策略 #{strategy_id} 运行异常\n错误: {error_message}",
        notification_type="alert",
        priority="P2",  # 系统告警，最高优先级
        metadata={"strategy_id": strategy_id, "error": error_message},
        strategy_id=strategy_id
    )

# 示例3: 数据同步模块发送完成通知
async def on_sync_completed(sync_stats: Dict):
    """数据同步完成"""
    await notify_hub.notify(
        user_id=1,
        title="✅ 数据同步完成",
        message=f"同步了 {sync_stats['records']} 条记录",
        notification_type="info",
        priority="P0",  # 信息类通知，低优先级
        metadata=sync_stats
    )
```

#### 2.4.9 数据库表设计

NotifyHub 相关的数据库表在 `models/notification.py` 中已定义：

- `notification_channel_configs`: 通知渠道配置表
- `notification_frequency_limits`: 通知频率限制配置表
- `notification_time_rules`: 通知时间规则配置表
- `notification_history`: 通知历史记录表

详见 **2.1.4 信号和通知表** 部分。

### 2.5 前端组件设计

#### 2.5.1 主要页面组件
```typescript
// 货币对管理页面
interface CurrencyPair {
  id: number;
  symbol: string;
  exchange: string;
  isActive: boolean;
}

// 策略管理页面
interface Strategy {
  id: number;
  name: string;
  description: string;
  config: Record<string, any>;
  status: 'running' | 'stopped' | 'error';
  isActive: boolean;
}

// 图表展示组件
interface ChartData {
  symbol: string;
  timeframe: string;
  klines: KlineData[];
  signals: SignalData[];
  indicators: IndicatorData[];
}
```

#### 2.5.2 状态管理
```typescript
// Pinia store
export const useStrategyStore = defineStore('strategy', {
  state: () => ({
    strategies: [] as Strategy[],
    currentStrategy: null as Strategy | null,
  }),

  actions: {
    async fetchStrategies() {
      const response = await api.get('/strategies');
      this.strategies = response.data;
    },

    async startStrategy(id: number) {
      await api.post(`/strategies/${id}/start`);
      await this.fetchStrategies();
    }
  }
});
```

## 3. 技术选型总结

### 3.1 技术栈对比表

| 组件层级 | 技术选型 | 版本要求 | 说明 | 新增/更新 |
|----------|----------|----------|------|-----------|
| **前端框架** | Vue.js + TypeScript | 3.x | 组件化开发，生态丰富 | - |
| **UI组件库** | Element Plus | 2.x | 成熟的Vue3组件库 | - |
| **图表组件** | TradingView Charts | Latest | 专业级金融图表 | - |
| **状态管理** | Pinia | 2.x | Vue3官方状态管理 | - |
| **后端框架** | FastAPI | 0.104+ | 高性能异步API框架 | - |
| **数据库** | PostgreSQL | 15+ | 关系型数据库，支持分区 | 增强 |
| **缓存** | Redis | 7+ | 内存缓存和消息队列 | 保留 |
| **价格采集** | WebSocket + asyncio | - | 多交易所实时数据收集 | **新增** |
| **数据同步** | aiohttp + 定时任务 | - | 远程数据增量同步 | **新增** |
| **策略引擎** | FreqTrade | 2024.x | 成熟的量化交易框架 | - |
| **容器化** | Docker + Compose | 24+ | 容器化部署 | - |
| **反向代理** | Nginx | 1.25+ | 静态文件和负载均衡 | - |

### 3.2 新增服务说明

#### 3.2.1 价格数据服务 (Price Service)
- **目的**: 解决交易所API历史数据不准确问题
- **技术**: Python asyncio + WebSocket + 批量写入
- **特点**: 高并发、自动重连、数据去重
- **存储**: PostgreSQL分区表 + Redis缓存

#### 3.2.2 数据同步服务 (Sync Service)
- **目的**: 从远程价格服务器同步历史数据到本地
- **技术**: aiohttp异步HTTP客户端 + 增量同步算法
- **特点**: 断点续传、多源支持、状态监控
- **配置**: Web界面管理同步节点和任务

### 3.3 数据存储策略

#### 3.3.1 PostgreSQL优化配置
```ini
# 针对16GB内存的优化配置
shared_buffers = 4GB              # 共享缓冲区
effective_cache_size = 12GB       # 有效缓存大小
work_mem = 256MB                  # 工作内存
maintenance_work_mem = 1GB        # 维护工作内存
max_connections = 200             # 最大连接数

# 时间序列数据优化
wal_buffers = 16MB                # WAL缓冲区
checkpoint_completion_target = 0.9 # 检查点完成目标
max_wal_size = 2GB               # 最大WAL大小
```

#### 3.3.2 分区表策略
- **ticker数据**: 按月分区，保留3个月
- **1分钟K线**: 按年分区，保留1年
- **5分钟K线**: 按年分区，保留2年
- **小时K线**: 不分区，保留3年
- **日K线**: 不分区，保留5年

#### 3.3.3 索引优化
```sql
-- 时间序列查询优化
CREATE INDEX idx_tickers_pair_time ON price_tickers(trading_pair_id, timestamp DESC);
CREATE INDEX idx_klines_pair_tf_time ON klines(trading_pair_id, timeframe, open_time DESC);

-- 部分索引优化
CREATE INDEX idx_active_pairs ON trading_pairs(symbol) WHERE is_active = true;
CREATE INDEX idx_recent_signals ON signals(timestamp)
WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL '24 hours';
```

## 4. 部署架构

### 4.1 更新的Docker服务组合

```yaml
services:
  # 前端Web服务
  web:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - api

  # 主要API服务
  api:
    build: ./backend
    ports:
      - "8000:8000"
    depends_on:
      - db
      - redis
      - price-service

  # 价格数据服务 (新增)
  price-service:
    build: ./price-service
    environment:
      - ENABLE_BINANCE=true
      - ENABLE_OKX=true
      - BATCH_SIZE=100
    volumes:
      - ./data/logs/price-service:/var/log
    depends_on:
      - db
      - redis

  # 数据同步服务 (新增，可选)
  sync-service:
    build: ./sync-service
    environment:
      - SYNC_INTERVAL=300  # 5分钟同步一次
    volumes:
      - ./data/logs/sync-service:/var/log
    depends_on:
      - db
      - redis
    profiles:
      - sync  # 默认不启动，需要时启用

  # FreqTrade策略服务
  freqtrade:
    build: ./freqtrade
    volumes:
      - ./freqtrade/user_data:/freqtrade/user_data
      - ./data/signals:/app/signals
    depends_on:
      - db
      - redis

  # 通知服务
  notification:
    build: ./notification
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - WECHAT_CORP_ID=${WECHAT_CORP_ID}
    depends_on:
      - redis
      - db

  # 数据库服务 (增强配置)
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./sql/init.sql:/docker-entrypoint-initdb.d/init.sql
      - ./postgresql.conf:/etc/postgresql/postgresql.conf
    command: postgres -c config_file=/etc/postgresql/postgresql.conf
    shm_size: 1g  # 增加共享内存

  # Redis缓存服务
  redis:
    image: redis:7-alpine
    command: redis-server --maxmemory 1gb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data

  # Nginx反向代理
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - web
      - api

volumes:
  postgres_data:
  redis_data:
```

### 4.2 部署配置选项

#### 4.2.1 标准部署（本地开发+策略监控）
```bash
# 启动核心服务
docker-compose up -d

# 包含的服务:
# - web, api, db, redis, freqtrade, notification, nginx
```

#### 4.2.2 完整部署（包含价格采集）
```bash
# 启动所有服务，包括价格采集
docker-compose --profile price-service up -d

# 新增服务:
# - price-service (实时价格采集和存储)
```

#### 4.2.3 分布式部署（本地+远程数据源）
```bash
# 远程服务器：仅运行价格采集服务
docker-compose -f docker-compose.price-only.yml up -d

# 本地服务器：运行策略监控+同步服务
docker-compose --profile sync up -d
```

### 4.3 Alpha部署环境（生产/外部访问环境）

#### 4.3.1 架构概述
Alpha环境是用于生产部署和外部访问的环境配置，通过Nginx反向代理和FRP内网穿透实现外部访问。

```
外网访问流程:
Internet ──▶ FRP Server ──▶ FRP Client ──▶ Nginx (80/443) ──▶ Frontend (8501)
                                                    │
                                                    └──▶ Backend API (8000)
```

#### 4.3.2 端口配置
```yaml
# Alpha环境端口映射
Frontend (Streamlit):  8501  # Nginx反向代理目标端口
Backend API:           8000  # API服务端口
Nginx:                 80    # HTTP外部访问端口
                       443   # HTTPS外部访问端口（可选）
PostgreSQL:            5432  # 数据库（内部访问）
Redis:                 6379  # 缓存（内部访问）
```

#### 4.3.3 Nginx配置示例（Alpha环境）
```nginx
# /etc/nginx/sites-available/btc-watcher-alpha.conf

server {
    listen 80;
    server_name _;  # 或配置具体域名

    # 前端代理到8501端口
    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;

        # WebSocket支持
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # 常规代理头
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Streamlit特定配置
        proxy_read_timeout 86400;
        proxy_buffering off;
    }

    # 后端API代理
    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_http_version 1.1;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket API代理
    location /ws/ {
        proxy_pass http://localhost:8000/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

#### 4.3.4 FRP配置（内网穿透）

**FRP Client配置** (`frpc.ini`):
```ini
[common]
server_addr = <FRP服务器地址>
server_port = 7000
token = <认证令牌>

[btc-watcher-alpha]
type = tcp
local_ip = 127.0.0.1
local_port = 80              # Nginx监听端口
remote_port = 60001          # 外网访问端口
```

**访问方式**:
- 外部访问：`http://<FRP服务器IP>:60001`
- 内部访问：`http://localhost:80` 或 `http://localhost:8501`

#### 4.3.5 部署步骤

1. **启动后端服务**
```bash
cd /path/to/btc-watcher/backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

2. **启动前端服务**
```bash
cd /path/to/btc-watcher/frontend
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

3. **配置Nginx**
```bash
sudo cp nginx/btc-watcher-alpha.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/btc-watcher-alpha.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

4. **启动FRP客户端**
```bash
./frpc -c frpc.ini
```

#### 4.3.6 安全建议

- **启用HTTPS**: 配置SSL证书（Let's Encrypt）
- **访问控制**:
  ```nginx
  # 限制访问IP（可选）
  allow 10.0.0.0/8;
  allow 192.168.0.0/16;
  deny all;
  ```
- **认证保护**:
  - 在Nginx层添加Basic Auth
  - 或在应用层实现JWT认证
- **防火墙配置**: 只开放必要端口（80, 443, FRP端口）

#### 4.3.7 监控和维护

```bash
# 检查服务状态
systemctl status nginx
ps aux | grep streamlit
ps aux | grep uvicorn
ps aux | grep frpc

# 查看日志
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
tail -f backend/logs/app.log
tail -f frontend/logs/streamlit.log
```

### 4.4 环境变量配置更新

```bash
# .env 文件新增配置项

# 价格数据服务配置
ENABLE_PRICE_SERVICE=true
ENABLE_BINANCE=true
ENABLE_OKX=true
ENABLE_BYBIT=false
PRICE_SERVICE_BATCH_SIZE=100
PRICE_SERVICE_FLUSH_INTERVAL=10

# 数据同步配置
ENABLE_SYNC_SERVICE=false
DEFAULT_SYNC_INTERVAL=300
MAX_SYNC_RECORDS=1000

# PostgreSQL性能配置
PG_SHARED_BUFFERS=4GB
PG_EFFECTIVE_CACHE_SIZE=12GB
PG_WORK_MEM=256MB
PG_MAX_CONNECTIONS=200

# Redis配置
REDIS_MAXMEMORY=1gb
REDIS_MAXMEMORY_POLICY=allkeys-lru

# 监控的交易对
MONITORED_SYMBOLS=BTCUSDT,ETHUSDT,ADAUSDT,DOTUSDT,LINKUSDT,SOLUSDT
```

### 4.5 资源使用估算

#### 4.5.1 内存使用（16GB系统）
```
PostgreSQL:     ~6GB  (shared_buffers 4GB + 其他)
Redis:          ~1GB  (价格数据缓存)
Price Service:  ~500MB (WebSocket连接 + 数据处理)
API Service:    ~300MB (FastAPI应用)
FreqTrade:      ~200MB (策略执行)
Sync Service:   ~200MB (数据同步，可选)
Web/Nginx:      ~100MB (静态文件服务)
系统预留:       ~7GB

总计:          ~15GB (在16GB系统上运行良好)
```

#### 4.5.2 磁盘使用估算（按天）
```
价格数据存储（5个交易对）:
- Ticker数据: ~50MB/天
- 1分钟K线: ~20MB/天
- 5分钟K线: ~4MB/天
- 1小时K线: ~0.3MB/天
- 1天K线: ~0.01MB/天

总计: ~75MB/天
月度总计: ~2.3GB
年度总计: ~27GB (包含数据清理)
```

### 4.6 部署脚本更新

#### 4.6.1 启动脚本增强功能
```bash
# scripts/start.sh 新增选项

# 标准启动
./scripts/start.sh

# 包含价格采集服务启动
./scripts/start.sh --with-price-service

# 包含数据同步服务启动
./scripts/start.sh --with-sync-service

# 完整功能启动
./scripts/start.sh --full
```

#### 4.6.2 监控和维护
```bash
# 新增管理脚本

# 数据库维护
./scripts/db-maintenance.sh    # 数据分区、清理、优化

# 服务健康检查
./scripts/health-check.sh      # 检查所有服务状态

# 性能监控
./scripts/performance.sh       # 显示资源使用情况
```

这个设计文档提供了完整的系统架构方案，下一步我将创建更详细的实现文档和Docker部署配置。