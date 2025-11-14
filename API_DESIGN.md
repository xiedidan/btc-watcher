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

### 2.3.1 策略心跳监控接口

#### GET /api/v1/strategies/{strategy_id}/heartbeat
获取策略心跳状态

**响应**:
```json
{
  "success": true,
  "data": {
    "strategy_id": 123,
    "last_heartbeat_time": "2024-01-15T14:25:30Z",
    "last_pid": 872423,
    "last_version": "2025.9.1",
    "last_state": "RUNNING",
    "timeout_seconds": 300,
    "is_abnormal": false,
    "consecutive_failures": 0,
    "restart_count": 2,
    "last_restart_time": "2024-01-15T10:00:00Z",
    "time_since_last_heartbeat_seconds": 45
  }
}
```

#### GET /api/v1/strategies/{strategy_id}/heartbeat/config
获取策略心跳监控配置

**响应**:
```json
{
  "success": true,
  "data": {
    "strategy_id": 123,
    "enabled": true,
    "timeout_seconds": 300,
    "check_interval_seconds": 30,
    "auto_restart": true,
    "max_restart_attempts": 3,
    "restart_cooldown_seconds": 60,
    "created_at": "2024-01-10T10:00:00Z",
    "updated_at": "2024-01-15T14:25:30Z"
  }
}
```

#### PUT /api/v1/strategies/{strategy_id}/heartbeat/config
更新策略心跳监控配置

**请求体**:
```json
{
  "enabled": true,
  "timeout_seconds": 600,
  "check_interval_seconds": 30,
  "auto_restart": true,
  "max_restart_attempts": 5,
  "restart_cooldown_seconds": 120
}
```

**响应**: 同GET /api/v1/strategies/{strategy_id}/heartbeat/config

#### GET /api/v1/strategies/{strategy_id}/heartbeat/history
获取策略心跳历史记录

**查询参数**:
- `page`: 页码 (默认: 1)
- `page_size`: 每页大小 (默认: 20)
- `start_time`: 开始时间
- `end_time`: 结束时间
- `is_timeout`: 是否只查询超时记录 (true/false)

**响应**:
```json
{
  "success": true,
  "data": {
    "history": [
      {
        "id": 10001,
        "strategy_id": 123,
        "heartbeat_time": "2024-01-15T14:25:30Z",
        "pid": 872423,
        "version": "2025.9.1",
        "state": "RUNNING",
        "is_timeout": false,
        "time_since_last_heartbeat_seconds": 45,
        "created_at": "2024-01-15T14:25:31Z"
      },
      {
        "id": 10000,
        "strategy_id": 123,
        "heartbeat_time": "2024-01-15T14:24:45Z",
        "pid": 872423,
        "version": "2025.9.1",
        "state": "RUNNING",
        "is_timeout": false,
        "time_since_last_heartbeat_seconds": 60,
        "created_at": "2024-01-15T14:24:46Z"
      }
    ]
  },
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 1524,
    "total_pages": 77
  }
}
```

#### GET /api/v1/strategies/{strategy_id}/restart/history
获取策略重启历史记录

**查询参数**:
- `page`: 页码 (默认: 1)
- `page_size`: 每页大小 (默认: 20)
- `start_time`: 开始时间
- `end_time`: 结束时间
- `restart_reason`: 重启原因筛选 (heartbeat_timeout/manual/error)
- `restart_success`: 重启结果筛选 (true/false)

**响应**:
```json
{
  "success": true,
  "data": {
    "history": [
      {
        "id": 501,
        "strategy_id": 123,
        "restart_reason": "heartbeat_timeout",
        "restart_time": "2024-01-15T14:00:00Z",
        "restart_success": true,
        "error_message": null,
        "previous_pid": 872400,
        "new_pid": 872423,
        "created_at": "2024-01-15T14:00:01Z"
      },
      {
        "id": 500,
        "strategy_id": 123,
        "restart_reason": "manual",
        "restart_time": "2024-01-15T10:00:00Z",
        "restart_success": true,
        "error_message": null,
        "previous_pid": 872350,
        "new_pid": 872400,
        "created_at": "2024-01-15T10:00:01Z"
      }
    ]
  },
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 45,
    "total_pages": 3
  }
}
```

