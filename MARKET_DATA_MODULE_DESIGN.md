# 市场数据模块设计文档

## 1. 模块概述

### 1.1 模块定位

市场数据模块是BTC Watcher系统的核心数据源模块，负责从多个加密货币交易所获取实时和历史市场数据，并提供统一的数据访问接口供前端图表和策略系统使用。

### 1.2 核心职责

- **数据获取**: 通过CCXT库从多个交易所获取K线数据和实时行情
- **指标计算**: 计算常用技术指标（MA、MACD、RSI、布林带、成交量）
- **数据缓存**: 使用Redis缓存热数据，减少API调用
- **数据持久化**: 将历史数据存储到PostgreSQL，支持长期查询
- **限流降级**: API限流时自动降级到缓存/数据库
- **交易所故障切换**: 自动检测并切换到健康的交易所
- **配置管理**: 提供系统级市场数据配置管理

### 1.3 模块边界

**输入**:
- 前端请求: K线数据、技术指标、实时价格、系统配置
- 定时任务触发: 数据更新调度

**输出**:
- K线数据: OHLCV格式的历史和实时数据
- 技术指标: 计算后的指标值
- 实时价格: Ticker数据
- 系统配置: 当前市场数据配置

**不包含**:
- 策略信号生成（由FreqTrade策略模块负责）
- 通知发送（由通知模块负责）
- 用户认证（由认证模块负责）

---

## 2. 模块架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend Layer                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Charts.vue   │  │Settings.vue  │  │Dashboard.vue │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                  │                  │                  │
│         └──────────────────┼──────────────────┘                  │
│                            │ HTTP/WebSocket                      │
└────────────────────────────┼─────────────────────────────────────┘
                             │
┌────────────────────────────┼─────────────────────────────────────┐
│                    API Gateway Layer                             │
│  ┌──────────────────────────┴───────────────────────────┐        │
│  │         FastAPI Router (backend/api/v1/)             │        │
│  │  /market/klines  /market/indicators  /system/config  │        │
│  └──────────────────────────┬───────────────────────────┘        │
└────────────────────────────┼─────────────────────────────────────┘
                             │
┌────────────────────────────┼─────────────────────────────────────┐
│                  Business Logic Layer                            │
│  ┌──────────────────────────┴───────────────────────────┐        │
│  │          Market Data Service (核心服务层)            │        │
│  │  ┌──────────────────┐  ┌──────────────────────┐     │        │
│  │  │ CCXTManager      │  │ IndicatorCalculator  │     │        │
│  │  │ - fetch_ohlcv    │  │ - calculate_ma       │     │        │
│  │  │ - fetch_ticker   │  │ - calculate_macd     │     │        │
│  │  │ - proxy_support  │  │ - calculate_rsi      │     │        │
│  │  └──────────────────┘  └──────────────────────┘     │        │
│  │  ┌──────────────────┐  ┌──────────────────────┐     │        │
│  │  │FailoverManager   │  │ RateLimitHandler     │     │        │
│  │  │ - auto_switch    │  │ - fallback_strategy  │     │        │
│  │  │ - health_check   │  │ - cache_priority     │     │        │
│  │  └──────────────────┘  └──────────────────────┘     │        │
│  │  ┌──────────────────┐  ┌──────────────────────┐     │        │
│  │  │SystemConfigSvc   │  │ DataScheduler        │     │        │
│  │  │ - get_config     │  │ - interval_mode      │     │        │
│  │  │ - update_config  │  │ - n_periods_mode     │     │        │
│  │  └──────────────────┘  └──────────────────────┘     │        │
│  └──────────────────────────┬───────────────────────────┘        │
└────────────────────────────┼─────────────────────────────────────┘
                             │
┌────────────────────────────┼─────────────────────────────────────┐
│                    Data Access Layer                             │
│  ┌──────────────────────────┴───────────────────────────┐        │
│  │              Three-Layer Data Access                 │        │
│  │  ┌────────────┐  ┌──────────────┐  ┌─────────────┐  │        │
│  │  │ Redis      │→ │ PostgreSQL   │→ │ CCXT API    │  │        │
│  │  │ (L1 Cache) │  │ (L2 Storage) │  │ (L3 Source) │  │        │
│  │  │ TTL: 60s-  │  │ Partitioned  │  │ Binance/OKX │  │        │
│  │  │ 86400s     │  │ by timeframe │  │ Bybit/Bitget│  │        │
│  │  └────────────┘  └──────────────┘  └─────────────┘  │        │
│  └────────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 组件关系图

```mermaid
graph TB
    A[MarketDataAPI] --> B[CCXTManager]
    A --> C[IndicatorCalculator]
    A --> D[SystemConfigService]

    B --> E[ExchangeFailoverManager]
    B --> F[RateLimitHandler]

    F --> G[RedisCache]
    F --> H[PostgreSQL]
    F --> I[CCXT Exchange APIs]

    C --> G
    C --> H

    D --> H

    J[MarketDataScheduler] --> B
    J --> C
    J --> D

    K[ProxyManager] --> B
```

### 2.3 数据流图

#### 2.3.1 K线数据获取流程

```mermaid
sequenceDiagram
    participant FE as Frontend Charts
    participant API as MarketDataAPI
    participant RLH as RateLimitHandler
    participant Redis as Redis Cache
    participant DB as PostgreSQL
    participant CCXT as CCXT Client
    participant EX as Exchange API

    FE->>API: GET /market/klines?symbol=BTC/USDT&timeframe=1h
    API->>RLH: fetch_with_fallback()

    RLH->>Redis: get(klines:binance:BTCUSDT:1h)
    alt Cache Hit
        Redis-->>RLH: Cached Data
        RLH-->>API: Return Cached
        API-->>FE: { data, source: "cache" }
    else Cache Miss
        RLH->>DB: query klines table
        alt DB Has Data
            DB-->>RLH: Historical Data
            RLH->>Redis: cache data (TTL=3600s)
            RLH-->>API: Return DB Data
            API-->>FE: { data, source: "database" }
        else DB Empty
            RLH->>CCXT: fetch_ohlcv()
            CCXT->>EX: GET /api/v3/klines
            alt API Success
                EX-->>CCXT: Raw Data
                CCXT-->>RLH: Parsed Data
                RLH->>DB: bulk_insert()
                RLH->>Redis: cache data
                RLH-->>API: Return API Data
                API-->>FE: { data, source: "api" }
            else Rate Limited
                EX-->>CCXT: 429 Too Many Requests
                CCXT-->>RLH: RateLimitError
                RLH->>RLH: mark_rate_limited(1h)
                RLH->>DB: query latest available
                DB-->>RLH: Stale Data
                RLH-->>API: Return Stale (with warning)
                API-->>FE: { data, source: "database", stale: true }
            end
        end
    end
```

