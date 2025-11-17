# BTC Watcher API 参考文档

## 🎯 概述

BTC Watcher提供RESTful API接口，支持系统管理、策略控制、信号监控等核心功能。所有API都使用JSON格式，采用标准的HTTP状态码。

## 🔑 认证方式

### JWT Token认证

系统使用JWT (JSON Web Token) 进行身份认证。

#### 获取Token
```http
POST /api/v1/auth/token
Content-Type: application/x-www-form-urlencoded

username=your_username&password=your_password
```

**响应示例**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

#### 使用Token
在请求头中添加Authorization字段：
```http
GET /api/v1/strategies/
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### Token刷新
Token有效期为30分钟，过期后需要重新获取。

## 📡 基础信息

### 基础URL
- **开发环境**: `http://localhost:8000`
- **生产环境**: `https://your-domain.com`

### 请求格式
- **Content-Type**: `application/json`
- **字符编码**: `UTF-8`

### 响应格式
所有响应都包含以下结构：
```json
{
  "code": 200,
  "message": "success",
  "data": {},
  "timestamp": "2025-10-15T14:30:00Z"
}
```

## 👥 认证模块

### 用户注册
```http
POST /api/v1/auth/register
```

**请求参数**:
```json
{
  "username": "testuser",
  "email": "test@example.com",
  "password": "securepassword123"
}
```

**响应示例**:
```json
{
  "code": 201,
  "message": "User created successfully",
  "data": {
    "id": 1,
    "username": "testuser",
    "email": "test@example.com",
    "is_active": true,
    "created_at": "2025-10-15T14:30:00Z"
  }
}
```

### 用户登录
```http
POST /api/v1/auth/token
```

**请求参数**:
```json
{
  "username": "testuser",
  "password": "securepassword123"
}
```

**响应示例**:
```json
{
  "code": 200,
  "message": "Login successful",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 1800,
    "user": {
      "id": 1,
      "username": "testuser",
      "email": "test@example.com"
    }
  }
}
```

### 获取当前用户信息
```http
GET /api/v1/auth/me
Authorization: Bearer {token}
```

**响应示例**:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "username": "testuser",
    "email": "test@example.com",
    "is_active": true,
    "is_superuser": false,
    "created_at": "2025-10-15T14:30:00Z",
    "last_login": "2025-10-15T15:00:00Z"
  }
}
```

## 🎯 策略管理

### 获取策略列表
```http
GET /api/v1/strategies/?skip=0&limit=10&status=running
Authorization: Bearer {token}
```

**查询参数**:
- `skip` (可选): 跳过的记录数，默认0
- `limit` (可选): 返回的记录数，默认10
- `status` (可选): 策略状态筛选 (running, stopped, error)

**响应示例**:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "strategies": [
      {
        "id": 1,
        "name": "BTC趋势策略",
        "strategy_class": "TrendStrategy",
        "exchange": "binance",
        "timeframe": "1h",
        "port": 8081,
        "status": "running",
        "process_id": 1234,
        "config": {
          "stake_amount": 100,
          "max_open_trades": 3
        },
        "signal_thresholds": {
          "strong": 0.8,
          "medium": 0.6,
          "weak": 0.4
        },
        "created_at": "2025-10-15T10:00:00Z",
        "updated_at": "2025-10-15T14:00:00Z"
      }
    ],
    "total": 15,
    "skip": 0,
    "limit": 10
  }
}
```

### 创建策略
```http
POST /api/v1/strategies/
Authorization: Bearer {token}
```

**请求参数**:
```json
{
  "name": "ETH震荡策略",
  "strategy_class": "RSIStrategy",
  "exchange": "binance",
  "timeframe": "15m",
  "config": {
    "stake_amount": 50,
    "max_open_trades": 2,
    "stoploss": -0.03,
    "take_profit": 0.05
  },
  "signal_thresholds": {
    "strong": 0.8,
    "medium": 0.6,
    "weak": 0.4
  }
}
```