#### POST /api/v1/strategies/{strategy_id}/restart
手动重启策略

**请求体**:
```json
{
  "reason": "manual",
  "force": false
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "strategy_id": 123,
    "restart_time": "2024-01-15T14:30:00Z",
    "previous_pid": 872423,
    "new_pid": 872450,
    "restart_success": true
  }
}
```

#### GET /api/v1/system/heartbeat/summary
获取所有策略的心跳监控概览

**响应**:
```json
{
  "success": true,
  "data": {
    "total_strategies": 5,
    "healthy_strategies": 4,
    "abnormal_strategies": 1,
    "total_restarts_today": 3,
    "strategies": [
      {
        "strategy_id": 123,
        "strategy_name": "MA_Cross_BTC_Monitor",
        "last_heartbeat_time": "2024-01-15T14:25:30Z",
        "is_abnormal": false,
        "time_since_last_heartbeat_seconds": 45
      },
      {
        "strategy_id": 124,
        "strategy_name": "RSI_ETH_Monitor",
        "last_heartbeat_time": "2024-01-15T14:20:00Z",
        "is_abnormal": true,
        "time_since_last_heartbeat_seconds": 370
      }
    ]
  }
}
```

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

### 2.7 NotifyHub 通知中心接口

#### 2.7.1 通知渠道配置管理

##### GET /api/v1/notify/channels
获取用户的通知渠道配置列表

**响应**:
```json
{
  "success": true,
  "data": {
    "channels": [
      {
        "id": 1,
        "user_id": 1,
        "channel_type": "telegram",
        "channel_name": "Telegram Bot",
        "enabled": true,
        "priority": 1,
        "supported_priorities": ["P0", "P1", "P2"],
        "config": {
          "bot_token": "123456:ABC***",
          "chat_id": "987654321"
        },
        "rate_limit_enabled": true,
        "max_notifications_per_hour": 60,
        "max_notifications_per_day": 500,
        "total_sent": 1234,
        "total_failed": 12,
        "last_sent_at": "2024-01-15T14:25:30Z",
        "created_at": "2024-01-01T00:00:00Z"
      },
      {
        "id": 2,
        "channel_type": "feishu",
        "channel_name": "飞书群组",
        "enabled": true,
        "priority": 2,
        "supported_priorities": ["P1", "P2"],
        "config": {
          "webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
        }
      },
      {
        "id": 3,
        "channel_type": "discord",
        "channel_name": "Discord频道",
        "enabled": true,
        "priority": 3,
        "supported_priorities": ["P0", "P1", "P2"],
        "config": {
          "webhook_url": "https://discord.com/api/webhooks/xxx/yyy"
        },
        "rate_limit_enabled": true,
        "max_notifications_per_hour": 100,
        "max_notifications_per_day": 1000
      }
    ]
  }
}
```

**Discord配置说明**:

Discord支持两种配置模式：

1. **Webhook模式**（推荐，配置简单）:
```json
{
  "channel_type": "discord",
  "config": {
    "webhook_url": "https://discord.com/api/webhooks/123456789/abcdefg"
  }
}
```

2. **Bot模式**（更强大，需要Bot Token）:
```json
{
  "channel_type": "discord",
  "config": {
    "bot_token": "ABCDEFG",
    "channel_id": "987654321098765432"
  }
}
```

**如何获取Discord Webhook URL**:
1. 打开Discord服务器设置
2. 选择"整合" → "Webhooks"
3. 点击"新建Webhook"
4. 设置名称和选择频道
5. 复制Webhook URL