#### 2.3.2 技术指标计算流程

```mermaid
sequenceDiagram
    participant FE as Frontend Charts
    participant API as MarketDataAPI
    participant IC as IndicatorCalculator
    participant Redis as Redis Cache
    participant DB as PostgreSQL

    FE->>API: GET /market/indicators?symbol=BTC/USDT&indicators=MA,MACD
    API->>IC: calculate_indicators(klines, ["MA", "MACD"])

    IC->>Redis: get(indicators:binance:BTCUSDT:1h:MA)
    alt Cache Hit
        Redis-->>IC: Cached Indicators
        IC-->>API: Return Cached
    else Cache Miss
        IC->>DB: query technical_indicators table
        alt DB Has Recent
            DB-->>IC: Stored Indicators
            IC->>Redis: cache indicators
            IC-->>API: Return DB Data
        else Need Calculation
            IC->>IC: _calculate_ma(df)
            IC->>IC: _calculate_macd(df)
            IC->>DB: insert technical_indicators
            IC->>Redis: cache indicators
            IC-->>API: Return Calculated
        end
    end

    API-->>FE: { indicators: { MA: {...}, MACD: {...} } }
```

#### 2.3.3 交易所故障切换流程

```mermaid
sequenceDiagram
    participant Scheduler as DataScheduler
    participant FM as FailoverManager
    participant CCXT1 as CCXT(Binance)
    participant CCXT2 as CCXT(OKX)
    participant Health as HealthChecker

    Scheduler->>FM: get_active_exchange()
    FM->>FM: check current_exchange health

    alt Current Healthy
        FM-->>Scheduler: "binance"
    else Current Unhealthy
        FM->>Health: check_exchange_health("binance")
        Health->>CCXT1: ping()
        CCXT1-->>Health: Timeout/Error
        Health-->>FM: status: unhealthy

        FM->>FM: mark_exchange_failed("binance")
        FM->>Health: check_exchange_health("okx")
        Health->>CCXT2: ping()
        CCXT2-->>Health: Success
        Health-->>FM: status: healthy

        FM->>FM: switch to "okx"
        FM->>FM: notify_failover()
        FM-->>Scheduler: "okx"
    end
```

---

## 3. 核心组件设计

### 3.1 CCXTManager（交易所客户端管理器）

#### 职责
- 创建和管理CCXT交易所客户端实例
- 处理代理配置
- 执行市场数据请求
- 处理限流和网络错误

#### 接口定义

```python
class CCXTManager:
    """CCXT客户端管理器"""

    def __init__(self, config_service: SystemConfigService):
        self.config_service = config_service
        self.clients: Dict[str, ccxt.Exchange] = {}
        self.proxy_manager = ProxyManager()

    async def get_client(self, exchange: str) -> ccxt.Exchange:
        """获取或创建CCXT客户端实例

        Args:
            exchange: 交易所名称 (binance, okx, bybit, bitget)

        Returns:
            ccxt.Exchange: 交易所客户端实例
        """
        pass

    async def fetch_ohlcv(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        limit: int = 200
    ) -> List[List]:
        """获取K线数据

        Args:
            exchange: 交易所名称
            symbol: 交易对符号 (BTC/USDT)
            timeframe: 时间周期 (1m, 5m, 1h, 1d)
            limit: 返回数据条数

        Returns:
            List[List]: [[timestamp, open, high, low, close, volume], ...]

        Raises:
            RateLimitError: 超过限流
            NetworkError: 网络错误
        """
        pass

    async def fetch_ticker(
        self,
        exchange: str,
        symbol: str
    ) -> Dict:
        """获取实时行情

        Args:
            exchange: 交易所名称
            symbol: 交易对符号

        Returns:
            Dict: {
                "symbol": "BTC/USDT",
                "last": 45230.5,
                "bid": 45230.0,
                "ask": 45231.0,
                "volume": 12345.67,
                "change": 2.34,
                "timestamp": 1640000000000
            }
        """
        pass

    async def _create_client(self, exchange: str) -> ccxt.Exchange:
        """创建CCXT客户端（内部方法）"""
        pass

    async def _fetch_from_cache_or_db(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        limit: int
    ) -> List[List]:
        """降级到缓存或数据库（内部方法）"""
        pass
```

#### 配置示例

```python
# CCXT客户端配置
ccxt_config = {
    "binance": {
        "enableRateLimit": True,
        "timeout": 30000,
        "proxies": {
            "http": "http://proxy.example.com:1080",
            "https": "http://proxy.example.com:1080"
        }
    },
    "okx": {
        "enableRateLimit": True,
        "timeout": 30000
    }
}
```

#### 错误处理

| 错误类型 | 处理策略 |
|---------|---------|
| RateLimitExceeded | 降级到缓存→数据库，标记限流状态1小时 |
| NetworkError | 尝试代理切换，失败则降级 |
| ExchangeNotAvailable | 触发交易所故障切换 |
| InvalidSymbol | 返回400错误给前端 |

---

### 3.2 IndicatorCalculator（技术指标计算器）

#### 职责
- 计算常用技术指标（MA、MACD、RSI、布林带、成交量）
- 管理指标计算参数
- 缓存计算结果

#### 接口定义