**响应示例**:
```json
{
  "code": 201,
  "message": "Strategy created successfully",
  "data": {
    "id": 2,
    "name": "ETH震荡策略",
    "strategy_class": "RSIStrategy",
    "exchange": "binance",
    "timeframe": "15m",
    "port": 8082,
    "status": "stopped",
    "config": {
      "stake_amount": 50,
      "max_open_trades": 2,
      "stoploss": -0.03,
      "take_profit": 0.05
    },
    "created_at": "2025-10-15T15:00:00Z"
  }
}
```

### 获取策略详情
```http
GET /api/v1/strategies/{strategy_id}
Authorization: Bearer {token}
```

**响应示例**:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "name": "BTC趋势策略",
    "strategy_class": "TrendStrategy",
    "exchange": "binance",
    "timeframe": "1h",
    "port": 8081,
    "status": "running",
    "process_id": 1234,
    "config": {
      "stake_amount": 100,
      "max_open_trades": 3,
      "stoploss": -0.05,
      "take_profit": 0.08
    },
    "signal_thresholds": {
      "strong": 0.8,
      "medium": 0.6,
      "weak": 0.4
    },
    "stats": {
      "total_signals": 156,
      "total_trades": 45,
      "win_rate": 0.64,
      "profit_loss": 0.12
    },
    "created_at": "2025-10-15T10:00:00Z",
    "updated_at": "2025-10-15T14:00:00Z"
  }
}
```

### 更新策略
```http
PUT /api/v1/strategies/{strategy_id}
Authorization: Bearer {token}
```

**请求参数**:
```json
{
  "name": "BTC趋势策略V2",
  "config": {
    "stake_amount": 150,
    "max_open_trades": 4,
    "stoploss": -0.04,
    "take_profit": 0.07
  }
}
```

### 删除策略
```http
DELETE /api/v1/strategies/{strategy_id}
Authorization: Bearer {token}
```

### 启动策略
```http
POST /api/v1/strategies/{strategy_id}/start
Authorization: Bearer {token}
```

**响应示例**:
```json
{
  "code": 200,
  "message": "Strategy started successfully",
  "data": {
    "id": 1,
    "status": "running",
    "process_id": 1234,
    "port": 8081,
    "started_at": "2025-10-15T15:30:00Z"
  }
}
```

### 停止策略
```http
POST /api/v1/strategies/{strategy_id}/stop
Authorization: Bearer {token}
```

**响应示例**:
```json
{
  "code": 200,
  "message": "Strategy stopped successfully",
  "data": {
    "id": 1,
    "status": "stopped",
    "stopped_at": "2025-10-15T16:00:00Z"
  }
}
```

### 获取策略统计
```http
GET /api/v1/strategies/{strategy_id}/stats
Authorization: Bearer {token}
```

**响应示例**:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total_signals": 156,
    "total_trades": 45,
    "win_rate": 0.64,
    "profit_loss": 0.12,
    "sharpe_ratio": 1.8,
    "max_drawdown": 0.08,
    "avg_trade_duration": "2.5h",
    "best_trade": {
      "pair": "BTC/USDT",
      "profit": 0.15,
      "duration": "4h"
    },
    "worst_trade": {
      "pair": "ETH/USDT",
      "profit": -0.05,
      "duration": "1h"
    }
  }
}
```

## 📡 信号管理

### 获取信号列表
```http
GET /api/v1/signals/?skip=0&limit=20&strategy_id=1&signal_strength=strong
Authorization: Bearer {token}
```

**查询参数**:
- `skip` (可选): 跳过的记录数，默认0
- `limit` (可选): 返回的记录数，默认20
- `strategy_id` (可选): 策略ID筛选
- `pair` (可选): 交易对筛选，如"BTC/USDT"
- `action` (可选): 动作筛选 (buy, sell)
- `signal_strength` (可选): 信号强度筛选 (strong, medium, weak)
- `start_date` (可选): 开始时间 (ISO 8601格式)
- `end_date` (可选): 结束时间 (ISO 8601格式)

