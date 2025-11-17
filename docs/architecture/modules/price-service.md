# 价格数据服务设计方案

## 数据库表结构设计

### 1. 交易所配置表
```sql
-- 交易所配置表
CREATE TABLE exchanges (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE, -- binance, okx, bybit
    display_name VARCHAR(100) NOT NULL,
    api_base_url VARCHAR(255) NOT NULL,
    websocket_url VARCHAR(255),
    rate_limit_per_minute INTEGER DEFAULT 1200,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 插入初始数据
INSERT INTO exchanges (name, display_name, api_base_url, websocket_url) VALUES
('binance', 'Binance', 'https://api.binance.com', 'wss://stream.binance.com:9443'),
('okx', 'OKX', 'https://www.okx.com', 'wss://ws.okx.com:8443'),
('bybit', 'Bybit', 'https://api.bybit.com', 'wss://stream.bybit.com');
```

### 2. 交易对配置表
```sql
-- 交易对配置表（支持多交易所）
CREATE TABLE trading_pairs (
    id SERIAL PRIMARY KEY,
    exchange_id INTEGER REFERENCES exchanges(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL, -- BTCUSDT
    base_asset VARCHAR(10) NOT NULL, -- BTC
    quote_asset VARCHAR(10) NOT NULL, -- USDT
    price_precision INTEGER DEFAULT 8,
    quantity_precision INTEGER DEFAULT 8,
    min_notional DECIMAL(20,8),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(exchange_id, symbol)
);

-- 创建索引
CREATE INDEX idx_trading_pairs_symbol ON trading_pairs(symbol);
CREATE INDEX idx_trading_pairs_exchange ON trading_pairs(exchange_id);
CREATE INDEX idx_trading_pairs_active ON trading_pairs(is_active);
```

### 3. 实时价格数据表（高频数据）
```sql
-- 实时价格数据表（ticker数据）
CREATE TABLE price_tickers (
    id BIGSERIAL PRIMARY KEY,
    trading_pair_id INTEGER REFERENCES trading_pairs(id) ON DELETE CASCADE,
    price DECIMAL(20,8) NOT NULL,
    bid_price DECIMAL(20,8),
    ask_price DECIMAL(20,8),
    volume_24h DECIMAL(30,8),
    price_change_24h DECIMAL(10,8),
    price_change_percent_24h DECIMAL(10,4),
    high_24h DECIMAL(20,8),
    low_24h DECIMAL(20,8),
    timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建分区表（按月分区）
CREATE TABLE price_tickers_y2024m01 PARTITION OF price_tickers
FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

-- 创建索引
CREATE INDEX idx_price_tickers_pair_time ON price_tickers(trading_pair_id, timestamp DESC);
CREATE INDEX idx_price_tickers_timestamp ON price_tickers(timestamp DESC);
```

### 4. K线数据表（OHLCV数据）
```sql
-- K线数据表
CREATE TABLE klines (
    id BIGSERIAL PRIMARY KEY,
    trading_pair_id INTEGER REFERENCES trading_pairs(id) ON DELETE CASCADE,
    timeframe VARCHAR(10) NOT NULL, -- 1m, 5m, 15m, 1h, 4h, 1d
    open_time TIMESTAMP NOT NULL,
    close_time TIMESTAMP NOT NULL,
    open_price DECIMAL(20,8) NOT NULL,
    high_price DECIMAL(20,8) NOT NULL,
    low_price DECIMAL(20,8) NOT NULL,
    close_price DECIMAL(20,8) NOT NULL,
    volume DECIMAL(30,8) NOT NULL,
    quote_volume DECIMAL(30,8),
    trade_count INTEGER,
    taker_buy_volume DECIMAL(30,8),
    taker_buy_quote_volume DECIMAL(30,8),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(trading_pair_id, timeframe, open_time)
);

-- 创建分区表（按时间范围和交易对分区）
CREATE TABLE klines_1m PARTITION OF klines
FOR VALUES IN ('1m');

CREATE TABLE klines_5m PARTITION OF klines
FOR VALUES IN ('5m');

CREATE TABLE klines_1h PARTITION OF klines
FOR VALUES IN ('1h');

CREATE TABLE klines_1d PARTITION OF klines
FOR VALUES IN ('1d');

-- 创建索引
CREATE INDEX idx_klines_pair_timeframe_time ON klines(trading_pair_id, timeframe, open_time DESC);
CREATE INDEX idx_klines_close_time ON klines(close_time DESC);
```

