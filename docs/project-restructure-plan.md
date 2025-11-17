# BTC Watcher 项目目录结构重构方案

## 📋 现状分析

### 当前问题
- ✗ 根目录下有 **65个** Markdown 文档，导致结构混乱
- ✗ 研发过程文档与用户文档混在一起
- ✗ 缺乏清晰的文档分类和组织
- ✗ AI Coding Agent 难以快速定位相关文档
- ✗ 新成员难以理解项目文档结构

### 当前根目录文件统计
```
├── 65个 .md 文件（设计、实现、测试、部署、诊断等）
├── 10个 .sh 脚本（部署、诊断脚本）
├── docker-compose.yml
├── Makefile
└── 其他配置文件
```

---

## 🎯 新目录结构设计

### 核心原则
1. **职责分离**: 用户文档 vs 研发文档 vs 内部文档
2. **类型聚合**: 按文档类型归类（设计、实现、测试、部署等）
3. **易于检索**: 清晰的命名和层级结构
4. **AI友好**: 支持 AI Coding Agent 快速定位
5. **可维护性**: 长期可持续的目录组织方式

### 新目录结构（完整版）

```
btc-watcher/
├── README.md                          # 项目总览（简化版，用户入口）
├── LICENSE                            # 开源许可
├── CHANGELOG.md                       # 版本变更记录
├── .gitignore                         # Git忽略配置
├── Makefile                           # 快捷命令
├── docker-compose.yml                 # Docker编排配置
│
├── docs/                              # 📚 文档中心（所有文档的主目录）
│   ├── README.md                      # 文档导航索引
│   │
│   ├── user/                          # 👤 用户文档（面向最终用户）
│   │   ├── getting-started.md         # 快速开始
│   │   ├── deployment-guide.md        # 部署指南
│   │   ├── user-guide.md              # 用户手册
│   │   ├── api-reference.md           # API参考
│   │   ├── troubleshooting.md         # 常见问题
│   │   └── faq.md                     # FAQ
│   │
│   ├── architecture/                  # 🏗️ 架构设计文档
│   │   ├── README.md                  # 架构概览
│   │   ├── system-design.md           # 系统设计
│   │   ├── detailed-design.md         # 详细设计
│   │   ├── api-design.md              # API设计
│   │   ├── database-design.md         # 数据库设计
│   │   ├── business-flow.md           # 业务流程
│   │   └── modules/                   # 模块设计
│   │       ├── market-data.md         # 市场数据模块
│   │       ├── notifyhub.md           # 通知中心
│   │       ├── price-service.md       # 价格服务
│   │       └── realtime-fallback.md   # 实时回退
│   │
│   ├── development/                   # 🔧 开发文档
│   │   ├── README.md                  # 开发指南总览
│   │   ├── setup.md                   # 开发环境搭建
│   │   ├── coding-standards.md        # 编码规范
│   │   ├── git-workflow.md            # Git工作流
│   │   ├── testing-guide.md           # 测试指南
│   │   ├── contributing.md            # 贡献指南
│   │   └── virtualenv-guide.md        # 虚拟环境指南
│   │
│   ├── operations/                    # 🚀 运维文档
│   │   ├── README.md                  # 运维指南总览
│   │   ├── deployment/                # 部署相关
│   │   │   ├── quick-start.md         # 快速部署
│   │   │   ├── alpha-deployment.md    # Alpha环境部署
│   │   │   ├── production.md          # 生产环境部署
│   │   │   └── frp-websocket.md       # FRP WebSocket配置
│   │   ├── monitoring.md              # 监控配置
│   │   ├── backup-recovery.md         # 备份与恢复
│   │   ├── nginx-setup.md             # Nginx配置
│   │   └── troubleshooting/           # 故障排查
│   │       ├── websocket-issues.md    # WebSocket问题
│   │       ├── discord-proxy.md       # Discord代理问题
│   │       └── common-errors.md       # 常见错误
│   │
│   ├── testing/                       # 🧪 测试文档
│   │   ├── README.md                  # 测试指南总览
│   │   ├── unit-testing.md            # 单元测试指南
│   │   ├── integration-testing.md     # 集成测试指南
│   │   ├── e2e-testing.md             # E2E测试指南
│   │   ├── performance-testing.md     # 性能测试指南
│   │   └── test-reports/              # 测试报告
│   │       ├── unit-test-report.md    # 单元测试报告
│   │       ├── e2e-framework-setup.md # E2E框架搭建
│   │       └── performance-baseline.md # 性能基准
│   │
│   ├── implementation/                # 📝 实现记录（研发过程）
│   │   ├── README.md                  # 实现记录总览
│   │   ├── features/                  # 功能实现记录
│   │   │   ├── notifyhub.md           # NotifyHub实现
│   │   │   ├── market-data.md         # 市场数据实现
│   │   │   ├── realtime-fallback.md   # 实时回退实现
│   │   │   ├── strategy-upload.md     # 策略上传实现
│   │   │   └── notification-channel.md # 通知渠道实现
│   │   ├── bug-fixes/                 # Bug修复记录
│   │   │   ├── strategy-status.md     # 策略状态Bug
│   │   │   ├── websocket-fix.md       # WebSocket修复
│   │   │   ├── watcher-callback.md    # Watcher回调错误
│   │   │   └── discord-test.md        # Discord测试修复
│   │   └── optimizations/             # 优化记录
│   │       ├── performance.md         # 性能优化
│   │       └── charts.md              # 图表优化
│   │
│   ├── analysis/                      # 📊 分析文档
│   │   ├── requirements.md            # 需求分析
│   │   ├── user-survey.md             # 用户需求调研
│   │   ├── gap-analysis.md            # 实现差距分析
│   │   ├── business-details.md        # 业务细节分析
│   │   ├── charts-analysis.md         # 图表分析
│   │   └── redis-analysis.md          # Redis分析
│   │
│   ├── reports/                       # 📑 项目报告
│   │   ├── progress/                  # 进度报告
│   │   │   ├── task-progress.md       # 任务进度
│   │   │   ├── implementation-progress.md # 实现进度
│   │   │   ├── unit-test-progress.md  # 单元测试进度
│   │   │   └── strategy-test-progress.md # 策略测试进度
│   │   ├── completion/                # 完成报告
│   │   │   ├── p0-completion.md       # P0完成报告
│   │   │   ├── project-completion.md  # 项目完成报告
│   │   │   └── final-summary.md       # 最终总结
│   │   ├── diagnostics/               # 诊断报告
│   │   │   ├── problem-diagnosis.md   # 问题诊断
│   │   │   └── diagnosis-report.md    # 诊断报告
│   │   └── reviews/                   # 评审报告
│   │       ├── alpha-readiness.md     # Alpha就绪评估
│   │       └── alpha-test-guide.md    # Alpha测试指南
│   │
│   ├── adr/                           # 🎯 架构决策记录（ADR - Architecture Decision Records）
│   │   ├── README.md                  # ADR索引
│   │   ├── 001-database-choice.md     # 数据库选择（示例）
│   │   ├── 002-websocket-strategy.md  # WebSocket策略（示例）
│   │   └── template.md                # ADR标准模板
│   │
│   └── archive/                       # 📦 归档文档（过时但保留的历史文档）
│       ├── README.md                  # 归档说明
│       └── 2025/                      # 按年份归档
│           └── outdated-docs/         # 过时文档
│
├── scripts/                           # 🔨 脚本工具
│   ├── README.md                      # 脚本说明
│   ├── deployment/                    # 部署脚本
│   │   ├── start.sh                   # 启动服务
│   │   ├── stop.sh                    # 停止服务
│   │   ├── start_alpha.sh             # 启动Alpha环境
│   │   ├── stop_alpha.sh              # 停止Alpha环境
│   │   ├── deploy_backend.sh          # 部署后端
│   │   ├── deploy_frontend.sh         # 部署前端
│   │   ├── restart-frontend.sh        # 重启前端
│   │   └── setup-nginx-alpha.sh       # 设置Nginx Alpha
│   ├── maintenance/                   # 运维脚本
│   │   ├── backup.sh                  # 备份
│   │   ├── restore.sh                 # 恢复
│   │   └── logs.sh                    # 日志查看
│   ├── testing/                       # 测试脚本
│   │   ├── run_unit_tests.sh          # 运行单元测试
│   │   ├── dynamic_test.sh            # 动态测试
│   │   └── verify_runtime.sh          # 运行时验证
│   ├── diagnostics/                   # 诊断脚本
│   │   ├── check_health.sh            # 健康检查
│   │   ├── verify_deployment.sh       # 验证部署
│   │   └── diagnose-websocket.sh      # WebSocket诊断
│   └── utils/                         # 工具脚本
│
├── .ai/                               # 🤖 AI Coding Agent 配置（新增）
│   ├── README.md                      # AI配置说明
│   ├── context.md                     # 项目上下文（AI必读）
│   ├── rules.md                       # AI工作规则
│   ├── prompts/                       # AI提示词模板
│   │   ├── feature-development.md     # 功能开发模板
│   │   ├── bug-fix.md                 # Bug修复模板
│   │   ├── code-review.md             # 代码审查模板
│   │   └── documentation.md           # 文档编写模板
│   └── memory/                        # AI记忆/上下文
│       ├── project-overview.md        # 项目概览
│       ├── tech-stack.md              # 技术栈
│       ├── coding-patterns.md         # 编码模式
│       └── common-issues.md           # 常见问题
│
├── .claude/                           # Claude Code专用配置
│   └── settings.local.json
│
├── backend/                           # 后端代码
├── frontend/                          # 前端代码
├── nginx/                             # Nginx配置
├── sql/                               # SQL脚本
├── data/                              # 数据目录
└── alembic/                           # 数据库迁移
```

