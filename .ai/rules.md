# AI Coding Rules

## 文档管理规则

### 新文档创建位置
1. **新功能文档**: `docs/implementation/features/{feature-name}.md`
2. **Bug修复文档**: `docs/implementation/bug-fixes/{bug-description}.md`
3. **架构变更文档**: `docs/architecture/` 或 `docs/adr/{number}-{title}.md`
4. **测试报告**: `docs/testing/test-reports/{report-name}.md`
5. **进度报告**: `docs/reports/progress/{progress-report}.md`

### 命名规范
- **功能文档**: `{feature-name}.md` (kebab-case)
- **Bug文档**: `{bug-description}.md` (kebab-case)
- **ADR文档**: `{number}-{title}.md` (例: `001-database-choice.md`)
- **测试报告**: `{module}-test-report.md`

### 文档模板
新建文档时，参考 `.ai/prompts/` 目录下的模板：
- 功能开发: `feature-development.md`
- Bug修复: `bug-fix.md`
- 代码审查: `code-review.md`
- 文档编写: `documentation.md`

## Git 提交规范

### Commit Message格式
```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type类型
- `feat`: 新功能
- `fix`: Bug修复
- `docs`: 文档更新
- `test`: 测试相关
- `refactor`: 重构（不改变外部行为）
- `perf`: 性能优化
- `style`: 代码格式（不影响功能）
- `chore`: 构建/工具变更
- `ci`: CI/CD相关

### 示例
```bash
feat(strategy): 添加策略批量启动功能

- 支持一次启动多个策略
- 添加进度显示
- 优化并发处理

Closes #123
```

## 代码规范

### Python后端
1. **遵循PEP 8**: 使用black格式化
2. **类型提示**: 所有函数参数和返回值必须有类型提示
3. **异步编程**: I/O操作使用 `async/await`
4. **依赖注入**: 使用FastAPI的 `Depends`
5. **错误处理**: 使用自定义异常和HTTPException
6. **日志记录**: 使用结构化日志（logging模块）
7. **测试要求**: 新功能必须有单元测试和集成测试

**示例**:
```python
from typing import List
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

async def get_strategies(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100
) -> List[Strategy]:
    """获取策略列表"""
    try:
        result = await db.execute(
            select(Strategy).offset(skip).limit(limit)
        )
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Failed to get strategies: {e}")
        raise HTTPException(status_code=500, detail="Internal error")
```

### Vue 3前端
1. **Composition API**: 优先使用 `<script setup>`
2. **组件命名**: PascalCase（如 `StrategyList.vue`）
3. **Props定义**: 使用TypeScript或PropTypes
4. **响应式数据**: 使用 `ref` 和 `reactive`
5. **状态管理**: 复杂状态使用Pinia
6. **API调用**: 统一在 `src/api/` 目录
7. **错误处理**: 使用try-catch和全局错误处理

**示例**:
```vue
<script setup>
import { ref, onMounted } from 'vue'
import { getStrategies } from '@/api/strategy'
import { ElMessage } from 'element-plus'

const strategies = ref([])
const loading = ref(false)

