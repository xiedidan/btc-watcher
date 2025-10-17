# E2E测试使用指南
# End-to-End Testing Guide

## 概述

本项目使用 **Playwright** 进行端到端测试，采用 **Page Object Model (POM)** 设计模式，确保测试代码的可维护性和可重用性。

## 目录结构

```
tests/e2e/
├── __init__.py
├── conftest.py              # Pytest配置和fixtures
├── pages/                   # Page Object模型
│   ├── __init__.py
│   ├── base_page.py         # 页面基类
│   └── login_page.py        # 登录页面对象
├── test_auth_flow.py        # 认证流程测试
├── screenshots/             # 失败截图
├── videos/                  # 测试录像
└── reports/                 # 测试报告
```

## 快速开始

### 1. 安装依赖

```bash
# 安装Playwright
pip install pytest-playwright

# 安装浏览器
playwright install chromium

# 或安装所有浏览器
playwright install
```

### 2. 环境配置

设置环境变量（可选）：

```bash
# 前端URL
export E2E_BASE_URL="http://localhost:3000"

# 后端API URL
export API_BASE_URL="http://localhost:8000"

# 是否无头模式运行
export HEADLESS="true"

# 慢速模式（调试用，单位毫秒）
export SLOW_MO="0"
```

### 3. 运行测试

```bash
# 运行所有E2E测试
pytest tests/e2e/ -v

# 运行特定测试文件
pytest tests/e2e/test_auth_flow.py -v

# 运行特定测试
pytest tests/e2e/test_auth_flow.py::TestAuthenticationFlow::test_user_login_success -v

# 有头模式运行（显示浏览器）
pytest tests/e2e/ --headed

# 慢速模式（方便观察，每步延迟1秒）
pytest tests/e2e/ --headed --slowmo 1000

# 多浏览器测试
pytest tests/e2e/ --browser chromium --browser firefox

# 生成HTML报告
pytest tests/e2e/ --html=tests/e2e/reports/report.html --self-contained-html

# 保持浏览器打开（调试用）
PWDEBUG=1 pytest tests/e2e/test_auth_flow.py::test_user_login_success

# 并行运行测试
pytest tests/e2e/ -n auto
```

## Page Object Model

### 基本使用

#### 1. 创建页面对象

```python
from playwright.sync_api import Page
from .base_page import BasePage

class DashboardPage(BasePage):
    """仪表盘页面"""

    def __init__(self, page: Page):
        super().__init__(page)

        # 定义选择器
        self.title = "h1.page-title"
        self.metrics_card = ".metric-card"

    def goto(self):
        """访问仪表盘"""
        self.navigate("/dashboard")

    def get_metrics_count(self) -> int:
        """获取指标卡片数量"""
        return self.page.locator(self.metrics_card).count()
```

#### 2. 在测试中使用

```python
def test_dashboard_loads(page: Page):
    """测试仪表盘加载"""
    dashboard = DashboardPage(page)
    dashboard.goto()

    assert dashboard.get_metrics_count() > 0
```

## Fixtures使用

### 基础Fixtures

#### page
每个测试的新页面，自动清理

```python
def test_example(page: Page):
    page.goto("http://localhost:3000")
    # 测试代码
```

#### authenticated_page
已登录的页面

```python
def test_protected_page(authenticated_page: Page):
    # 已经登录，可以直接访问受保护页面
    authenticated_page.goto("http://localhost:3000/strategies")
```

### 数据Fixtures

#### test_user_credentials
测试用户凭证

```python
def test_login(page: Page, test_user_credentials):
    login_page = LoginPage(page)
    login_page.login(
        username=test_user_credentials["username"],
        password=test_user_credentials["password"]
    )
```

#### test_strategy_data
测试策略数据

```python
def test_create_strategy(page: Page, test_strategy_data):
    # 使用预定义的策略数据
    create_strategy(test_strategy_data)
```

### 辅助Fixtures

#### wait_for_api_call
等待API响应

```python
def test_api_interaction(page: Page, wait_for_api_call):
    response = wait_for_api_call("**/api/v1/strategies/")
    assert response.status == 200
```

#### take_screenshot
手动截图

```python
def test_example(page: Page, take_screenshot):
    page.goto("http://localhost:3000")
    take_screenshot("homepage")
```

## 编写测试

### 测试结构

```python
"""
E2E Test: Feature Description
功能描述的端到端测试
"""
import pytest
from playwright.sync_api import Page, expect
from pages.some_page import SomePage

class TestFeature:
    """功能测试类"""

    def test_scenario_1(self, page: Page):
        """测试场景1"""
        # Arrange - 准备
        some_page = SomePage(page)
        some_page.goto()

        # Act - 执行
        some_page.perform_action()

        # Assert - 验证
        assert some_page.is_action_successful()

    def test_scenario_2(self, authenticated_page: Page):
        """测试场景2（需要登录）"""
        page = authenticated_page
        # 测试代码
```

### 最佳实践

#### 1. 使用显式等待

```python
# ✅ 好
page.wait_for_selector(".loading").to_be_hidden()
page.click("button")

# ❌ 差
page.wait_for_timeout(5000)  # 硬编码等待
page.click("button")
```

#### 2. 使用有意义的选择器

```python
# ✅ 好 - 语义化选择器
page.click("button[aria-label='保存策略']")
page.click("button:has-text('提交')")

# ❌ 差 - 脆弱的选择器
page.click("#btn-123")  # ID可能变化
page.click("div > div > button")  # 结构依赖
```

