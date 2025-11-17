# 实时数据通信Fallback设计方案

## 📋 文档信息
- **版本**: 1.0
- **创建日期**: 2025-10-29
- **目标**: 实现WebSocket → HTTP轮询的自动降级机制
- **状态**: 待审核

---

## 1. 问题背景

### 1.1 现状
当前系统实时数据推送采用 **WebSocket** 方式：
- 前端通过WebSocket连接到后端 `/api/v1/ws`
- 后端推送实时数据（monitoring、strategies、signals、capacity）
- 依赖Nginx、FRP等中间层正确配置

### 1.2 存在的问题
1. **连接失败场景**：
   - FRP代理配置不当
   - Nginx WebSocket配置错误
   - 网络防火墙阻止WebSocket
   - Token过期导致认证失败

2. **用户体验影响**：
   - WebSocket连接失败时，前端完全无法获取实时数据
   - 用户看到的是空白或过期数据
   - 无任何降级或补偿机制

### 1.3 设计目标
实现 **渐进增强（Progressive Enhancement）** 策略：
- ✅ WebSocket可用时：使用WebSocket实时推送（最佳体验）
- ✅ WebSocket不可用时：自动降级到HTTP轮询（保证可用性）
- ✅ 自动检测和切换：无需用户手动干预
- ✅ 平滑过渡：切换时不丢失数据

---

## 2. 设计方案

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                     前端应用层                                │
├─────────────────────────────────────────────────────────────┤
│  Dashboard.vue  │  Strategies.vue  │  Monitoring.vue  │...  │
└────────────┬────────────────────────────────────────────────┘
             │
             ├─────────────────────────────────────────────────┐
             │                                                 │
             ▼                                                 ▼
┌─────────────────────────┐                    ┌─────────────────────────┐
│  Realtime Data Service  │◄──────切换──────►  │   Polling Data Service  │
│  (WebSocket优先)         │                    │   (HTTP轮询降级)         │
└────────────┬────────────┘                    └────────────┬────────────┘
             │                                               │
             ▼                                               ▼
┌─────────────────────────┐                    ┌─────────────────────────┐
│   WebSocket Client      │                    │    HTTP Client (Axios)  │
│   (utils/websocket.js)  │                    │    (api/index.js)       │
└────────────┬────────────┘                    └────────────┬────────────┘
             │                                               │
             │ ws://                                         │ http://
             ▼                                               ▼