```python
class IndicatorCalculator:
    """技术指标计算引擎"""

    def __init__(self, cache_service, db_service):
        self.cache_service = cache_service
        self.db_service = db_service

    async def calculate_indicators(
        self,
        klines: List[List],
        indicator_types: List[str],
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """计算多个技术指标

        Args:
            klines: K线数据
            indicator_types: 指标类型列表 ["MA", "MACD", "RSI", "BOLL", "VOL"]
            params: 自定义参数 {"MA": {"periods": [5, 10, 20]}}

        Returns:
            Dict: {
                "MA": {"ma5": [...], "ma10": [...], "ma20": [...]},
                "MACD": {"macd": [...], "signal": [...], "histogram": [...]},
                "RSI": {"rsi": [...]},
                "BOLL": {"upper": [...], "middle": [...], "lower": [...]},
                "VOL": {"volume": [...], "volume_ma": [...]}
            }
        """
        pass

    def _calculate_ma(
        self,
        df: pd.DataFrame,
        periods: List[int] = [5, 10, 20, 30]
    ) -> Dict[str, List]:
        """计算移动平均线"""
        pass

    def _calculate_macd(
        self,
        df: pd.DataFrame,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> Dict[str, List]:
        """计算MACD"""
        pass

    def _calculate_rsi(
        self,
        df: pd.DataFrame,
        period: int = 14
    ) -> Dict[str, List]:
        """计算RSI"""
        pass

    def _calculate_bollinger(
        self,
        df: pd.DataFrame,
        period: int = 20,
        std_dev: int = 2
    ) -> Dict[str, List]:
        """计算布林带"""
        pass

    def _calculate_volume(
        self,
        df: pd.DataFrame,
        ma_period: int = 20
    ) -> Dict[str, List]:
        """计算成交量指标"""
        pass
```

#### 依赖库

```python
# requirements.txt
pandas>=2.0.0
ta>=0.11.0  # Technical Analysis library
numpy>=1.24.0
```

#### 性能优化

- **批量计算**: 一次计算多个指标，避免重复DataFrame操作
- **增量计算**: 仅计算新增K线的指标值
- **并行计算**: 使用asyncio并行计算多个货币对的指标

```python
# 增量计算示例
async def calculate_incremental(
    self,
    existing_indicators: Dict,
    new_klines: List[List]
) -> Dict:
    """仅计算新增K线的指标值"""
    # 获取最后n根K线（窗口大小）
    # 计算指标
    # 返回新增部分
    pass
```

---

### 3.3 ExchangeFailoverManager（交易所故障切换管理器）

#### 职责
- 监控交易所健康状态
- 自动切换到健康的交易所
- 记录切换历史

#### 接口定义

```python
class ExchangeFailoverManager:
    """交易所自动故障切换管理器"""

    def __init__(self, config_service: SystemConfigService):
        self.config_service = config_service
        self.current_exchange: Optional[str] = None
        self.exchange_health: Dict[str, Dict] = {}

    async def get_active_exchange(self) -> str:
        """获取当前活跃的交易所

        Returns:
            str: 交易所名称 (binance, okx, bybit, bitget)
        """
        pass

    async def mark_exchange_failed(self, exchange: str):
        """标记交易所故障

        Args:
            exchange: 交易所名称
        """
        pass

    async def check_exchange_health(self, exchange: str) -> bool:
        """检查交易所健康状态

        Args:
            exchange: 交易所名称

        Returns:
            bool: True=健康, False=不健康
        """
        pass

    def _is_healthy(self, exchange: str) -> bool:
        """检查交易所健康状态（内部方法）"""
        pass
```

#### 健康检查策略

```python
# 健康检查参数
HEALTH_CHECK_CONFIG = {
    "check_interval_seconds": 60,  # 每60秒检查一次
    "failure_threshold": 3,         # 连续失败3次标记为不健康
    "recovery_threshold": 2,        # 连续成功2次标记为恢复
    "timeout_seconds": 10           # 健康检查超时时间
}
```

#### 故障切换流程

```python
async def _perform_failover(self):
    """执行故障切换"""
    config = await self.config_service.get_market_data_config()

    if not config['auto_failover']:
        logger.warning("Auto-failover disabled, staying with current exchange")
        return

    # 查找健康的交易所
    for exchange in config['enabled_exchanges']:
        if await self.check_exchange_health(exchange):
            if self.current_exchange != exchange:
                logger.info(f"Switching from {self.current_exchange} to {exchange}")
                self.current_exchange = exchange

                # 发送故障切换通知
                await self._notify_failover(exchange)
            return

    logger.error("All exchanges unhealthy, using default")
    self.current_exchange = config['default_exchange']
```

---

### 3.4 RateLimitHandler（限流处理器）

#### 职责
- 检测API限流状态
- 执行降级策略
- 管理限流恢复

#### 接口定义

```python
class RateLimitHandler:
    """限流处理器"""

    def __init__(self, cache_service, db_service):
        self.cache_service = cache_service
        self.db_service = db_service
        self.fallback_active = False
        self.rate_limit_until: Optional[datetime] = None

    async def fetch_with_fallback(
        self,
        fetch_func: Callable,
        cache_key: str,
        exchange: str,
        symbol: str,
        timeframe: str,
        limit: int
    ):
        """带降级的数据获取

        Args:
            fetch_func: 数据获取函数
            cache_key: 缓存键
            exchange: 交易所名称
            symbol: 交易对
            timeframe: 时间周期
            limit: 数据条数

        Returns:
            数据 + 来源信息
        """
        pass

    def _is_rate_limited(self) -> bool:
        """检查是否仍在限流期"""
        pass

    def _mark_rate_limited(self, duration_hours: int = 1):
        """标记进入限流期"""
        pass

    async def _fallback_fetch(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        limit: int
    ):
        """降级数据获取流程

        优先级: Redis Cache → PostgreSQL → Error
        """
        pass
```

#### 降级策略配置

```python
FALLBACK_CONFIG = {
    "rate_limit_duration_hours": 1,  # 限流标记持续1小时
    "cache_priority": True,           # 优先使用缓存
    "allow_stale_data": True,         # 允许返回过期数据
    "stale_data_max_age_hours": 24    # 最多接受24小时前的数据
}
```

---

### 3.5 SystemConfigService（系统配置服务）

#### 职责
- 管理市场数据系统配置
- 提供配置查询和更新接口
- 验证配置合法性

#### 接口定义

```python
class SystemConfigService:
    """系统配置服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_market_data_config(self) -> Dict:
        """获取市场数据配置

        Returns:
            Dict: {
                "default_exchange": "binance",
                "enabled_exchanges": ["binance", "okx", "bybit", "bitget"],
                "default_klines_limit": 200,
                "cache_config": {...},
                "update_mode": "interval",
                "update_interval_seconds": 5,
                "auto_failover": true,
                ...
            }
        """
        pass

    async def update_market_data_config(
        self,
        config_update: Dict
    ) -> SystemConfig:
        """更新市场数据配置

        Args:
            config_update: 配置更新（部分或全部）

        Returns:
            SystemConfig: 更新后的完整配置

        Raises:
            ValidationError: 配置验证失败
        """
        pass

    def _validate_config(self, config: Dict) -> bool:
        """验证配置合法性"""
        pass

    def _deep_merge(self, base: Dict, update: Dict) -> Dict:
        """深度合并两个字典"""
        pass

    async def _create_default_config(self) -> SystemConfig:
        """创建默认系统配置"""
        pass
```