#### 3. 使用expect进行断言

```python
# ✅ 好 - 自动等待
expect(page.locator("h1")).to_have_text("欢迎")

# ❌ 差 - 需要手动等待
assert page.locator("h1").text_content() == "欢迎"
```

#### 4. 避免硬编码数据

```python
# ✅ 好 - 使用fixtures
def test_login(page: Page, test_user_credentials):
    login_page.login(
        username=test_user_credentials["username"],
        password=test_user_credentials["password"]
    )

# ❌ 差 - 硬编码
def test_login(page: Page):
    login_page.login("admin", "password123")
```

## 调试技巧

### 1. 使用Playwright Inspector

```bash
# 启动调试模式
PWDEBUG=1 pytest tests/e2e/test_auth_flow.py::test_user_login_success
```

特性：
- 逐步执行
- 查看选择器
- 录制测试步骤
- 查看日志

### 2. 截图调试

```python
def test_example(page: Page):
    page.goto("http://localhost:3000")
    page.screenshot(path="debug.png")  # 手动截图

    # 测试失败时会自动截图到 screenshots/failed_*.png
```

### 3. 视频录制

测试运行时自动录制，失败时保存到 `videos/` 目录。

### 4. 控制台日志

```python
def test_example(page: Page):
    # 监听控制台消息
    page.on("console", lambda msg: print(f"Console: {msg.text}"))

    # 监听页面错误
    page.on("pageerror", lambda err: print(f"Error: {err}"))

    page.goto("http://localhost:3000")
```

### 5. 网络请求监控

```python
def test_example(page: Page):
    # 监听所有请求
    page.on("request", lambda req: print(f">> {req.method} {req.url}"))

    # 监听所有响应
    page.on("response", lambda res: print(f"<< {res.status} {res.url}"))

    page.goto("http://localhost:3000")
```

## 持续集成

### GitHub Actions示例

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v2

    - name: Setup Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install pytest-playwright
        playwright install chromium

    - name: Start backend
      run: |
        cd backend
        python -m uvicorn main:app &
        sleep 5

    - name: Start frontend
      run: |
        cd frontend
        npm install
        npm run build
        npm run start &
        sleep 10

    - name: Run E2E tests
      run: pytest tests/e2e/ -v --headed=false

    - name: Upload screenshots
      if: failure()
      uses: actions/upload-artifact@v2
      with:
        name: screenshots
        path: tests/e2e/screenshots/

    - name: Upload videos
      if: failure()
      uses: actions/upload-artifact@v2
      with:
        name: videos
        path: tests/e2e/videos/
```

## 常见问题

### Q: 测试运行很慢怎么办？

A:
1. 使用 `--headed=false` 无头模式
2. 使用 `pytest-xdist` 并行运行: `pytest -n auto`
3. 减少 `page.wait_for_timeout()` 的使用
4. 优化选择器，使用更快的定位策略

### Q: 测试不稳定（flaky）怎么办？

A:
1. 使用 `expect()` 替代 `assert`（自动重试）
2. 使用显式等待替代硬编码延迟
3. 等待网络空闲: `page.goto(url, wait_until="networkidle")`
4. 等待特定元素: `page.wait_for_selector()`

### Q: 如何测试移动端？

A:
```python
@pytest.fixture
def mobile_page(browser):
    iphone = playwright.devices["iPhone 12"]
    context = browser.new_context(**iphone)
    page = context.new_page()
    yield page
    context.close()

def test_mobile(mobile_page):
    mobile_page.goto("http://localhost:3000")
    # 移动端测试
```

### Q: 如何处理弹窗/对话框？

A:
```python
# 处理alert
page.on("dialog", lambda dialog: dialog.accept())

# 或手动处理
with page.expect_dialog() as dialog_info:
    page.click("button:has-text('删除')")
    dialog = dialog_info.value
    assert "确认删除" in dialog.message
    dialog.accept()
```

### Q: 如何测试文件上传？

A:
```python
# 方法1: 设置文件
page.set_input_files("input[type='file']", "path/to/file.jpg")

# 方法2: 使用 file chooser
with page.expect_file_chooser() as fc_info:
    page.click("button:has-text('上传')")
    file_chooser = fc_info.value
    file_chooser.set_files("path/to/file.jpg")
```

## 参考资源

- [Playwright官方文档](https://playwright.dev/python/)
- [Playwright Python API](https://playwright.dev/python/docs/api/class-playwright)
- [pytest-playwright插件](https://github.com/microsoft/playwright-pytest)
- [Page Object Model最佳实践](https://playwright.dev/python/docs/pom)

## 贡献指南

添加新的E2E测试时：

1. **创建页面对象**
   - 在 `pages/` 目录创建新的页面对象类
   - 继承 `BasePage`
   - 定义选择器和方法

2. **编写测试**
   - 在 `tests/e2e/` 创建新的测试文件
   - 使用描述性的测试类和方法名
   - 添加中英文文档字符串

3. **运行测试**
   - 确保所有测试通过
   - 检查截图和视频（如果有失败）

4. **提交代码**
   - 更新文档
   - 提交Pull Request

## 联系方式

如有问题，请提Issue或联系测试团队。

---

**最后更新:** 2025-10-14
**维护者:** BTC Watcher团队