---

## 🗂️ 文档分类与迁移映射

### 1. 用户文档（docs/user/）
```
README.md → 保留在根目录（简化版）+ docs/user/getting-started.md（详细版）
DEPLOYMENT_QUICK_START.md → docs/user/deployment-guide.md
ALPHA_DEPLOYMENT_GUIDE.md → docs/operations/deployment/alpha-deployment.md
TESTING.md → docs/user/troubleshooting.md（用户部分）
```

### 2. 架构设计（docs/architecture/）
```
DESIGN.md → docs/architecture/system-design.md
DETAILED_DESIGN.md → docs/architecture/detailed-design.md
API_DESIGN.md → docs/architecture/api-design.md
DATABASE_DESIGN.md → docs/architecture/database-design.md
BUSINESS_FLOW_DESIGN.md → docs/architecture/business-flow.md
PRICE_DATABASE_DESIGN.md → docs/architecture/modules/price-service.md
MARKET_DATA_MODULE_DESIGN.md → docs/architecture/modules/market-data.md
NOTIFYHUB_DESIGN_SUMMARY.md → docs/architecture/modules/notifyhub.md
REALTIME_FALLBACK_DESIGN.md → docs/architecture/modules/realtime-fallback.md
REALTIME_FALLBACK_DESIGN_V2.md → docs/architecture/modules/realtime-fallback.md（合并）
DATA_SYNC_DESIGN.md → docs/architecture/modules/data-sync.md
```