#### 配置验证规则

```python
VALIDATION_RULES = {
    "default_exchange": {
        "type": "string",
        "allowed_values": ["binance", "okx", "bybit", "bitget"]
    },
    "enabled_exchanges": {
        "type": "array",
        "min_length": 1,
        "item_type": "string"
    },
    "default_klines_limit": {
        "type": "integer",
        "min": 1,
        "max": 1000
    },
    "cache_config.ttl.1m": {
        "type": "integer",
        "min": 10,
        "max": 3600
    },
    "update_mode": {
        "type": "string",
        "allowed_values": ["interval", "n_periods"]
    }
}
```

---

### 3.6 MarketDataScheduler（数据更新调度器）

#### 职责
- 定时更新市场数据
- 支持两种更新模式（固定间隔、N周期）
- 管理调度任务生命周期

#### 接口定义

```python
class MarketDataScheduler:
    """市场数据更新调度器"""

    def __init__(
        self,
        config_service: SystemConfigService,
        market_data_service: MarketDataService
    ):
        self.config_service = config_service
        self.market_data_service = market_data_service
        self.scheduler = AsyncIOScheduler()

    async def start(self):
        """启动调度器"""
        pass

    async def stop(self):
        """停止调度器"""
        pass

    async def _start_interval_mode(self, config: Dict):
        """启动固定间隔模式"""
        pass

    async def _start_n_periods_mode(self, config: Dict):
        """启动N周期模式"""
        pass

    async def _update_all_timeframes(self):
        """更新所有时间周期的数据"""
        pass

    async def _update_timeframe(self, timeframe: str):
        """更新指定时间周期的数据"""
        pass

    async def _get_active_symbols(self, exchange: str) -> List[str]:
        """获取活跃的交易对列表"""
        pass
```

#### 调度模式配置

**固定间隔模式**:
```python
# 所有时间周期统一按5秒间隔更新
scheduler.add_job(
    update_all_timeframes,
    'interval',
    seconds=5,
    id='market_data_interval_update'
)
```

**N周期模式**:
```python
# 为每个时间周期设置独立的更新间隔
TIMEFRAME_UPDATE_MAPPING = {
    '1m': 60,      # 每60秒更新
    '5m': 300,     # 每5分钟更新
    '15m': 900,    # 每15分钟更新
    '1h': 3600,    # 每1小时更新
    '4h': 14400,   # 每4小时更新
    '1d': 14400    # 每4小时更新（1d的N倍周期是4h）
}

for timeframe, interval in TIMEFRAME_UPDATE_MAPPING.items():
    scheduler.add_job(
        update_timeframe,
        'interval',
        seconds=interval,
        args=[timeframe],
        id=f'market_data_{timeframe}_update'
    )
```

---

## 4. 数据模型

### 4.1 数据库模型

#### SystemConfig表

```python
# backend/models/system_config.py
from sqlalchemy import Column, Integer, JSON, TIMESTAMP, CheckConstraint
from sqlalchemy.sql import func
from .base import Base

class SystemConfig(Base):
    """系统配置表（单例）"""
    __tablename__ = "system_config"

    id = Column(Integer, primary_key=True, default=1)

    # 市场数据配置（JSON格式）
    market_data = Column(JSON, nullable=False, default={
        "default_exchange": "binance",
        "enabled_exchanges": ["binance", "okx", "bybit", "bitget"],
        "default_klines_limit": 200,
        "cache_config": {
            "ttl": {
                "1m": 60,
                "5m": 300,
                "15m": 900,
                "1h": 3600,
                "4h": 14400,
                "1d": 86400
            },
            "max_size_mb": 512
        },
        "update_mode": "interval",
        "update_interval_seconds": 5,
        "n_periods": 1,
        "auto_failover": True,
        "rate_limit_fallback": True,
        "historical_data_days": {
            "1m": 7,
            "5m": 30,
            "15m": 30,
            "1h": 90,
            "4h": 365,
            "1d": 365
        }
    })

    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint('id = 1', name='single_row_constraint'),
    )
```

#### TechnicalIndicator表

```python
# backend/models/technical_indicator.py
from sqlalchemy import Column, BigInteger, Integer, String, TIMESTAMP, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from .base import Base

class TechnicalIndicator(Base):
    """技术指标数据表"""
    __tablename__ = "technical_indicators"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    trading_pair_id = Column(Integer, ForeignKey("trading_pairs.id", ondelete="CASCADE"), nullable=False)
    timeframe = Column(String(10), nullable=False)  # 1m, 5m, 15m, 1h, 4h, 1d
    timestamp = Column(TIMESTAMP, nullable=False)
    indicator_type = Column(String(20), nullable=False)  # MA, MACD, RSI, BOLL, VOL
    indicator_params = Column(JSON)  # {"period": 14, "type": "EMA"}
    indicator_values = Column(JSON, nullable=False)  # {"ma5": 45230.5, "ma10": 45100.2}
    created_at = Column(TIMESTAMP, server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            'trading_pair_id', 'timeframe', 'timestamp', 'indicator_type', 'indicator_params',
            name='uix_indicator_unique'
        ),
    )
```

### 4.2 API数据模型

#### K线数据响应

```python
# backend/schemas/market_data.py
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class KlineData(BaseModel):
    """单根K线数据"""
    open_time: datetime
    close_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    quote_volume: Optional[float] = None
    trade_count: Optional[int] = None

class KlineResponse(BaseModel):
    """K线数据响应"""
    exchange: str
    symbol: str
    timeframe: str
    data: List[KlineData]
    data_source: str  # "cache" | "database" | "api"
    is_stale: bool = False
    last_update: datetime
```

#### 技术指标响应

