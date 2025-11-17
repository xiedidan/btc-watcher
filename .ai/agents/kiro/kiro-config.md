# Kiro AI Configuration for BTC Watcher

## Project Context
请阅读: `../../context.md`

## Project Rules
请阅读: `../../rules.md`

## Kiro专属配置

### 代码分析重点
1. **性能优化机会识别**
2. **代码重复检测**
3. **复杂度分析**
4. **潜在Bug识别**
5. **最佳实践建议**

## 分析优先级

### 高优先级
- 数据库查询性能（N+1问题、缺失索引）
- 异步代码中的同步阻塞操作
- 内存泄漏风险（未关闭的连接、大对象缓存）
- 安全漏洞（SQL注入、XSS、敏感信息泄露）

### 中优先级
- 代码重复（DRY原则违反）
- 函数复杂度过高（圈复杂度 > 10）
- 缺少错误处理
- 缺少类型提示（Python）

### 低优先级
- 代码风格问题
- 注释缺失
- 变量命名优化

## 分析模式

### 1. 性能分析模式
关注点:
- 数据库查询效率
- 缓存使用
- 异步处理
- 资源管理

检查清单:
- [ ] 是否存在N+1查询问题
- [ ] 是否合理使用了Redis缓存
- [ ] 是否正确使用async/await
- [ ] 是否及时关闭数据库连接
- [ ] 是否有不必要的计算或I/O

### 2. 代码质量模式
关注点:
- 代码复用
- 模块化
- 可测试性
- 可维护性

检查清单:
- [ ] 是否有重复代码可以提取
- [ ] 函数是否单一职责
- [ ] 是否容易编写测试
- [ ] 是否有清晰的模块边界

### 3. 安全审计模式
关注点:
- 输入验证
- 认证授权
- 敏感信息保护
- 依赖安全

检查清单:
- [ ] 是否验证所有用户输入
- [ ] 是否正确实现认证授权
- [ ] 是否有硬编码的敏感信息
- [ ] 依赖库是否有已知漏洞

## 重构建议模板

### 性能优化建议
```markdown
**问题**: [描述性能问题]
**位置**: {文件路径}:{行号}
**影响**: [性能影响评估]
**建议**: [优化方案]
**示例代码**:
[优化后的代码示例]
```

### 代码质量建议
```markdown
**问题**: [描述代码质量问题]
**位置**: {文件路径}:{行号}
**违反原则**: [SOLID/DRY等原则]
**建议**: [改进方案]
**重构步骤**:
1. [步骤1]
2. [步骤2]
```

## 项目特定关注点

### Backend (Python/FastAPI)
- 异步数据库操作是否正确使用AsyncSession
- 依赖注入是否合理使用
- 异常处理是否完善
- 日志记录是否充分

### Frontend (Vue 3)
- 响应式数据是否正确使用ref/reactive
- 组件是否适当拆分
- 是否有内存泄漏（未清理的监听器/定时器）
- 状态管理是否合理

### FreqTrade集成
- 端口管理逻辑是否健壮
- 策略启动/停止是否处理并发
- 是否正确处理策略崩溃场景
- Webhook接收是否验证来源

## 输出格式

### 分析报告结构
```markdown
# 代码分析报告 - {模块名称}

## 概览
- 分析文件数: X
- 发现问题: Y
- 高优先级: A
- 中优先级: B
- 低优先级: C

## 高优先级问题
### 1. [问题标题]
- 位置:
- 描述:
- 影响:
- 建议:

## 中优先级问题
[同上格式]

## 低优先级问题
[同上格式]

## 总体建议
[整体改进建议]
```

## 使用指南

### 分析单个文件
```bash
kiro analyze backend/services/strategy.py --mode=quality
```

### 分析整个模块
```bash
kiro analyze backend/services/ --mode=performance
```

### 生成重构建议
```bash
kiro refactor backend/services/strategy.py --output=docs/analysis/
```

## 集成建议

### Pre-commit Hook
在提交前运行快速代码质量检查:
```bash
kiro quick-check --changed-files
```

### CI/CD Pipeline
在PR时运行完整分析:
```bash
kiro analyze --all --mode=full --output=report.md
```

## 学习资源
- [BTC Watcher架构设计](../../docs/architecture/system-design.md)
- [编码规范](../../.ai/rules.md)
- [性能优化报告](../../docs/implementation/optimizations/performance.md)
