# E2E测试和性能测试规划
# End-to-End & Performance Testing Plan

## 目录
1. [E2E测试框架设计](#1-e2e测试框架设计)
2. [E2E测试场景](#2-e2e测试场景)
3. [性能测试框架设计](#3-性能测试框架设计)
4. [性能测试场景](#4-性能测试场景)
5. [实施计划](#5-实施计划)

---

## 1. E2E测试框架设计

### 1.1 技术选型

**推荐方案: Playwright**

**理由:**
- ✅ 支持Python原生API
- ✅ 跨浏览器支持 (Chrome, Firefox, Safari, Edge)
- ✅ 自动等待机制，减少flaky测试
- ✅ 强大的选择器引擎
- ✅ 内置截图和视频录制
- ✅ 并行测试支持
- ✅ 优秀的调试工具
- ✅ 由Microsoft维护，活跃更新

**替代方案:**
- Selenium: 更成熟但配置复杂，需要手动等待
- Cypress: JavaScript only，不适合Python项目

### 1.2 项目结构

```
backend/
├── tests/
│   ├── e2e/
│   │   ├── __init__.py
│   │   ├── conftest.py              # Playwright fixtures
│   │   ├── pages/                   # Page Object Model
│   │   │   ├── __init__.py
│   │   │   ├── base_page.py         # 基础页面类
│   │   │   ├── login_page.py        # 登录页
│   │   │   ├── dashboard_page.py    # 仪表盘页
│   │   │   ├── strategy_page.py     # 策略管理页
│   │   │   └── signal_page.py       # 信号监控页
│   │   ├── test_auth_flow.py        # 认证流程测试
│   │   ├── test_strategy_flow.py    # 策略管理流程测试
│   │   ├── test_signal_flow.py      # 信号监控流程测试
│   │   └── test_complete_workflow.py # 完整业务流程测试
│   └── performance/
│       ├── __init__.py
│       ├── locustfile.py            # Locust性能测试
│       ├── api_tests.py             # API性能测试
│       ├── database_tests.py        # 数据库性能测试
│       └── reports/                 # 性能测试报告
├── playwright.config.py             # Playwright配置
└── requirements-e2e.txt             # E2E测试依赖
```

### 1.3 Page Object Model设计

**base_page.py 示例:**
```python
from playwright.sync_api import Page, expect

class BasePage:
    """页面基类"""

    def __init__(self, page: Page):
        self.page = page
        self.base_url = "http://localhost:3000"

    def navigate(self, path: str):
        """导航到指定路径"""
        self.page.goto(f"{self.base_url}{path}")

    def wait_for_url(self, url: str, timeout: int = 30000):
        """等待URL变化"""
        self.page.wait_for_url(url, timeout=timeout)

    def take_screenshot(self, name: str):
        """截图"""
        self.page.screenshot(path=f"screenshots/{name}.png")

    def wait_for_api_response(self, url_pattern: str):
        """等待API响应"""
        with self.page.expect_response(url_pattern) as response_info:
            return response_info.value
```

**login_page.py 示例:**
```python
from playwright.sync_api import Page, expect
from .base_page import BasePage

class LoginPage(BasePage):
    """登录页面"""

    def __init__(self, page: Page):
        super().__init__(page)
        # 选择器
        self.username_input = "input[name='username']"
        self.password_input = "input[name='password']"
        self.login_button = "button[type='submit']"
        self.error_message = ".error-message"

    def goto(self):
        """访问登录页"""
        self.navigate("/login")

    def login(self, username: str, password: str):
        """执行登录"""
        self.page.fill(self.username_input, username)
        self.page.fill(self.password_input, password)
        self.page.click(self.login_button)

    def get_error_message(self) -> str:
        """获取错误消息"""
        return self.page.text_content(self.error_message)

    def is_login_successful(self) -> bool:
        """验证登录成功"""
        self.wait_for_url("/dashboard", timeout=5000)
        return "dashboard" in self.page.url
```

### 1.4 E2E测试配置

**playwright.config.py:**
```python
from playwright.sync_api import sync_playwright

# 浏览器配置
BROWSERS = ["chromium", "firefox"]  # 可选: webkit

# 视口大小
VIEWPORT_SIZES = [
    {"width": 1920, "height": 1080},  # 桌面
    {"width": 1366, "height": 768},   # 笔记本
    {"width": 375, "height": 667},    # 移动设备
]

# 超时配置
DEFAULT_TIMEOUT = 30000  # 30秒
NAVIGATION_TIMEOUT = 60000  # 60秒

# 截图和视频
SCREENSHOT_ON_FAILURE = True
VIDEO_ON_FAILURE = True

# 测试环境
TEST_BASE_URL = "http://localhost:3000"
API_BASE_URL = "http://localhost:8000"
```

---

## 2. E2E测试场景

### 2.1 认证流程测试

**test_auth_flow.py:**
```python
"""
E2E Test: Authentication Flow
测试用户注册、登录、登出完整流程
"""
import pytest
from playwright.sync_api import Page, expect
from pages.login_page import LoginPage
from pages.dashboard_page import DashboardPage

class TestAuthenticationFlow:
    """用户认证流程E2E测试"""

    def test_user_registration_flow(self, page: Page):
        """测试用户注册流程"""
        # 1. 访问注册页
        page.goto("http://localhost:3000/register")

        # 2. 填写注册表单
        page.fill("input[name='username']", "newuser")
        page.fill("input[name='email']", "newuser@example.com")
        page.fill("input[name='password']", "SecurePass123!")
        page.fill("input[name='confirmPassword']", "SecurePass123!")

        # 3. 提交注册
        page.click("button[type='submit']")

        # 4. 验证注册成功
        expect(page).to_have_url("/login", timeout=10000)
        expect(page.locator(".success-message")).to_contain_text("注册成功")

    def test_user_login_success(self, page: Page):
        """测试用户成功登录"""
        login_page = LoginPage(page)

        # 1. 访问登录页
        login_page.goto()

        # 2. 执行登录
        login_page.login("testuser", "testpass123")

        # 3. 验证跳转到仪表盘
        assert login_page.is_login_successful()

        # 4. 验证仪表盘元素
        expect(page.locator("h1")).to_contain_text("仪表盘")

    def test_user_login_invalid_credentials(self, page: Page):
        """测试错误凭证登录"""
        login_page = LoginPage(page)

        login_page.goto()
        login_page.login("wronguser", "wrongpass")

        # 验证错误消息
        error_msg = login_page.get_error_message()
        assert "用户名或密码错误" in error_msg

    def test_user_logout(self, page: Page, authenticated_page):
        """测试用户登出"""
        # authenticated_page是已登录的page fixture

        # 点击登出按钮
        page.click("button[aria-label='登出']")

        # 验证跳转到登录页
        expect(page).to_have_url("/login")

        # 验证无法访问受保护页面
        page.goto("http://localhost:3000/dashboard")
        expect(page).to_have_url("/login")
```

### 2.2 策略管理流程测试

**test_strategy_flow.py:**
```python
"""
E2E Test: Strategy Management Flow
测试策略的创建、启动、停止、删除完整流程
"""
import pytest
from playwright.sync_api import Page, expect

class TestStrategyManagementFlow:
    """策略管理流程E2E测试"""

    def test_create_strategy_complete_flow(self, page: Page, authenticated_page):
        """测试创建策略完整流程"""
        # 1. 访问策略页
        page.goto("http://localhost:3000/strategies")

        # 2. 点击创建策略按钮
        page.click("button:has-text('创建策略')")

        # 3. 填写策略表单
        page.fill("input[name='name']", "E2E Test Strategy")
        page.fill("textarea[name='description']", "E2E测试策略")
        page.select_option("select[name='exchange']", "binance")
        page.select_option("select[name='timeframe']", "1h")

        # 4. 添加交易对
        page.click("button:has-text('添加交易对')")
        page.fill("input[name='pair-0']", "BTC/USDT")
        page.click("button:has-text('添加交易对')")
        page.fill("input[name='pair-1']", "ETH/USDT")

        # 5. 设置参数
        page.fill("input[name='dryRunWallet']", "1000")
        page.fill("input[name='maxOpenTrades']", "3")

        # 6. 提交创建
        page.click("button[type='submit']")

        # 7. 等待API响应
        with page.expect_response("**/api/v1/strategies/**") as response_info:
            response = response_info.value
            assert response.status == 201

        # 8. 验证策略出现在列表中
        expect(page.locator("text=E2E Test Strategy")).to_be_visible()

    def test_start_stop_strategy_flow(self, page: Page, authenticated_page):
        """测试启动和停止策略流程"""
        page.goto("http://localhost:3000/strategies")

        # 1. 找到测试策略
        strategy_row = page.locator("tr:has-text('E2E Test Strategy')")

        # 2. 启动策略
        strategy_row.locator("button:has-text('启动')").click()

        # 3. 确认启动对话框
        page.click("button:has-text('确认启动')")

        # 4. 等待状态更新
        expect(strategy_row.locator(".status-badge")).to_have_text("运行中", timeout=10000)

        # 5. 等待3秒
        page.wait_for_timeout(3000)

        # 6. 停止策略
        strategy_row.locator("button:has-text('停止')").click()
        page.click("button:has-text('确认停止')")

        # 7. 验证状态变为已停止
        expect(strategy_row.locator(".status-badge")).to_have_text("已停止", timeout=10000)

    def test_delete_strategy_flow(self, page: Page, authenticated_page):
        """测试删除策略流程"""
        page.goto("http://localhost:3000/strategies")

        strategy_row = page.locator("tr:has-text('E2E Test Strategy')")

        # 1. 点击删除按钮
        strategy_row.locator("button:has-text('删除')").click()

        # 2. 确认删除
        page.fill("input[placeholder='输入策略名称确认']", "E2E Test Strategy")
        page.click("button:has-text('确认删除')")

        # 3. 验证策略消失
        expect(page.locator("text=E2E Test Strategy")).not_to_be_visible(timeout=5000)
```

### 2.3 信号监控流程测试

**test_signal_flow.py:**
```python
"""
E2E Test: Signal Monitoring Flow
测试信号监控、过滤、详情查看完整流程
"""
import pytest
from playwright.sync_api import Page, expect

class TestSignalMonitoringFlow:
    """信号监控流程E2E测试"""

    def test_view_signals_list(self, page: Page, authenticated_page):
        """测试查看信号列表"""
        # 1. 访问信号页
        page.goto("http://localhost:3000/signals")

        # 2. 验证信号列表加载
        expect(page.locator("table")).to_be_visible()

        # 3. 验证列标题
        expect(page.locator("th:has-text('交易对')")).to_be_visible()
        expect(page.locator("th:has-text('动作')")).to_be_visible()
        expect(page.locator("th:has-text('信号强度')")).to_be_visible()
        expect(page.locator("th:has-text('时间')")).to_be_visible()

    def test_filter_signals(self, page: Page, authenticated_page):
        """测试信号过滤"""
        page.goto("http://localhost:3000/signals")

        # 1. 按交易对过滤
        page.select_option("select[name='pair']", "BTC/USDT")
        page.click("button:has-text('应用过滤')")

        # 2. 验证过滤结果
        signals = page.locator("tbody tr")
        count = signals.count()
        for i in range(count):
            expect(signals.nth(i).locator("td").first).to_contain_text("BTC/USDT")

        # 3. 按动作过滤
        page.select_option("select[name='action']", "buy")
        page.click("button:has-text('应用过滤')")

        # 4. 验证buy信号
        for i in range(signals.count()):
            expect(signals.nth(i).locator(".action-badge")).to_have_class("action-buy")

    def test_view_signal_detail(self, page: Page, authenticated_page):
        """测试查看信号详情"""
        page.goto("http://localhost:3000/signals")

        # 1. 点击第一个信号
        page.locator("tbody tr").first.click()

        # 2. 验证详情模态框打开
        modal = page.locator(".signal-detail-modal")
        expect(modal).to_be_visible()

        # 3. 验证详情字段
        expect(modal.locator("text=信号强度")).to_be_visible()
        expect(modal.locator("text=当前价格")).to_be_visible()
        expect(modal.locator("text=指标数据")).to_be_visible()

        # 4. 关闭模态框
        modal.locator("button[aria-label='关闭']").click()
        expect(modal).not_to_be_visible()

    def test_real_time_signal_update(self, page: Page, authenticated_page):
        """测试信号实时更新"""
        page.goto("http://localhost:3000/signals")

        # 1. 记录初始信号数量
        initial_count = page.locator("tbody tr").count()

        # 2. 等待新信号（假设有定时刷新或WebSocket）
        page.wait_for_timeout(10000)  # 等待10秒

        # 3. 验证信号数量变化或内容更新
        # 注意：这需要后端有测试数据生成或模拟信号推送
        final_count = page.locator("tbody tr").count()

        # 可能有新信号，或者至少页面没有崩溃
        assert final_count >= initial_count
```

### 2.4 完整业务流程测试

**test_complete_workflow.py:**
```python
"""
E2E Test: Complete Business Workflow
测试从登录到策略管理到信号监控的完整业务流程
"""
import pytest
from playwright.sync_api import Page, expect

class TestCompleteBusinessWorkflow:
    """完整业务流程E2E测试"""

    def test_end_to_end_trading_workflow(self, page: Page):
        """测试端到端交易工作流"""

        # ===== 第1步: 用户登录 =====
        page.goto("http://localhost:3000/login")
        page.fill("input[name='username']", "testuser")
        page.fill("input[name='password']", "testpass123")
        page.click("button[type='submit']")
        expect(page).to_have_url("**/dashboard")

        # ===== 第2步: 查看仪表盘 =====
        expect(page.locator("h1")).to_contain_text("仪表盘")

        # 验证关键指标卡片
        expect(page.locator(".metric-card:has-text('运行策略')")).to_be_visible()
        expect(page.locator(".metric-card:has-text('今日信号')")).to_be_visible()

        # ===== 第3步: 创建新策略 =====
        page.click("a[href='/strategies']")
        page.click("button:has-text('创建策略')")

        # 填写策略表单
        page.fill("input[name='name']", "BTC Auto Trader")
        page.select_option("select[name='exchange']", "binance")
        page.select_option("select[name='timeframe']", "5m")
        page.fill("input[name='pair-0']", "BTC/USDT")
        page.fill("input[name='dryRunWallet']", "10000")

        page.click("button[type='submit']")
        expect(page.locator("text=BTC Auto Trader")).to_be_visible(timeout=10000)

        # ===== 第4步: 启动策略 =====
        strategy_row = page.locator("tr:has-text('BTC Auto Trader')")
        strategy_row.locator("button:has-text('启动')").click()
        page.click("button:has-text('确认启动')")

        # 等待策略启动
        expect(strategy_row.locator(".status-badge")).to_have_text("运行中", timeout=15000)

        # ===== 第5步: 查看信号 =====
        page.click("a[href='/signals']")
        expect(page.locator("h1")).to_contain_text("信号")

        # 过滤该策略的信号
        page.select_option("select[name='strategy']", "BTC Auto Trader")
        page.click("button:has-text('应用过滤')")

        # ===== 第6步: 查看信号详情 =====
        # 等待信号出现（可能需要时间）
        page.wait_for_timeout(5000)

        signals = page.locator("tbody tr")
        if signals.count() > 0:
            signals.first.click()
            expect(page.locator(".signal-detail-modal")).to_be_visible()
            page.locator("button[aria-label='关闭']").click()

        # ===== 第7步: 停止策略 =====
        page.click("a[href='/strategies']")
        strategy_row = page.locator("tr:has-text('BTC Auto Trader')")
        strategy_row.locator("button:has-text('停止')").click()
        page.click("button:has-text('确认停止')")

        expect(strategy_row.locator(".status-badge")).to_have_text("已停止", timeout=10000)

        # ===== 第8步: 登出 =====
        page.click("button[aria-label='用户菜单']")
        page.click("button:has-text('登出')")
        expect(page).to_have_url("**/login")
```

---

## 3. 性能测试框架设计

### 3.1 技术选型

**推荐方案: Locust**

**理由:**
- ✅ Python原生支持
- ✅ 分布式负载测试
- ✅ Web UI实时监控
- ✅ 灵活的用户行为定义
- ✅ 丰富的统计报告
- ✅ 支持自定义指标
- ✅ 易于扩展

**替代方案:**
- JMeter: Java based, GUI heavy
- k6: JavaScript, 更适合CI/CD
- Artillery: JavaScript, 配置为主

### 3.2 性能测试架构

```
┌─────────────────┐
│  Locust Master  │  ← Web UI (http://localhost:8089)
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼──┐  ┌──▼───┐
│Worker│  │Worker│  ← 多个Worker并发测试
└──┬───┘  └──┬───┘
   │         │
   └────┬────┘
        │
   ┌────▼────┐
   │ Backend │  ← BTC Watcher Backend (FastAPI)
   │  API    │
   └────┬────┘
        │
   ┌────▼────┐
   │Database │  ← PostgreSQL / SQLite
   └─────────┘
```

### 3.3 性能指标

**关键指标:**
1. **响应时间 (Response Time)**
   - 平均响应时间 (Average)
   - 中位数 (Median / P50)
   - 95分位数 (P95)
   - 99分位数 (P99)
   - 最大响应时间 (Max)

2. **吞吐量 (Throughput)**
   - 请求/秒 (RPS)
   - 并发用户数 (Concurrent Users)

3. **错误率 (Error Rate)**
   - 失败请求百分比
   - HTTP错误码分布

4. **资源使用 (Resource Usage)**
   - CPU使用率
   - 内存使用率
   - 数据库连接数

**性能目标 (示例):**
```
API端点性能目标:
├── GET /api/v1/strategies/      : < 100ms (P95)
├── GET /api/v1/signals/         : < 150ms (P95)
├── POST /api/v1/auth/token      : < 200ms (P95)
├── POST /api/v1/strategies/     : < 300ms (P95)
└── POST /api/v1/signals/webhook/: < 100ms (P95)

并发能力目标:
├── 100并发用户: 95%成功率
├── 500并发用户: 90%成功率
└── 1000并发用户: 80%成功率
```

---

## 4. 性能测试场景

### 4.1 基础API性能测试

**locustfile.py:**
```python
"""
Performance Test: API Load Testing
API负载测试 - 测试各API端点在不同负载下的性能
"""
from locust import HttpUser, task, between, events
import json
import random
from datetime import datetime

class BTCWatcherUser(HttpUser):
    """BTC Watcher用户行为模拟"""

    wait_time = between(1, 3)  # 请求间隔1-3秒

    def on_start(self):
        """用户开始时执行 - 登录获取token"""
        response = self.client.post("/api/v1/auth/token", data={
            "username": "testuser",
            "password": "testpass123"
        })

        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = None
            self.headers = {}

    @task(5)  # 权重5 - 最常用的操作
    def list_strategies(self):
        """查询策略列表"""
        with self.client.get(
            "/api/v1/strategies/",
            headers=self.headers,
            catch_response=True,
            name="GET /strategies/"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "strategies" in data:
                    response.success()
                else:
                    response.failure("Missing strategies in response")
            else:
                response.failure(f"Got {response.status_code}")

    @task(10)  # 权重10 - 非常常用
    def list_signals(self):
        """查询信号列表"""
        # 随机过滤条件
        params = {}
        if random.random() < 0.3:
            params["pair"] = random.choice(["BTC/USDT", "ETH/USDT"])
        if random.random() < 0.2:
            params["action"] = random.choice(["buy", "sell", "hold"])

        with self.client.get(
            "/api/v1/signals/",
            params=params,
            headers=self.headers,
            catch_response=True,
            name="GET /signals/"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got {response.status_code}")

    @task(3)
    def get_signal_statistics(self):
        """获取信号统计"""
        hours = random.choice([24, 48, 168])
        with self.client.get(
            f"/api/v1/signals/statistics/summary?hours={hours}",
            headers=self.headers,
            catch_response=True,
            name="GET /signals/statistics/summary"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got {response.status_code}")

    @task(2)
    def webhook_signal(self):
        """模拟接收Webhook信号"""
        signal_data = {
            "pair": random.choice(["BTC/USDT", "ETH/USDT", "BNB/USDT"]),
            "action": random.choice(["buy", "sell", "hold"]),
            "current_rate": random.uniform(30000, 70000),
            "indicators": {
                "signal_strength": random.uniform(0.3, 1.0),
                "rsi": random.uniform(20, 80),
                "macd": random.uniform(-100, 100)
            }
        }

        # 假设策略ID=1存在
        with self.client.post(
            "/api/v1/signals/webhook/1",
            json=signal_data,
            headers=self.headers,
            catch_response=True,
            name="POST /signals/webhook/{id}"
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            elif response.status_code == 404:
                response.success()  # 策略不存在也算预期行为
            else:
                response.failure(f"Got {response.status_code}")

    @task(1)
    def create_strategy(self):
        """创建策略（低频操作）"""
        strategy_data = {
            "name": f"LoadTest Strategy {random.randint(1000, 9999)}",
            "strategy_class": "TestStrategy",
            "exchange": "binance",
            "timeframe": random.choice(["1m", "5m", "15m", "1h"]),
            "pair_whitelist": ["BTC/USDT"],
            "signal_thresholds": {"strong": 0.8, "medium": 0.6, "weak": 0.4}
        }

        with self.client.post(
            "/api/v1/strategies/",
            json=strategy_data,
            headers=self.headers,
            catch_response=True,
            name="POST /strategies/"
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure(f"Got {response.status_code}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """测试开始时执行"""
    print("Performance test started!")
    print(f"Target host: {environment.host}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """测试结束时执行"""
    print("Performance test finished!")
    print(f"Total requests: {environment.stats.total.num_requests}")
    print(f"Total failures: {environment.stats.total.num_failures}")
```

### 4.2 数据库性能测试

**database_tests.py:**
```python
"""
Performance Test: Database Performance
数据库性能测试 - 测试数据库在不同数据量下的性能
"""
import asyncio
import time
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db, engine
from models.signal import Signal
from models.strategy import Strategy

async def test_signal_query_performance(
    db: AsyncSession,
    record_count: int = 10000
):
    """测试信号查询性能"""

    print(f"\n=== Testing signal query with {record_count} records ===")

    # 1. 简单查询
    start = time.time()
    result = await db.execute(select(Signal).limit(100))
    signals = result.scalars().all()
    elapsed = time.time() - start
    print(f"Simple query (limit 100): {elapsed:.3f}s")

    # 2. 带过滤的查询
    start = time.time()
    result = await db.execute(
        select(Signal)
        .where(Signal.pair == "BTC/USDT")
        .where(Signal.action == "buy")
        .limit(100)
    )
    signals = result.scalars().all()
    elapsed = time.time() - start
    print(f"Filtered query: {elapsed:.3f}s")

    # 3. 聚合查询
    start = time.time()
    result = await db.execute(
        select(
            Signal.action,
            func.count(Signal.id),
            func.avg(Signal.signal_strength)
        )
        .group_by(Signal.action)
    )
    stats = result.all()
    elapsed = time.time() - start
    print(f"Aggregation query: {elapsed:.3f}s")

    # 4. Join查询
    start = time.time()
    result = await db.execute(
        select(Signal, Strategy)
        .join(Strategy, Signal.strategy_id == Strategy.id)
        .limit(100)
    )
    data = result.all()
    elapsed = time.time() - start
    print(f"Join query: {elapsed:.3f}s")


async def test_concurrent_writes(db: AsyncSession, concurrent_count: int = 100):
    """测试并发写入性能"""

    print(f"\n=== Testing {concurrent_count} concurrent writes ===")

    start = time.time()

    tasks = []
    for i in range(concurrent_count):
        signal = Signal(
            strategy_id=1,
            pair="BTC/USDT",
            action="buy",
            signal_strength=0.75,
            strength_level="medium",
            current_rate=50000.0
        )
        db.add(signal)

    await db.commit()

    elapsed = time.time() - start
    print(f"Wrote {concurrent_count} records in {elapsed:.3f}s")
    print(f"Throughput: {concurrent_count / elapsed:.1f} records/sec")


async def run_database_performance_tests():
    """运行数据库性能测试套件"""
    async with AsyncSession(engine) as db:
        # 测试不同数据规模
        for count in [1000, 10000, 50000]:
            await test_signal_query_performance(db, count)

        # 测试并发写入
        await test_concurrent_writes(db, 100)
        await test_concurrent_writes(db, 500)


if __name__ == "__main__":
    asyncio.run(run_database_performance_tests())
```

### 4.3 压力测试场景

**stress_test.py:**
```python
"""
Performance Test: Stress Testing
压力测试 - 测试系统在极限负载下的表现
"""
from locust import HttpUser, task, between, LoadTestShape

class StressTestUser(HttpUser):
    """压力测试用户"""

    wait_time = between(0.5, 1)  # 更短的等待时间

    def on_start(self):
        """登录"""
        response = self.client.post("/api/v1/auth/token", data={
            "username": "testuser",
            "password": "testpass123"
        })
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}

    @task
    def heavy_query(self):
        """重负载查询"""
        self.client.get("/api/v1/signals/?hours=168", headers=self.headers)
        self.client.get("/api/v1/strategies/", headers=self.headers)
        self.client.get("/api/v1/signals/statistics/summary", headers=self.headers)


class StressTestShape(LoadTestShape):
    """
    自定义负载曲线
    阶段1 (0-60s): 逐渐增加到100用户
    阶段2 (60-120s): 保持100用户
    阶段3 (120-180s): 快速增加到500用户
    阶段4 (180-240s): 保持500用户
    阶段5 (240-300s): 快速增加到1000用户
    阶段6 (300-360s): 保持1000用户
    阶段7 (360-420s): 逐渐降低到0
    """

    stages = [
        {"duration": 60, "users": 100, "spawn_rate": 5},
        {"duration": 120, "users": 100, "spawn_rate": 0},
        {"duration": 180, "users": 500, "spawn_rate": 20},
        {"duration": 240, "users": 500, "spawn_rate": 0},
        {"duration": 300, "users": 1000, "spawn_rate": 25},
        {"duration": 360, "users": 1000, "spawn_rate": 0},
        {"duration": 420, "users": 0, "spawn_rate": 10},
    ]

    def tick(self):
        run_time = self.get_run_time()

        for stage in self.stages:
            if run_time < stage["duration"]:
                return (stage["users"], stage["spawn_rate"])

        return None
```

---

## 5. 实施计划

### 5.1 第一阶段: E2E测试框架搭建 (2-3天)

**Day 1: 环境准备**
- [ ] 安装Playwright: `pip install pytest-playwright`
- [ ] 初始化Playwright: `playwright install`
- [ ] 创建测试目录结构
- [ ] 创建基础Page Object类

**Day 2: 核心页面对象**
- [ ] 实现LoginPage
- [ ] 实现DashboardPage
- [ ] 实现StrategyPage
- [ ] 实现SignalPage
- [ ] 创建fixtures (conftest.py)

**Day 3: 基础测试用例**
- [ ] 实现认证流程测试
- [ ] 实现策略管理基础测试
- [ ] 实现信号监控基础测试
- [ ] 运行测试验证

### 5.2 第二阶段: E2E测试完善 (2-3天)

**Day 4-5: 高级测试场景**
- [ ] 完整业务流程测试
- [ ] 错误处理测试
- [ ] 边界条件测试
- [ ] 多浏览器测试

**Day 6: 截图和报告**
- [ ] 配置失败截图
- [ ] 配置视频录制
- [ ] 生成测试报告
- [ ] 优化测试性能

### 5.3 第三阶段: 性能测试框架 (2-3天)

**Day 7: Locust环境**
- [ ] 安装Locust: `pip install locust`
- [ ] 创建性能测试目录
- [ ] 实现基础locustfile
- [ ] 配置测试数据

**Day 8: API性能测试**
- [ ] 实现各API端点测试
- [ ] 实现用户行为模拟
- [ ] 配置性能指标收集
- [ ] 运行基准测试

**Day 9: 数据库性能测试**
- [ ] 实现查询性能测试
- [ ] 实现写入性能测试
- [ ] 实现并发测试
- [ ] 建立性能基准

### 5.4 第四阶段: 压力和稳定性测试 (2天)

**Day 10: 压力测试**
- [ ] 实现压力测试场景
- [ ] 实现自定义负载曲线
- [ ] 运行极限负载测试
- [ ] 分析瓶颈

**Day 11: 报告和优化**
- [ ] 生成性能测试报告
- [ ] 分析性能数据
- [ ] 提出优化建议
- [ ] 建立性能基准数据库

### 5.5 预期成果

**E2E测试:**
- ✅ 覆盖核心业务流程的30+个E2E测试
- ✅ 支持Chrome和Firefox
- ✅ 自动截图和视频录制
- ✅ 完整的测试报告

**性能测试:**
- ✅ 各API端点性能基准
- ✅ 支持100-1000并发用户
- ✅ 数据库性能基准
- ✅ 实时性能监控面板
- ✅ 性能测试报告和优化建议

---

## 6. 测试工具和命令

### E2E测试命令

```bash
# 安装Playwright
pip install pytest-playwright
playwright install

# 运行所有E2E测试
pytest tests/e2e/ -v

# 运行特定测试
pytest tests/e2e/test_auth_flow.py -v

# 运行并生成报告
pytest tests/e2e/ --html=report.html

# 调试模式（有UI）
pytest tests/e2e/ --headed --slowmo 1000

# 多浏览器测试
pytest tests/e2e/ --browser chromium --browser firefox

# 录制视频
pytest tests/e2e/ --video on
```

### 性能测试命令

```bash
# 安装Locust
pip install locust

# 启动Locust (Web UI)
locust -f tests/performance/locustfile.py --host=http://localhost:8000

# 无UI模式（命令行）
locust -f tests/performance/locustfile.py \
       --host=http://localhost:8000 \
       --users 100 \
       --spawn-rate 10 \
       --run-time 5m \
       --headless

# 分布式测试（master）
locust -f tests/performance/locustfile.py --master

# 分布式测试（worker）
locust -f tests/performance/locustfile.py --worker --master-host=localhost

# 生成HTML报告
locust -f tests/performance/locustfile.py \
       --headless --users 100 --run-time 5m \
       --html=performance_report.html
```

---

**文档创建时间:** 2025-10-14 02:15

**状态:** 待实施

**优先级:** 高