```python
class IndicatorValues(BaseModel):
    """指标值"""
    ma5: Optional[List[float]] = None
    ma10: Optional[List[float]] = None
    ma20: Optional[List[float]] = None
    ma30: Optional[List[float]] = None
    macd: Optional[List[float]] = None
    macd_signal: Optional[List[float]] = None
    macd_histogram: Optional[List[float]] = None
    rsi: Optional[List[float]] = None
    boll_upper: Optional[List[float]] = None
    boll_middle: Optional[List[float]] = None
    boll_lower: Optional[List[float]] = None
    volume: Optional[List[float]] = None
    volume_ma: Optional[List[float]] = None

class IndicatorResponse(BaseModel):
    """技术指标响应"""
    exchange: str
    symbol: str
    timeframe: str
    indicators: IndicatorValues
    data_source: str
    calculated_at: datetime
```

#### 系统配置请求/响应

```python
class MarketDataConfig(BaseModel):
    """市场数据配置"""
    default_exchange: str
    enabled_exchanges: List[str]
    default_klines_limit: int
    cache_config: dict
    update_mode: str
    update_interval_seconds: Optional[int] = None
    n_periods: Optional[int] = None
    auto_failover: bool
    rate_limit_fallback: bool
    historical_data_days: dict

class SystemConfigResponse(BaseModel):
    """系统配置响应"""
    market_data: MarketDataConfig
    current_exchange: str  # 当前实际使用的交易所
    last_updated: datetime
```

### 4.3 Redis缓存模型

#### 缓存键命名规范

```python
# backend/core/redis_keys.py
class RedisKeys:
    """Redis缓存键管理"""

    @staticmethod
    def klines(exchange: str, symbol: str, timeframe: str, limit: int) -> str:
        """K线缓存键"""
        return f"klines:{exchange}:{symbol}:{timeframe}:latest:{limit}"

    @staticmethod
    def indicators(
        exchange: str,
        symbol: str,
        timeframe: str,
        indicator_type: str,
        params_hash: str
    ) -> str:
        """技术指标缓存键"""
        return f"indicators:{exchange}:{symbol}:{timeframe}:{indicator_type}:{params_hash}"

    @staticmethod
    def ticker(exchange: str, symbol: str) -> str:
        """实时行情缓存键"""
        return f"ticker:{exchange}:{symbol}"

    @staticmethod
    def exchange_status(exchange: str) -> str:
        """交易所状态缓存键"""
        return f"exchange:status:{exchange}"
```

#### 缓存数据结构

```python
# K线数据缓存（JSON字符串）
{
    "exchange": "binance",
    "symbol": "BTC/USDT",
    "timeframe": "1h",
    "data": [
        {
            "open_time": "2024-01-15T14:00:00Z",
            "close_time": "2024-01-15T14:59:59Z",
            "open": 45230.5,
            "high": 45450.2,
            "low": 45100.3,
            "close": 45320.8,
            "volume": 1234.56
        },
        ...
    ],
    "cached_at": "2024-01-15T15:00:00Z"
}

# 技术指标缓存（JSON字符串）
{
    "indicator_type": "MA",
    "params": {"periods": [5, 10, 20, 30]},
    "values": {
        "ma5": [45230.5, 45240.2, ...],
        "ma10": [45100.2, 45110.5, ...],
        "ma20": [44980.7, 44990.3, ...],
        "ma30": [44850.3, 44860.1, ...]
    },
    "calculated_at": "2024-01-15T15:00:00Z"
}
```

---

## 5. API接口设计

### 5.1 K线数据接口

**端点**: `GET /api/v1/market/klines`

**查询参数**:
| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| exchange | string | 否 | 交易所名称，默认使用系统配置 | binance |
| symbol | string | 是 | 交易对符号 | BTC/USDT |
| timeframe | string | 是 | 时间周期 | 1h |
| limit | integer | 否 | 返回数据条数，默认200 | 200 |

**响应示例**:
```json
{
    "success": true,
    "data": {
        "exchange": "binance",
        "symbol": "BTC/USDT",
        "timeframe": "1h",
        "data": [
            {
                "open_time": "2024-01-15T14:00:00Z",
                "close_time": "2024-01-15T14:59:59Z",
                "open": 45230.5,
                "high": 45450.2,
                "low": 45100.3,
                "close": 45320.8,
                "volume": 1234.56
            }
        ],
        "data_source": "cache",
        "is_stale": false,
        "last_update": "2024-01-15T15:00:00Z"
    }
}
```

---

### 5.2 技术指标接口

**端点**: `GET /api/v1/market/indicators`

**查询参数**:
| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| exchange | string | 否 | 交易所名称 | binance |
| symbol | string | 是 | 交易对符号 | BTC/USDT |
| timeframe | string | 是 | 时间周期 | 1h |
| indicators | string | 是 | 指标类型（逗号分隔） | MA,MACD,RSI |

**响应示例**:
```json
{
    "success": true,
    "data": {
        "exchange": "binance",
        "symbol": "BTC/USDT",
        "timeframe": "1h",
        "indicators": {
            "MA": {
                "ma5": [45230.5, 45240.2, ...],
                "ma10": [45100.2, 45110.5, ...],
                "ma20": [44980.7, 44990.3, ...],
                "ma30": [44850.3, 44860.1, ...]
            },
            "MACD": {
                "macd": [120.5, 125.3, ...],
                "macd_signal": [115.3, 120.1, ...],
                "macd_histogram": [5.2, 5.2, ...]
            },
            "RSI": {
                "rsi": [68.5, 69.2, ...]
            }
        },
        "data_source": "cache",
        "calculated_at": "2024-01-15T15:00:00Z"
    }
}
```

---

### 5.3 实时行情接口

**端点**: `GET /api/v1/market/ticker`

**查询参数**:
| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| exchange | string | 否 | 交易所名称 | binance |
| symbol | string | 是 | 交易对符号 | BTC/USDT |

**响应示例**:
```json
{
    "success": true,
    "data": {
        "exchange": "binance",
        "symbol": "BTC/USDT",
        "last": 45320.8,
        "bid": 45320.5,
        "ask": 45321.0,
        "volume_24h": 12345.67,
        "change_24h": 2.34,
        "high_24h": 45800.0,
        "low_24h": 44200.0,
        "timestamp": "2024-01-15T15:00:00Z"
    }
}
```

---

### 5.4 系统配置接口

**端点**: `GET /api/v1/system/config`