### 5. 数据同步状态表
```sql
-- 数据同步状态表
CREATE TABLE sync_status (
    id SERIAL PRIMARY KEY,
    source_node_id VARCHAR(100) NOT NULL, -- 远程数据源节点ID
    trading_pair_id INTEGER REFERENCES trading_pairs(id) ON DELETE CASCADE,
    data_type VARCHAR(20) NOT NULL, -- ticker, kline_1m, kline_5m, etc.
    last_sync_timestamp TIMESTAMP,
    last_sync_id BIGINT, -- 最后同步的记录ID
    sync_status VARCHAR(20) DEFAULT 'pending', -- pending, syncing, completed, failed
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(source_node_id, trading_pair_id, data_type)
);

-- 创建索引
CREATE INDEX idx_sync_status_node_pair ON sync_status(source_node_id, trading_pair_id);
CREATE INDEX idx_sync_status_timestamp ON sync_status(last_sync_timestamp);
```

### 6. 数据源节点配置表
```sql
-- 数据源节点配置表（用于多节点数据同步）
CREATE TABLE data_source_nodes (
    id SERIAL PRIMARY KEY,
    node_id VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    api_endpoint VARCHAR(255) NOT NULL, -- http://remote-server:8000/api/v1
    api_key VARCHAR(255), -- 访问远程API的密钥
    is_active BOOLEAN DEFAULT true,
    priority INTEGER DEFAULT 1, -- 同步优先级
    sync_interval_minutes INTEGER DEFAULT 5, -- 同步间隔（分钟）
    max_records_per_sync INTEGER DEFAULT 1000, -- 单次同步最大记录数
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 数据库性能优化

### 1. 分区策略
```sql
-- 自动创建月度分区的函数
CREATE OR REPLACE FUNCTION create_monthly_partition()
RETURNS void AS $$
DECLARE
    start_date date;
    end_date date;
    partition_name text;
BEGIN
    start_date := date_trunc('month', CURRENT_DATE);
    end_date := start_date + interval '1 month';
    partition_name := 'price_tickers_y' || extract(year from start_date) || 'm' || lpad(extract(month from start_date)::text, 2, '0');

    EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF price_tickers FOR VALUES FROM (%L) TO (%L)',
                   partition_name, start_date, end_date);
END;
$$ LANGUAGE plpgsql;

-- 设置定时任务每月创建分区
SELECT cron.schedule('create-partition', '0 0 1 * *', 'SELECT create_monthly_partition();');
```

### 2. 数据清理策略
```sql
-- 清理旧数据的函数
CREATE OR REPLACE FUNCTION cleanup_old_price_data()
RETURNS void AS $$
BEGIN
    -- 删除3个月前的ticker数据
    DELETE FROM price_tickers
    WHERE timestamp < CURRENT_TIMESTAMP - INTERVAL '3 months';

    -- 删除1年前的1分钟K线数据
    DELETE FROM klines
    WHERE timeframe = '1m' AND open_time < CURRENT_TIMESTAMP - INTERVAL '1 year';

    -- 删除2年前的5分钟K线数据
    DELETE FROM klines
    WHERE timeframe = '5m' AND open_time < CURRENT_TIMESTAMP - INTERVAL '2 years';

    -- 日线数据保留5年
    DELETE FROM klines
    WHERE timeframe = '1d' AND open_time < CURRENT_TIMESTAMP - INTERVAL '5 years';
END;
$$ LANGUAGE plpgsql;

-- 设置每周执行清理任务
SELECT cron.schedule('cleanup-old-data', '0 2 * * 0', 'SELECT cleanup_old_price_data();');
```

### 3. 数据压缩和索引优化
```sql
-- 启用时间序列数据压缩（如果使用TimescaleDB）
SELECT add_compression_policy('price_tickers', INTERVAL '7 days');
SELECT add_compression_policy('klines', INTERVAL '30 days');

