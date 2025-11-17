# 文档归档目录

本目录用于存放过时但具有历史价值的文档。这些文档不再适用于当前版本，但保留以供参考和追溯项目演进历史。

## 📦 归档原则

### 什么文档应该归档？

1. **过时的设计文档**: 已被新设计替代的旧方案
2. **历史实现记录**: 已重构或废弃功能的实现文档
3. **过时的进度报告**: 已完成项目阶段的进度文档
4. **临时分析文档**: 特定时期的临时性分析文档
5. **废弃的计划文档**: 未采纳或已变更的计划文档

### 什么文档不应该归档？

- ❌ 仍在使用的功能文档
- ❌ 当前架构的设计文档
- ❌ 活跃的测试文档
- ❌ 有效的ADR（即使已被替代，也保留在adr/目录）

## 🗂️ 归档组织方式

### 按年份组织

```
archive/
├── README.md（本文件）
├── 2025/
│   └── outdated-docs/
│       ├── MISSING_FEATURES_SUMMARY.md
│       ├── IMPROVEMENT_CHECKLIST.md
│       ├── FIXES_SUMMARY.md
│       ├── FIXES_SOLUTION_PLAN.md
│       ├── FRONTEND_IMPLEMENTATION_PLAN.md
│       ├── PRIORITY_REDEFINITION.md
│       ├── test_logs.md
│       └── STRATEGY_PORT_INCONSISTENCY_FIX.md
├── 2026/
│   └── outdated-docs/
└── ...
```

### 目录结构说明

- **年份目录**: 按文档归档的年份组织
- **outdated-docs**: 存放该年度归档的文档
- 可以根据需要创建子目录分类（features/, bugs/, reports/等）

## 📋 归档流程

### 1. 识别需要归档的文档

检查文档是否满足归档条件：
- 文档是否已过时？
- 是否已被新文档替代？
- 是否仍有参考价值？

### 2. 移动文档到归档目录

```bash
# 移动文档
mv docs/implementation/features/old-feature.md docs/archive/2025/outdated-docs/

# 或者从根目录移动
mv OLD_DOCUMENT.md docs/archive/2025/outdated-docs/
```

### 3. 添加归档标记

在原文档位置（如果需要）添加跳转说明：

```markdown
# {原文档标题}

> **⚠️ 文档已归档**
>
> 本文档已于 2025-XX-XX 归档。
>
> **归档原因**: [说明原因，如"功能已重构"、"设计已变更"等]
>
> **新文档位置**: [如有替代文档，提供链接]
>
> **归档位置**: [docs/archive/2025/outdated-docs/{filename}](../archive/2025/outdated-docs/{filename}.md)
```

### 4. 更新相关索引

- 更新 `docs/README.md`，将文档状态标记为"已归档"
- 如果是ADR，在ADR README中更新状态
- 如果有替代文档，添加链接关系

### 5. 提交变更

```bash
git add docs/archive/
git commit -m "docs: 归档过时文档 {文档名}"
```

## 📌 归档文档清单

### 2025年归档

#### 过时的计划和总结文档

| 文档名 | 归档日期 | 归档原因 | 替代文档 |
|--------|----------|----------|----------|
| MISSING_FEATURES_SUMMARY.md | 2025-11-14 | 功能已完成 | - |
| IMPROVEMENT_CHECKLIST.md | 2025-11-14 | 改进已完成 | - |
| FIXES_SUMMARY.md | 2025-11-14 | 修复已完成 | - |
| FIXES_SOLUTION_PLAN.md | 2025-11-14 | 方案已执行 | - |
| FRONTEND_IMPLEMENTATION_PLAN.md | 2025-11-14 | 前端已实现 | - |
| PRIORITY_REDEFINITION.md | 2025-11-14 | 优先级已调整 | - |

#### 临时调试文档

| 文档名 | 归档日期 | 归档原因 | 替代文档 |
|--------|----------|----------|----------|
| test_logs.md | 2025-11-14 | 临时测试日志 | - |
| STRATEGY_PORT_INCONSISTENCY_FIX.md | 2025-11-14 | Bug已修复 | docs/implementation/bug-fixes/ |

## 🔍 查找归档文档

### 按年份查找
```bash
# 查看2025年的所有归档文档
ls docs/archive/2025/outdated-docs/
```

### 按关键词搜索
```bash
# 在归档目录中搜索关键词
grep -r "关键词" docs/archive/
```

### 按文件名查找
```bash
# 查找特定文件
find docs/archive/ -name "*strategy*.md"
```

## 💡 使用建议

### 何时查阅归档文档？

1. **历史追溯**: 了解某个功能的历史演进
2. **问题诊断**: 类似问题的历史解决方案
3. **学习参考**: 了解团队过去的决策过程
4. **知识传承**: 帮助新成员了解项目历史

### 注意事项

⚠️ **归档文档可能包含过时信息**
- 代码可能已变更
- 技术栈可能已升级
- API可能已废弃
- 最佳实践可能已改变

✅ **使用归档文档时**
- 仅作为参考，不要直接使用
- 查看文档的归档日期
- 对照当前文档验证信息
- 必要时咨询团队成员

## 📊 归档统计

### 2025年
- 归档文档总数: 8
- 计划类文档: 6
- 临时类文档: 2

### 总计
- 所有归档文档: 8

## 🔧 维护

### 定期清理
每年年底进行归档文档审查：
- 检查是否有文档可以永久删除
- 整理归档目录结构
- 更新归档清单

### 归档策略
- **短期保留**（1-2年）: 临时文档、测试日志
- **中期保留**（3-5年）: 实现记录、Bug修复
- **长期保留**（永久）: 重要设计决策、架构变更

---

**维护者**: BTC Watcher Documentation Team
**最后更新**: 2025-11-14
**版本**: v1.0

**说明**: 如需归档文档或有疑问，请联系文档维护团队
