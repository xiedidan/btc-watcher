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

接下来我将设计价格订阅服务的具体实现。