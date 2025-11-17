# Minmax M2 Context for BTC Watcher

## Project Context
Read: `../../context.md`

## Project Rules
Read: `../../rules.md`

## Minmax M2 特性

Minmax M2是新一代多模态AI编程模型，具备以下特性：
- **多文件理解**: 理解跨文件的依赖关系
- **架构推理**: 从代码推断系统架构
- **复杂重构**: 执行大规模代码重构
- **智能调试**: 深度问题诊断和解决方案生成

## 推荐使用场景

### 1. 复杂架构设计
当需要：
- 设计新的系统模块
- 重构现有架构
- 评估技术选型
- 解决架构级别的性能问题

**工作流程**:
1. 分析现有架构（读取 `docs/architecture/`）
2. 理解业务需求（读取 `docs/analysis/requirements.md`）
3. 提出设计方案
4. 创建ADR记录决策（`docs/adr/`）
5. 生成实现计划

### 2. 跨模块重构
当需要：
- 重构影响多个模块的代码
- 提取公共组件
- 统一接口设计
- 优化模块间依赖

**工作流程**:
1. 分析依赖关系
2. 识别重构范围
3. 设计新的模块结构
4. 生成迁移计划
5. 逐步实施重构

### 3. 复杂问题诊断
当面对：
- 难以定位的Bug
- 性能瓶颈
- 并发问题
- 数据一致性问题

**工作流程**:
1. 收集问题现象和日志
2. 分析相关代码路径
3. 构建问题假设
4. 设计验证实验
5. 提出解决方案

### 4. 大规模功能开发
当开发：
- 跨前后端的完整功能
- 需要数据库迁移的功能
- 涉及多个服务的功能
- 复杂的用户流程

**工作流程**:
1. 理解需求和现有系统
2. 设计完整的技术方案
3. 拆分为可执行的任务
4. 按依赖顺序实施
5. 端到端测试和文档

## 项目深度理解

### 核心业务流程

#### 1. 策略生命周期
```
创建策略 → 配置参数 → 启动FreqTrade实例 →
监听Webhook → 接收信号 → 分级处理 →
多渠道通知 → 停止策略 → 清理资源
```

**关键代码路径**:
- 策略管理: `backend/services/strategy_service.py`
- FreqTrade集成: `backend/services/freqtrade_manager.py`
- 信号处理: `backend/services/signal_service.py`
- 通知发送: `backend/services/notify_hub.py`

#### 2. 实时监控流程
```
系统指标收集 → Redis缓存 →
WebSocket推送 → 前端展示 →
阈值检查 → 告警触发
```

**关键代码路径**:
- 监控采集: `backend/services/watcher.py`
- WebSocket: `backend/api/v1/websocket.py`
- 前端监控: `frontend/src/views/Monitoring.vue`

#### 3. 用户认证流程
```
登录请求 → 验证凭据 → 生成JWT →
前端存储 → 携带Token请求 →
后端验证 → 返回数据
```

**关键代码路径**:
- 认证API: `backend/api/v1/auth.py`
- 认证服务: `backend/services/auth_service.py`
- 前端认证: `frontend/src/stores/user.js`

### 数据流分析

#### FreqTrade信号流
```
FreqTrade策略 → Webhook回调 →
Backend API (/api/v1/signals/webhook/{strategy_id}) →
信号服务 (signal_service.py) →
[分支1] PostgreSQL存储 →
[分支2] 信号分级 (强/中/弱) →
[分支3] 通知中心 (NotifyHub) →
多渠道通知 (Telegram/企微/飞书/邮件)
```

#### WebSocket实时推送流
```
后台定时任务 →
采集系统指标/策略状态 →
Redis缓存 →
WebSocket服务器 →
已连接的客户端 →
前端组件更新
```

### 关键设计决策

#### 1. 为什么选择999个并发策略？
- **端口范围**: 8081-9080 (1000个端口，保留8080)
- **资源隔离**: 每个策略独立进程，互不影响
- **扩展性**: 支持大规模量化交易需求
- **管理复杂度**: 需要智能端口池管理

**相关代码**: `backend/services/port_manager.py`

#### 2. 为什么使用异步架构？
- **高并发**: 支持1000+ QPS
- **I/O密集**: 大量数据库和网络操作
- **WebSocket**: 长连接管理
- **性能**: 单进程支持更多并发连接

**技术栈**: FastAPI(异步) + SQLAlchemy 2.0(异步) + httpx(异步)