┌─────────────────────────────────────────────────────────────┐
│                        后端服务                              │
│  /api/v1/ws (WebSocket)  │  /api/v1/monitoring/* (REST)    │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 核心组件设计

#### 2.2.1 数据获取抽象层 (Realtime Data Adapter)

**新建文件**: `frontend/src/utils/realtimeDataAdapter.js`

**职责**：
- 统一的数据获取接口
- 自动检测和切换传输模式
- 管理轮询定时器
- 数据格式统一化

**接口设计**：
```javascript
class RealtimeDataAdapter {
  // 配置
  config = {
    pollingInterval: 5000,      // 轮询间隔（毫秒）
    wsRetryAttempts: 3,         // WebSocket重试次数
    wsRetryDelay: 3000,         // WebSocket重试延迟
    fallbackDelay: 10000        // 降级等待时间
  }

  // 方法
  connect(token)                // 连接（优先WebSocket）
  disconnect()                  // 断开连接
  subscribe(topic)              // 订阅主题
  unsubscribe(topic)            // 取消订阅

  // 内部方法
  _tryWebSocket()               // 尝试WebSocket连接
  _fallbackToPolling()          // 降级到轮询
  _startPolling()               // 启动轮询
  _stopPolling()                // 停止轮询
  _pollData(topic)              // 轮询单个主题数据
}
```

#### 2.2.2 WebSocket Store 改造

**修改文件**: `frontend/src/stores/websocket.js`

**改动点**：
1. 新增状态字段：
```javascript
state: () => ({
  // 现有字段...

  // 新增字段
  connectionMode: 'websocket',    // 'websocket' | 'polling'
  pollingTimers: {},              // 轮询定时器
  pollingInterval: 5000,          // 轮询间隔（可配置）
  failoverEnabled: true,          // 是否启用降级
})
```

2. 新增方法：
```javascript
actions: {
  // 现有方法...

  // 新增方法
  enablePollingMode()             // 启用轮询模式
  disablePollingMode()            // 禁用轮询模式
  startTopicPolling(topic)        // 启动主题轮询
  stopTopicPolling(topic)         // 停止主题轮询
  pollMonitoring()                // 轮询监控数据
  pollStrategies()                // 轮询策略数据
  pollSignals()                   // 轮询信号数据
  pollCapacity()                  // 轮询容量数据
}
```

---

## 3. 详细实现方案

### 3.1 连接流程

```
开始登录
    │
    ▼
获取JWT Token
    │
    ▼
尝试WebSocket连接
    │
    ├─ 成功 ──────────────────────────┐
    │                                 ▼
    │                        使用WebSocket模式
    │                        订阅所有主题
    │                        实时接收推送
    │
    └─ 失败（3次重试后）
        │
        ▼
    触发降级机制
        │
        ▼
    切换到轮询模式
        │
        ▼
    启动定时轮询
    - monitoring: 每5秒
    - strategies: 每5秒
    - signals: 每10秒
    - capacity: 每30秒
```

### 3.2 降级触发条件

**自动降级场景**：
1. WebSocket连接超时（10秒内未收到connected消息）
2. WebSocket连接被拒绝（403/401）
3. WebSocket连接异常关闭（code !== 1000）
4. 连续3次重连失败

**降级策略**：
```javascript
// 伪代码
if (websocketFailed && retryAttempts >= MAX_RETRIES) {
  console.warn('WebSocket unavailable, falling back to polling')
  this.connectionMode = 'polling'
  this.startPolling()
}
```

### 3.3 数据同步机制

#### WebSocket模式
```javascript
// 服务端主动推送
ws.on('data', (message) => {
  switch(message.topic) {
    case 'monitoring':
      this.monitoringData = message.data
      break
    // ...
  }
})
```

#### 轮询模式
```javascript
// 客户端定时拉取
setInterval(async () => {
  const data = await monitoringAPI.system()
  this.monitoringData = data
}, 5000)
```

### 3.4 轮询API映射

| 主题 (Topic) | WebSocket推送 | HTTP轮询API | 轮询间隔 |
|-------------|--------------|-------------|---------|
| monitoring  | `{type:'data', topic:'monitoring'}` | `GET /api/v1/monitoring/system` | 5秒 |
| strategies  | `{type:'data', topic:'strategies'}` | `GET /api/v1/strategies/overview` | 5秒 |
| signals     | `{type:'data', topic:'signals'}` | `GET /api/v1/signals/?last_id=X&limit=10` | 10秒 |
| capacity    | `{type:'data', topic:'capacity'}` | `GET /api/v1/system/capacity` | 30秒 |

---

## 4. 文件修改范围

### 4.1 设计文档修改

#### 📄 API_DESIGN.md
**修改位置**: 第3章 "WebSocket 实时接口"

**新增内容**:
```markdown
### 3.4 降级机制 (Fallback Strategy)

当WebSocket不可用时，前端自动降级到HTTP轮询模式：

#### 轮询API端点映射

1. **监控数据**:
   - WebSocket: `{type:'data', topic:'monitoring'}`
   - 轮询: `GET /api/v1/monitoring/system`
   - 间隔: 5秒

2. **策略状态**:
   - WebSocket: `{type:'data', topic:'strategies'}`
   - 轮询: `GET /api/v1/strategies/overview`
   - 间隔: 5秒

3. **信号数据**:
   - WebSocket: `{type:'data', topic:'signals'}`
   - 轮询: `GET /api/v1/signals/?last_id={last_id}&limit=10`
   - 间隔: 10秒

4. **容量数据**:
   - WebSocket: `{type:'data', topic:'capacity'}`
   - 轮询: `GET /api/v1/system/capacity`
   - 间隔: 30秒

#### 降级触发条件

- WebSocket连接失败（连续3次重试）
- 认证失败（Token过期）
- 网络不支持WebSocket协议
```

#### 📄 DESIGN.md
**修改位置**: 1.2.1 前端Web UI

**新增内容**:
```markdown
- **实时通信**: WebSocket优先，HTTP轮询降级
  - WebSocket: 服务端主动推送，延迟<100ms
  - HTTP轮询: 客户端定时拉取，延迟3-30秒
  - 自动检测和切换
```

### 4.2 前端代码修改

#### 📁 frontend/src/utils/realtimeDataAdapter.js
**状态**: 新建文件
**代码行数**: ~300行
**职责**: 实时数据获取抽象层

#### 📁 frontend/src/stores/websocket.js
**状态**: 修改现有文件
**修改点**:
- 新增状态字段（connectionMode、pollingTimers等）
- 新增轮询相关方法
- 修改connect方法（增加降级逻辑）

#### 📁 frontend/src/stores/user.js
**状态**: 修改现有文件
**修改点**:
- 使用realtimeDataAdapter替代直接调用wsClient

#### 📁 frontend/src/utils/websocket.js
**状态**: 修改现有文件
**修改点**:
- 增加连接失败回调
- 增加重试计数器
- 暴露连接状态

### 4.3 后端代码修改

#### 📁 backend/api/v1/strategies.py
**状态**: 修改现有文件
**新增端点**:
```python
@router.get("/overview")
async def get_strategies_overview(db: AsyncSession = Depends(get_db)):
    """
    获取策略概览（用于轮询）
    返回所有策略的运行状态摘要
    """
    # 实现...
```

#### 📁 backend/api/v1/signals.py
**状态**: 修改现有文件
**优化端点**:
```python
@router.get("/")
async def list_signals(
    last_id: int = 0,          # 新增：增量查询参数
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """
    获取信号列表（支持增量查询）
    last_id: 上次查询的最后一个信号ID
    """
    # 实现...
```

---

## 5. 配置参数设计

### 5.1 前端配置文件

**新建文件**: `frontend/src/config/realtime.js`

```javascript
export const REALTIME_CONFIG = {
  // WebSocket配置
  websocket: {
    enabled: true,              // 是否启用WebSocket
    retryAttempts: 3,           // 最大重试次数
    retryDelay: 3000,           // 重试延迟（毫秒）
    heartbeatInterval: 25000,   // 心跳间隔
    connectionTimeout: 10000    // 连接超时
  },

  // 轮询配置
  polling: {
    enabled: true,              // 是否启用轮询降级
    fallbackDelay: 10000,       // 降级等待时间
    intervals: {
      monitoring: 5000,         // 监控数据轮询间隔
      strategies: 5000,         // 策略状态轮询间隔
      signals: 10000,           // 信号数据轮询间隔
      capacity: 30000           // 容量数据轮询间隔
    }
  },

  // 调试选项
  debug: {
    forcePolling: false,        // 强制使用轮询模式（测试用）
    logConnections: true        // 记录连接日志
  }
}
```

### 5.2 用户设置扩展

**修改表**: `user_settings`

**新增字段**:
```sql
ALTER TABLE user_settings
ADD COLUMN realtime_mode VARCHAR(20) DEFAULT 'auto',  -- 'auto' | 'websocket' | 'polling'
ADD COLUMN polling_interval INTEGER DEFAULT 5000;      -- 自定义轮询间隔
```

**前端设置页面新增选项**:
```
实时数据模式:
  ○ 自动选择（推荐）
  ○ 仅WebSocket
  ○ 仅轮询

轮询间隔: [滑块: 3秒 ←→ 30秒]
```

---

## 6. 用户体验设计

### 6.1 连接状态指示器

**位置**: 页面右上角或底部状态栏

**状态展示**:
```
🟢 实时连接 (WebSocket)
🟡 轮询模式 (5秒刷新)
🔴 离线
```

**交互**:
- 点击状态图标显示详细信息
- 提供"重试WebSocket"按钮

### 6.2 降级提示

**场景**: WebSocket降级到轮询时

**提示内容**:
```
ℹ️ 实时推送不可用，已切换到轮询模式（每5秒刷新）

可能原因：
• 网络环境不支持WebSocket
• 代理服务器配置问题

影响：数据更新延迟3-30秒

[重试WebSocket] [不再提示]
```

### 6.3 数据时效性标识

**在数据面板显示**:
```
系统监控
更新于: 3秒前 (轮询)
[🔄 手动刷新]
```

---

## 7. 性能考虑

### 7.1 资源消耗对比

| 模式 | 网络请求 | 服务器负载 | 数据延迟 | 带宽消耗 |
|-----|---------|----------|---------|---------|
| WebSocket | 1个长连接 | 低 | <100ms | 低（推送） |
| 轮询（5秒） | 12次/分钟 | 中 | 0-5秒 | 中（拉取） |
| 轮询（30秒） | 2次/分钟 | 低 | 0-30秒 | 低 |

### 7.2 优化措施

1. **智能轮询频率**:
   - 页面可见时: 正常间隔
   - 页面隐藏时: 2倍间隔或暂停
   - 数据无变化: 逐步降低频率

2. **批量请求优化**:
   ```javascript
   // 合并多个主题的请求
   GET /api/v1/realtime/batch?topics=monitoring,strategies,capacity
   ```

3. **缓存策略**:
   - 使用HTTP缓存头（ETag、Last-Modified）
   - 304 Not Modified 减少传输

### 7.3 后端优化

**新增批量端点**: `GET /api/v1/realtime/batch`

```python
@router.get("/realtime/batch")
async def get_realtime_batch(
    topics: str = Query(..., description="逗号分隔的主题列表"),
    last_update: Optional[str] = None
):
    """
    批量获取多个主题的实时数据

    示例: /api/v1/realtime/batch?topics=monitoring,strategies,capacity

    返回:
    {
      "monitoring": {...},
      "strategies": {...},
      "capacity": {...},
      "timestamp": "2025-10-29T13:20:00Z"
    }
    """
    # 实现...
```

---

## 8. 测试方案

### 8.1 单元测试

**前端测试** (`frontend/tests/unit/realtimeDataAdapter.spec.js`):
```javascript
describe('RealtimeDataAdapter', () => {
  test('应该优先尝试WebSocket连接', async () => {})
  test('WebSocket失败后应该降级到轮询', async () => {})
  test('轮询时应该按配置间隔请求', async () => {})
  test('切换模式时应该清理资源', async () => {})
})
```

**后端测试** (`backend/tests/test_realtime.py`):
```python
def test_batch_endpoint_returns_all_topics():
    """批量端点应该返回所有请求的主题数据"""

def test_batch_endpoint_handles_invalid_topics():
    """批量端点应该正确处理无效主题"""
```

### 8.2 集成测试

**场景1**: WebSocket正常工作
```
1. 登录系统
2. 验证WebSocket连接建立
3. 验证实时数据推送
4. 验证状态指示器显示"实时连接"
```

**场景2**: WebSocket不可用（模拟）
```
1. 登录系统
2. 阻止WebSocket连接（网络拦截）
3. 验证自动降级到轮询
4. 验证状态指示器显示"轮询模式"
5. 验证数据正常更新
```

**场景3**: 从轮询恢复到WebSocket
```
1. 初始处于轮询模式
2. 修复WebSocket配置
3. 点击"重试WebSocket"
4. 验证成功切换回WebSocket
5. 验证轮询定时器被清理
```

### 8.3 性能测试

**测试指标**:
- 轮询模式下CPU使用率
- 轮询模式下内存占用
- 轮询模式下网络请求数
- 切换模式的响应时间

**工具**:
- Chrome DevTools Performance
- Backend: Locust负载测试

---

## 9. 上线计划

### 9.1 实施阶段

**Phase 1: 后端准备（1天）**
- [ ] 新增批量查询端点
- [ ] 优化现有轮询端点
- [ ] 单元测试

**Phase 2: 前端核心（2天）**
- [ ] 实现realtimeDataAdapter
- [ ] 改造WebSocket Store
- [ ] 配置管理

**Phase 3: UI集成（1天）**
- [ ] 连接状态指示器
- [ ] 设置页面选项
- [ ] 降级提示

**Phase 4: 测试（1天）**
- [ ] 单元测试
- [ ] 集成测试
- [ ] 性能测试

**Phase 5: 文档和发布（0.5天）**
- [ ] 更新用户文档
- [ ] 发布说明
- [ ] 监控设置

### 9.2 回滚方案

如果出现严重问题：
1. 禁用轮询降级功能（`REALTIME_CONFIG.polling.enabled = false`）
2. 恢复到纯WebSocket模式
3. 修复问题后重新启用

### 9.3 监控指标

上线后需要监控：
- WebSocket连接成功率
- 降级触发频率
- 轮询模式使用占比
- API响应时间（轮询端点）

---

## 10. 未来优化方向

### 10.1 Server-Sent Events (SSE)

考虑使用SSE作为第二级降级方案：
```
优先级: WebSocket > SSE > HTTP Polling
```

**优势**:
- 比轮询更高效（服务端推送）
- 比WebSocket更简单（单向通信足够）
- 更好的浏览器兼容性

### 10.2 智能预测轮询

根据数据变化频率动态调整轮询间隔：
```javascript
if (dataUnchangedCount > 3) {
  // 数据3次没变化，降低轮询频率
  pollingInterval *= 1.5
}
```

### 10.3 离线支持

使用Service Worker缓存：
- 离线时显示最后缓存的数据
- 标注数据时效性
- 恢复连接后自动同步

---

## 11. 风险评估

| 风险 | 影响 | 可能性 | 缓解措施 |
|-----|------|-------|---------|
| 轮询增加服务器负载 | 中 | 高 | 智能轮询频率、批量API |
| 用户体验下降 | 低 | 中 | 明确提示、可配置 |
| 实现复杂度高 | 中 | 中 | 充分测试、分阶段实施 |
| 维护成本增加 | 中 | 低 | 良好的文档和监控 |

---

## 12. 总结

### 12.1 核心价值

✅ **可用性优先**: 确保在任何网络环境下都能获取数据
✅ **渐进增强**: WebSocket优先，优雅降级
✅ **用户可控**: 提供手动选择和配置选项
✅ **性能平衡**: 在体验和资源消耗间取得平衡

### 12.2 需要确认的问题

**请审核以下关键决策**:

1. **轮询间隔设置**:
   - 监控数据: 5秒 ✓
   - 策略状态: 5秒 ✓
   - 信号数据: 10秒 ✓
   - 容量数据: 30秒 ✓

2. **降级策略**:
   - WebSocket失败后自动降级 ✓
   - 提供手动重试选项 ✓
   - 允许用户强制选择模式 ✓

3. **实施优先级**:
   - 是否立即实施？
   - 是否需要调整功能范围？
   - 是否需要更详细的某个部分？

---

**下一步**: 请审核本设计方案，确认后我将开始实施。