**响应示例**:
```json
{
    "success": true,
    "data": {
        "market_data": {
            "default_exchange": "binance",
            "enabled_exchanges": ["binance", "okx", "bybit", "bitget"],
            "default_klines_limit": 200,
            "cache_config": {
                "ttl": {
                    "1m": 60,
                    "5m": 300,
                    "15m": 900,
                    "1h": 3600,
                    "4h": 14400,
                    "1d": 86400
                },
                "max_size_mb": 512
            },
            "update_mode": "interval",
            "update_interval_seconds": 5,
            "auto_failover": true,
            "rate_limit_fallback": true
        },
        "current_exchange": "binance",
        "last_updated": "2024-01-15T15:00:00Z"
    }
}
```

**端点**: `PUT /api/v1/system/config`

**请求体**:
```json
{
    "market_data": {
        "default_exchange": "okx",
        "update_mode": "n_periods",
        "n_periods": 1
    }
}
```

**响应**: 同GET响应

---

## 6. 错误处理与降级

### 6.1 错误分类

| 错误类型 | HTTP状态码 | 错误代码 | 处理策略 |
|---------|-----------|---------|---------|
| 参数验证失败 | 400 | INVALID_PARAMS | 返回详细错误信息 |
| API限流 | 429 | RATE_LIMITED | 降级到缓存/数据库 |
| 网络错误 | 503 | NETWORK_ERROR | 重试3次，失败则降级 |
| 交易所不可用 | 503 | EXCHANGE_UNAVAILABLE | 触发故障切换 |
| 数据不可用 | 404 | DATA_NOT_AVAILABLE | 返回错误信息 |
| 配置错误 | 400 | INVALID_CONFIG | 返回验证错误 |

### 6.2 降级策略

```mermaid
graph TD
    A[收到请求] --> B{检查限流状态}
    B -->|未限流| C[尝试API请求]
    B -->|已限流| D[跳过API]

    C -->|成功| E[返回API数据]
    C -->|限流| F[标记限流1小时]
    C -->|网络错误| G[重试3次]

    F --> D
    G -->|仍失败| D

    D --> H{检查Redis缓存}
    H -->|命中| I[返回缓存数据]
    H -->|未命中| J{检查数据库}

    J -->|有数据| K[返回数据库数据]
    J -->|无数据| L[返回错误]

    I --> M[更新缓存TTL]
    K --> N[写入缓存]
```

### 6.3 错误响应格式

```json
{
    "success": false,
    "error": {
        "code": "RATE_LIMITED",
        "message": "API rate limit exceeded, using cached data",
        "details": {
            "exchange": "binance",
            "retry_after": "2024-01-15T16:00:00Z",
            "fallback_source": "cache"
        }
    },
    "data": {
        "is_stale": true,
        "cached_at": "2024-01-15T14:30:00Z"
    }
}
```

---

## 7. 性能优化

### 7.1 缓存策略

#### Redis缓存配置

```python
# backend/core/redis_client.py
import redis.asyncio as redis
from typing import Optional

class RedisCache:
    """Redis缓存管理器"""

    def __init__(self, url: str = "redis://localhost:6379/0"):
        self.client = redis.from_url(url, decode_responses=True)

    async def get(self, key: str) -> Optional[str]:
        """获取缓存"""
        return await self.client.get(key)

    async def set(self, key: str, value: str, ttl: int):
        """设置缓存"""
        await self.client.setex(key, ttl, value)

    async def delete(self, key: str):
        """删除缓存"""
        await self.client.delete(key)

    async def get_memory_usage(self) -> dict:
        """获取内存使用情况"""
        info = await self.client.info('memory')
        return {
            "used_memory_mb": info['used_memory'] / 1024 / 1024,
            "used_memory_peak_mb": info['used_memory_peak'] / 1024 / 1024,
            "maxmemory_mb": info['maxmemory'] / 1024 / 1024 if info['maxmemory'] > 0 else None
        }
```

#### 缓存预热

```python
async def warmup_cache():
    """缓存预热：系统启动时预加载热数据"""
    config = await config_service.get_market_data_config()
    exchange = config['default_exchange']

    # 预加载主要交易对的1小时K线
    hot_pairs = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT"]

    for symbol in hot_pairs:
        try:
            klines = await ccxt_manager.fetch_ohlcv(exchange, symbol, "1h", 200)
            cache_key = RedisKeys.klines(exchange, symbol, "1h", 200)
            await cache_service.set(cache_key, json.dumps(klines), ttl=3600)

            logger.info(f"Warmed up cache for {symbol}")
        except Exception as e:
            logger.error(f"Failed to warmup {symbol}: {e}")
```

### 7.2 批量查询优化

```python
async def batch_fetch_indicators(
    symbols: List[str],
    timeframe: str,
    indicators: List[str]
) -> Dict[str, Dict]:
    """批量获取多个交易对的指标"""

    tasks = []
    for symbol in symbols:
        task = indicator_calculator.calculate_indicators(
            await get_klines(symbol, timeframe),
            indicators
        )
        tasks.append(task)

    results = await asyncio.gather(*tasks, return_exceptions=True)

    return {
        symbol: result
        for symbol, result in zip(symbols, results)
        if not isinstance(result, Exception)
    }
```

### 7.3 数据库查询优化

```python
# 使用索引优化查询
# backend/models/kline.py

class Kline(Base):
    """K线数据表"""
    __tablename__ = "klines"

    # ... 字段定义 ...

    __table_args__ = (
        # 复合索引：交易对 + 时间周期 + 时间（降序）
        Index(
            'idx_klines_pair_timeframe_time',
            'trading_pair_id', 'timeframe', 'open_time',
            postgresql_ops={'open_time': 'DESC'}
        ),
        # 分区键索引
        Index('idx_klines_timeframe', 'timeframe'),
    )
```

### 7.4 并发控制

```python
# backend/services/market_data_service.py
from asyncio import Semaphore

class MarketDataService:
    """市场数据服务"""

    def __init__(self):
        # 限制并发API请求数量
        self.api_semaphore = Semaphore(10)
        # 限制并发数据库查询数量
        self.db_semaphore = Semaphore(20)

    async def fetch_klines_with_limit(self, exchange, symbol, timeframe, limit):
        """带并发控制的K线获取"""
        async with self.api_semaphore:
            return await self.ccxt_manager.fetch_ohlcv(
                exchange, symbol, timeframe, limit
            )
```

