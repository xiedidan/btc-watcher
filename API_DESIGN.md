# BTC Watcher API 设计文档

## 1. API 架构设计

### 1.1 技术选型

**后端框架**: FastAPI + Python 3.11+
- 高性能异步框架
- 自动生成OpenAPI文档
- 内置数据验证和序列化

**数据库**: PostgreSQL + Redis
- PostgreSQL: 主数据存储
- Redis: 缓存 + 实时数据 + WebSocket会话

**认证方案**: JWT Token
- 简单安全的个人使用认证
- 支持Token过期和刷新

### 1.2 API设计原则

- **RESTful**: 遵循REST设计原则
- **版本控制**: API路径包含版本号 `/api/v1/`
- **统一响应**: 标准化的响应格式
- **错误处理**: 详细的错误码和错误信息
- **分页支持**: 统一的分页参数和响应格式

### 1.3 统一响应格式

```json
{
  "success": true,
  "data": {},
  "message": "操作成功",
  "timestamp": "2024-01-15T14:25:30Z",
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 156,
    "total_pages": 8
  }
}
```

**错误响应格式**:
```json
{
  "success": false,
  "error": {
    "code": "STRATEGY_NOT_FOUND",
    "message": "策略不存在",
    "details": "Strategy with ID 123 not found"
  },
  "timestamp": "2024-01-15T14:25:30Z"
}
```

---

## 2. 核心API接口

### 2.1 认证相关接口

#### POST /api/v1/auth/login
用户登录接口

**请求体**:
```json
{
  "username": "admin",
  "password": "password123"
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_type": "bearer",
    "expires_in": 86400,
    "user": {
      "id": 1,
      "username": "admin",
      "language": "zh-CN",
      "timezone": "Asia/Shanghai"
    }
  }
}
```

#### POST /api/v1/auth/refresh
Token刷新接口

#### POST /api/v1/auth/logout
用户登出接口

---

### 2.2 策略管理接口

#### GET /api/v1/strategies
获取策略列表

**查询参数**:
- `page`: 页码 (默认: 1)
- `page_size`: 每页大小 (默认: 10)
- `status`: 策略状态 (running/stopped/error/draft)
- `type`: 策略类型 (signal_monitor/trade_execution)

**响应**:
```json
{
  "success": true,
  "data": {
    "strategies": [
      {
        "id": 123,
        "name": "MA_Cross_BTC_Monitor",
        "version": "v2.1",
        "type": "signal_monitor",
        "status": "running",
        "health_score": 92,
        "uptime_seconds": 7920,
        "signal_count_24h": 15,
        "last_signal_time": "2024-01-15T14:25:30Z",
        "created_at": "2024-01-10T10:30:00Z",
        "updated_at": "2024-01-15T14:25:30Z"
      }
    ]
  },
  "pagination": {...}
}
```

#### POST /api/v1/strategies
创建新策略

**请求体**:
```json
{
  "name": "MA_Cross_BTC_Monitor",
  "description": "双均线交叉监控策略",
  "type": "signal_monitor",
  "config": {
    "strategy_file": "user_data/strategies/ma_cross.py",
    "strategy_class": "MACrossStrategy",
    "timeframe": "5m",
    "pair_whitelist": ["BTC/USDT", "ETH/USDT"],
    "exchange": "binance",
    "proxy_settings": {
      "enabled": true,
      "proxy_id": 1
    },
    "signal_thresholds": {
      "strong_threshold": 80,
      "medium_threshold": 50,
      "weak_threshold": 20
    }
  },
  "is_draft": false
}
```

#### GET /api/v1/strategies/{strategy_id}
获取策略详情

#### PUT /api/v1/strategies/{strategy_id}
更新策略配置

#### DELETE /api/v1/strategies/{strategy_id}
删除策略

#### POST /api/v1/strategies/{strategy_id}/start
启动策略

#### POST /api/v1/strategies/{strategy_id}/stop
停止策略

#### GET /api/v1/strategies/{strategy_id}/logs
获取策略日志

**查询参数**:
- `page`: 页码
- `level`: 日志级别 (DEBUG/INFO/WARNING/ERROR)
- `start_time`: 开始时间
- `end_time`: 结束时间

---

### 2.3 草稿管理接口

#### GET /api/v1/strategies/drafts
获取草稿列表

#### POST /api/v1/strategies/{strategy_id}/save-draft
保存策略草稿

#### POST /api/v1/strategies/drafts/{draft_id}/publish
发布草稿为正式策略

#### DELETE /api/v1/strategies/drafts/{draft_id}
删除草稿

#### POST /api/v1/strategies/drafts/cleanup
清理过期草稿

---

### 2.4 信号管理接口

#### GET /api/v1/signals
获取信号列表

