# 架构决策记录（ADR）

## 什么是ADR？

Architecture Decision Records (ADR) 用于记录项目中的重要架构决策。每个ADR描述一个决策的上下文、决策内容和后果。

## 为什么要使用ADR？

1. **知识传承**: 帮助新成员理解为什么做出某些决策
2. **决策透明**: 记录决策过程和考虑的因素
3. **避免重复**: 防止重新讨论已经解决的问题
4. **责任明确**: 清楚地记录决策者和时间
5. **历史追溯**: 了解系统演进的历史脉络

## ADR格式

我们使用标准的ADR格式，包含以下章节：

1. **上下文（Context）**: 描述促使做出决策的背景和问题
2. **决策（Decision）**: 说明最终采取的行动和选择
3. **备选方案（Alternatives Considered）**: 列出考虑过的其他方案及优缺点
4. **后果（Consequences）**: 描述决策带来的影响（正面和负面）
5. **实施计划（Implementation）**: 如何实施这个决策
6. **参考资料（References）**: 相关文档和资料链接

详细模板见: [template.md](template.md)

## ADR列表

| 编号 | 标题 | 状态 | 日期 | 描述 |
|------|------|------|------|------|
| [001](001-database-choice.md) | 选择PostgreSQL作为主数据库 | 已接受 | 2025-01-10 | 数据库技术选型决策 |
| [002](002-websocket-strategy.md) | WebSocket实时推送架构 | 已接受 | 2025-02-15 | WebSocket设计决策 |
| [Template](template.md) | ADR标准模板 | 模板 | - | 创建新ADR时使用 |

## ADR状态说明

- **提议中（Proposed）**: 正在讨论中，尚未做出决定
- **已接受（Accepted）**: 已经采纳并开始实施
- **已废弃（Deprecated）**: 不再使用，但保留记录
- **已替代（Superseded）**: 被新的ADR替代（需注明替代的ADR编号）
- **已拒绝（Rejected）**: 经讨论决定不采用

## 如何创建新的ADR？

### 步骤1: 确定需要ADR的决策

以下情况建议创建ADR：
- 选择技术栈或框架
- 改变系统架构模式
- 选择重要的依赖库
- 设计关键的数据模型
- 制定性能优化方案
- 安全策略决策
- 可扩展性设计决策

### 步骤2: 创建ADR文件

```bash
# 1. 复制模板
cp docs/adr/template.md docs/adr/003-your-decision-title.md

# 2. 编辑文件
# 填写所有章节内容
```

### 步骤3: 填写ADR内容

按照模板填写：
1. 修改标题和日期
2. 描述上下文和问题
3. 说明最终决策
4. 列出备选方案
5. 分析后果
6. 制定实施计划
7. 添加参考资料

### 步骤4: 更新索引

```markdown
# 在本文件的ADR列表中添加一行
| [003](003-your-decision-title.md) | 决策标题 | 提议中 | 2025-XX-XX | 简短描述 |
```

### 步骤5: 团队讨论

1. 创建PR提交ADR
2. 团队成员Review和讨论
3. 达成共识后合并
4. 更新状态为"已接受"

## ADR命名规范

格式: `{编号}-{简短标题}.md`

- **编号**: 三位数字，从001开始递增
- **标题**: 使用kebab-case，简洁描述决策内容
- **扩展名**: 统一使用 `.md`

**示例**:
- ✅ `001-database-choice.md`
- ✅ `002-websocket-strategy.md`
- ✅ `003-redis-cache-design.md`
- ❌ `database.md` (缺少编号)
- ❌ `001_Database_Choice.md` (格式错误)

## ADR更新规则

### 补充信息
如果需要补充信息，可以直接编辑ADR：
- 添加新的备选方案分析
- 更新实施进度
- 补充参考资料

### 改变决策
如果需要改变决策：
1. 创建新的ADR
2. 在新ADR中说明替代关系
3. 将旧ADR状态改为"已替代"
4. 在旧ADR中添加链接到新ADR

**示例**:
```markdown
# 旧ADR头部添加
> **状态**: 已替代 - 被 [ADR-005](005-new-decision.md) 替代
```

## 常见问题

### Q: 所有决策都需要ADR吗？
A: 不需要。只有**重要的**、**影响架构的**、**需要记录原因的**决策才需要ADR。日常的小决策不需要。

### Q: ADR应该多详细？
A: 足够详细以便他人理解决策背景和原因，但不要过于冗长。一般1-3页为宜。

### Q: 谁来编写ADR？
A: 通常由做出决策的架构师或技术负责人编写，但任何人都可以提议ADR。

### Q: ADR可以修改吗？
A: 已接受的ADR原则上不应大幅修改。如需改变决策，创建新的ADR并标记旧ADR为"已替代"。

### Q: ADR和设计文档的区别？
A: ADR专注于**决策过程**和**为什么**，设计文档专注于**如何实现**。两者互补。

## 参考资源

### 外部资源
- [ADR GitHub](https://adr.github.io/)
- [Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
- [架构决策记录最佳实践](https://github.com/joelparkerhenderson/architecture-decision-record)

### 项目内资源
- [ADR模板](template.md)
- [架构设计文档](../architecture/)
- [技术选型分析](../analysis/)

## 工具和辅助

### 自动化编号
```bash
# 获取下一个ADR编号
ls docs/adr/ | grep -E '^[0-9]{3}-' | tail -1 | awk -F'-' '{printf "%03d\n", $1+1}'
```

### 创建ADR快捷脚本
```bash
#!/bin/bash
# scripts/utils/new-adr.sh

# 获取下一个编号
NEXT_NUM=$(ls docs/adr/ | grep -E '^[0-9]{3}-' | tail -1 | awk -F'-' '{printf "%03d\n", $1+1}')
if [ -z "$NEXT_NUM" ]; then
    NEXT_NUM="001"
fi

# 获取标题
echo "Enter ADR title (kebab-case):"
read TITLE

# 创建文件
FILENAME="docs/adr/${NEXT_NUM}-${TITLE}.md"
cp docs/adr/template.md "$FILENAME"

# 更新日期
sed -i "s/YYYY-MM-DD/$(date +%Y-%m-%d)/" "$FILENAME"
sed -i "s/{编号}/$NEXT_NUM/" "$FILENAME"

echo "Created: $FILENAME"
echo "Please edit the file and update docs/adr/README.md"
```

---

**维护者**: BTC Watcher Architecture Team
**最后更新**: 2025-11-14
**版本**: v1.0