---

## 8. 监控与日志

### 8.1 性能指标监控

```python
# backend/services/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# API请求计数
api_requests_total = Counter(
    'market_data_api_requests_total',
    'Total API requests',
    ['exchange', 'endpoint', 'status']
)

# API响应时间
api_response_time = Histogram(
    'market_data_api_response_seconds',
    'API response time',
    ['exchange', 'endpoint']
)

# 缓存命中率
cache_hits_total = Counter(
    'market_data_cache_hits_total',
    'Total cache hits',
    ['cache_type']
)

cache_misses_total = Counter(
    'market_data_cache_misses_total',
    'Total cache misses',
    ['cache_type']
)

# 交易所健康状态
exchange_health_status = Gauge(
    'market_data_exchange_health',
    'Exchange health status (1=healthy, 0=unhealthy)',
    ['exchange']
)

# Redis内存使用
redis_memory_usage_mb = Gauge(
    'market_data_redis_memory_mb',
    'Redis memory usage in MB'
)
```

### 8.2 结构化日志

```python
# backend/core/logger.py
import structlog

logger = structlog.get_logger()

# 使用示例
logger.info(
    "klines_fetched",
    exchange="binance",
    symbol="BTC/USDT",
    timeframe="1h",
    source="api",
    count=200,
    duration_ms=150
)

logger.warning(
    "rate_limit_exceeded",
    exchange="binance",
    retry_after="2024-01-15T16:00:00Z",
    fallback_to="cache"
)

logger.error(
    "exchange_unavailable",
    exchange="binance",
    error="Connection timeout",
    failover_to="okx"
)
```

### 8.3 健康检查端点

```python
# backend/api/v1/health.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/health/market-data")
async def market_data_health():
    """市场数据模块健康检查"""

    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {}
    }

    # 检查Redis
    try:
        await redis_client.ping()
        health_status["components"]["redis"] = {"status": "healthy"}
    except Exception as e:
        health_status["components"]["redis"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"

    # 检查PostgreSQL
    try:
        await db.execute("SELECT 1")
        health_status["components"]["database"] = {"status": "healthy"}
    except Exception as e:
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"

    # 检查交易所连接
    config = await config_service.get_market_data_config()
    for exchange in config['enabled_exchanges']:
        is_healthy = await failover_manager.check_exchange_health(exchange)
        health_status["components"][f"exchange_{exchange}"] = {
            "status": "healthy" if is_healthy else "unhealthy"
        }

    return health_status
```

---

## 9. 测试策略

### 9.1 单元测试

```python
# tests/unit/test_ccxt_manager.py
import pytest
from unittest.mock import AsyncMock, patch
from backend.services.ccxt_manager import CCXTManager

@pytest.mark.asyncio
async def test_fetch_ohlcv_success():
    """测试成功获取K线数据"""
    manager = CCXTManager(config_service=AsyncMock())

    with patch.object(manager, 'get_client') as mock_client:
        mock_exchange = AsyncMock()
        mock_exchange.fetch_ohlcv.return_value = [
            [1640000000000, 45000, 45500, 44800, 45200, 1000]
        ]
        mock_client.return_value = mock_exchange

        result = await manager.fetch_ohlcv("binance", "BTC/USDT", "1h", 1)

        assert len(result) == 1
        assert result[0][0] == 1640000000000

@pytest.mark.asyncio
async def test_fetch_ohlcv_rate_limited():
    """测试API限流时的降级处理"""
    manager = CCXTManager(config_service=AsyncMock())

    with patch.object(manager, 'get_client') as mock_client:
        mock_exchange = AsyncMock()
        mock_exchange.fetch_ohlcv.side_effect = ccxt.RateLimitExceeded("Rate limit")
        mock_client.return_value = mock_exchange

        with patch.object(manager, '_fetch_from_cache_or_db') as mock_fallback:
            mock_fallback.return_value = [[1640000000000, 45000, 45500, 44800, 45200, 1000]]

            result = await manager.fetch_ohlcv("binance", "BTC/USDT", "1h", 1)

            assert len(result) == 1
            mock_fallback.assert_called_once()
```

### 9.2 集成测试

```python
# tests/integration/test_market_data_flow.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_klines_api_flow(async_client: AsyncClient):
    """测试K线API完整流程"""

    # 1. 第一次请求：从API获取
    response = await async_client.get(
        "/api/v1/market/klines",
        params={"symbol": "BTC/USDT", "timeframe": "1h", "limit": 10}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["data_source"] in ["api", "cache", "database"]
    assert len(data["data"]["data"]) == 10

    # 2. 第二次请求：应该从缓存获取
    response2 = await async_client.get(
        "/api/v1/market/klines",
        params={"symbol": "BTC/USDT", "timeframe": "1h", "limit": 10}
    )

    data2 = response2.json()
    assert data2["data"]["data_source"] == "cache"
```

### 9.3 性能测试

```python
# tests/performance/test_concurrent_requests.py
import pytest
import asyncio
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_concurrent_klines_requests():
    """测试并发K线请求性能"""

    async with AsyncClient(base_url="http://localhost:8000") as client:
        # 并发100个请求
        tasks = [
            client.get(
                "/api/v1/market/klines",
                params={"symbol": "BTC/USDT", "timeframe": "1h", "limit": 200}
            )
            for _ in range(100)
        ]

        start_time = asyncio.get_event_loop().time()
        responses = await asyncio.gather(*tasks)
        end_time = asyncio.get_event_loop().time()

        duration = end_time - start_time

        # 断言
        assert all(r.status_code == 200 for r in responses)
        assert duration < 5.0  # 100个请求应在5秒内完成

        print(f"Completed 100 concurrent requests in {duration:.2f}s")
        print(f"Average: {duration/100*1000:.2f}ms per request")
```

---

## 10. 部署配置

### 10.1 Docker配置

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 环境变量
ENV PYTHONUNBUFFERED=1
ENV REDIS_URL=redis://redis:6379/0
ENV DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/btc_watcher

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 10.2 Docker Compose配置

```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379/0
      - DATABASE_URL=postgresql+asyncpg://btc_watcher:password@postgres:5432/btc_watcher
      - PROXY_URL=${PROXY_URL:-}
    depends_on:
      - redis
      - postgres
    volumes:
      - ./backend:/app
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=btc_watcher
      - POSTGRES_USER=btc_watcher
      - POSTGRES_PASSWORD=password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  redis_data:
  postgres_data:
```