**查询参数**:
- `page`: 页码
- `page_size`: 每页大小 (默认: 20)
- `strategy_id`: 策略ID筛选
- `pair`: 交易对筛选
- `signal_type`: 信号类型 (BUY/SELL/HOLD)
- `strength_level`: 强度等级 (strong/medium/weak)
- `start_time`: 开始时间
- `end_time`: 结束时间

**响应**:
```json
{
  "success": true,
  "data": {
    "signals": [
      {
        "id": "uuid",
        "timestamp": "2024-01-15T14:25:30Z",
        "strategy_id": 123,
        "strategy_name": "MA_Cross_BTC_Monitor",
        "strategy_version": "v2.1",
        "pair": "BTC/USDT",
        "exchange": "binance",
        "timeframe": "5m",
        "signal_type": "BUY",
        "strength_raw": 85.5,
        "strength_level": "strong",
        "priority": "P0",
        "price": 42500.00,
        "indicators": {
          "rsi": 68.5,
          "macd": 0.25,
          "ma_fast": 42300,
          "ma_slow": 42100
        },
        "notification_sent": true,
        "notification_channels": ["sms", "feishu"]
      }
    ]
  },
  "pagination": {...}
}
```

#### GET /api/v1/signals/{signal_id}
获取信号详情

#### GET /api/v1/signals/stats
获取信号统计信息

**响应**:
```json
{
  "success": true,
  "data": {
    "total_signals_24h": 156,
    "by_type": {
      "BUY": 89,
      "SELL": 67
    },
    "by_strength": {
      "strong": 23,
      "medium": 85,
      "weak": 48
    },
    "by_strategy": {
      "MA_Cross_BTC": 45,
      "RSI_ETH": 32,
      "Custom_SOL": 79
    }
  }
}
```

---

### 2.5 FreqTrade版本管理接口

#### GET /api/v1/freqtrade/version
获取当前版本信息

**响应**:
```json
{
  "success": true,
  "data": {
    "current_version": "2024.1",
    "installed_path": "/app/freqtrade/",
    "install_date": "2024-01-15T10:30:00Z",
    "status": "running",
    "dependency_status": "healthy",
    "last_check": "2024-01-15T14:25:30Z",
    "strategy_compatibility": {
      "total_strategies": 25,
      "compatible_strategies": 25,
      "incompatible_strategies": 0
    }
  }
}
```

#### GET /api/v1/freqtrade/versions
获取可用版本列表

#### POST /api/v1/freqtrade/check-updates
检查版本更新

#### POST /api/v1/freqtrade/compatibility-check
版本兼容性检查

**请求体**:
```json
{
  "target_version": "2024.2"
}
```

#### POST /api/v1/freqtrade/upgrade
执行版本升级

#### POST /api/v1/freqtrade/rollback
版本回滚

---

### 2.6 网络代理管理接口

#### GET /api/v1/proxies
获取代理配置列表

#### POST /api/v1/proxies
创建代理配置

**请求体**:
```json
{
  "name": "主代理SOCKS5",
  "type": "socks5",
  "host": "proxy.example.com",
  "port": 1080,
  "username": "proxyuser",
  "password": "proxypass",
  "enabled": true,
  "priority": 1,
  "test_url": "https://api.binance.com/api/v3/ping",
  "health_check": {
    "interval_seconds": 3600,
    "timeout_seconds": 10,
    "retry_count": 3
  }
}
```

#### PUT /api/v1/proxies/{proxy_id}
更新代理配置

#### DELETE /api/v1/proxies/{proxy_id}
删除代理配置

#### POST /api/v1/proxies/{proxy_id}/test
测试代理连接

**响应**:
```json
{
  "success": true,
  "data": {
    "connectivity": true,
    "latency_ms": 156,
    "success_rate": 95.2,
    "test_time": "2024-01-15T14:25:30Z",
    "error_message": null
  }
}
```

---

### 2.7 通知管理接口

#### GET /api/v1/notifications/channels
获取通知渠道配置

#### PUT /api/v1/notifications/channels
更新通知渠道配置

#### POST /api/v1/notifications/test
测试通知发送

**请求体**:
```json
{
  "channel": "sms",
  "message": "测试消息"
}
```

#### GET /api/v1/notifications/history
获取通知历史

**查询参数**:
- `page`: 页码
- `channel`: 通知渠道筛选
- `status`: 发送状态筛选 (success/failed/pending)
- `start_time`: 开始时间
- `end_time`: 结束时间

---

### 2.8 图表数据接口

#### GET /api/v1/charts/kline
获取K线数据

**查询参数**:
- `pair`: 交易对 (必需)
- `timeframe`: 时间周期 (必需)
- `start_time`: 开始时间
- `end_time`: 结束时间
- `limit`: 数据条数限制

**响应**:
```json
{
  "success": true,
  "data": {
    "pair": "BTC/USDT",
    "timeframe": "5m",
    "data": [
      {
        "timestamp": "2024-01-15T14:25:00Z",
        "open": 42400.00,
        "high": 42520.00,
        "low": 42380.00,
        "close": 42500.00,
        "volume": 125.5
      }
    ]
  }
}
```