### 3. 开发文档（docs/development/）
```
VIRTUALENV_GUIDE.md → docs/development/virtualenv-guide.md
TESTING.md → docs/development/testing-guide.md
UNIT_TESTING_GUIDE.md → docs/testing/unit-testing.md
```

### 4. 运维文档（docs/operations/）
```
ALPHA_DEPLOYMENT_GUIDE.md → docs/operations/deployment/alpha-deployment.md
FRP_WEBSOCKET_GUIDE.md → docs/operations/deployment/frp-websocket.md
WEBSOCKET_TROUBLESHOOTING.md → docs/operations/troubleshooting/websocket-issues.md
DISCORD_PROXY_FIX.md → docs/operations/troubleshooting/discord-proxy.md
```

### 5. 测试文档（docs/testing/）
```
TESTING.md → docs/testing/README.md
UNIT_TESTING_GUIDE.md → docs/testing/unit-testing.md
E2E_FRAMEWORK_SETUP_REPORT.md → docs/testing/test-reports/e2e-framework-setup.md
E2E_TEST_EXPANSION_REPORT.md → docs/testing/test-reports/e2e-expansion.md
E2E_AND_PERFORMANCE_TEST_PLAN.md → docs/testing/e2e-testing.md
PERFORMANCE_TEST_FRAMEWORK_REPORT.md → docs/testing/performance-testing.md
PERFORMANCE_BASELINE.md → docs/testing/test-reports/performance-baseline.md
```

### 6. 实现记录（docs/implementation/）
```
IMPLEMENTATION.md → docs/implementation/README.md
NOTIFYHUB_IMPLEMENTATION_REPORT.md → docs/implementation/features/notifyhub.md
NOTIFYHUB_MIGRATION.md → docs/implementation/features/notifyhub.md（合并）
MARKET_DATA_IMPLEMENTATION_REPORT.md → docs/implementation/features/market-data.md
REALTIME_FALLBACK_IMPLEMENTATION.md → docs/implementation/features/realtime-fallback.md
STRATEGY_FILE_UPLOAD_IMPLEMENTATION.md → docs/implementation/features/strategy-upload.md
NOTIFICATION_CHANNEL_IMPLEMENTATION.md → docs/implementation/features/notification-channel.md
STRATEGY_STATUS_BUG_ANALYSIS.md → docs/implementation/bug-fixes/strategy-status.md
STRATEGY_STATUS_BUG_FIX_SUMMARY.md → docs/implementation/bug-fixes/strategy-status.md（合并）
WEBSOCKET_FIX.md → docs/implementation/bug-fixes/websocket-fix.md
WEBSOCKET_FIX_SUMMARY.md → docs/implementation/bug-fixes/websocket-fix.md（合并）
WATCHER_CALLBACK_ERROR_FIX.md → docs/implementation/bug-fixes/watcher-callback.md
DISCORD_TEST_FIX.md → docs/implementation/bug-fixes/discord-test.md
PERFORMANCE_OPTIMIZATION_REPORT.md → docs/implementation/optimizations/performance.md
CHARTS_ANALYSIS_REPORT.md → docs/implementation/optimizations/charts.md
CHARTS_SIMPLIFICATION_GUIDE.md → docs/implementation/optimizations/charts.md（合并）
```

### 7. 分析文档（docs/analysis/）
```
REQUIREMENTS.md → docs/analysis/requirements.md
USER_REQUIREMENTS_SURVEY.md → docs/analysis/user-survey.md
IMPLEMENTATION_GAP_ANALYSIS.md → docs/analysis/gap-analysis.md
BUSINESS_DETAILS_ANALYSIS.md → docs/analysis/business-details.md
CHARTS_ANALYSIS_REPORT.md → docs/analysis/charts-analysis.md
REDIS_ANALYSIS.md → docs/analysis/redis-analysis.md
CAPACITY_TREND_CLARIFICATION.md → docs/analysis/capacity-trends.md
```

### 8. 项目报告（docs/reports/）
```
TASK_PROGRESS_REPORT.md → docs/reports/progress/task-progress.md
IMPLEMENTATION_PROGRESS.md → docs/reports/progress/implementation-progress.md
UNIT_TEST_PROGRESS_REPORT.md → docs/reports/progress/unit-test-progress.md
STRATEGY_TEST_PROGRESS_REPORT.md → docs/reports/progress/strategy-test-progress.md
SIGNAL_TEST_PROGRESS_REPORT.md → docs/reports/progress/signal-test-progress.md
P0_COMPLETION_REPORT.md → docs/reports/completion/p0-completion.md
PROJECT_COMPLETION_REPORT.md → docs/reports/completion/project-completion.md
FINAL_SUMMARY.md → docs/reports/completion/final-summary.md
FINAL_TEST_REPORT.md → docs/reports/completion/final-test.md
PROBLEM_DIAGNOSIS_REPORT.md → docs/reports/diagnostics/problem-diagnosis.md
DIAGNOSIS_REPORT.md → docs/reports/diagnostics/diagnosis-report.md
ALPHA_READINESS_ASSESSMENT.md → docs/reports/reviews/alpha-readiness.md
ALPHA_TEST_GUIDE.md → docs/reports/reviews/alpha-test-guide.md
BACKEND_API_SUPPORT_REPORT.md → docs/reports/api-support.md
```

