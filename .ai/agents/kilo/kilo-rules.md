# Kilo AI Rules for BTC Watcher

## Project Context
Read: `../../context.md`

## Project Rules
Read: `../../rules.md`

## Kilo专属职责

Kilo专注于代码质量和测试，确保代码符合最高标准。

### 核心职责
1. **代码规范检查**
2. **测试覆盖率验证**
3. **安全漏洞扫描**
4. **依赖管理**
5. **文档完整性检查**

## 检查规则

### 1. 代码规范检查

#### Python后端
- [x] PEP 8 合规性
- [x] 类型提示完整性
- [x] Docstring存在性
- [x] Import顺序和分组
- [x] 函数复杂度 < 10
- [x] 文件长度 < 500行
- [x] 类方法数 < 20

#### JavaScript/Vue前端
- [x] ESLint规则合规
- [x] Prettier格式化
- [x] 组件命名规范（PascalCase）
- [x] Props类型定义
- [x] Emit事件定义
- [x] 使用Composition API
- [x] 避免使用Options API

### 2. 测试覆盖率验证

#### 覆盖率要求
- **总体覆盖率**: >= 80%
- **核心服务**: >= 90%
- **API端点**: 100%
- **工具函数**: >= 85%

#### 测试类型检查
- [x] 单元测试存在
- [x] 集成测试存在（API端点）
- [x] E2E测试存在（关键流程）
- [x] 测试命名规范
- [x] 测试断言明确
- [x] Mock使用合理

### 3. 安全漏洞扫描

#### 常见漏洞检查
- [x] SQL注入风险（禁止字符串拼接）
- [x] XSS风险（验证输入，转义输出）
- [x] 硬编码敏感信息
- [x] 不安全的随机数生成
- [x] 缺失的认证检查
- [x] CSRF防护
- [x] 依赖库漏洞

#### 敏感信息检查
禁止出现：
- API密钥
- 数据库密码
- JWT密钥
- 第三方Token
- 私钥文件

### 4. 依赖管理

#### Python依赖
```bash
# 检查过时依赖
pip list --outdated

# 检查安全漏洞
pip-audit

# 验证requirements.txt
pip check
```

#### JavaScript依赖
```bash
# 检查过时依赖
npm outdated

# 检查安全漏洞
npm audit

# 修复安全漏洞
npm audit fix
```

### 5. 文档完整性检查

#### 代码文档
- [x] 所有公共函数有docstring
- [x] 复杂逻辑有注释
- [x] API端点有描述
- [x] Schema有示例
- [x] 环境变量有说明

#### 项目文档
- [x] README.md存在且完整
- [x] API文档更新
- [x] 架构文档同步
- [x] 部署文档准确
- [x] CHANGELOG更新

## 质量门禁

### PR合并前必须通过

#### 代码质量
```bash
# Python
black --check backend/
flake8 backend/
mypy backend/

# JavaScript
npm run lint
npm run type-check
```

#### 测试
```bash
# 所有测试通过
pytest backend/tests/

# 覆盖率达标
pytest --cov=backend --cov-report=term --cov-fail-under=80
```

#### 安全检查
```bash
# Python安全检查
bandit -r backend/

# JavaScript安全检查
npm audit --audit-level=moderate
```

## 自动化检查

### Pre-commit检查
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    hooks:
      - id: black
  - repo: https://github.com/pycqa/flake8
    hooks:
      - id: flake8
  - repo: https://github.com/pre-commit/mirrors-mypy
    hooks:
      - id: mypy
```

### CI/CD Pipeline
```yaml
# .github/workflows/quality-check.yml
jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - name: Code Format Check
        run: black --check .

      - name: Lint Check
        run: flake8 .

      - name: Type Check
        run: mypy .

      - name: Test
        run: pytest --cov=. --cov-fail-under=80

      - name: Security Scan
        run: bandit -r .
```

## 错误级别

### Critical（阻止合并）
- 测试失败
- 覆盖率低于阈值
- 安全漏洞（高危）
- 硬编码敏感信息
- 语法错误

### Error（必须修复）
- 代码规范严重违反
- 缺失关键测试
- 未处理的异常
- 安全漏洞（中危）
- 重要文档缺失

### Warning（建议修复）
- 代码规范轻微违反
- 测试覆盖率偏低（60-80%）
- 代码复杂度高
- 依赖版本过时
- 注释不足

### Info（可忽略）
- 代码风格建议
- 性能优化建议
- 命名建议
- 文档改进建议

## 检查清单

### 提交代码前检查
```markdown
- [ ] 代码格式化（black/prettier）
- [ ] Lint检查通过（flake8/eslint）
- [ ] 类型检查通过（mypy/typescript）
- [ ] 所有测试通过
- [ ] 测试覆盖率达标
- [ ] 无安全漏洞
- [ ] 无硬编码敏感信息
- [ ] 文档已更新
- [ ] Commit message符合规范
```

### PR Review检查
```markdown
- [ ] 代码质量门禁通过
- [ ] 测试充分
- [ ] 文档完整
- [ ] 无安全风险
- [ ] 性能无明显下降
- [ ] 向后兼容
- [ ] 日志完善
```

## 报告格式

### 质量检查报告
```markdown
# 代码质量检查报告

## 概览
- 检查文件: X个
- Critical: A个
- Error: B个
- Warning: C个
- Info: D个

## Critical Issues
### [文件路径]:[行号]
**问题**: [描述]
**规则**: [违反的规则]
**修复**: [修复建议]

## Error Issues
[同上格式]

## Warning Issues
[同上格式]

## 测试覆盖率
- 总体: X%
- 后端: Y%
- 前端: Z%

## 安全扫描
- 高危漏洞: 0
- 中危漏洞: 0
- 低危漏洞: X

## 建议
[整体改进建议]
```

## 集成方式

### IDE集成
```json
// VSCode settings.json
{
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "eslint.enable": true
}
```

### Git Hooks
```bash
#!/bin/bash
# .git/hooks/pre-push

# Run quality checks
kilo check --all

if [ $? -ne 0 ]; then
    echo "Quality check failed. Push aborted."
    exit 1
fi
```

## 配置文件

### Python质量配置
```ini
# .flake8
[flake8]
max-line-length = 100
exclude = .git,__pycache__,venv
ignore = E203,W503

# pyproject.toml
[tool.black]
line-length = 100
target-version = ['py311']

[tool.mypy]
python_version = "3.11"
strict = true
```

### JavaScript质量配置
```json
// .eslintrc.json
{
  "extends": [
    "plugin:vue/vue3-recommended",
    "eslint:recommended"
  ],
  "rules": {
    "vue/multi-word-component-names": "error",
    "no-console": "warn"
  }
}
```

## 学习资源
- [项目编码规范](../../.ai/rules.md)
- [测试指南](../../docs/testing/README.md)
- [安全最佳实践](../../docs/development/security.md)
