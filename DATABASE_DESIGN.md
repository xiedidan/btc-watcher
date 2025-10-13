# BTC Watcher 数据库设计文档

## 1. 数据库架构

### 1.1 技术选型
- **主数据库**: PostgreSQL 15+
- **缓存数据库**: Redis 7+
- **连接池**: asyncpg (Python异步PostgreSQL客户端)
- **ORM**: SQLAlchemy 2.0 + Alembic (数据库迁移)

### 1.2 数据库分工
- **PostgreSQL**: 持久化数据存储，支持复杂查询和事务
- **Redis**: 缓存、实时数据、WebSocket会话管理

---

## 2. PostgreSQL 表结构设计

### 2.1 用户认证相关

#### users 表
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    language VARCHAR(10) DEFAULT 'zh-CN',
    timezone VARCHAR(50) DEFAULT 'Asia/Shanghai',
    preferences JSONB DEFAULT '{}',
    security_info JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
```

#### user_sessions 表
```sql
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_token_hash ON user_sessions(token_hash);
CREATE INDEX idx_user_sessions_expires_at ON user_sessions(expires_at);
```

### 2.2 FreqTrade版本管理

#### freqtrade_versions 表
```sql
CREATE TABLE freqtrade_versions (
    id SERIAL PRIMARY KEY,
    version VARCHAR(20) UNIQUE NOT NULL,
    release_date DATE,
    type VARCHAR(20) DEFAULT 'stable', -- stable, beta, alpha
    download_url TEXT,
    changelog_url TEXT,
    compatibility_info JSONB DEFAULT '{}',
    is_installed BOOLEAN DEFAULT FALSE,
    install_date TIMESTAMP WITH TIME ZONE,
    install_path VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_freqtrade_versions_version ON freqtrade_versions(version);
CREATE INDEX idx_freqtrade_versions_is_installed ON freqtrade_versions(is_installed);
```

#### freqtrade_upgrade_history 表
```sql
CREATE TABLE freqtrade_upgrade_history (
    id SERIAL PRIMARY KEY,
    from_version VARCHAR(20),
    to_version VARCHAR(20) NOT NULL,
    upgrade_type VARCHAR(20) NOT NULL, -- upgrade, downgrade, install
    status VARCHAR(20) NOT NULL, -- pending, in_progress, completed, failed, rolled_back
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    backup_path VARCHAR(500),
    migration_log JSONB DEFAULT '{}',
    user_id INTEGER REFERENCES users(id)
);

-- 索引
CREATE INDEX idx_upgrade_history_status ON freqtrade_upgrade_history(status);
CREATE INDEX idx_upgrade_history_date ON freqtrade_upgrade_history(started_at);
```

### 2.3 网络代理管理

#### proxies 表
```sql
CREATE TABLE proxies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(20) NOT NULL, -- http, socks4, socks5
    host VARCHAR(255) NOT NULL,
    port INTEGER NOT NULL,
    username VARCHAR(100),
    password_encrypted TEXT, -- 加密存储
    enabled BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 1,
    test_url VARCHAR(500) DEFAULT 'https://api.binance.com/api/v3/ping',
    health_check_config JSONB DEFAULT '{}',
    performance_metrics JSONB DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'unknown', -- healthy, unhealthy, unknown
    last_test_time TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_proxies_enabled ON proxies(enabled);
CREATE INDEX idx_proxies_priority ON proxies(priority);
CREATE INDEX idx_proxies_status ON proxies(status);
```

#### proxy_test_history 表
```sql
CREATE TABLE proxy_test_history (
    id BIGSERIAL PRIMARY KEY,
    proxy_id INTEGER REFERENCES proxies(id) ON DELETE CASCADE,
    test_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    success BOOLEAN NOT NULL,
    latency_ms INTEGER,
    error_message TEXT,
    test_details JSONB DEFAULT '{}'
);

-- 分区表按月分区
CREATE INDEX idx_proxy_test_history_proxy_time ON proxy_test_history(proxy_id, test_time);
CREATE INDEX idx_proxy_test_history_time ON proxy_test_history(test_time);
```

### 2.4 策略管理

#### strategies 表
```sql
CREATE TABLE strategies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    type VARCHAR(50) DEFAULT 'signal_monitor', -- signal_monitor, trade_execution
    version VARCHAR(20) DEFAULT 'v1.0',
    status VARCHAR(20) DEFAULT 'stopped', -- running, stopped, error, starting, stopping
    config JSONB NOT NULL DEFAULT '{}',
    freqtrade_config JSONB NOT NULL DEFAULT '{}',
    signal_thresholds JSONB DEFAULT '{}',
    health_metrics JSONB DEFAULT '{}',
    performance_metrics JSONB DEFAULT '{}',
    is_draft BOOLEAN DEFAULT FALSE,
    draft_expires_at TIMESTAMP WITH TIME ZONE,
    parent_strategy_id INTEGER REFERENCES strategies(id),
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_strategies_name ON strategies(name);
CREATE INDEX idx_strategies_status ON strategies(status);
CREATE INDEX idx_strategies_type ON strategies(type);
CREATE INDEX idx_strategies_is_draft ON strategies(is_draft);
CREATE INDEX idx_strategies_created_at ON strategies(created_at);
```

#### strategy_versions 表
```sql
CREATE TABLE strategy_versions (
    id SERIAL PRIMARY KEY,
    strategy_id INTEGER REFERENCES strategies(id) ON DELETE CASCADE,
    version VARCHAR(20) NOT NULL,
    config_snapshot JSONB NOT NULL,
    change_summary TEXT,
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(strategy_id, version)
);

-- 索引
CREATE INDEX idx_strategy_versions_strategy_id ON strategy_versions(strategy_id);
CREATE INDEX idx_strategy_versions_is_active ON strategy_versions(is_active);
```

#### strategy_processes 表
```sql
CREATE TABLE strategy_processes (
    id SERIAL PRIMARY KEY,
    strategy_id INTEGER REFERENCES strategies(id) ON DELETE CASCADE,
    pid INTEGER,
    start_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    stop_time TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) NOT NULL, -- starting, running, stopping, stopped, error
    resource_usage JSONB DEFAULT '{}',
    last_heartbeat TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_strategy_processes_strategy_id ON strategy_processes(strategy_id);
CREATE INDEX idx_strategy_processes_status ON strategy_processes(status);
```

### 2.5 信号管理

#### signals 表 (按月分区)
```sql
CREATE TABLE signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    strategy_id INTEGER REFERENCES strategies(id),
    strategy_name VARCHAR(100) NOT NULL,
    strategy_version VARCHAR(20),
    pair VARCHAR(20) NOT NULL,
    exchange VARCHAR(50) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    signal_type VARCHAR(10) NOT NULL, -- BUY, SELL, HOLD
    strength_raw DECIMAL(10,4) NOT NULL,
    strength_level VARCHAR(20) NOT NULL, -- strong, medium, weak
    priority VARCHAR(5) NOT NULL, -- P0, P1, P2
    price DECIMAL(20,8) NOT NULL,
    indicators JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    notification_sent BOOLEAN DEFAULT FALSE,
    notification_channels TEXT[] DEFAULT '{}',
    notification_time TIMESTAMP WITH TIME ZONE
) PARTITION BY RANGE (timestamp);