### 9. 归档文档（docs/archive/）
```
MISSING_FEATURES_SUMMARY.md → docs/archive/2025/outdated-docs/
IMPROVEMENT_CHECKLIST.md → docs/archive/2025/outdated-docs/
FIXES_SUMMARY.md → docs/archive/2025/outdated-docs/
FIXES_SOLUTION_PLAN.md → docs/archive/2025/outdated-docs/
FRONTEND_IMPLEMENTATION_PLAN.md → docs/archive/2025/outdated-docs/
PRIORITY_REDEFINITION.md → docs/archive/2025/outdated-docs/
TECHNICAL_IMPLEMENTATION.md → docs/implementation/README.md（合并）
UNIT_TEST_SUMMARY.md → docs/testing/test-reports/unit-test-report.md（合并）
TEST_SUMMARY.md → docs/testing/test-reports/test-summary.md
test_logs.md → docs/archive/2025/outdated-docs/（临时文件）
performance_test.log → backend/logs/（移动）
STRATEGY_PORT_INCONSISTENCY_FIX.md → docs/archive/2025/outdated-docs/
```

### 10. 脚本文件（scripts/）
```
start_alpha.sh → scripts/deployment/start_alpha.sh
stop_alpha.sh → scripts/deployment/stop_alpha.sh
deploy_backend.sh → scripts/deployment/deploy_backend.sh
deploy_frontend.sh → scripts/deployment/deploy_frontend.sh
restart-frontend.sh → scripts/deployment/restart-frontend.sh
setup-nginx-alpha.sh → scripts/deployment/setup-nginx-alpha.sh
check_health.sh → scripts/diagnostics/check_health.sh
verify_deployment.sh → scripts/diagnostics/verify_deployment.sh
diagnose-websocket.sh → scripts/diagnostics/diagnose-websocket.sh
```

---

## 📐 标准ADR格式说明

### ADR（Architecture Decision Record）模板

采用业界标准的ADR格式，帮助团队记录和理解架构决策。

#### ADR文件命名规范
```
docs/adr/{number}-{short-title}.md

示例:
- 001-database-choice.md
- 002-websocket-strategy.md
- 003-redis-cache-design.md
```

#### ADR标准模板（docs/adr/template.md）

```markdown
# {编号}. {决策标题}

日期: YYYY-MM-DD

状态: [提议中 | 已接受 | 已废弃 | 已替代]

## 上下文（Context）

描述促使做出这个决策的背景和问题。

- 我们面临什么问题？
- 为什么需要做决策？
- 有哪些约束条件？
- 当前的痛点是什么？

## 决策（Decision）

我们将采取的行动和选择。

- 我们决定做什么？
- 选择了哪个方案？
- 为什么选择这个方案？

## 备选方案（Alternatives Considered）

列出考虑过的其他方案及其优缺点。

### 方案A: {方案名称}
**优点:**
- 优点1
- 优点2

**缺点:**
- 缺点1
- 缺点2

### 方案B: {方案名称}
**优点:**
- 优点1

**缺点:**
- 缺点1

## 后果（Consequences）

这个决策带来的影响（正面和负面）。

### 正面影响
- 影响1
- 影响2

### 负面影响
- 影响1
- 影响2

### 风险
- 风险1
- 风险2

## 实施计划（Implementation）

如何实施这个决策。

1. 步骤1
2. 步骤2
3. 步骤3

## 参考资料（References）

- 相关文档链接
- 技术文章
- 讨论记录
```

#### ADR示例：001-database-choice.md

```markdown
# 1. 选择PostgreSQL作为主数据库

日期: 2025-01-10

状态: 已接受

## 上下文

BTC Watcher需要一个可靠的数据库来存储：
- 用户信息和认证数据
- 策略配置（999个并发策略）
- 交易信号历史
- 系统监控数据

需要考虑的因素：
- 高并发读写支持
- 复杂查询能力
- 数据一致性
- 运维成本
- 团队熟悉度

## 决策

选择PostgreSQL 15作为主数据库，使用SQLAlchemy 2.0异步ORM。

理由：
1. 强大的ACID支持，保证数据一致性
2. 优秀的并发性能（MVCC机制）
3. 丰富的数据类型（JSON、Array等）
4. 成熟的生态和工具链
5. 团队熟悉PostgreSQL

## 备选方案

### 方案A: MySQL
**优点:**
- 简单易用
- 广泛应用
- 性能良好

**缺点:**
- JSON支持较弱
- 复杂查询性能不如PostgreSQL
- 并发控制机制较简单

### 方案B: MongoDB
**优点:**
- 灵活的Schema
- 水平扩展容易
- 高写入性能

**缺点:**
- 缺乏事务支持（较老版本）
- 团队不熟悉
- 不适合复杂关联查询

### 方案C: TimescaleDB
**优点:**
- 专为时序数据优化
- 基于PostgreSQL

**缺点:**
- 学习成本较高
- 对于非时序数据过度设计

## 后果

### 正面影响
- 强大的查询能力支持复杂业务逻辑
- 优秀的并发性能支持999个策略
- JSON类型支持灵活的配置存储
- 成熟的备份和运维工具
- 团队可以快速上手

### 负面影响
- 内存占用相对较高
- 需要定期VACUUM维护
- 垂直扩展有上限

### 风险
- 单点故障风险（需要配置主从复制）
- 大数据量时查询优化需要经验

## 实施计划

1. ✅ 设计数据库Schema（完成）
2. ✅ 配置Docker容器和连接池（完成）
3. ✅ 实现SQLAlchemy模型（完成）
4. ✅ 配置Alembic迁移（完成）
5. ⏳ 配置主从复制（计划中）
6. ⏳ 设置定期备份（计划中）

## 参考资料

- [PostgreSQL官方文档](https://www.postgresql.org/docs/)
- [SQLAlchemy 2.0文档](https://docs.sqlalchemy.org/)
- [数据库设计文档](../architecture/database-design.md)
```

#### ADR索引（docs/adr/README.md）