**响应示例**:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "signals": [
      {
        "id": 123,
        "strategy_id": 1,
        "strategy_name": "BTC趋势策略",
        "pair": "BTC/USDT",
        "action": "buy",
        "signal_strength": "strong",
        "signal_score": 0.85,
        "price": 43250.0,
        "volume": 0.023,
        "timestamp": "2025-10-15T14:32:15Z",
        "profit_loss": 0.08,
        "metadata": {
          "indicators": {
            "macd": 0.8,
            "rsi": 0.75,
            "bollinger": 0.9
          },
          "market_conditions": {
            "volatility": 0.12,
            "volume_spike": true
          }
        }
      }
    ],
    "total": 567,
    "skip": 0,
    "limit": 20
  }
}
```

### 获取信号详情
```http
GET /api/v1/signals/{signal_id}
Authorization: Bearer {token}
```

### 获取策略的信号
```http
GET /api/v1/signals/strategy/{strategy_id}?limit=10
Authorization: Bearer {token}
```

### 获取信号统计
```http
GET /api/v1/signals/stats?strategy_id=1&start_date=2025-10-01&end_date=2025-10-15
Authorization: Bearer {token}
```

**响应示例**:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total_signals": 156,
    "signal_distribution": {
      "strong": 45,
      "medium": 67,
      "weak": 44
    },
    "action_distribution": {
      "buy": 89,
      "sell": 67
    },
    "pair_distribution": {
      "BTC/USDT": 78,
      "ETH/USDT": 45,
      "BNB/USDT": 33
    },
    "daily_stats": [
      {
        "date": "2025-10-14",
        "total": 23,
        "strong": 8,
        "medium": 10,
        "weak": 5
      }
    ]
  }
}
```

### 接收FreqTrade信号（Webhook）
```http
POST /api/v1/signals/webhook/{strategy_id}
Content-Type: application/json
```

**请求参数**:
```json
{
  "pair": "BTC/USDT",
  "action": "buy",
  "signal_strength": 0.85,
  "price": 43250.0,
  "volume": 0.023,
  "timestamp": "2025-10-15T14:32:15Z",
  "metadata": {
    "indicators": {
      "macd": 0.8,
      "rsi": 0.75
    }
  }
}
```

## 🔧 系统管理

### 健康检查
```http
GET /api/v1/system/health
```

**响应示例**:
```json
{
  "code": 200,
  "message": "System is healthy",
  "data": {
    "status": "healthy",
    "timestamp": "2025-10-15T15:00:00Z",
    "services": {
      "database": "healthy",
      "redis": "healthy",
      "freqtrade_gateway": "healthy"
    },
    "version": "1.0.0"
  }
}
```

### 系统容量
```http
GET /api/v1/system/capacity
Authorization: Bearer {token}
```

**响应示例**:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total_capacity": 999,
    "used_capacity": 15,
    "available_capacity": 984,
    "usage_percentage": 1.5,
    "port_range": {
      "start": 8081,
      "end": 9080
    },
    "running_strategies": 15,
    "stopped_strategies": 23,
    "error_strategies": 2
  }
}
```

### 系统信息
```http
GET /api/v1/system/info
Authorization: Bearer {token}
```

**响应示例**:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "version": "1.0.0",
    "environment": "production",
    "database": {
      "type": "postgresql",
      "version": "15.4",
      "connected": true
    },
    "redis": {
      "version": "7.2.0",
      "connected": true
    },
    "system_stats": {
      "total_users": 25,
      "total_strategies": 40,
      "total_signals": 15678,
      "uptime": "2 days, 14 hours"
    }
  }
}
```

### 系统指标
```http
GET /api/v1/system/metrics
Authorization: Bearer {token}
```