-- 创建部分索引（仅活跃数据）
CREATE INDEX idx_active_trading_pairs ON trading_pairs(symbol) WHERE is_active = true;
CREATE INDEX idx_recent_price_tickers ON price_tickers(trading_pair_id, timestamp)
WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL '24 hours';
```

## 数据库配置建议

### postgresql.conf 优化配置
```ini
# 内存配置（16GB内存建议）
shared_buffers = 4GB
effective_cache_size = 12GB
work_mem = 256MB
maintenance_work_mem = 1GB

# 时间序列数据优化
wal_buffers = 16MB
checkpoint_completion_target = 0.9
max_wal_size = 2GB
min_wal_size = 512MB

# 连接配置
max_connections = 200
```

这个数据库设计具有以下特点：

1. **分区优化**: 按时间和数据类型分区，提高查询性能
2. **灵活扩展**: 支持多交易所、多时间周期
3. **数据完整性**: 外键约束保证数据一致性
4. **同步机制**: 专门的同步状态表追踪数据同步
5. **性能优化**: 合理的索引策略和数据清理机制

### 7. 技术指标数据表
```sql
-- 技术指标数据表（存储计算后的指标值）
CREATE TABLE technical_indicators (
    id BIGSERIAL PRIMARY KEY,
    trading_pair_id INTEGER REFERENCES trading_pairs(id) ON DELETE CASCADE,
    timeframe VARCHAR(10) NOT NULL, -- 1m, 5m, 15m, 1h, 4h, 1d
    timestamp TIMESTAMP NOT NULL,
    indicator_type VARCHAR(20) NOT NULL, -- MA, MACD, RSI, BOLL, etc.
    indicator_params JSONB, -- {"period": 14, "type": "EMA"} 等参数
    indicator_values JSONB NOT NULL, -- {"ma5": 45230.5, "ma10": 45100.2} 或 {"macd": 120.5, "signal": 115.3, "histogram": 5.2}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(trading_pair_id, timeframe, timestamp, indicator_type, indicator_params)
);

-- 创建索引
CREATE INDEX idx_indicators_pair_timeframe_time ON technical_indicators(trading_pair_id, timeframe, timestamp DESC);
CREATE INDEX idx_indicators_type ON technical_indicators(indicator_type);
CREATE INDEX idx_indicators_timestamp ON technical_indicators(timestamp DESC);

-- 创建分区（按timeframe分区）
CREATE TABLE technical_indicators_1m PARTITION OF technical_indicators
FOR VALUES IN ('1m');

CREATE TABLE technical_indicators_5m PARTITION OF technical_indicators
FOR VALUES IN ('5m');

CREATE TABLE technical_indicators_1h PARTITION OF technical_indicators
FOR VALUES IN ('1h');

CREATE TABLE technical_indicators_1d PARTITION OF technical_indicators
FOR VALUES IN ('1d');
```

### 8. 系统配置表
```sql
-- 系统配置表（全局单例配置）
CREATE TABLE system_config (
    id INTEGER PRIMARY KEY DEFAULT 1, -- 仅一条记录

    -- 市场数据配置
    market_data JSONB DEFAULT '{
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
        "auto_failover": true,
        "rate_limit_fallback": true,
        "historical_data_days": {
            "1m": 7,
            "5m": 30,
            "15m": 30,
            "1h": 90,
            "4h": 365,
            "1d": 365
        }
    }'::jsonb,

    -- 其他系统级配置可以继续扩展
    -- monitoring JSONB DEFAULT '{...}'::jsonb,
    -- logging JSONB DEFAULT '{...}'::jsonb,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT single_row_constraint CHECK (id = 1)
);

-- 插入默认系统配置
INSERT INTO system_config (id) VALUES (1)
ON CONFLICT (id) DO NOTHING;

-- 创建更新触发器
CREATE OR REPLACE FUNCTION update_system_config_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_system_config_timestamp
BEFORE UPDATE ON system_config
FOR EACH ROW
EXECUTE FUNCTION update_system_config_timestamp();
```

## Redis缓存策略设计

### 1. 缓存键命名规范
```
# K线数据缓存
klines:{exchange}:{symbol}:{timeframe}:{start_time}:{end_time}
示例: klines:binance:BTCUSDT:1h:1640000000:1640003600

# 技术指标缓存
indicators:{exchange}:{symbol}:{timeframe}:{indicator_type}:{params_hash}:{start_time}:{end_time}
示例: indicators:binance:BTCUSDT:1h:MA:abc123:1640000000:1640003600