```markdown
# 架构决策记录（ADR）

## 什么是ADR？

Architecture Decision Records (ADR) 用于记录项目中的重要架构决策。每个ADR描述一个决策的上下文、决策内容和后果。

## 为什么要使用ADR？

1. **知识传承**: 帮助新成员理解为什么做出某些决策
2. **决策透明**: 记录决策过程和考虑的因素
3. **避免重复**: 防止重新讨论已经解决的问题
4. **责任明确**: 清楚地记录决策者和时间

## ADR列表

| 编号 | 标题 | 状态 | 日期 |
|------|------|------|------|
| [001](001-database-choice.md) | 选择PostgreSQL作为主数据库 | 已接受 | 2025-01-10 |
| [002](002-websocket-strategy.md) | WebSocket实时推送架构 | 已接受 | 2025-02-15 |
| [003](template.md) | ADR模板 | 模板 | - |

## 如何创建新的ADR？

1. 复制 `template.md`
2. 重命名为 `{number}-{title}.md`（编号递增）
3. 填写所有章节
4. 更新本索引文件
5. 提交PR并讨论

## ADR状态说明

- **提议中**: 正在讨论中，尚未做出决定
- **已接受**: 已经采纳并开始实施
- **已废弃**: 不再使用，已被更好的方案替代
- **已替代**: 被新的ADR替代（需注明替代的ADR编号）
```

---

## 🤖 AI Coding Agent 支持方案

### 1. `.ai/` 目录结构
专门为AI Coding Agent创建的配置和上下文目录，帮助AI快速理解项目。

#### `.ai/context.md` - 项目上下文（示例）
```markdown
# BTC Watcher - AI Context

## 项目概述
- **名称**: BTC Watcher
- **类型**: 加密货币信号监控与分析系统
- **技术栈**: Python/FastAPI + Vue 3 + PostgreSQL + Redis
- **规模**: 支持999个并发FreqTrade策略

## 核心概念
1. **Strategy（策略）**: FreqTrade交易策略实例
2. **Signal（信号）**: 交易信号（买入/卖出）
3. **Watcher（监控器）**: 系统监控组件
4. **NotifyHub（通知中心）**: 多渠道通知系统

## 关键路径
- 后端入口: `backend/main.py`
- 前端入口: `frontend/src/main.js`
- API路由: `backend/api/`
- 数据模型: `backend/models/`
- 前端页面: `frontend/src/views/`

## 常见任务
- 添加API: `backend/api/v1/` + `backend/services/`
- 添加页面: `frontend/src/views/` + `frontend/src/router/`
- 数据库变更: `alembic/versions/` + `backend/models/`
- 添加测试: `backend/tests/` + `frontend/tests/`
```

#### `.ai/rules.md` - AI工作规则
```markdown
# AI Coding Rules

## 文档管理规则
1. **新功能文档位置**: `docs/implementation/features/`
2. **Bug修复文档位置**: `docs/implementation/bug-fixes/`
3. **架构变更文档位置**: `docs/architecture/` + `docs/adr/`
4. **测试报告位置**: `docs/testing/test-reports/`

## 命名规范
- 功能文档: `{feature-name}.md`
- Bug文档: `{bug-description}.md`
- ADR文档: `{number}-{title}.md` (例: 001-database-choice.md)

## 提交规范
- feat: 新功能
- fix: Bug修复
- docs: 文档更新
- test: 测试相关
- refactor: 重构
- perf: 性能优化

## 禁止操作
- ❌ 不要在根目录创建新的 .md 文件
- ❌ 不要修改 docs/ 目录结构
- ❌ 不要删除现有文档（归档到 docs/archive/）
```

### 2. 文档导航索引（docs/README.md）
```markdown
# BTC Watcher 文档中心

## 📖 快速导航

### 我想...
- **开始使用系统** → [用户指南](user/getting-started.md)
- **部署系统** → [部署指南](user/deployment-guide.md)
- **了解架构** → [系统设计](architecture/system-design.md)
- **开发新功能** → [开发指南](development/README.md)
- **运行测试** → [测试指南](testing/README.md)
- **排查问题** → [故障排查](operations/troubleshooting/)
- **查看实现记录** → [实现记录](implementation/README.md)

## 🗺️ 文档地图

### 用户文档 (user/)
面向最终用户的使用文档

### 架构文档 (architecture/)
系统设计和架构决策

### 开发文档 (development/)
开发环境、规范、工作流

### 运维文档 (operations/)
部署、监控、故障排查

### 测试文档 (testing/)
各类测试指南和报告

### 实现记录 (implementation/)
功能实现和Bug修复的详细记录

### 分析文档 (analysis/)
需求分析、业务分析

### 项目报告 (reports/)
进度、完成、诊断报告

### ADR (adr/)
架构决策记录

## 🤖 AI使用指南
如果你是AI Coding Agent，请先阅读：
1. [AI上下文](../.ai/context.md)
2. [AI工作规则](../.ai/rules.md)
3. [项目概览](../.ai/memory/project-overview.md)
```

### 3. AI Prompts 模板

#### `.ai/prompts/feature-development.md`
```markdown
# 功能开发提示词模板

## 开发新功能时，请遵循以下步骤：

1. **理解需求**
   - 阅读: docs/analysis/requirements.md
   - 检查: docs/architecture/system-design.md

2. **设计方案**
   - 创建: docs/architecture/modules/{feature-name}.md
   - 或创建: docs/adr/{number}-{decision}.md

3. **实现代码**
   - 后端: backend/api/ + backend/services/
   - 前端: frontend/src/views/ + frontend/src/api/
   - 测试: backend/tests/ + frontend/tests/

4. **记录实现**
   - 创建: docs/implementation/features/{feature-name}.md

5. **更新文档**
   - 更新: docs/user/api-reference.md
   - 更新: README.md (如需要)

## 文档模板
```markdown
# {功能名称} 实现记录