**响应示例**:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "system_metrics": {
      "cpu_usage": 45.2,
      "memory_usage": 62.8,
      "disk_usage": 38.5,
      "network_io": {
        "bytes_sent": 1234567,
        "bytes_recv": 987654
      }
    },
    "timestamp": "2025-10-15T15:00:00Z"
  }
}
```

## 📊 监控模块

### 监控概览
```http
GET /api/v1/monitoring/overview
Authorization: Bearer {token}
```

**响应示例**:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "system_overview": {
      "cpu_usage": 45.2,
      "memory_usage": 62.8,
      "disk_usage": 38.5,
      "active_strategies": 15
    },
    "alerts": [
      {
        "id": 1,
        "type": "capacity_warning",
        "message": "System capacity usage above 80%",
        "severity": "warning",
        "created_at": "2025-10-15T14:00:00Z"
      }
    ],
    "recent_signals": 23,
    "system_status": "healthy"
  }
}
```

### 容量趋势
```http
GET /api/v1/monitoring/capacity-trend?days=7
Authorization: Bearer {token}
```

**响应示例**:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "trend_data": [
      {
        "timestamp": "2025-10-08T00:00:00Z",
        "used_capacity": 12,
        "total_capacity": 999,
        "usage_percentage": 1.2
      },
      {
        "timestamp": "2025-10-09T00:00:00Z",
        "used_capacity": 15,
        "total_capacity": 999,
        "usage_percentage": 1.5
      }
    ],
    "prediction": {
      "next_week_forecast": 18,
      "growth_rate": 0.3
    }
  }
}
```

### 获取告警列表
```http
GET /api/v1/monitoring/alerts?status=active&severity=warning
Authorization: Bearer {token}
```

**查询参数**:
- `status` (可选): 告警状态 (active, acknowledged, resolved)
- `severity` (可选): 告警级别 (info, warning, error, critical)

### 确认告警
```http
POST /api/v1/monitoring/alerts/{alert_id}/acknowledge
Authorization: Bearer {token}
```

## 📱 通知模块

### 获取通知列表
```http
GET /api/v1/notifications/?skip=0&limit=10&status=unread
Authorization: Bearer {token}
```

**响应示例**:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "notifications": [
      {
        "id": 1,
        "type": "signal_alert",
        "title": "强信号提醒",
        "message": "BTC趋势策略产生强买入信号",
        "priority": "high",
        "channel": "telegram",
        "status": "unread",
        "sent_at": "2025-10-15T14:32:15Z",
        "created_at": "2025-10-15T14:32:10Z"
      }
    ],
    "total": 15,
    "unread_count": 5
  }
}
```

### 标记通知为已读
```http
POST /api/v1/notifications/{notification_id}/read
Authorization: Bearer {token}
```

### 发送通知
```http
POST /api/v1/notifications/send
Authorization: Bearer {token}
```

**请求参数**:
```json
{
  "type": "custom",
  "title": "系统维护通知",
  "message": "系统将于今晚进行维护升级",
  "priority": "medium",
  "channels": ["telegram", "email"]
}
```

### 获取未读通知数
```http
GET /api/v1/notifications/unread-count
Authorization: Bearer {token}
```

## 📋 状态码说明

### 成功状态码
- `200 OK`: 请求成功
- `201 Created`: 资源创建成功
- `204 No Content`: 请求成功但无返回内容

### 错误状态码
- `400 Bad Request`: 请求参数错误
- `401 Unauthorized`: 未认证或认证失败
- `403 Forbidden`: 权限不足
- `404 Not Found`: 资源不存在
- `409 Conflict`: 资源冲突
- `422 Unprocessable Entity`: 请求格式正确但语义错误
- `429 Too Many Requests`: 请求频率过高
- `500 Internal Server Error`: 服务器内部错误
- `503 Service Unavailable`: 服务不可用

## ⚡ 速率限制

- **认证接口**: 5次/分钟
- **普通API**: 100次/分钟
- **WebSocket**: 无限制，但有过期时间

## 🔌 WebSocket API

### 连接地址
- **开发环境**: `ws://localhost:8000/ws`
- **生产环境**: `wss://your-domain.com/ws`