const fetchStrategies = async () => {
  loading.value = true
  try {
    const response = await getStrategies()
    strategies.value = response.data
  } catch (error) {
    ElMessage.error('获取策略列表失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchStrategies()
})
</script>
```

### 数据库操作
1. **使用ORM**: 所有数据库操作通过SQLAlchemy
2. **异步查询**: 使用AsyncSession
3. **防SQL注入**: 不要拼接SQL字符串
4. **事务管理**: 复杂操作使用事务
5. **连接池**: 使用FastAPI的依赖注入管理连接

### API设计
1. **RESTful**: 遵循REST规范
2. **版本控制**: 路径包含版本号 `/api/v1/`
3. **状态码**: 正确使用HTTP状态码
4. **分页**: 列表接口支持分页（skip/limit）
5. **过滤排序**: 使用查询参数
6. **响应格式**: 统一JSON格式

## 安全规范

### 禁止操作 ❌
1. **不要在根目录创建新的 .md 文件**
   - 所有文档必须在 `docs/` 目录下
   - 唯一例外: `README.md`, `CHANGELOG.md`, `LICENSE`

2. **不要删除现有文档**
   - 过时文档移到 `docs/archive/` 而非删除
   - 保留Git历史记录

3. **不要修改 docs/ 目录结构**
   - 按照既定的目录组织原则
   - 需要调整时先提PR讨论

4. **不要硬编码敏感信息**
   - 密码、Token、API Key 必须使用环境变量
   - 使用 `.env` 文件（不提交到Git）
   - 提供 `.env.example` 模板

5. **不要在async函数中使用同步I/O**
   - 数据库查询: 使用AsyncSession
   - HTTP请求: 使用httpx异步客户端
   - 文件I/O: 使用aiofiles

6. **不要跳过测试**
   - 新功能必须有测试
   - 修复Bug必须添加回归测试
   - PR必须通过所有测试

## 测试规范

### 测试要求
1. **单元测试**: 测试独立函数和类方法
2. **集成测试**: 测试API端点和数据库交互
3. **E2E测试**: 测试完整用户流程
4. **性能测试**: 关键接口需要性能测试

### 测试覆盖率
- 总体覆盖率: > 80%
- 核心服务: > 90%
- API端点: 100%

### 测试命名
```python
def test_{function_name}_{scenario}_{expected_result}():
    """测试描述"""
    pass

# 示例
def test_create_strategy_with_valid_data_returns_201():
    """测试使用有效数据创建策略返回201"""
    pass
```

## 文档规范

### 文档更新时机
1. **新功能**: 完成后立即更新文档
2. **API变更**: 同步更新API文档
3. **架构变更**: 创建ADR记录决策
4. **Bug修复**: 重要Bug需记录修复过程

### ADR（架构决策记录）
当进行以下决策时，创建ADR：
- 技术栈选择
- 架构模式变更
- 重要依赖库选择
- 数据模型设计
- 性能优化方案

ADR格式参考: `docs/adr/template.md`

## 开发流程

### 功能开发流程
1. 阅读需求: `docs/analysis/requirements.md`
2. 设计方案: 创建设计文档或ADR
3. 实现代码: 遵循编码规范
4. 编写测试: 单元测试 + 集成测试
5. 本地验证: 运行所有测试
6. 创建PR: 包含代码、测试、文档
7. 代码审查: 等待审查通过
8. 合并代码: 合并到主分支
9. 记录实现: 创建实现文档

### Bug修复流程
1. 重现问题: 理解Bug现象
2. 诊断原因: 查找根本原因
3. 设计修复: 确定修复方案
4. 实现修复: 修改代码
5. 添加测试: 防止回归
6. 验证修复: 确认问题解决
7. 创建PR: 提交修复
8. 记录过程: 创建Bug修复文档

## 性能优化规范

### 后端性能
1. **数据库查询**: 使用索引、避免N+1查询
2. **缓存策略**: 使用Redis缓存热点数据
3. **异步处理**: 耗时操作使用后台任务
4. **连接池**: 合理配置数据库连接池
5. **分页查询**: 大数据集必须分页

### 前端性能
1. **懒加载**: 路由和组件按需加载
2. **防抖节流**: 频繁操作添加防抖/节流
3. **虚拟滚动**: 长列表使用虚拟滚动
4. **缓存优化**: 合理使用Pinia缓存
5. **打包优化**: 代码分割、Tree Shaking

## 检查清单

### 提交代码前检查
- [ ] 代码遵循规范（PEP 8 / ESLint）
- [ ] 添加了必要的类型提示（Python）
- [ ] 添加了单元测试
- [ ] 添加了集成测试（如适用）
- [ ] 所有测试通过
- [ ] 更新了相关文档
- [ ] 没有硬编码敏感信息
- [ ] 没有在根目录创建文档
- [ ] Commit message符合规范

### PR检查
- [ ] PR描述清晰
- [ ] 包含测试代码
- [ ] 文档已更新
- [ ] 通过CI/CD检查
- [ ] 代码审查通过

## 工具使用

### 推荐工具
- **代码格式化**: black (Python), prettier (JS)
- **代码检查**: pylint/flake8 (Python), ESLint (JS)
- **类型检查**: mypy (Python), TypeScript
- **测试**: pytest (Python), vitest (JS)
- **API测试**: httpx/pytest-asyncio
- **性能分析**: locust, cProfile

### 开发命令
```bash
# 运行测试
make test

# 检查代码格式
make lint

# 启动开发服务器
make dev

# 查看日志
make logs

# 检查文档结构
make docs-check
```

## 学习资源

### 项目文档
- [项目README](../README.md)
- [架构设计](../docs/architecture/system-design.md)
- [开发指南](../docs/development/README.md)
- [测试指南](../docs/testing/README.md)

### 外部资源
- [FastAPI文档](https://fastapi.tiangolo.com/)
- [Vue 3文档](https://vuejs.org/)
- [SQLAlchemy 2.0](https://docs.sqlalchemy.org/)
- [Element Plus](https://element-plus.org/)