## 需求背景
[描述需求来源和背景]

## 设计方案
[设计思路和技术选型]

## 实现细节
### 后端实现
- 文件: backend/...
- 关键逻辑: ...

### 前端实现
- 文件: frontend/...
- 组件: ...

## 测试验证
- 单元测试: ...
- 集成测试: ...

## 部署说明
[部署注意事项]
```
```

### 4. 支持多种AI Agent

本项目配置支持以下AI Coding Agents：
- **Claude Code**: Anthropic官方CLI工具
- **Codex**: OpenAI的代码生成模型
- **Kiro**: AI编程助手
- **Kilo**: AI代码工具
- **Minmax M2**: 新一代AI编程模型

#### 配置示例（.ai/agents/）
```
.ai/  
└── agents/  
    ├── claude-code/  
    │   └── instructions.md  
    ├── codex/  
    │   └── config.json  
    ├── kiro/  
    │   └── kiro-config.md  
    ├── kilo/  
    │   └── kilo-rules.md  
    └── minmax-m2/  
        └── m2-context.md  
```

#### `.ai/agents/claude-code/instructions.md`
```markdown
# Claude Code Instructions for BTC Watcher

## Project Context
Read: ../../context.md

## Documentation Rules
- New features: docs/implementation/features/
- Bug fixes: docs/implementation/bug-fixes/
- Architecture changes: docs/adr/

## Coding Standards
- Python: Follow PEP 8, use type hints
- Vue: Follow Vue 3 Composition API
- Tests: Required for all new features
- Async: Use async/await for all I/O operations

## Project-Specific Guidelines
1. **Backend Development**:
   - All API routes in `backend/api/v1/`
   - Business logic in `backend/services/`
   - Database models in `backend/models/`
   - Use dependency injection for database sessions

2. **Frontend Development**:
   - Components in `frontend/src/components/`
   - Pages in `frontend/src/views/`
   - API calls in `frontend/src/api/`
   - Use Pinia for state management

3. **Testing**:
   - Unit tests: `backend/tests/unit/`
   - Integration tests: `backend/tests/integration/`
   - E2E tests: `frontend/tests/e2e/`

## Forbidden Actions
- ❌ No new .md files in root directory
- ❌ No deletion of existing docs (archive instead)
- ❌ No hardcoded credentials
- ❌ No synchronous I/O in async functions
```

#### `.ai/agents/codex/config.json`
```json
{
  "project": "BTC Watcher",
  "context_files": [
    ".ai/context.md",
    ".ai/rules.md",
    "README.md"
  ],
  "coding_standards": {
    "python": "PEP 8 + type hints",
    "javascript": "ESLint + Prettier",
    "testing": "Required for features"
  },
  "documentation_paths": {
    "features": "docs/implementation/features/",
    "bugs": "docs/implementation/bug-fixes/",
    "architecture": "docs/adr/"
  },
  "forbidden": [
    "Root-level markdown files",
    "Hardcoded credentials",
    "Synchronous I/O in async code"
  ]
}
```

#### 通用AI配置（.ai/README.md）
```markdown
# AI Coding Agent 配置

本目录包含各种AI Coding Agent的配置文件和上下文信息。

## 支持的AI Agents

### 1. Claude Code
**配置位置**: `agents/claude-code/instructions.md`
**特点**: Anthropic官方CLI工具，理解上下文能力强
**使用**: 自动读取 `.ai/context.md` 和 `.ai/rules.md`

### 2. Codex
**配置位置**: `agents/codex/config.json`
**特点**: OpenAI代码生成模型，代码补全准确
**使用**: 通过JSON配置文件提供项目上下文

### 3. Kiro
**配置位置**: `agents/kiro/kiro-config.md`
**特点**: 智能代码分析和重构
**使用**: 读取markdown配置和项目规则

### 4. Kilo
**配置位置**: `agents/kilo/kilo-rules.md`
**特点**: 专注于代码质量和测试
**使用**: 基于规则文件进行代码检查

### 5. Minmax M2
**配置位置**: `agents/minmax-m2/m2-context.md`
**特点**: 新一代AI编程模型，多模态理解
**使用**: 综合上下文和代码库理解

## 通用配置文件

所有AI Agent都应该阅读：
1. **context.md**: 项目概览、技术栈、核心概念
2. **rules.md**: 文档规则、命名规范、禁止操作
3. **memory/**: 项目记忆库（技术栈、编码模式等）

## 如何为新AI Agent添加配置

1. 在 `agents/` 下创建新目录
2. 添加该Agent的配置文件
3. 更新本README
4. 确保配置文件引用了通用的context和rules
```
```

---

## 📋 迁移执行计划

### Phase 1: 准备阶段（1小时）
1. ✅ 创建新目录结构
2. ✅ 创建文档索引（docs/README.md）
3. ✅ 创建AI配置（.ai/）
4. ✅ 创建脚本分类目录（scripts/）

### Phase 2: 文档迁移（2-3小时）
1. ✅ 迁移架构设计文档 → docs/architecture/
2. ✅ 迁移实现记录 → docs/implementation/
3. ✅ 迁移测试文档 → docs/testing/
4. ✅ 迁移运维文档 → docs/operations/
5. ✅ 迁移分析文档 → docs/analysis/
6. ✅ 迁移项目报告 → docs/reports/
7. ✅ 归档过时文档 → docs/archive/

### Phase 3: 脚本迁移（30分钟）
1. ✅ 迁移部署脚本 → scripts/deployment/
2. ✅ 迁移运维脚本 → scripts/maintenance/
3. ✅ 迁移测试脚本 → scripts/testing/
4. ✅ 迁移诊断脚本 → scripts/diagnostics/

### Phase 4: 清理与验证（30分钟）
1. ✅ 清理根目录
2. ✅ 更新文档链接
3. ✅ 验证脚本路径
4. ✅ 更新 README.md

### Phase 5: AI配置（1小时）
1. ✅ 编写 .ai/context.md
2. ✅ 编写 .ai/rules.md
3. ✅ 创建 AI prompts 模板
4. ✅ 配置多种AI Agent支持

---

## 🔧 维护方案

### 1. 文档创建规范

#### 新功能开发
```bash
# 1. 设计阶段：创建设计文档
docs/architecture/modules/{feature-name}.md