### 连接示例
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onopen = function(event) {
    // 订阅系统监控
    ws.send(JSON.stringify({
        type: 'subscribe',
        channel: 'system'
    }));
};

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};
```

### 支持的消息类型

#### 订阅请求
```json
{
  "type": "subscribe",
  "channel": "system"  // system, strategies, signals, capacity
}
```

#### 取消订阅
```json
{
  "type": "unsubscribe",
  "channel": "system"
}
```

#### 心跳消息
```json
{
  "type": "ping"
}
```

### 实时数据格式

#### 系统指标
```json
{
  "type": "system_metrics",
  "data": {
    "cpu_usage": 45.2,
    "memory_usage": 62.8,
    "disk_usage": 38.5,
    "active_strategies": 15,
    "timestamp": "2025-10-15T15:00:00Z"
  }
}
```

#### 策略更新
```json
{
  "type": "strategy_update",
  "data": {
    "strategy_id": 1,
    "status": "running",
    "process_id": 1234,
    "port": 8081,
    "timestamp": "2025-10-15T15:00:00Z"
  }
}
```

#### 新信号
```json
{
  "type": "signal_received",
  "data": {
    "signal_id": 123,
    "strategy_id": 1,
    "pair": "BTC/USDT",
    "action": "buy",
    "signal_strength": "strong",
    "price": 43250.0,
    "timestamp": "2025-10-15T15:00:00Z"
  }
}
```

## 💡 使用示例

### Python示例
```python
import requests
import json

# API基础配置
BASE_URL = "http://localhost:8000/api/v1"

# 用户登录
def login(username, password):
    response = requests.post(
        f"{BASE_URL}/auth/token",
        data={"username": username, "password": password}
    )
    return response.json()["data"]["access_token"]

# 获取策略列表
def get_strategies(token):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/strategies/", headers=headers)
    return response.json()["data"]

# 创建策略
def create_strategy(token, strategy_data):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(
        f"{BASE_URL}/strategies/",
        headers=headers,
        json=strategy_data
    )
    return response.json()["data"]

# 使用示例
token = login("testuser", "password123")
strategies = get_strategies(token)
print(f"当前策略数量: {len(strategies['strategies'])}")
```

### JavaScript示例
```javascript
// API客户端类
class BTCWatcherAPI {
    constructor(baseURL) {
        this.baseURL = baseURL;
        this.token = null;
    }

    async login(username, password) {
        const response = await fetch(`${this.baseURL}/auth/token`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `username=${username}&password=${password}`
        });
        
        const data = await response.json();
        this.token = data.data.access_token;
        return this.token;
    }

    async getStrategies() {
        const response = await fetch(`${this.baseURL}/strategies/`, {
            headers: {
                'Authorization': `Bearer ${this.token}`
            }
        });
        
        const data = await response.json();
        return data.data;
    }

    async createStrategy(strategyData) {
        const response = await fetch(`${this.baseURL}/strategies/`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(strategyData)
        });
        
        const data = await response.json();
        return data.data;
    }
}

// 使用示例
const api = new BTCWatcherAPI('http://localhost:8000/api/v1');
await api.login('testuser', 'password123');
const strategies = await api.getStrategies();
console.log(`当前策略数量: ${strategies.strategies.length}`);
```

### curl示例
```bash
# 用户登录
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=password123" | \
  jq -r '.data.access_token')

# 获取策略列表
curl -X GET "http://localhost:8000/api/v1/strategies/" \
  -H "Authorization: Bearer $TOKEN"

# 创建策略
curl -X POST "http://localhost:8000/api/v1/strategies/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "测试策略",
    "strategy_class": "TestStrategy",
    "exchange": "binance",
    "timeframe": "1h"
  }'

# 启动策略
curl -X POST "http://localhost:8000/api/v1/strategies/1/start" \
  -H "Authorization: Bearer $TOKEN"
```

## 📚 相关文档

- [用户手册](user-guide.md) - 详细功能说明
- [部署指南](deployment-guide.md) - 部署配置
- [故障排查](troubleshooting.md) - 常见问题
- [WebSocket协议](../development/) - 实时通信

---

**版本**: v1.0.0
**更新日期**: 2025-10-15
**维护团队**: BTC Watcher Development Team