#### GET /api/v1/charts/indicators
获取技术指标数据

#### GET /api/v1/charts/signals
获取图表信号标注

---

### 2.9 系统监控接口

#### GET /api/v1/system/health
系统健康检查

**响应**:
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "timestamp": "2024-01-15T14:25:30Z",
    "components": {
      "database": "healthy",
      "redis": "healthy",
      "freqtrade": "healthy",
      "proxy": "healthy"
    },
    "metrics": {
      "cpu_percent": 45.2,
      "memory_percent": 62.1,
      "disk_percent": 28.5,
      "uptime_seconds": 7920
    }
  }
}
```

#### GET /api/v1/system/stats
系统统计信息

---

## 3. WebSocket 实时接口

### 3.1 连接认证

```javascript
// 连接时需要提供JWT Token
const ws = new WebSocket('ws://localhost:8000/ws?token=jwt_token_here');
```

### 3.2 消息格式

**标准消息格式**:
```json
{
  "type": "signal_update",
  "data": {...},
  "timestamp": "2024-01-15T14:25:30Z"
}
```

### 3.3 消息类型

#### signal_update
新信号通知
```json
{
  "type": "signal_update",
  "data": {
    "signal": {...}  // 完整信号数据
  }
}
```

#### strategy_status_update
策略状态更新
```json
{
  "type": "strategy_status_update",
  "data": {
    "strategy_id": 123,
    "status": "running",
    "health_score": 92
  }
}
```

#### system_alert
系统告警
```json
{
  "type": "system_alert",
  "data": {
    "level": "warning",
    "message": "代理连接异常",
    "component": "proxy"
  }
}
```

---

## 4. 关键技术问题和建议

### 4.1 技术架构问题

**问题1: FreqTrade集成方式**
- **选项A**: 通过FreqTrade的REST API集成 (REST API仅支持查看，Alpha状态)
- **选项B**: 直接集成FreqTrade代码库 (采用)
- **确认**: 使用选项B，通过Docker容器内代码集成，直接控制FreqTrade实例

**问题2: 实时数据推送方案**
- **选项A**: WebSocket + Redis pub/sub
- **选项B**: Server-Sent Events (SSE)
- **建议**: 使用选项A，支持双向通信

**问题3: 策略配置热更新**
- **方案**: 通过API修改FreqTrade配置文件，然后发送重载信号
- **考虑**: 需要处理配置验证和回滚机制

### 4.2 数据存储问题

**问题4: 信号数据存储策略**
- **实时信号**: Redis (保存24小时)
- **历史信号**: PostgreSQL (永久保存) ✓
- **分区策略**: 按月分区，提高查询性能

**问题5: 通知历史数据管理**
- **保留策略**: PostgreSQL永久保存 ✓
- **分区策略**: 按月分区，不设置清理策略

### 4.3 安全性问题

**问题6: API安全防护**
- **Rate Limiting**: 限制API调用频率
- **数据验证**: 严格的输入验证和清理
- **敏感数据**: 代理密码、API密钥的加密存储

### 4.4 性能优化问题

**问题7: 系统监控频率**
- **系统状态缓存**: Redis缓存30秒 ✓
- **策略状态更新**: 30秒更新频率 ✓
- **图表数据缓存**: Redis缓存10分钟
- **配置文件管理**: 所有监控参数通过配置文件统一管理 ✓

**问题8: 数据库连接池**
- **推荐配置**: asyncpg连接池，最小5个连接，最大20个连接

---

## 5. 需要确认的技术决策

### 5.1 急需确认的问题

1. **FreqTrade版本**: 使用FreqTrade 2025.8作为初始版本 ✓
2. **数据保留策略**: 信号历史数据永久保存 ✓，通知历史数据永久保存 ✓
3. **并发策略数量**: 预期同时运行3-5个策略 ✓
4. **代理轮换策略**: 多个代理时的负载均衡和故障切换策略 ✓
5. **通知频率限制**: 具体的通知发送频率限制规则 ✓
6. **版本升级策略**: 用户手动触发升级，不使用自动升级 ✓

### 5.2 可选的技术增强

1. **API文档**: 是否需要集成Swagger UI进行API文档展示？
2. **监控告警**: 是否需要集成Prometheus + Grafana进行系统监控？
3. **日志聚合**: 是否需要ELK stack进行日志分析？
4. **备份策略**: 数据库自动备份的频率和保留策略？

请您review这份API设计，并告诉我：
1. 哪些接口设计需要调整？
2. 有哪些遗漏的功能接口？
3. 对于提出的技术问题，您的倾向性选择？
4. 是否有其他技术考虑因素？

接下来我会基于您的反馈完善数据库设计和技术实现细节。