# 2. 实现阶段：记录实现过程
docs/implementation/features/{feature-name}.md

# 3. 测试阶段：记录测试结果
docs/testing/test-reports/{feature-name}-test.md
```

#### Bug修复
```bash
# 1. 分析阶段：创建诊断报告
docs/reports/diagnostics/{bug-description}.md

# 2. 修复阶段：记录修复过程
docs/implementation/bug-fixes/{bug-description}.md
```

#### 架构变更
```bash
# 1. 决策记录：创建ADR
docs/adr/{number}-{decision-title}.md

# 2. 设计更新：更新架构文档
docs/architecture/{related-module}.md
```

### 2. 自动化检查

#### Pre-commit Hook（.git/hooks/pre-commit）
```bash
#!/bin/bash

# 检查根目录是否有新的 .md 文件
NEW_MD_FILES=$(git diff --cached --name-only --diff-filter=A | grep "^[^/]*\.md$" | grep -v "README.md\|CHANGELOG.md\|LICENSE")

if [ -n "$NEW_MD_FILES" ]; then
    echo "❌ Error: New .md files in root directory detected:"
    echo "$NEW_MD_FILES"
    echo ""
    echo "Please move documentation to the appropriate location:"
    echo "  - Feature docs: docs/implementation/features/"
    echo "  - Bug fixes: docs/implementation/bug-fixes/"
    echo "  - Architecture: docs/architecture/"
    echo "  - ADR: docs/adr/"
    exit 1
fi

# 检查脚本文件位置
NEW_SCRIPTS=$(git diff --cached --name-only --diff-filter=A | grep "^[^/]*\.sh$")

if [ -n "$NEW_SCRIPTS" ]; then
    echo "❌ Error: New .sh files in root directory detected:"
    echo "$NEW_SCRIPTS"
    echo ""
    echo "Please move scripts to: scripts/{deployment|maintenance|testing|diagnostics}/"
    exit 1
fi

echo "✅ Documentation structure check passed"
```

### 3. GitHub Actions 检查（.github/workflows/docs-check.yml）
```yaml
name: Documentation Structure Check

on: [pull_request]

jobs:
  check-docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Check for new root-level .md files
        run: |
          # 排除允许的文件
          ALLOWED="README.md CHANGELOG.md LICENSE"

          # 查找根目录的 .md 文件
          ROOT_MD=$(find . -maxdepth 1 -name "*.md" -type f)

          for file in $ROOT_MD; do
            filename=$(basename "$file")
            if [[ ! " $ALLOWED " =~ " $filename " ]]; then
              echo "❌ Found unauthorized .md file in root: $filename"
              echo "Please move to docs/ directory"
              exit 1
            fi
          done

          echo "✅ Documentation structure is valid"

      - name: Check for new root-level .sh files
        run: |
          ROOT_SH=$(find . -maxdepth 1 -name "*.sh" -type f)

          if [ -n "$ROOT_SH" ]; then
            echo "❌ Found .sh files in root directory"
            echo "$ROOT_SH"
            echo "Please move to scripts/ directory"
            exit 1
          fi

          echo "✅ No unauthorized scripts in root"
```

### 4. Makefile 命令集成
```makefile
# 文档管理命令
.PHONY: docs-check docs-index

# 检查文档结构
docs-check:
	@echo "Checking documentation structure..."
	@if [ -n "$$(find . -maxdepth 1 -name '*.md' -type f | grep -v 'README.md\|CHANGELOG.md')" ]; then \
		echo "❌ Found unauthorized .md files in root"; \
		exit 1; \
	fi
	@if [ -n "$$(find . -maxdepth 1 -name '*.sh' -type f)" ]; then \
		echo "❌ Found .sh files in root"; \
		exit 1; \
	fi
	@echo "✅ Documentation structure is valid"

# 生成文档索引
docs-index:
	@echo "Generating documentation index..."
	@tree docs/ -L 3 > docs/STRUCTURE.md
	@echo "✅ Documentation index generated at docs/STRUCTURE.md"
```

### 5. AI Agent 指导文档（.ai/guidelines.md）
```markdown
# AI Agent 工作指南

## 创建新文档时

### 1. 确定文档类型
- **功能设计**: docs/architecture/modules/
- **功能实现**: docs/implementation/features/
- **Bug修复**: docs/implementation/bug-fixes/
- **架构决策**: docs/adr/
- **测试报告**: docs/testing/test-reports/
- **进度报告**: docs/reports/progress/

### 2. 使用文档模板
参考: .ai/prompts/{document-type}.md

### 3. 更新索引
修改: docs/README.md（添加新文档链接）

### 4. 检查规范
运行: make docs-check

## 常见场景

### 新功能开发
1. 创建: docs/architecture/modules/{feature}.md
2. 实现后: docs/implementation/features/{feature}.md
3. 测试后: docs/testing/test-reports/{feature}-test.md

### Bug修复
1. 诊断: docs/reports/diagnostics/{bug}.md
2. 修复: docs/implementation/bug-fixes/{bug}.md