-- 创建分区表 (示例：按月分区)
CREATE TABLE signals_2024_01 PARTITION OF signals
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

-- 索引
CREATE INDEX idx_signals_timestamp ON signals(timestamp);
CREATE INDEX idx_signals_strategy_id ON signals(strategy_id);
CREATE INDEX idx_signals_pair ON signals(pair);
CREATE INDEX idx_signals_signal_type ON signals(signal_type);
CREATE INDEX idx_signals_strength_level ON signals(strength_level);
CREATE INDEX idx_signals_composite ON signals(strategy_id, pair, timestamp);
```

### 2.6 通知管理

#### notification_channels 表
```sql
CREATE TABLE notification_channels (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    type VARCHAR(20) NOT NULL, -- sms, email, wechat, feishu, telegram
    enabled BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 1,
    config JSONB NOT NULL DEFAULT '{}',
    rate_limit_config JSONB DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'unknown', -- healthy, error, unknown
    last_test_time TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_notification_channels_type ON notification_channels(type);
CREATE INDEX idx_notification_channels_enabled ON notification_channels(enabled);
```

#### notification_history 表 (按月分区)
```sql
CREATE TABLE notification_history (
    id BIGSERIAL PRIMARY KEY,
    signal_id UUID REFERENCES signals(id),
    channel_id INTEGER REFERENCES notification_channels(id),
    channel_type VARCHAR(20) NOT NULL,
    message_type VARCHAR(20) NOT NULL, -- signal, alert, system
    content TEXT NOT NULL,
    status VARCHAR(20) NOT NULL, -- pending, sent, failed, retry
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    response_code INTEGER,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}'
) PARTITION BY RANGE (sent_at);

