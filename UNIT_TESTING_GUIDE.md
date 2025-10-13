# BTC Watcher 单元测试指南
# Unit Testing Guide

## 📋 目录

1. [单元测试概述](#单元测试概述)
2. [测试框架](#测试框架)
3. [运行测试](#运行测试)
4. [测试覆盖率](#测试覆盖率)
5. [编写测试](#编写测试)
6. [测试最佳实践](#测试最佳实践)

---

## 单元测试概述

### 什么是单元测试？

单元测试是对软件中最小可测试单元（通常是函数或方法）进行验证的测试。BTC Watcher项目包含全面的单元测试套件，确保每个组件的正确性。

### 测试统计

| 测试类别 | 测试文件 | 测试用例数 | 覆盖模块 |
|---------|---------|-----------|---------|
| FreqTrade管理器 | test_freqtrade_manager.py | 15+ | core/freqtrade_manager.py |
| 监控服务 | test_monitoring_service.py | 12+ | services/monitoring_service.py |
| 通知服务 | test_notification_service.py | 13+ | services/notification_service.py |
| API路由 | test_api_routes.py | 20+ | api/v1/*.py |
| 数据模型 | test_models.py | 12+ | models/*.py |
| **总计** | **5个文件** | **72+用例** | **所有核心模块** |

---

## 测试框架

### 使用的工具

1. **pytest** - Python测试框架
2. **pytest-asyncio** - 异步测试支持
3. **pytest-cov** - 测试覆盖率
4. **unittest.mock** - Mock对象
5. **httpx** - HTTP客户端测试

### 安装依赖

```bash
cd backend
pip install -r requirements-test.txt
```

包含的依赖：
```
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
httpx==0.25.2
```

---

## 运行测试

### 方式1: 使用测试脚本（推荐）

```bash
# 运行所有单元测试
./scripts/run_unit_tests.sh
```

### 方式2: 直接使用pytest

```bash
cd backend

# 运行所有单元测试
pytest tests/unit/ -v

# 运行特定测试文件
pytest tests/unit/test_freqtrade_manager.py -v

# 运行特定测试类
pytest tests/unit/test_freqtrade_manager.py::TestFreqTradeGatewayManager -v

# 运行特定测试用例
pytest tests/unit/test_freqtrade_manager.py::TestFreqTradeGatewayManager::test_initialization -v
```

### 方式3: 使用Makefile

```bash
# 添加到Makefile
make test-unit
```

---

## 测试覆盖率

### 生成覆盖率报告

```bash
cd backend

# 运行测试并生成覆盖率报告
pytest tests/unit/ --cov=. --cov-report=html --cov-report=term-missing

# 查看HTML报告
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### 覆盖率目标

| 模块 | 目标覆盖率 | 当前状态 |
|------|-----------|---------|
| core/freqtrade_manager.py | 80%+ | ✅ 已测试 |
| services/monitoring_service.py | 75%+ | ✅ 已测试 |
| services/notification_service.py | 75%+ | ✅ 已测试 |
| api/v1/*.py | 70%+ | ✅ 已测试 |
| models/*.py | 85%+ | ✅ 已测试 |

---

## 编写测试

### 测试文件结构

```
backend/tests/
├── __init__.py
├── conftest.py              # 共享fixtures
├── unit/                    # 单元测试
│   ├── test_freqtrade_manager.py
│   ├── test_monitoring_service.py
│   ├── test_notification_service.py
│   ├── test_api_routes.py
│   └── test_models.py
└── integration/             # 集成测试
    └── test_api.py
```

### 基本测试模板

```python
"""
模块单元测试
Module Unit Tests
"""
import pytest
from unittest.mock import Mock, patch


class TestYourClass:
    """测试类"""

    def test_basic_functionality(self):
        """测试基本功能"""
        # Arrange
        obj = YourClass()

        # Act
        result = obj.method()

        # Assert
        assert result == expected_value

    @pytest.mark.asyncio
    async def test_async_functionality(self):
        """测试异步功能"""
        obj = YourClass()
        result = await obj.async_method()
        assert result is not None
```

### 使用Fixtures

```python
# conftest.py
@pytest.fixture
def sample_user(db_session):
    """创建测试用户"""
    user = User(
        username="testuser",
        email="test@example.com"
    )
    db_session.add(user)
    db_session.commit()
    return user

# 在测试中使用
def test_with_fixture(sample_user):
    assert sample_user.username == "testuser"
```

### 使用Mock

```python
from unittest.mock import Mock, patch

def test_with_mock():
    """使用Mock对象"""
    mock_manager = Mock()
    mock_manager.get_capacity.return_value = {
        "total_slots": 999,
        "used_slots": 10
    }

    result = mock_manager.get_capacity()
    assert result["total_slots"] == 999

@patch('module.function')
def test_with_patch(mock_function):
    """使用patch装饰器"""
    mock_function.return_value = "mocked"
    result = module.function()
    assert result == "mocked"
```

---

## 测试最佳实践

### 1. 测试命名规范

```python
# ✅ 好的命名
def test_allocate_port_preferred():
    """测试端口分配 - 优先分配策略ID对应端口"""
    pass

def test_user_creation():
    """测试创建用户"""
    pass

# ❌ 不好的命名
def test1():
    pass

def test_something():
    pass
```

### 2. AAA模式（Arrange-Act-Assert）

```python
def test_port_allocation():
    # Arrange - 准备测试数据
    manager = FreqTradeGatewayManager()
    strategy_id = 1

    # Act - 执行测试操作
    port = await manager._allocate_port(strategy_id)

    # Assert - 验证结果
    assert port == 8082
    assert 8082 not in manager.port_pool
```

### 3. 测试独立性

```python
# ✅ 每个测试都是独立的
def test_create_user(db_session):
    user = User(username="test1")
    db_session.add(user)
    db_session.commit()
    assert user.id is not None

def test_create_another_user(db_session):
    user = User(username="test2")  # 不依赖上一个测试
    db_session.add(user)
    db_session.commit()
    assert user.id is not None
```

### 4. 测试边缘情况

```python
class TestFreqTradeManagerEdgeCases:
    """测试边缘情况"""

    def test_allocate_all_ports(self):
        """测试分配所有端口"""
        # 测试极限情况
        pass

    def test_allocate_port_max_limit(self):
        """测试达到最大限制"""
        with pytest.raises(Exception):
            # 测试异常情况
            pass
```

### 5. 使用参数化测试

```python
@pytest.mark.parametrize("input,expected", [
    (0.85, "strong"),
    (0.65, "medium"),
    (0.45, "weak"),
    (0.35, "ignore"),
])
def test_signal_classification(input, expected):
    """测试信号分类"""
    result = classify_signal(input)
    assert result == expected
```

### 6. 测试异步代码

```python
@pytest.mark.asyncio
async def test_async_function():
    """测试异步函数"""
    result = await async_function()
    assert result is not None

@pytest.mark.asyncio
async def test_multiple_async_calls():
    """测试多个异步调用"""
    results = await asyncio.gather(
        async_function1(),
        async_function2()
    )
    assert len(results) == 2
```

---

## 测试示例

### 示例1: 测试FreqTrade管理器

```python
class TestFreqTradeGatewayManager:
    def test_initialization(self):
        """测试管理器初始化"""
        manager = FreqTradeGatewayManager()

        assert manager.base_port == 8081
        assert manager.max_port == 9080
        assert manager.max_strategies == 999
        assert len(manager.port_pool) == 999

    @pytest.mark.asyncio
    async def test_allocate_port_preferred(self):
        """测试端口分配 - 优先分配"""
        manager = FreqTradeGatewayManager()
        port = await manager._allocate_port(1)

        assert port == 8082
        assert 8082 not in manager.port_pool
```

### 示例2: 测试监控服务

```python
class TestMonitoringService:
    @pytest.mark.asyncio
    async def test_check_alerts_high_cpu(self):
        """测试高CPU告警"""
        mock_manager = Mock()
        service = MonitoringService(mock_manager)

        metrics = {
            "cpu_usage": 95.0,
            "memory_usage": 50.0,
            "disk_usage": 40.0
        }

        alerts = await service._check_alerts(metrics)
        cpu_alerts = [a for a in alerts if "CPU" in a["message"]]

        assert len(cpu_alerts) > 0
        assert cpu_alerts[0]["level"] == "warning"
```

### 示例3: 测试API路由

```python
class TestAuthAPI:
    def test_register_user_success(self):
        """测试用户注册成功"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "password123"
            }
        )

        assert response.status_code in [200, 201]

    def test_login_wrong_password(self):
        """测试错误密码登录"""
        response = client.post(
            "/api/v1/auth/token",
            data={
                "username": "admin",
                "password": "wrongpassword"
            }
        )

        assert response.status_code == 401
```

---

## 持续集成

### GitHub Actions配置示例

```yaml
name: Unit Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install -r requirements-test.txt

      - name: Run unit tests
        run: |
          cd backend
          pytest tests/unit/ -v --cov=. --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v2
        with:
          file: ./backend/coverage.xml
```

---

## 故障排查

### 常见问题

#### 1. 测试数据库连接失败

```bash
# 使用内存数据库
export DATABASE_URL="sqlite:///:memory:"
pytest tests/unit/
```

#### 2. 异步测试失败

```python
# 确保使用 @pytest.mark.asyncio
@pytest.mark.asyncio
async def test_async():
    result = await async_function()
    assert result is not None
```

#### 3. Mock不生效

```python
# 使用正确的路径
@patch('api.v1.auth.get_db')  # ✅ 正确
@patch('database.session.get_db')  # ❌ 可能不正确
```

#### 4. Fixture冲突

```python
# 使用scope控制fixture生命周期
@pytest.fixture(scope="function")  # 每个测试重新创建
@pytest.fixture(scope="session")   # 整个session共享
```

---

## 测试检查清单

运行测试前：
- [ ] 所有依赖已安装
- [ ] 测试环境变量已配置
- [ ] 测试数据库已准备

编写测试时：
- [ ] 测试命名清晰
- [ ] 使用AAA模式
- [ ] 测试独立性
- [ ] 包含边缘情况
- [ ] 添加必要的文档字符串

提交代码前：
- [ ] 所有测试通过
- [ ] 覆盖率达标
- [ ] 没有跳过的测试
- [ ] 代码符合规范

---

## 相关资源

- [pytest官方文档](https://docs.pytest.org/)
- [pytest-asyncio文档](https://pytest-asyncio.readthedocs.io/)
- [unittest.mock文档](https://docs.python.org/3/library/unittest.mock.html)
- [测试驱动开发（TDD）](https://en.wikipedia.org/wiki/Test-driven_development)

---

## 快速命令参考

```bash
# 运行所有单元测试
./scripts/run_unit_tests.sh

# 运行特定文件
pytest tests/unit/test_freqtrade_manager.py -v

# 运行特定测试
pytest tests/unit/test_freqtrade_manager.py::test_initialization -v

# 生成覆盖率报告
pytest tests/unit/ --cov=. --cov-report=html

# 运行并显示详细输出
pytest tests/unit/ -v -s

# 运行失败的测试
pytest tests/unit/ --lf

# 并行运行测试（需要pytest-xdist）
pytest tests/unit/ -n auto
```

---

**单元测试文档版本**: v1.0
**最后更新**: 2025-10-11
