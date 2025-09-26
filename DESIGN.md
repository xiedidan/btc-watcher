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

### 2.4 通知系统设计

#### 2.4.1 通知适配器
```python
from abc import ABC, abstractmethod
from typing import Dict, Any

class NotificationChannel(ABC):
    """通知渠道抽象基类"""

    @abstractmethod
    async def send(self, message: str, metadata: Dict[str, Any] = None) -> bool:
        pass

class TelegramChannel(NotificationChannel):
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id

    async def send(self, message: str, metadata: Dict[str, Any] = None) -> bool:
        # Telegram Bot API 实现
        pass

class WeChatChannel(NotificationChannel):
    # 微信通知实现
    pass

class EmailChannel(NotificationChannel):
    # 邮件通知实现
    pass
```

#### 2.4.2 通知服务
```python
class NotificationService:
    def __init__(self):
        self.channels = {}

    def register_channel(self, name: str, channel: NotificationChannel):
        self.channels[name] = channel

    async def send_signal_notification(self, signal: dict):
        """发送信号通知"""
        message = self.format_signal_message(signal)

        # 并发发送到所有激活的通知渠道
        tasks = []
        for name, channel in self.channels.items():
            tasks.append(channel.send(message, signal))

        await asyncio.gather(*tasks)
```

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

### 4.3 环境变量配置更新

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

### 4.4 资源使用估算

#### 4.4.1 内存使用（16GB系统）
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

#### 4.4.2 磁盘使用估算（按天）
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

### 4.5 部署脚本更新

#### 4.5.1 启动脚本增强功能
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

#### 4.5.2 监控和维护
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