# 实时Ticker缓存
ticker:{exchange}:{symbol}
示例: ticker:binance:BTCUSDT

# 交易所状态缓存
exchange:status:{exchange}
示例: exchange:status:binance
```

### 2. 缓存数据结构
```python
# K线数据 (List of Hashes)
# Key: klines:binance:BTCUSDT:1h:1640000000:1640003600
# Value: [
#   {
#     "open_time": "1640000000",
#     "close_time": "1640003600",
#     "open": "45230.5",
#     "high": "45450.2",
#     "low": "45100.3",
#     "close": "45320.8",
#     "volume": "1234.56"
#   },
#   ...
# ]

# 技术指标数据 (Hash)
# Key: indicators:binance:BTCUSDT:1h:MA:default:1640000000:1640003600
# Value: {
#   "timestamp": "1640003600",
#   "ma5": "45230.5",
#   "ma10": "45100.2",
#   "ma20": "44980.7",
#   "ma30": "44850.3"
# }

# Ticker数据 (Hash with TTL)
# Key: ticker:binance:BTCUSDT
# TTL: 5秒
# Value: {
#   "price": "45320.8",
#   "bid": "45320.5",
#   "ask": "45321.0",
#   "volume_24h": "12345.67",
#   "change_24h": "2.34",
#   "timestamp": "1640003600"
# }
```

### 3. 缓存更新策略
```python
# 三层数据访问优先级
def get_klines(exchange, symbol, timeframe, limit):
    """
    1. 尝试从Redis缓存读取
    2. 缓存未命中，从PostgreSQL读取并更新缓存
    3. 数据库无数据，从CCXT API获取并同时写入缓存和数据库
    """

    # Layer 1: Redis Cache
    cache_key = f"klines:{exchange}:{symbol}:{timeframe}:latest:{limit}"
    cached_data = redis.get(cache_key)
    if cached_data:
        return json.loads(cached_data)

    # Layer 2: PostgreSQL
    db_data = db.query(Klines).filter(
        trading_pair=symbol,
        timeframe=timeframe
    ).order_by(Klines.open_time.desc()).limit(limit).all()

    if db_data:
        # 更新缓存
        ttl = get_ttl_for_timeframe(timeframe)
        redis.setex(cache_key, ttl, json.dumps(db_data))
        return db_data

    # Layer 3: CCXT API
    api_data = ccxt_client.fetch_ohlcv(symbol, timeframe, limit=limit)

    # 同时写入数据库和缓存
    db.bulk_insert(api_data)
    redis.setex(cache_key, ttl, json.dumps(api_data))

    return api_data

# 限流降级策略
def get_klines_with_fallback(exchange, symbol, timeframe, limit):
    """
    遇到API限流时的降级策略
    """
    try:
        return get_klines(exchange, symbol, timeframe, limit)
    except RateLimitError:
        # 降级到仅使用缓存和数据库
        logger.warning(f"API rate limited, falling back to cache/db")

        # 尝试缓存
        cached = get_from_cache(...)
        if cached:
            return cached

        # 降级到数据库历史数据
        return get_from_database(...)
```

### 4. 缓存容量管理
```python
# Redis内存配置
maxmemory: 512mb
maxmemory-policy: allkeys-lru  # LRU淘汰策略

# 监控缓存使用率
def monitor_cache_usage():
    """
    监控Redis缓存使用情况
    """
    info = redis.info('memory')
    used_memory_mb = info['used_memory'] / 1024 / 1024
    max_memory_mb = 512

    usage_percent = (used_memory_mb / max_memory_mb) * 100

    if usage_percent > 90:
        logger.warning(f"Cache usage high: {usage_percent}%")
        # 触发缓存清理或扩容告警
```

## 数据更新调度设计

### 1. 固定间隔模式
```python
# 所有时间周期统一按5秒间隔更新
@scheduler.scheduled_job('interval', seconds=5)
async def update_market_data_interval_mode():
    """
    固定间隔更新模式
    """
    config = get_system_config()
    interval = config['market_data']['update_interval_seconds']

    for exchange in config['market_data']['enabled_exchanges']:
        for symbol in get_active_symbols(exchange):
            for timeframe in ['1m', '5m', '15m', '1h', '4h', '1d']:
                await update_klines(exchange, symbol, timeframe)
                await calculate_indicators(exchange, symbol, timeframe)