-- 索引
CREATE INDEX idx_notification_history_signal_id ON notification_history(signal_id);
CREATE INDEX idx_notification_history_channel_id ON notification_history(channel_id);
CREATE INDEX idx_notification_history_status ON notification_history(status);
CREATE INDEX idx_notification_history_sent_at ON notification_history(sent_at);
```

### 2.7 系统监控

#### system_metrics 表
```sql
CREATE TABLE system_metrics (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metric_type VARCHAR(50) NOT NULL, -- cpu, memory, disk, network
    component VARCHAR(50) NOT NULL, -- api, freqtrade, database, redis
    value DECIMAL(10,4) NOT NULL,
    unit VARCHAR(20) NOT NULL,
    metadata JSONB DEFAULT '{}'
);

-- 索引
CREATE INDEX idx_system_metrics_timestamp ON system_metrics(timestamp);
CREATE INDEX idx_system_metrics_type_component ON system_metrics(metric_type, component);
```

#### error_logs 表
```sql
CREATE TABLE error_logs (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    level VARCHAR(20) NOT NULL, -- DEBUG, INFO, WARNING, ERROR, CRITICAL
    component VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    stack_trace TEXT,
    context JSONB DEFAULT '{}',
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP WITH TIME ZONE
);

-- 索引
CREATE INDEX idx_error_logs_timestamp ON error_logs(timestamp);
CREATE INDEX idx_error_logs_level ON error_logs(level);
CREATE INDEX idx_error_logs_component ON error_logs(component);
CREATE INDEX idx_error_logs_resolved ON error_logs(resolved);
```

---

## 3. Redis 数据结构设计

### 3.1 缓存数据

#### 策略状态缓存
```
Key: "strategy:status:{strategy_id}"
Type: Hash
TTL: 60 seconds
Fields:
- status: "running"
- health_score: "92"
- uptime: "7920"
- last_update: "1642252530"
```

#### 实时信号缓存
```
Key: "signals:realtime"
Type: List (FIFO)
TTL: 24 hours
Data: JSON字符串 (最新100个信号)
```

#### 系统状态缓存
```
Key: "system:status"
Type: Hash
TTL: 30 seconds
Fields:
- cpu_percent: "45.2"
- memory_percent: "62.1"
- active_strategies: "5"
- total_signals_24h: "156"
```

### 3.2 会话管理

#### WebSocket会话
```
Key: "ws:session:{user_id}"
Type: Hash
TTL: 24 hours
Fields:
- connection_id: "uuid"
- connected_at: "timestamp"
- last_ping: "timestamp"
```

#### API Rate Limiting
```
Key: "rate_limit:{ip}:{endpoint}"
Type: String (计数器)
TTL: 60 seconds
Value: 请求次数
```

### 3.3 实时数据流

#### 信号推送队列
```
Key: "queue:signals"
Type: Stream
Data: 信号数据JSON
```

#### 通知队列
```
Key: "queue:notifications:{priority}"
Type: List
Data: 通知任务JSON
Priority: P0, P1, P2
```

---

## 4. 数据库优化策略

### 4.1 分区策略

#### 信号表分区
- **分区键**: timestamp (按月分区)
- **分区管理**: 自动创建未来3个月分区，删除12个月前分区
- **查询优化**: 大部分查询都有时间范围限制

#### 通知历史分区
- **分区键**: sent_at (按月分区)
- **保留策略**: 保留6个月历史数据

### 4.2 索引策略

#### 复合索引
```sql
-- 信号查询优化
CREATE INDEX idx_signals_query_optimized ON signals(strategy_id, timestamp DESC, pair);

