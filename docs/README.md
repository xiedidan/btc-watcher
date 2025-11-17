# BTC Watcher 文档中心

欢迎来到BTC Watcher文档中心！这里包含了项目的所有文档，帮助你快速上手和深入理解系统。

## 📖 快速导航

### 我想...
- **开始使用系统** → [快速开始](user/getting-started.md) | [部署指南](user/deployment-guide.md)
- **了解系统架构** → [系统设计](architecture/system-design.md) | [详细设计](architecture/detailed-design.md)
- **开发新功能** → [开发指南](development/README.md) | [编码规范](development/coding-standards.md)
- **部署和运维** → [部署文档](operations/deployment/) | [故障排查](operations/troubleshooting/)
- **运行测试** → [测试指南](testing/README.md) | [单元测试](testing/unit-testing.md)
- **查看实现记录** → [功能实现](implementation/features/) | [Bug修复](implementation/bug-fixes/)
- **了解架构决策** → [ADR索引](adr/README.md)

---

## 🗺️ 文档地图

### 📁 文档目录结构

```
docs/
├── user/                    # 👤 用户文档
├── architecture/            # 🏗️ 架构设计
├── development/             # 🔧 开发文档
├── operations/              # 🚀 运维文档
├── testing/                 # 🧪 测试文档
├── implementation/          # 📝 实现记录
├── analysis/                # 📊 分析文档
├── reports/                 # 📑 项目报告
├── adr/                     # 🎯 架构决策记录
└── archive/                 # 📦 归档文档
```

---

## 📚 文档分类详解

### 👤 用户文档 (user/)
**面向**: 最终用户、系统管理员
**内容**: 使用指南、部署手册、常见问题

| 文档 | 描述 | 状态 |
|------|------|------|
| [快速开始](user/getting-started.md) | 5分钟上手指南 | ✅ 已完成 |
| [部署指南](user/deployment-guide.md) | 完整部署流程 | ✅ 已完成 |
| [用户手册](user/user-guide.md) | 详细使用说明 | ✅ 已完成 |
| [API参考](user/api-reference.md) | API接口文档 | ✅ 已完成 |
| [故障排查](user/troubleshooting.md) | 常见问题解决 | ✅ 已完成 |
| [FAQ](user/faq.md) | 常见问题FAQ | ✅ 已完成 |

### 🏗️ 架构设计 (architecture/)
**面向**: 架构师、高级开发者
**内容**: 系统架构、设计文档、技术选型

| 文档 | 描述 | 状态 |
|------|------|------|
| [架构概览](architecture/README.md) | 架构总体介绍 | 📝 待创建 |
| [系统设计](architecture/system-design.md) | 系统整体设计 | 📝 待创建 |
| [详细设计](architecture/detailed-design.md) | 详细技术设计 | 📝 待创建 |
| [API设计](architecture/api-design.md) | API接口设计 | 📝 待创建 |
| [数据库设计](architecture/database-design.md) | 数据库Schema设计 | 📝 待创建 |
| [业务流程](architecture/business-flow.md) | 业务流程设计 | 📝 待创建 |

**模块设计** (architecture/modules/):
- [市场数据模块](architecture/modules/market-data.md)
- [通知中心](architecture/modules/notifyhub.md)
- [价格服务](architecture/modules/price-service.md)
- [实时回退](architecture/modules/realtime-fallback.md)

### 🔧 开发文档 (development/)
**面向**: 开发者、贡献者
**内容**: 开发环境、编码规范、工作流程

| 文档 | 描述 | 状态 |
|------|------|------|
| [开发指南总览](development/README.md) | 开发指南索引 | 📝 待创建 |
| [环境搭建](development/setup.md) | 开发环境配置 | 📝 待创建 |
| [编码规范](development/coding-standards.md) | 代码规范 | 📝 待创建 |
| [Git工作流](development/git-workflow.md) | Git使用规范 | 📝 待创建 |
| [测试指南](development/testing-guide.md) | 测试编写指南 | 📝 待创建 |
| [贡献指南](development/contributing.md) | 如何贡献代码 | 📝 待创建 |
| [虚拟环境](development/virtualenv-guide.md) | Python虚拟环境 | 📝 待创建 |

### 🚀 运维文档 (operations/)
**面向**: 运维工程师、DevOps
**内容**: 部署、监控、故障排查

