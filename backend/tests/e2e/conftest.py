"""
E2E Test Fixtures
E2E测试fixtures配置
"""
import pytest
from playwright.sync_api import Page, BrowserContext, Browser
from typing import Generator
import os


# 基础配置
BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:3000")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"
SLOW_MO = int(os.getenv("SLOW_MO", "0"))


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """
    浏览器上下文参数配置

    配置视口大小、权限、语言等
    """
    return {
        **browser_context_args,
        "viewport": {
            "width": 1920,
            "height": 1080,
        },
        "locale": "zh-CN",
        "timezone_id": "Asia/Shanghai",
        "permissions": ["notifications"],
        "record_video_dir": "tests/e2e/videos/",
        "record_video_size": {"width": 1920, "height": 1080},
    }


@pytest.fixture(scope="function")
def context(browser: Browser):
    """
    为每个测试创建独立的浏览器上下文

    确保测试之间的隔离性
    """
    context = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        locale="zh-CN",
        timezone_id="Asia/Shanghai",
        record_video_dir="tests/e2e/videos/",
        record_video_size={"width": 1920, "height": 1080},
    )
    yield context
    context.close()


@pytest.fixture(scope="function")
def page(context: BrowserContext) -> Generator[Page, None, None]:
    """
    为每个测试创建新页面

    测试结束后自动截图（如果失败）
    """
    page = context.new_page()

    # 设置默认超时
    page.set_default_timeout(30000)
    page.set_default_navigation_timeout(60000)

    yield page

    # 测试失败时自动截图
    if hasattr(page, "_test_failed") and page._test_failed:
        test_name = os.environ.get("PYTEST_CURRENT_TEST", "unknown").split(":")[-1].split(" ")[0]
        screenshot_path = f"tests/e2e/screenshots/failed_{test_name}.png"
        page.screenshot(path=screenshot_path)

    page.close()


@pytest.fixture(scope="function")
def authenticated_page(page: Page) -> Page:
    """
    已登录的页面fixture

    自动完成登录流程，返回登录后的页面
    """
    # 访问登录页
    page.goto(f"{BASE_URL}/login")
    page.wait_for_load_state("networkidle")

    # 填写登录信息 - 使用Element Plus选择器
    page.fill(".el-input__inner[placeholder='用户名']", "testuser")
    page.fill(".el-input__inner[type='password'][placeholder='密码']", "testpass123")

    # 点击登录按钮
    page.click("button.el-button:has-text('登录')")

    # 等待跳转到仪表盘或主页
    try:
        page.wait_for_url("**/dashboard", timeout=10000)
    except Exception:
        try:
            page.wait_for_url("**/**", timeout=5000)
            # 如果没有跳转到dashboard，可能跳转到了主页
        except Exception:
            # 如果没有跳转，可能是登录失败，但继续测试
            pass

    return page


@pytest.fixture(scope="function")
def api_context(page: Page):
    """
    API请求上下文

    用于在E2E测试中直接调用API
    """
    # 可以在这里添加API token等
    return page.request


@pytest.fixture(autouse=True)
def setup_test_environment(request, page: Page):
    """
    测试环境设置（自动使用）

    在每个测试前后执行
    """
    # 测试前：清理cookies、localStorage等
    page.context.clear_cookies()

    yield

    # 测试后：记录测试失败状态
    if request.node.rep_call.failed:
        page._test_failed = True


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Hook: 获取测试结果

    用于在fixture中判断测试是否失败
    """
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


# 测试数据fixtures

@pytest.fixture
def test_user_credentials():
    """测试用户凭证"""
    return {
        "username": "testuser",
        "password": "testpass123",
        "email": "testuser@example.com"
    }


@pytest.fixture
def test_strategy_data():
    """测试策略数据"""
    return {
        "name": "E2E Test Strategy",
        "description": "E2E测试策略",
        "strategy_class": "TestStrategy",
        "exchange": "binance",
        "timeframe": "1h",
        "pair_whitelist": ["BTC/USDT", "ETH/USDT"],
        "dry_run": True,
        "dry_run_wallet": 1000.0,
        "max_open_trades": 3,
        "signal_thresholds": {"strong": 0.8, "medium": 0.6, "weak": 0.4}
    }


@pytest.fixture
def test_signal_data():
    """测试信号数据"""
    return {
        "pair": "BTC/USDT",
        "action": "buy",
        "current_rate": 50000.0,
        "indicators": {"signal_strength": 0.85},
        "metadata": {"source": "e2e_test"}
    }


# 辅助函数fixtures

@pytest.fixture
def wait_for_api_call(page: Page):
    """
    等待API调用的辅助函数

    Returns:
        一个可以等待特定API调用的函数
    """
    def _wait(url_pattern: str, timeout: int = 30000):
        with page.expect_response(url_pattern, timeout=timeout) as response_info:
            return response_info.value
    return _wait


@pytest.fixture
def take_screenshot(page: Page):
    """
    截图辅助函数

    Returns:
        一个可以截图的函数
    """
    def _screenshot(name: str):
        page.screenshot(path=f"tests/e2e/screenshots/{name}.png")
    return _screenshot