**Discord消息特性**:
- 使用Embed格式显示通知（更美观）
- 根据优先级自动设置消息颜色：
  - P2（高优先级）: 红色 (#e74c3c)
  - P1（中优先级）: 橙色 (#f39c12)
  - P0（低优先级）: 灰色 (#95a5a6)
- 根据通知类型设置颜色：
  - alert（告警）: 红色
  - signal（交易信号）: 绿色
  - info（信息）: 蓝色
- 自动添加时间戳和元数据字段

##### POST /api/v1/notify/channels
创建新的通知渠道配置

**请求体示例 - Discord Webhook**:
```json
{
  "channel_type": "discord",
  "channel_name": "Discord通知频道",
  "enabled": true,
  "priority": 1,
  "supported_priorities": ["P0", "P1", "P2"],
  "config": {
    "webhook_url": "https://discord.com/api/webhooks/123456789/abcdefg"
  },
  "rate_limit_enabled": true,
  "max_notifications_per_hour": 100,
  "max_notifications_per_day": 1000
}
```

**请求体示例 - Telegram**:
```json
{
  "channel_type": "telegram",
  "channel_name": "我的Telegram",
  "enabled": true,
  "priority": 1,
  "supported_priorities": ["P0", "P1", "P2"],
  "config": {
    "bot_token": "123456:ABCDEFG",
    "chat_id": "987654321"
  },
  "rate_limit_enabled": true,
  "max_notifications_per_hour": 60,
  "max_notifications_per_day": 500
}
```

**支持的渠道类型**:
- `telegram`: Telegram Bot
- `discord`: Discord Bot/Webhook
- `feishu`: 飞书 Webhook
- `wechat`: 企业微信
- `email`: 邮件
- `sms`: 短信

##### PUT /api/v1/notify/channels/{channel_id}
更新通知渠道配置

##### DELETE /api/v1/notify/channels/{channel_id}
删除通知渠道配置

##### POST /api/v1/notify/channels/{channel_id}/test
测试通知渠道连接

**请求体**:
```json
{
  "test_message": "这是一条测试消息"
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "test_result": "success",
    "latency_ms": 256,
    "sent_at": "2024-01-15T14:25:30Z",
    "response_code": 200,
    "error_message": null
  }
}
```

---

#### 2.7.2 频率限制配置

##### GET /api/v1/notify/frequency-limits
获取用户的频率限制配置

**响应**:
```json
{
  "success": true,
  "data": {
    "user_id": 1,
    "p2_min_interval": 0,
    "p1_min_interval": 60,
    "p0_batch_interval": 300,
    "p0_batch_enabled": true,
    "p0_batch_max_size": 10,
    "enabled": true,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-15T14:25:30Z"
  }
}
```

**字段说明**:
- `p2_min_interval`: P2(最高优先级)最小发送间隔(秒)，0表示无限制
- `p1_min_interval`: P1(中等优先级)最小发送间隔(秒)
- `p0_batch_interval`: P0(低优先级)批量发送间隔(秒)
- `p0_batch_enabled`: 是否启用P0批量发送
- `p0_batch_max_size`: 每批最多合并通知数

##### PUT /api/v1/notify/frequency-limits
更新频率限制配置

**请求体**:
```json
{
  "p1_min_interval": 120,
  "p0_batch_interval": 600,
  "p0_batch_enabled": true,
  "p0_batch_max_size": 20
}
```

---

#### 2.7.3 时间规则配置

##### GET /api/v1/notify/time-rules
获取用户的时间规则配置列表

**响应**:
```json
{
  "success": true,
  "data": {
    "time_rules": [
      {
        "id": 1,
        "user_id": 1,
        "rule_name": "工作日规则",
        "enabled": true,
        "quiet_hours_enabled": true,
        "quiet_start_time": "22:00",
        "quiet_end_time": "08:00",
        "quiet_priority_filter": "P2",
        "weekend_mode_enabled": true,
        "weekend_downgrade_p1_to_p0": true,
        "weekend_batch_p0": true,
        "working_hours_enabled": false,
        "working_start_time": "09:00",
        "working_end_time": "18:00",
        "working_days": [1, 2, 3, 4, 5],
        "holiday_mode_enabled": false,
        "holiday_dates": ["2024-01-01", "2024-02-10"],
        "created_at": "2024-01-01T00:00:00Z"
      }
    ]
  }
}
```

**字段说明**:
- `quiet_hours_enabled`: 是否启用勿扰时段
- `quiet_start_time`: 勿扰开始时间(HH:MM格式)
- `quiet_end_time`: 勿扰结束时间
- `quiet_priority_filter`: 勿扰时段只发送此优先级及以上的通知
- `weekend_mode_enabled`: 是否启用周末模式
- `weekend_downgrade_p1_to_p0`: 周末是否将P1降级为P0
- `working_hours_enabled`: 是否启用工作时间限制
- `working_days`: 工作日(1=Monday, 7=Sunday)
- `holiday_mode_enabled`: 是否启用假期模式

##### POST /api/v1/notify/time-rules
创建新的时间规则

##### PUT /api/v1/notify/time-rules/{rule_id}
更新时间规则

##### DELETE /api/v1/notify/time-rules/{rule_id}
删除时间规则

---

#### 2.7.4 发送通知接口

##### POST /api/v1/notify/send
发送通知(通常由业务代码调用)

**请求体**:
```json
{
  "title": "强买入信号",
  "message": "BTC/USDT 出现强买入信号\n信号强度: 85%\n当前价格: $42,500",
  "notification_type": "signal",
  "priority": "P2",
  "metadata": {
    "pair": "BTC/USDT",
    "signal_strength": 0.85,
    "price": 42500.00,
    "action": "BUY"
  },
  "strategy_id": 10,
  "signal_id": 12345
}
```

**字段说明**:
- `title`: 通知标题(必填)
- `message`: 通知内容(必填)
- `notification_type`: 通知类型 - signal/alert/info/system(必填)
- `priority`: 优先级 - P0/P1/P2(默认P1)
- `metadata`: 元数据(可选)
- `strategy_id`: 关联的策略ID(可选)
- `signal_id`: 关联的信号ID(可选)

**响应**:
```json
{
  "success": true,
  "data": {
    "queued": true,
    "notification_id": "uuid",
    "estimated_send_time": "2024-01-15T14:25:30Z",
    "target_channels": ["telegram", "feishu"]
  }
}
```

##### POST /api/v1/notify/batch-send
批量发送通知

**请求体**:
```json
{
  "notifications": [
    {
      "title": "通知1",
      "message": "内容1",
      "notification_type": "info",
      "priority": "P0"
    },
    {
      "title": "通知2",
      "message": "内容2",
      "notification_type": "info",
      "priority": "P0"
    }
  ]
}
```

---

#### 2.7.5 通知历史查询

##### GET /api/v1/notify/history
获取通知历史记录

**查询参数**:
- `page`: 页码(默认: 1)
- `page_size`: 每页大小(默认: 20)
- `channel_type`: 按渠道类型筛选
- `status`: 按状态筛选(sent/failed/pending/batched)
- `notification_type`: 按通知类型筛选
- `priority`: 按优先级筛选
- `start_time`: 开始时间
- `end_time`: 结束时间

**响应**:
```json
{
  "success": true,
  "data": {
    "history": [
      {
        "id": 1001,
        "user_id": 1,
        "title": "强买入信号",
        "message": "BTC/USDT 出现强买入信号...",
        "notification_type": "signal",
        "priority": "P2",
        "channel_type": "telegram",
        "channel_config_id": 1,
        "status": "sent",
        "sent_at": "2024-01-15T14:25:30Z",
        "error_message": null,
        "signal_id": 12345,
        "strategy_id": 10,
        "extra_data": {
          "pair": "BTC/USDT",
          "strength": 0.85
        },
        "created_at": "2024-01-15T14:25:28Z"
      }
    ]
  },
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 1234,
    "total_pages": 62
  }
}
```

##### GET /api/v1/notify/history/{notification_id}
获取单个通知历史详情

---

#### 2.7.6 通知统计接口

##### GET /api/v1/notify/stats
获取通知统计信息

**查询参数**:
- `period`: 统计周期(today/week/month/custom)
- `start_date`: 自定义开始日期
- `end_date`: 自定义结束日期

**响应**:
```json
{
  "success": true,
  "data": {
    "period": "today",
    "total_notifications": 156,
    "by_status": {
      "sent": 145,
      "failed": 8,
      "pending": 3
    },
    "by_priority": {
      "P2": 23,
      "P1": 85,
      "P0": 48
    },
    "by_channel": {
      "telegram": 89,
      "feishu": 67
    },
    "by_type": {
      "signal": 120,
      "alert": 15,
      "info": 21
    },
    "success_rate": 0.949,
    "avg_delivery_time_ms": 456,
    "chart_data": {
      "hourly": [
        {"hour": "00:00", "count": 5},
        {"hour": "01:00", "count": 3},
        {"hour": "02:00", "count": 2}
      ]
    }
  }
}
```

##### GET /api/v1/notify/stats/channels
获取各渠道的统计信息

**响应**:
```json
{
  "success": true,
  "data": {
    "channels": [
      {
        "channel_id": 1,
        "channel_type": "telegram",
        "channel_name": "Telegram Bot",
        "total_sent": 1234,
        "total_failed": 12,
        "success_rate": 0.990,
        "avg_latency_ms": 256,
        "last_sent_at": "2024-01-15T14:25:30Z",
        "last_error": null,
        "last_error_at": null,
        "daily_usage": {
          "sent_today": 45,
          "limit_per_day": 500,
          "remaining": 455
        }
      }
    ]
  }
}
```

---

#### 2.7.7 通知模板管理

##### GET /api/v1/notify/templates
获取通知模板列表

**响应**:
```json
{
  "success": true,
  "data": {
    "templates": [
      {
        "id": 1,
        "name": "交易信号模板",
        "notification_type": "signal",
        "channel_type": "telegram",
        "priority": "P2",
        "template_content": "📊 **{{action}} 信号: {{pair}}**\n\n信号强度: {{strength}}\n当前价格: ${{price}}\n时间: {{timestamp}}",
        "variables": ["action", "pair", "strength", "price", "timestamp"],
        "enabled": true,
        "created_at": "2024-01-01T00:00:00Z"
      }
    ]
  }
}
```

##### POST /api/v1/notify/templates
创建通知模板

**请求体**:
```json
{
  "name": "系统告警模板",
  "notification_type": "alert",
  "channel_type": "feishu",
  "priority": "P2",
  "template_content": "🚨 系统告警\n\n{{alert_title}}\n详情: {{alert_message}}\n时间: {{timestamp}}",
  "variables": ["alert_title", "alert_message", "timestamp"],
  "enabled": true
}
```

##### PUT /api/v1/notify/templates/{template_id}
更新通知模板

##### DELETE /api/v1/notify/templates/{template_id}
删除通知模板

##### POST /api/v1/notify/templates/{template_id}/test
测试通知模板

**请求体**:
```json
{
  "variables": {
    "action": "BUY",
    "pair": "BTC/USDT",
    "strength": "85%",
    "price": "42500.00",
    "timestamp": "2024-01-15 14:25:30"
  }
}
```

---

#### 2.7.8 通知规则管理

##### GET /api/v1/notify/rules
获取通知路由规则

**响应**:
```json
{
  "success": true,
  "data": {
    "rules": [
      {
        "id": 1,
        "name": "强信号立即通知所有渠道",
        "enabled": true,
        "conditions": {
          "notification_type": "signal",
          "priority": "P2",
          "metadata_filter": {
            "signal_strength": {">=": 0.8}
          }
        },
        "actions": {
          "channels": ["telegram", "feishu", "sms"],
          "override_frequency_limit": true
        },
        "priority": 1,
        "created_at": "2024-01-01T00:00:00Z"
      },
      {
        "id": 2,
        "name": "弱信号仅Telegram批量发送",
        "enabled": true,
        "conditions": {
          "notification_type": "signal",
          "priority": "P0"
        },
        "actions": {
          "channels": ["telegram"],
          "force_batch": true
        },
        "priority": 2
      }
    ]
  }
}
```

##### POST /api/v1/notify/rules
创建通知规则

##### PUT /api/v1/notify/rules/{rule_id}
更新通知规则

##### DELETE /api/v1/notify/rules/{rule_id}
删除通知规则

##### PUT /api/v1/notify/rules/reorder
调整规则优先级顺序

**请求体**:
```json
{
  "rule_ids": [3, 1, 2, 4]
}
```

---

#### 2.7.9 NotifyHub 系统管理

##### GET /api/v1/notify/system/health
NotifyHub健康检查

**响应**:
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "queue_size": 3,
    "worker_status": "running",
    "channels_health": {
      "telegram": "healthy",
      "feishu": "healthy",
      "email": "degraded",
      "sms": "unhealthy"
    },
    "last_error": null,
    "uptime_seconds": 86400
  }
}
```

##### POST /api/v1/notify/system/flush-batch
手动触发批量发送队列刷新

**响应**:
```json
{
  "success": true,
  "data": {
    "flushed_count": 15,
    "channels_flushed": ["telegram", "feishu"]
  }
}
```

##### GET /api/v1/notify/system/queue
查看当前通知队列状态

**响应**:
```json
{
  "success": true,
  "data": {
    "queue_size": 5,
    "pending_notifications": [
      {
        "title": "通知1",
        "priority": "P1",
        "created_at": "2024-01-15T14:25:30Z",
        "estimated_send_time": "2024-01-15T14:26:30Z"
      }
    ],
    "batch_queues": {
      "telegram": {
        "p0_count": 8,
        "next_flush_time": "2024-01-15T14:30:00Z"
      }
    }
  }
}
```

---

### 2.8 市场数据接口

#### GET /api/v1/market/klines
获取K线数据（OHLCV）

**查询参数**:
| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| exchange | string | 否 | 交易所名称，默认使用系统配置 | binance |
| symbol | string | 是 | 交易对符号 | BTC/USDT |
| timeframe | string | 是 | 时间周期 | 1h |
| limit | integer | 否 | 返回数据条数，默认200 | 200 |

**响应**:
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
        "volume": 1234.56,
        "quote_volume": 55432.12,
        "trade_count": 15234
      }
    ],
    "data_source": "cache",
    "is_stale": false,
    "last_update": "2024-01-15T15:00:00Z"
  }
}
```

**data_source字段说明**:
- `cache`: 数据来自Redis缓存
- `database`: 数据来自PostgreSQL数据库
- `api`: 数据来自交易所API

**is_stale字段说明**:
- `true`: 数据可能过期（在API限流降级时）
- `false`: 数据为最新

---

#### GET /api/v1/market/indicators
获取技术指标数据

**查询参数**:
| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| exchange | string | 否 | 交易所名称 | binance |
| symbol | string | 是 | 交易对符号 | BTC/USDT |
| timeframe | string | 是 | 时间周期 | 1h |
| indicators | string | 是 | 指标类型（逗号分隔） | MA,MACD,RSI |

**支持的指标类型**:
- `MA`: 移动平均线（MA5, MA10, MA20, MA30）
- `MACD`: MACD指标（MACD线、信号线、柱状图）
- `RSI`: 相对强弱指数
- `BOLL`: 布林带（上轨、中轨、下轨）
- `VOL`: 成交量（成交量、成交量MA）

**响应**:
```json
{
  "success": true,
  "data": {
    "exchange": "binance",
    "symbol": "BTC/USDT",
    "timeframe": "1h",
    "indicators": {
      "MA": {
        "ma5": [45230.5, 45240.2, 45250.8, ...],
        "ma10": [45100.2, 45110.5, 45120.3, ...],
        "ma20": [44980.7, 44990.3, 45000.1, ...],
        "ma30": [44850.3, 44860.1, 44870.5, ...]
      },
      "MACD": {
        "macd": [120.5, 125.3, 130.1, ...],
        "macd_signal": [115.3, 120.1, 125.5, ...],
        "macd_histogram": [5.2, 5.2, 4.6, ...]
      },
      "RSI": {
        "rsi": [68.5, 69.2, 70.1, ...]
      },
      "BOLL": {
        "upper": [45800.0, 45850.0, 45900.0, ...],
        "middle": [45230.5, 45240.2, 45250.8, ...],
        "lower": [44660.0, 44630.0, 44600.0, ...]
      },
      "VOL": {
        "volume": [1234.56, 1456.78, 1678.90, ...],
        "volume_ma": [1500.0, 1510.5, 1520.3, ...]
      }
    },
    "data_source": "cache",
    "calculated_at": "2024-01-15T15:00:00Z"
  }
}
```

---

#### GET /api/v1/market/ticker
获取实时行情数据

**查询参数**:
| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| exchange | string | 否 | 交易所名称 | binance |
| symbol | string | 是 | 交易对符号 | BTC/USDT |

**响应**:
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
    "change_percent_24h": 0.052,
    "high_24h": 45800.0,
    "low_24h": 44200.0,
    "timestamp": "2024-01-15T15:00:00Z"
  }
}
```

---

#### GET /api/v1/system/config
获取系统配置

**响应**:
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
    },
    "current_exchange": "binance",
    "exchange_health": {
      "binance": "healthy",
      "okx": "healthy",
      "bybit": "healthy",
      "bitget": "unhealthy"
    },
    "last_updated": "2024-01-15T15:00:00Z"
  }
}
```