**部署相关** (operations/deployment/):
- [快速部署](operations/deployment/quick-start.md)
- [Alpha环境部署](operations/deployment/alpha-deployment.md)
- [生产环境部署](operations/deployment/production.md)
- [FRP WebSocket配置](operations/deployment/frp-websocket.md)

**故障排查** (operations/troubleshooting/):
- [WebSocket问题](operations/troubleshooting/websocket-issues.md)
- [Discord代理问题](operations/troubleshooting/discord-proxy.md)
- [常见错误](operations/troubleshooting/common-errors.md)

**其他**:
- [监控配置](operations/monitoring.md)
- [备份与恢复](operations/backup-recovery.md)
- [Nginx配置](operations/nginx-setup.md)

### 🧪 测试文档 (testing/)
**面向**: 测试工程师、开发者
**内容**: 测试策略、测试指南、测试报告

| 文档 | 描述 | 状态 |
|------|------|------|
| [测试指南总览](testing/README.md) | 测试指南索引 | 📝 待创建 |
| [单元测试](testing/unit-testing.md) | 单元测试指南 | 📝 待创建 |
| [集成测试](testing/integration-testing.md) | 集成测试指南 | 📝 待创建 |
| [E2E测试](testing/e2e-testing.md) | E2E测试指南 | 📝 待创建 |
| [性能测试](testing/performance-testing.md) | 性能测试指南 | 📝 待创建 |

**测试报告** (testing/test-reports/):
- [单元测试报告](testing/test-reports/unit-test-report.md)
- [E2E框架搭建](testing/test-reports/e2e-framework-setup.md)
- [性能基准](testing/test-reports/performance-baseline.md)

### 📝 实现记录 (implementation/)
**面向**: 开发团队
**内容**: 功能实现过程、Bug修复记录、优化历史

**功能实现** (implementation/features/):
- [NotifyHub实现](implementation/features/notifyhub.md)
- [市场数据实现](implementation/features/market-data.md)
- [实时回退实现](implementation/features/realtime-fallback.md)
- [策略上传实现](implementation/features/strategy-upload.md)
- [通知渠道实现](implementation/features/notification-channel.md)

**Bug修复** (implementation/bug-fixes/):
- [策略状态Bug](implementation/bug-fixes/strategy-status.md)
- [WebSocket修复](implementation/bug-fixes/websocket-fix.md)
- [Watcher回调错误](implementation/bug-fixes/watcher-callback.md)
- [Discord测试修复](implementation/bug-fixes/discord-test.md)

**性能优化** (implementation/optimizations/):
- [性能优化](implementation/optimizations/performance.md)
- [图表优化](implementation/optimizations/charts.md)

### 📊 分析文档 (analysis/)
**面向**: 产品经理、架构师
**内容**: 需求分析、业务分析、技术调研

| 文档 | 描述 | 状态 |
|------|------|------|
| [需求分析](analysis/requirements.md) | 需求文档 | 📝 待创建 |
| [用户需求调研](analysis/user-survey.md) | 用户调研结果 | 📝 待创建 |
| [实现差距分析](analysis/gap-analysis.md) | 需求vs实现 | 📝 待创建 |
| [业务细节分析](analysis/business-details.md) | 业务逻辑分析 | 📝 待创建 |
| [图表分析](analysis/charts-analysis.md) | 图表需求分析 | 📝 待创建 |
| [Redis分析](analysis/redis-analysis.md) | Redis使用分析 | 📝 待创建 |

### 📑 项目报告 (reports/)
**面向**: 项目管理、团队成员
**内容**: 进度报告、完成报告、诊断报告

**进度报告** (reports/progress/):
- [任务进度](reports/progress/task-progress.md)
- [实现进度](reports/progress/implementation-progress.md)
- [单元测试进度](reports/progress/unit-test-progress.md)
- [策略测试进度](reports/progress/strategy-test-progress.md)

**完成报告** (reports/completion/):
- [P0完成报告](reports/completion/p0-completion.md)
- [项目完成报告](reports/completion/project-completion.md)
- [最终总结](reports/completion/final-summary.md)

**诊断报告** (reports/diagnostics/):
- [问题诊断](reports/diagnostics/problem-diagnosis.md)
- [诊断报告](reports/diagnostics/diagnosis-report.md)

**评审报告** (reports/reviews/):
- [Alpha就绪评估](reports/reviews/alpha-readiness.md)
- [Alpha测试指南](reports/reviews/alpha-test-guide.md)

### 🎯 架构决策记录 (adr/)
**面向**: 架构师、技术负责人
**内容**: 重要技术决策的记录

