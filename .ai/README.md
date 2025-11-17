# AI Coding Agent 配置

本目录包含各种AI Coding Agent的配置文件和上下文信息，帮助AI快速理解项目并遵循规范。

## 📁 目录结构

```
.ai/
├── README.md              # 本文件（AI配置说明）
├── context.md             # 项目上下文（必读）
├── rules.md               # AI工作规则（必读）
├── prompts/               # AI提示词模板
│   ├── feature-development.md
│   ├── bug-fix.md
│   ├── code-review.md
│   └── documentation.md
├── memory/                # AI记忆库
│   ├── project-overview.md
│   ├── tech-stack.md
│   ├── coding-patterns.md
│   └── common-issues.md
└── agents/                # 各AI Agent专属配置
    ├── claude-code/
    ├── codex/
    ├── kiro/
    ├── kilo/
    └── minmax-m2/
```

## 🤖 支持的AI Agents

### 1. Claude Code
**配置位置**: `agents/claude-code/instructions.md`
**特点**: Anthropic官方CLI工具，理解上下文能力强
**使用**: 自动读取 `context.md` 和 `rules.md`
**适用场景**:
- 复杂功能开发
- 架构设计讨论
- 代码重构
- 文档编写

### 2. Codex
**配置位置**: `agents/codex/config.json`
**特点**: OpenAI代码生成模型，代码补全准确
**使用**: 通过JSON配置文件提供项目上下文
**适用场景**:
- 代码自动补全
- 函数生成
- 单元测试编写
- 快速原型开发

### 3. Kiro
**配置位置**: `agents/kiro/kiro-config.md`
**特点**: 智能代码分析和重构
**使用**: 读取markdown配置和项目规则
**适用场景**:
- 代码审查
- 性能优化
- 代码重构
- 最佳实践建议

### 4. Kilo
**配置位置**: `agents/kilo/kilo-rules.md`
**特点**: 专注于代码质量和测试
**使用**: 基于规则文件进行代码检查
**适用场景**:
- 代码质量检查
- 测试覆盖分析
- 安全漏洞检测
- 代码规范验证

### 5. Minmax M2
**配置位置**: `agents/minmax-m2/m2-context.md`
**特点**: 新一代AI编程模型，多模态理解
**使用**: 综合上下文和代码库理解
**适用场景**:
- 复杂问题诊断
- 架构设计
- 多文件重构
- 跨模块开发

## 📖 通用配置文件

所有AI Agent都应该阅读以下文件：

### 1. context.md（项目上下文）
包含内容：
- 项目概述和技术栈
- 核心概念和术语
- 关键路径和文件位置
- 常见开发任务
- 编码规范和约束

**何时阅读**: 开始工作前必读

### 2. rules.md（AI工作规则）
包含内容：
- 文档管理规则
- 代码规范
- Git提交规范
- 安全规范
- 测试规范
- 禁止操作清单

**何时阅读**: 开始工作前必读，编码过程中查阅

### 3. prompts/（提示词模板）
提供标准化的工作流程模板：
- **feature-development.md**: 开发新功能时的步骤
- **bug-fix.md**: 修复Bug的流程
- **code-review.md**: 代码审查检查清单
- **documentation.md**: 编写文档的模板

**何时使用**: 根据任务类型选择对应模板

### 4. memory/（记忆库）
长期记忆和知识库：
- **project-overview.md**: 项目全局概览
- **tech-stack.md**: 技术栈详细信息
- **coding-patterns.md**: 项目中常用的编码模式
- **common-issues.md**: 常见问题和解决方案

**何时使用**: 遇到问题或需要参考时查阅

## 🚀 快速开始

### 对于AI Agent
1. 阅读 `context.md` 了解项目
2. 阅读 `rules.md` 了解规范
3. 根据任务类型选择 `prompts/` 中的模板
4. 查阅 `agents/{your-agent}/` 中的专属配置
5. 开始工作！

### 对于开发者
1. 根据使用的AI Agent，查看对应配置
2. 按需更新 `context.md` 和 `rules.md`
3. 为常见任务添加提示词模板
4. 记录常见问题到 `memory/common-issues.md`

## 📝 配置更新

### 何时更新配置

#### 更新 context.md
- 添加新的核心概念
- 技术栈发生变化
- 项目结构调整
- 新增重要功能模块

#### 更新 rules.md
- 编码规范变更
- 新增禁止操作
- 工作流程优化
- 新增检查规则

#### 添加 prompts
- 发现新的常见任务模式
- 工作流程标准化需求
- 团队最佳实践总结

#### 更新 memory
- 解决了新的常见问题
- 发现了新的编码模式
- 技术栈深度使用经验

### 如何更新
1. 编辑对应的markdown文件
2. 提交PR并说明变更原因
3. 团队Review后合并
4. 通知相关AI Agent用户

## 🎯 使用最佳实践

### 1. 明确任务类型
在开始前，明确你的任务：
- 新功能开发
- Bug修复
- 代码审查
- 文档编写
- 架构设计

### 2. 参考对应模板
根据任务类型，查阅 `prompts/` 中的相应模板。

### 3. 遵循工作流程
按照模板中的步骤执行，不要跳过关键环节。

### 4. 记录重要决策
架构决策记录到 `docs/adr/`，实现细节记录到 `docs/implementation/`。

### 5. 保持配置更新
发现配置不足或过时时，及时更新。

## 🔧 配置示例

### 示例1: 使用Claude Code开发新功能
```bash
# 1. 阅读上下文
cat .ai/context.md

# 2. 查看规则
cat .ai/rules.md

# 3. 选择模板
cat .ai/prompts/feature-development.md

# 4. 查看专属配置
cat .ai/agents/claude-code/instructions.md

# 5. 开始开发
# Claude Code会自动遵循配置
```

### 示例2: 使用Codex进行代码补全
```json
// 在IDE中配置Codex时，指向配置文件
{
  "codex.configPath": ".ai/agents/codex/config.json"
}
```

## 📚 相关文档

- [项目README](../README.md)
- [开发指南](../docs/development/README.md)
- [架构设计](../docs/architecture/system-design.md)
- [测试指南](../docs/testing/README.md)

## 🤝 如何为新AI Agent添加配置

1. 在 `agents/` 下创建新目录: `agents/{agent-name}/`
2. 添加该Agent的配置文件（markdown或JSON）
3. 确保配置文件引用了通用的 `context.md` 和 `rules.md`
4. 更新本README文件，添加Agent说明
5. 测试配置是否生效
6. 提交PR

### 配置文件模板
```markdown
# {Agent Name} Configuration for BTC Watcher

## Project Context
Read: ../../context.md

## Project Rules
Read: ../../rules.md

## Agent-Specific Settings
[Agent特定的配置]

## Usage
[如何使用此配置]
```

## 🔍 故障排查

### AI Agent无法理解项目
- 检查 `context.md` 是否完整
- 确认Agent配置文件路径正确
- 验证配置文件格式是否符合Agent要求

### AI Agent不遵循规范
- 检查 `rules.md` 是否清晰明确
- 在提示词中明确引用规则
- 考虑在Agent专属配置中强调关键规则

### 配置文件冲突
- 通用配置（context.md, rules.md）优先级最高
- Agent专属配置作为补充
- 发生冲突时，以更严格的规则为准

## 💡 提示

- 定期更新配置，保持与项目同步
- 记录AI使用过程中的问题和解决方案
- 与团队分享有效的提示词和配置
- 根据实际使用效果优化配置

---

**维护者**: BTC Watcher Team
**更新时间**: 2025-11-14
**版本**: v1.0