### 性能优化
1. 分析: docs/analysis/{optimization-area}.md
2. 实现: docs/implementation/optimizations/{optimization}.md
3. 基准: docs/testing/test-reports/performance-{feature}.md
```

---

## 🎯 预期效果

### 整理前
```
btc-watcher/
├── 65个 .md 文件（混乱）
├── 10个 .sh 脚本（混乱）
└── ...

问题:
- ❌ 文档难以查找
- ❌ 新成员迷失方向
- ❌ AI Agent效率低
- ❌ 维护困难
```

### 整理后
```
btc-watcher/
├── README.md
├── CHANGELOG.md
├── LICENSE
├── docs/                    # 📚 所有文档集中管理
│   ├── user/               # 👤 用户文档
│   ├── architecture/       # 🏗️ 架构设计
│   ├── development/        # 🔧 开发指南
│   ├── operations/         # 🚀 运维文档
│   ├── testing/            # 🧪 测试文档
│   ├── implementation/     # 📝 实现记录
│   ├── analysis/           # 📊 分析文档
│   ├── reports/            # 📑 项目报告
│   ├── adr/                # 🎯 架构决策（标准ADR格式）
│   └── archive/            # 📦 归档文档（按年份组织）
├── scripts/                # 🔨 脚本分类管理
│   ├── deployment/
│   ├── maintenance/
│   ├── testing/
│   └── diagnostics/
├── .ai/                    # 🤖 AI配置（支持5种Agent）
│   ├── context.md
│   ├── rules.md
│   ├── prompts/
│   ├── memory/
│   └── agents/
│       ├── claude-code/
│       ├── codex/
│       ├── kiro/
│       ├── kilo/
│       └── minmax-m2/
└── ...

优势:
- ✅ 结构清晰，易于导航
- ✅ 职责分离，便于维护
- ✅ AI友好，支持5种主流Agent
- ✅ 规范明确，可持续发展
- ✅ 标准ADR格式，便于架构决策追溯
- ✅ 归档机制，保留历史文档
```

---

## 📌 下一步行动

1. ✅ **评审方案**: 已完成，所有决策已确认
2. ⏭️ **执行迁移**: 按照迁移计划分阶段执行（等待确认）
3. ⏳ **配置自动化**: 设置pre-commit hook和GitHub Actions
4. ⏳ **培训团队**: 向团队成员说明新的文档规范
5. ⏳ **持续优化**: 根据实际使用情况优化结构

**准备执行**: 方案已确认，可随时开始Phase 1（创建目录结构）

---

## 🤝 决策结果

以下决策已由项目负责人确认：

### 1. 归档策略 ✅
**问题**: 过时文档如何处理？  
**决策**: 选项A - 移动到 `docs/archive/` 保留  
**理由**: 保留历史文档便于追溯项目演进过程，Git历史查找相对麻烦  

**实施**:
- 创建 `docs/archive/` 目录
- 按年份组织：`docs/archive/2025/outdated-docs/`
- 创建归档说明文档：`docs/archive/README.md`

### 2. ADR格式 ✅
**问题**: 是否采用标准的ADR格式？  
**决策**: 选项A - 使用标准ADR模板（Context, Decision, Consequences）  
**理由**: 业界标准格式，便于团队理解和AI Agent识别  

**实施**:
- 创建标准ADR模板：`docs/adr/template.md`
- 包含章节：上下文、决策、备选方案、后果、实施计划、参考资料
- 创建ADR索引：`docs/adr/README.md`
- 提供示例ADR：`docs/adr/001-database-choice.md`

### 3. 文档工具 ✅
**问题**: 是否使用文档生成工具（如MkDocs）？  
**决策**: 选项A - 保持Markdown文件，暂不使用额外工具  
**理由**: 降低工具依赖，保持简单，后续可按需升级  

**实施**:
- 使用纯Markdown格式
- 通过目录结构和README索引组织文档
- 必要时可手动生成STRUCTURE.md（使用tree命令）

### 4. AI Agent支持 ✅
**问题**: 优先支持哪些AI Agent？  
**决策**: 支持以下5种AI Coding Agents  
- Claude Code（Anthropic官方CLI）
- Codex（OpenAI代码生成模型）
- Kiro（AI编程助手）
- Kilo（AI代码工具）
- Minmax M2（新一代AI编程模型）

**实施**:
- 创建统一的AI配置目录：`.ai/`
- 通用配置：`context.md`, `rules.md`, `prompts/`, `memory/`
- 各Agent专属配置：`.ai/agents/{agent-name}/`
- 提供配置文档：`.ai/README.md`

---

## 📊 工作量估算

| 阶段 | 工作量 | 说明 |
|------|--------|------|
| 准备阶段 | 1小时 | 创建目录结构和索引 |
| 文档迁移 | 2-3小时 | 移动和整理65个文档 |
| 脚本迁移 | 30分钟 | 移动10个脚本文件 |
| 清理验证 | 30分钟 | 清理根目录和验证 |
| AI配置 | 1小时 | 编写AI配置文件 |
| **总计** | **5-6小时** | 建议分2-3次完成 |

---

**方案版本**: v2.0（已根据决策更新）  
**创建日期**: 2025-11-14  
**更新日期**: 2025-11-14  
**作者**: Claude Code  
**状态**: 已确认决策，待执行  

**变更记录**:
- v1.0: 初始方案  
- v2.0: 根据项目负责人决策更新  
  - ✅ 确认归档策略：docs/archive/  
  - ✅ 确认ADR格式：标准模板  
  - ✅ 确认文档工具：暂不使用  
  - ✅ 确认AI支持：Claude Code, Codex, Kiro, Kilo, Minmax M2  