> ADR (Architecture Decision Record) 记录项目中的重要架构决策，包括决策背景、选项分析、最终决定和后果。

| 文档 | 描述 | 状态 |
|------|------|------|
| [ADR索引](adr/README.md) | ADR列表和说明 | ✅ 模板已创建 |
| [ADR模板](adr/template.md) | 标准ADR模板 | ✅ 已创建 |
| [001-数据库选择](adr/001-database-choice.md) | PostgreSQL选型 | 📝 待创建 |
| [002-WebSocket策略](adr/002-websocket-strategy.md) | WebSocket设计 | 📝 待创建 |

### 📦 归档文档 (archive/)
**面向**: 历史参考
**内容**: 过时但保留的历史文档

查看 [归档说明](archive/README.md) 了解归档文档的组织方式。

---

## 🤖 AI使用指南

如果你是AI Coding Agent，请先阅读：
1. [AI上下文](../.ai/context.md) - 项目概览、技术栈、核心概念
2. [AI工作规则](../.ai/rules.md) - 文档规则、编码规范、禁止操作
3. [AI配置说明](../.ai/README.md) - 各种AI Agent的配置方式
4. [项目概览](../.ai/memory/project-overview.md) - 项目全局信息

### AI创建文档时的规则
- ❌ **不要在根目录创建** .md 文件
- ✅ **按类型放置**: 功能 → features/, Bug → bug-fixes/, 架构 → adr/
- ✅ **使用模板**: 参考 `.ai/prompts/` 目录
- ✅ **更新索引**: 创建文档后更新本README
- ✅ **遵循规范**: 参考 `.ai/rules.md`

---

## 📋 文档状态说明

- ✅ **已完成**: 文档已完整编写
- 🔄 **更新中**: 文档正在更新
- 📝 **待创建**: 文档计划创建但尚未开始
- 🗃️ **已归档**: 文档已移至archive/

---

## 🔍 如何查找文档？

### 按角色查找
- **用户/管理员** → `user/` 目录
- **开发者** → `development/` + `implementation/`
- **架构师** → `architecture/` + `adr/`
- **测试工程师** → `testing/`
- **运维工程师** → `operations/`
- **项目经理** → `reports/` + `analysis/`

### 按任务查找
- **部署系统** → `user/deployment-guide.md` 或 `operations/deployment/`
- **开发功能** → `development/` → `architecture/modules/` → `implementation/features/`
- **修复Bug** → `development/` → `implementation/bug-fixes/`
- **了解决策** → `adr/`
- **性能优化** → `implementation/optimizations/` + `testing/performance-testing.md`

### 按关键词查找
```bash
# 在docs目录下搜索关键词
grep -r "关键词" docs/

# 搜索特定类型文档
find docs/ -name "*strategy*.md"
```

---

## 📝 文档贡献

### 创建新文档
1. 确定文档类型和位置
2. 使用对应的模板（`.ai/prompts/`）
3. 编写文档内容
4. 更新本README索引
5. 提交PR

### 更新现有文档
1. 修改文档内容
2. 更新文档顶部的"更新时间"
3. 如有重大变更，更新CHANGELOG
4. 提交PR

### 归档过时文档
1. 不要删除，移至 `archive/2025/outdated-docs/`
2. 在原位置添加跳转说明
3. 更新本README，标记为已归档
4. 提交PR

---

## 🔗 相关资源

### 项目链接
- [项目README](../README.md)
- [AI配置目录](../.ai/)
- [后端代码](../backend/)
- [前端代码](../frontend/)

### 在线文档
- [API文档](http://localhost:8000/docs) (开发环境)
- [ReDoc](http://localhost:8000/redoc) (开发环境)

### 外部资源
- [FastAPI官方文档](https://fastapi.tiangolo.com/)
- [Vue 3官方文档](https://vuejs.org/)
- [Element Plus文档](https://element-plus.org/)
- [FreqTrade文档](https://www.freqtrade.io/)

---

## 💡 使用提示

1. **文档优先**: 开发前先查阅相关文档
2. **及时更新**: 代码变更同步更新文档
3. **记录决策**: 重要决策创建ADR
4. **保持同步**: 文档与代码保持一致
5. **善用搜索**: 使用grep/find快速定位

---

**文档版本**: v1.0
**最后更新**: 2025-11-14
**维护者**: BTC Watcher Team

**反馈**: 如有文档问题或建议，请提Issue或PR