```

### 2. N周期模式
```python
# 根据时间周期倍数关系更新（N=1示例）
TIMEFRAME_UPDATE_MAPPING = {
    '1m': 60,      # 每60秒更新
    '5m': 300,     # 每5分钟更新
    '15m': 900,    # 每15分钟更新
    '1h': 3600,    # 每1小时更新
    '4h': 14400,   # 每4小时更新
    '1d': 14400    # 每4小时更新（1d的N倍周期是4h）
}

@scheduler.scheduled_job('interval', seconds=60)
async def update_market_data_n_periods_mode():
    """
    N周期更新模式
    """
    current_time = int(time.time())

    for timeframe, update_interval in TIMEFRAME_UPDATE_MAPPING.items():
        if current_time % update_interval == 0:
            # 到达更新时间点
            await update_timeframe_data(timeframe)
```

### 3. 数据清理优化
```sql
-- 更新数据清理策略（适配技术指标）
CREATE OR REPLACE FUNCTION cleanup_old_market_data()
RETURNS void AS $$
BEGIN
    -- Ticker数据：保留3个月
    DELETE FROM price_tickers
    WHERE timestamp < CURRENT_TIMESTAMP - INTERVAL '3 months';

    -- K线数据按时间周期不同保留
    DELETE FROM klines WHERE timeframe = '1m' AND open_time < CURRENT_TIMESTAMP - INTERVAL '7 days';
    DELETE FROM klines WHERE timeframe = '5m' AND open_time < CURRENT_TIMESTAMP - INTERVAL '30 days';
    DELETE FROM klines WHERE timeframe = '15m' AND open_time < CURRENT_TIMESTAMP - INTERVAL '30 days';
    DELETE FROM klines WHERE timeframe = '1h' AND open_time < CURRENT_TIMESTAMP - INTERVAL '90 days';
    DELETE FROM klines WHERE timeframe = '4h' AND open_time < CURRENT_TIMESTAMP - INTERVAL '1 year';
    DELETE FROM klines WHERE timeframe = '1d' AND open_time < CURRENT_TIMESTAMP - INTERVAL '5 years';

    -- 技术指标数据：与K线保持一致的保留期
    DELETE FROM technical_indicators WHERE timeframe = '1m' AND timestamp < CURRENT_TIMESTAMP - INTERVAL '7 days';
    DELETE FROM technical_indicators WHERE timeframe = '5m' AND timestamp < CURRENT_TIMESTAMP - INTERVAL '30 days';
    DELETE FROM technical_indicators WHERE timeframe = '15m' AND timestamp < CURRENT_TIMESTAMP - INTERVAL '30 days';
    DELETE FROM technical_indicators WHERE timeframe = '1h' AND timestamp < CURRENT_TIMESTAMP - INTERVAL '90 days';
    DELETE FROM technical_indicators WHERE timeframe = '4h' AND timestamp < CURRENT_TIMESTAMP - INTERVAL '1 year';
    DELETE FROM technical_indicators WHERE timeframe = '1d' AND timestamp < CURRENT_TIMESTAMP - INTERVAL '5 years';
END;
$$ LANGUAGE plpgsql;

-- 每天凌晨2点执行清理
SELECT cron.schedule('cleanup-market-data', '0 2 * * *', 'SELECT cleanup_old_market_data();');
```

## 数据库设计总结

这个增强的数据库设计具有以下特点：

1. **技术指标存储**: 独立的technical_indicators表，支持多种指标类型和参数配置
2. **系统配置管理**: 单例SystemConfig表，遵循现有UserSettings的JSON列模式
3. **三层数据访问**: Redis缓存 → PostgreSQL存储 → CCXT API，确保高性能和高可用
4. **灵活的更新策略**: 支持固定间隔和N周期两种模式，满足不同使用场景
5. **限流降级保护**: API限流时自动降级到缓存/数据库，避免服务中断
6. **智能缓存管理**: LRU淘汰策略，自动监控和告警
7. **数据生命周期管理**: 按时间周期设置不同的数据保留期，平衡存储成本和查询需求
8. **分区优化**: 按timeframe分区，提升查询和清理性能