---

#### PUT /api/v1/system/config
更新系统配置

**请求体**:
```json
{
  "market_data": {
    "default_exchange": "okx",
    "update_mode": "n_periods",
    "n_periods": 1,
    "cache_config": {
      "max_size_mb": 1024
    }
  }
}
```

**注意事项**:
- 请求体支持部分更新（深度合并）
- 配置更新后会自动验证合法性
- 部分配置（如update_mode）更新后需要重启调度器

**响应**: 同GET /api/v1/system/config

---

#### GET /api/v1/health/market-data
市场数据模块健康检查

**响应**:
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "timestamp": "2024-01-15T15:00:00Z",
    "components": {
      "redis": {
        "status": "healthy",
        "memory_usage_mb": 256.5,
        "memory_max_mb": 512.0
      },
      "database": {
        "status": "healthy",
        "connection_pool": "5/20"
      },
      "exchange_binance": {
        "status": "healthy",
        "last_check": "2024-01-15T15:00:00Z",
        "latency_ms": 120
      },
      "exchange_okx": {
        "status": "healthy",
        "last_check": "2024-01-15T15:00:00Z",
        "latency_ms": 145
      },
      "exchange_bybit": {
        "status": "healthy",
        "last_check": "2024-01-15T15:00:00Z",
        "latency_ms": 132
      },
      "exchange_bitget": {
        "status": "unhealthy",
        "last_check": "2024-01-15T14:58:00Z",
        "error": "Connection timeout"
      }
    },
    "metrics": {
      "api_requests_total": 15234,
      "cache_hit_rate": 0.85,
      "avg_response_time_ms": 45
    }
  }
}
```

**status字段说明**:
- `healthy`: 所有组件正常
- `degraded`: 部分组件异常但服务可用
- `unhealthy`: 核心组件异常，服务不可用

---

### 2.9 图表数据接口（已废弃，请使用市场数据接口）

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
获取技术指标数据（已废弃，请使用 GET /api/v1/market/indicators）

#### GET /api/v1/charts/signals
获取图表信号标注

**注意**: 本节的K线和技术指标接口已废弃，建议使用2.8节的市场数据接口获取数据。

---

### 2.10 系统监控接口

#### GET /api/v1/system/health
系统整体健康检查

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