### 10.3 环境变量配置

```bash
# .env
# 数据库配置
DATABASE_URL=postgresql+asyncpg://btc_watcher:password@localhost:5432/btc_watcher

# Redis配置
REDIS_URL=redis://localhost:6379/0

# 代理配置（可选）
PROXY_URL=http://proxy.example.com:1080

# CCXT配置
CCXT_ENABLE_RATE_LIMIT=true
CCXT_TIMEOUT=30000

# 系统配置
DEFAULT_EXCHANGE=binance
ENABLE_AUTO_FAILOVER=true
UPDATE_MODE=interval
UPDATE_INTERVAL_SECONDS=5

# 日志配置
LOG_LEVEL=INFO
LOG_FORMAT=json
```

---

## 11. 安全考虑

### 11.1 API密钥管理

```python
# backend/core/secrets.py
from cryptography.fernet import Fernet
import os

class SecretsManager:
    """敏感信息加密管理"""

    def __init__(self):
        # 从环境变量获取加密密钥
        key = os.getenv('ENCRYPTION_KEY')
        if not key:
            raise ValueError("ENCRYPTION_KEY not set")
        self.cipher = Fernet(key.encode())

    def encrypt(self, plaintext: str) -> str:
        """加密"""
        return self.cipher.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """解密"""
        return self.cipher.decrypt(ciphertext.encode()).decode()

# 使用示例
secrets = SecretsManager()

# 加密API密钥
encrypted_key = secrets.encrypt("your-api-key")

# 存储到数据库
proxy.api_key = encrypted_key

# 使用时解密
real_key = secrets.decrypt(proxy.api_key)
```

### 11.2 请求验证

```python
# backend/api/dependencies.py
from fastapi import Header, HTTPException

async def verify_api_token(x_api_token: str = Header(...)):
    """验证API令牌"""
    valid_tokens = os.getenv('API_TOKENS', '').split(',')

    if x_api_token not in valid_tokens:
        raise HTTPException(status_code=401, detail="Invalid API token")

    return x_api_token

# 使用示例
@router.get("/market/klines", dependencies=[Depends(verify_api_token)])
async def get_klines(...):
    ...
```

### 11.3 速率限制

```python
# backend/middleware/rate_limit.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# 应用到路由
@router.get("/market/klines")
@limiter.limit("60/minute")  # 每分钟最多60次请求
async def get_klines(request: Request, ...):
    ...
```

---

## 12. 未来扩展

### 12.1 WebSocket实时推送

```python
# backend/api/v1/websocket.py
from fastapi import WebSocket

@router.websocket("/ws/market/{symbol}")
async def market_websocket(websocket: WebSocket, symbol: str):
    """市场数据WebSocket推送"""
    await websocket.accept()

    try:
        while True:
            # 从Redis Pub/Sub获取实时数据
            ticker = await redis_client.get(f"ticker:binance:{symbol}")

            if ticker:
                await websocket.send_json({
                    "type": "ticker",
                    "symbol": symbol,
                    "data": json.loads(ticker)
                })

            await asyncio.sleep(1)
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {symbol}")
```

### 12.2 多时间框架分析

```python
async def analyze_multi_timeframe(symbol: str) -> Dict:
    """多时间框架综合分析"""

    timeframes = ['5m', '15m', '1h', '4h', '1d']

    results = {}
    for tf in timeframes:
        klines = await get_klines(symbol, tf)
        indicators = await calculate_indicators(klines, ['MA', 'RSI', 'MACD'])

        # 分析趋势
        trend = analyze_trend(indicators)

        results[tf] = {
            "trend": trend,
            "strength": calculate_trend_strength(indicators)
        }

    # 综合判断
    overall_signal = combine_timeframe_signals(results)

    return {
        "symbol": symbol,
        "timeframes": results,
        "overall": overall_signal
    }
```

### 12.3 自定义指标支持

```python
class CustomIndicatorRegistry:
    """自定义指标注册中心"""

    def __init__(self):
        self.indicators = {}

    def register(self, name: str, func: Callable):
        """注册自定义指标"""
        self.indicators[name] = func

    async def calculate(self, name: str, klines: List, params: Dict) -> Dict:
        """计算自定义指标"""
        if name not in self.indicators:
            raise ValueError(f"Unknown indicator: {name}")

        return await self.indicators[name](klines, **params)

# 使用示例
registry = CustomIndicatorRegistry()

@registry.register("CUSTOM_MA_CROSS")
async def custom_ma_cross(klines, fast=5, slow=20):
    """自定义MA交叉指标"""
    df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

    ma_fast = df['close'].rolling(window=fast).mean()
    ma_slow = df['close'].rolling(window=slow).mean()

    cross_signal = (ma_fast > ma_slow).astype(int).diff()

    return {
        "ma_fast": ma_fast.tolist(),
        "ma_slow": ma_slow.tolist(),
        "cross_signal": cross_signal.tolist()
    }
```

---

## 13. 总结

### 13.1 模块优势

1. **高性能**: 三层数据访问架构，Redis缓存优先，响应时间<100ms
2. **高可用**: 交易所自动故障切换，限流降级保护
3. **易扩展**: 模块化设计，支持新增交易所、指标、时间周期
4. **易维护**: 清晰的职责划分，完善的日志和监控
5. **成本优化**: 智能缓存策略，减少API调用费用

### 13.2 关键指标

| 指标 | 目标值 | 监控方式 |
|------|--------|---------|
| API响应时间 | P95 < 200ms | Prometheus Histogram |
| 缓存命中率 | > 80% | Prometheus Counter |
| 交易所可用性 | > 99% | Prometheus Gauge |
| 数据延迟 | < 10s | 日志分析 |
| 并发处理能力 | 100 req/s | 负载测试 |

### 13.3 依赖清单

```txt
# backend/requirements.txt (市场数据模块相关)
ccxt>=4.0.0
pandas>=2.0.0
ta>=0.11.0
numpy>=1.24.0
redis>=5.0.0
asyncpg>=0.29.0
APScheduler>=3.10.0
structlog>=23.0.0
prometheus-client>=0.19.0
```

---

**文档版本**: 1.0
**最后更新**: 2025-01-15
**维护者**: BTC Watcher Team