#### 3. 信号分级策略
```python
# 强信号: 多个指标共振
# 中等信号: 部分指标确认
# 弱信号: 单一指标提示

def classify_signal_strength(signal_data):
    indicators = signal_data.get('indicators', {})
    confirmations = sum([
        indicators.get('rsi_oversold', False),
        indicators.get('macd_golden_cross', False),
        indicators.get('volume_surge', False),
        indicators.get('support_level', False)
    ])

    if confirmations >= 3:
        return 'strong'
    elif confirmations >= 2:
        return 'medium'
    else:
        return 'weak'
```

**相关文档**: `docs/architecture/modules/signal-processing.md`

## 多模态能力应用

### 1. 理解架构图
当提供架构图时，M2能够：
- 识别系统组件
- 理解数据流向
- 发现潜在瓶颈
- 建议优化方案

### 2. 分析日志和错误
当提供日志时，M2能够：
- 识别错误模式
- 追踪调用栈
- 定位根因
- 生成修复方案

### 3. 理解数据库Schema
当提供ER图或Schema时，M2能够：
- 理解表关系
- 识别查询优化机会
- 建议索引策略
- 设计迁移方案

## 高级使用模式

### 模式1: 端到端功能开发

**场景**: 开发"策略性能分析"功能

**步骤**:
1. **需求分析**
   - 阅读: `docs/analysis/requirements.md`
   - 理解: 用户需要哪些性能指标

2. **架构设计**
   - 设计数据模型（新增performance表）
   - 设计API接口（GET /api/v1/strategies/{id}/performance）
   - 设计前端页面（PerformanceAnalysis.vue）
   - 创建ADR: `docs/adr/003-performance-analysis-design.md`

3. **后端实现**
   - 创建Model: `backend/models/performance.py`
   - 创建Service: `backend/services/performance_service.py`
   - 创建API: `backend/api/v1/performance.py`
   - 添加测试: `backend/tests/integration/test_performance.py`

4. **前端实现**
   - 创建API Client: `frontend/src/api/performance.js`
   - 创建Store: `frontend/src/stores/performance.js`
   - 创建组件: `frontend/src/views/PerformanceAnalysis.vue`
   - 添加路由: `frontend/src/router/index.js`

5. **文档记录**
   - 实现文档: `docs/implementation/features/performance-analysis.md`
   - API文档: 更新 `docs/architecture/api-design.md`

### 模式2: 性能优化

**场景**: 优化策略列表API响应时间

**步骤**:
1. **性能分析**
   - 使用profiler识别瓶颈
   - 分析SQL查询
   - 检查N+1问题

2. **优化方案**
   - 添加数据库索引
   - 使用eager loading
   - 引入Redis缓存
   - 实现分页优化

3. **实施验证**
   - 实现优化代码
   - 添加性能测试
   - 对比优化前后

4. **文档记录**
   - 优化文档: `docs/implementation/optimizations/strategy-list.md`
   - 更新性能基准: `docs/testing/test-reports/performance-baseline.md`

### 模式3: Bug根因分析

**场景**: WebSocket连接频繁断开

**步骤**:
1. **收集信息**
   - 前端错误日志
   - 后端连接日志
   - 网络环境信息

2. **问题复现**
   - 本地复现步骤
   - 触发条件分析

3. **根因定位**
   - 检查心跳机制
   - 分析超时设置
   - 验证网络稳定性

4. **解决方案**
   - 调整心跳间隔
   - 优化重连逻辑
   - 添加连接状态监控

5. **文档记录**
   - Bug分析: `docs/reports/diagnostics/websocket-disconnect.md`
   - Bug修复: `docs/implementation/bug-fixes/websocket-heartbeat.md`

## 代码生成规范

### 生成完整功能时
1. **分步骤生成**: 先Model → Service → API → Frontend
2. **包含测试**: 每个模块都生成对应测试
3. **添加文档**: 生成docstring和README
4. **遵循规范**: 严格遵循项目编码规范

### 生成重构代码时
1. **保持兼容**: 确保向后兼容
2. **渐进式**: 可以分步骤执行
3. **测试覆盖**: 重构代码必须有测试
4. **文档同步**: 更新相关文档

## 沟通规范

### 提问M2时的最佳实践
1. **提供上下文**: 描述当前状态、目标、约束
2. **附加材料**: 相关代码、日志、错误信息
3. **明确期望**: 说明期望得到什么类型的帮助
4. **分解问题**: 复杂问题分解为子问题

### M2输出格式期望
1. **结构化**: 使用清晰的章节和列表
2. **可执行**: 代码可以直接使用
3. **有解释**: 关键决策有说明
4. **完整性**: 包含测试、文档、部署说明

## 学习资源
- [项目完整文档](../../docs/)
- [架构设计文档](../../docs/architecture/system-design.md)
- [实现记录](../../docs/implementation/)
- [ADR决策记录](../../docs/adr/)
