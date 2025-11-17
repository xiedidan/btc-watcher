# BTC Watcher - AI Context

## 项目概述
- **名称**: BTC Watcher
- **类型**: 加密货币信号监控与分析系统
- **技术栈**: Python/FastAPI + Vue 3 + PostgreSQL + Redis
- **规模**: 支持999个并发FreqTrade策略
- **状态**: 生产就绪

## 核心概念

### 1. Strategy（策略）
- FreqTrade交易策略实例
- 每个策略独立运行在专用端口（8081-9080）
- 支持动态启动/停止
- 状态：running, stopped, error

### 2. Signal（信号）
- 交易信号（买入/卖出）
- 来源：FreqTrade策略的Webhook回调
- 分级：强信号、中等信号、弱信号
- 存储：PostgreSQL + 实时推送

### 3. Watcher（监控器）
- 系统监控组件
- 监控指标：CPU、内存、磁盘、策略状态
- 实时推送：WebSocket
- 告警：多渠道通知

### 4. NotifyHub（通知中心）
- 多渠道通知系统
- 支持：Telegram、企业微信、飞书、邮件
- 智能分级：根据信号强度选择通知方式

## 关键路径

### 后端
- **入口**: `backend/main.py`
- **API路由**: `backend/api/v1/`
- **服务层**: `backend/services/`
- **数据模型**: `backend/models/`
- **数据库配置**: `backend/database/`
- **工具函数**: `backend/utils/`

### 前端
- **入口**: `frontend/src/main.js`
- **API客户端**: `frontend/src/api/`
- **状态管理**: `frontend/src/stores/` (Pinia)
- **路由**: `frontend/src/router/`
- **页面组件**: `frontend/src/views/`
- **UI组件**: `frontend/src/components/`

### 测试
- **单元测试**: `backend/tests/unit/`
- **集成测试**: `backend/tests/integration/`
- **E2E测试**: `frontend/tests/e2e/`
- **性能测试**: `backend/locustfile.py`

## 常见任务

### 添加新API
1. 创建路由: `backend/api/v1/{module}.py`
2. 实现服务: `backend/services/{service}.py`
3. 定义Schema: `backend/schemas/{schema}.py`
4. 添加测试: `backend/tests/integration/test_{module}.py`
5. 更新文档: `docs/architecture/api-design.md`

### 添加新页面
1. 创建组件: `frontend/src/views/{Page}.vue`
2. 配置路由: `frontend/src/router/index.js`
3. 添加API: `frontend/src/api/{module}.js`
4. 状态管理: `frontend/src/stores/{store}.js`
5. E2E测试: `frontend/tests/e2e/{page}.spec.js`

### 数据库变更
1. 修改模型: `backend/models/{model}.py`
2. 生成迁移: `alembic revision --autogenerate -m "description"`
3. 检查迁移: `alembic/versions/{revision}.py`
4. 应用迁移: `alembic upgrade head`
5. 更新文档: `docs/architecture/database-design.md`

### 添加测试
1. 单元测试: `backend/tests/unit/test_{module}.py`
2. 集成测试: `backend/tests/integration/test_{module}.py`
3. E2E测试: `frontend/tests/e2e/{feature}.spec.js`
4. 运行测试: `make test` 或 `pytest`

## 技术细节

### 后端架构
- **框架**: FastAPI 0.104（异步）
- **ORM**: SQLAlchemy 2.0（异步）
- **数据库**: PostgreSQL 15
- **缓存**: Redis 7
- **认证**: JWT
- **WebSocket**: FastAPI原生支持

### 前端架构
- **框架**: Vue 3（Composition API）
- **UI库**: Element Plus 2.5
- **状态**: Pinia 2.1
- **图表**: ECharts 5.4
- **HTTP**: Axios 1.6
- **构建**: Vite 5.0

### 部署架构
- **容器化**: Docker + Docker Compose
- **反向代理**: Nginx
- **进程管理**: Docker容器
- **数据持久化**: Docker Volumes
- **端口范围**:
  - Frontend: 80, 3000
  - Backend: 8000
  - FreqTrade: 8081-9080

## 编码规范

### Python
- 遵循 PEP 8
- 使用类型提示 (Type Hints)
- 所有I/O操作使用 async/await
- 依赖注入使用 FastAPI Depends
- 测试覆盖率 > 80%

### JavaScript/Vue
- 使用 Composition API
- 遵循 Vue 3 风格指南
- ESLint + Prettier
- 组件命名：PascalCase
- 文件命名：kebab-case

### Git提交规范
- `feat`: 新功能
- `fix`: Bug修复
- `docs`: 文档更新
- `test`: 测试相关
- `refactor`: 重构
- `perf`: 性能优化
- `chore`: 构建/工具变更

## 重要约束

### 性能要求
- API响应时间: < 100ms (P90)
- 并发请求: > 1000 QPS
- WebSocket延迟: < 50ms
- 数据库连接池: 5-20

### 安全要求
- 所有API需JWT认证（除公开接口）
- 密码使用bcrypt加密
- 环境变量存储敏感信息
- SQL注入防护（使用ORM）
- XSS防护（Vue自动转义）

### 可扩展性
- 支持999个并发策略
- 水平扩展：通过Nginx负载均衡
- 垂直扩展：优化数据库查询

## 项目状态

### 已完成功能 ✅
- 用户认证与授权
- 策略CRUD管理
- 策略启动/停止控制
- 999个并发策略支持
- 交易信号接收与存储
- 信号强度自动分级
- 实时系统监控
- WebSocket实时推送
- 多渠道通知推送
- 完整测试套件（单元/集成/E2E/性能）

### 计划中功能 🔜
- 策略性能分析
- 历史数据回测
- 移动端应用
- 高级图表分析

## 文档位置

- **用户文档**: `docs/user/`
- **架构设计**: `docs/architecture/`
- **开发指南**: `docs/development/`
- **运维文档**: `docs/operations/`
- **测试文档**: `docs/testing/`
- **实现记录**: `docs/implementation/`
- **ADR**: `docs/adr/`

## 快速链接

- [项目README](../README.md)
- [API文档](http://localhost:8000/docs)
- [架构设计](../docs/architecture/system-design.md)
- [数据库设计](../docs/architecture/database-design.md)
- [测试指南](../docs/testing/README.md)