-- 通知历史查询优化
CREATE INDEX idx_notification_history_query ON notification_history(channel_id, sent_at DESC, status);
```

#### 部分索引
```sql
-- 只索引活跃策略
CREATE INDEX idx_strategies_active ON strategies(id) WHERE status IN ('running', 'starting');

-- 只索引失败通知
CREATE INDEX idx_notification_failed ON notification_history(sent_at) WHERE status = 'failed';
```

### 4.3 查询优化

#### 连接池配置
```python
# asyncpg连接池设置
DATABASE_CONFIG = {
    "min_size": 5,
    "max_size": 20,
    "command_timeout": 60,
    "server_settings": {
        "jit": "off",  # 小查询较多时关闭JIT
        "application_name": "btc_watcher"
    }
}
```

#### 查询缓存策略
- **策略列表**: 缓存5分钟
- **系统状态**: 缓存30秒
- **K线数据**: 缓存根据timeframe动态调整 (1m缓存1分钟，1h缓存30分钟)

---

## 5. 数据迁移和备份

### 5.1 数据库迁移 (Alembic)

#### 初始化迁移环境
```bash
# 初始化Alembic
alembic init migrations

# 创建初始迁移
alembic revision --autogenerate -m "Initial migration"

# 执行迁移
alembic upgrade head
```

#### 版本升级迁移示例
```python
# migrations/versions/xxx_add_signal_thresholds.py
def upgrade():
    op.add_column('strategies',
        sa.Column('signal_thresholds',
                 postgresql.JSONB(),
                 nullable=True,
                 default={}))

    # 为现有策略设置默认阈值
    op.execute("""
        UPDATE strategies
        SET signal_thresholds = '{"strong": 80, "medium": 50, "weak": 20}'
        WHERE signal_thresholds IS NULL
    """)
```

### 5.2 自动备份策略

#### 每日备份脚本
```bash
#!/bin/bash
# scripts/backup.sh

# PostgreSQL备份
pg_dump -h localhost -U btc_watcher btc_watcher | gzip > /backup/pg_$(date +%Y%m%d).sql.gz

# Redis备份
redis-cli --rdb /backup/redis_$(date +%Y%m%d).rdb

# 清理30天前备份
find /backup -name "*.gz" -mtime +30 -delete
find /backup -name "*.rdb" -mtime +30 -delete
```

---

## 6. 性能监控和优化

### 6.1 数据库监控

#### 关键指标监控
```sql
-- 慢查询监控
SELECT query, mean_time, calls, total_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- 表大小监控
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

#### 连接池监控
```python
# 监控连接池状态
async def monitor_db_pool():
    pool_status = {
        "size": db_pool.get_size(),
        "checked_in": db_pool.get_checked_in_size(),
        "overflow": db_pool.get_overflow_size(),
        "checked_out": db_pool.get_checked_out_size()
    }
    return pool_status
```

### 6.2 Redis监控

#### 内存使用监控
```bash
# Redis内存使用
redis-cli info memory | grep used_memory_human

# Key过期监控
redis-cli info keyspace
```

---

## 7. 技术决策和建议

### 7.1 需要确认的数据库设计

1. **信号数据保留策略**:
   - 确认：实时信号Redis保存24小时，历史信号PostgreSQL永久保存 ✓
   - 分区策略：按月分区，永久保存不清理

2. **通知历史保留策略**:
   - 确认：PostgreSQL永久保存，按月分区 ✓
   - 不设置清理策略，允许长期数据分析

3. **性能指标采集频率**:
   - 系统指标：每30秒采集一次 ✓
   - 策略健康检查：每30秒一次 ✓
   - 代理测试：每小时一次
   - 配置文件管理：支持动态调整监控频率 ✓

### 7.2 扩展性考虑

1. **读写分离**: 如果后续数据量增大，可以配置PostgreSQL读写分离
2. **Redis集群**: 单机Redis不够时可以升级到Redis Cluster
3. **分库分表**: 信号表按策略ID进一步分表（目前不需要）

### 7.3 安全性设计

1. **敏感数据加密**: 代理密码、API密钥使用AES-256加密
2. **数据库权限**: 应用账号只有必要的表权限，禁止DROP等危险操作
3. **连接安全**: 生产环境使用SSL连接数据库

这份数据库设计是否满足您的需求？有哪些地方需要调整或补充？

接下来我将创建Docker配置和部署脚本的技术实现细节。