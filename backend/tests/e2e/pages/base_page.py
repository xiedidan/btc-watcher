"""
Base Page Object
页面对象基类 - 提供所有页面通用的方法
"""
from playwright.sync_api import Page, expect
from typing import Optional


class BasePage:
    """页面基类"""

    def __init__(self, page: Page, base_url: str = "http://localhost:3000"):
        self.page = page
        self.base_url = base_url

    def navigate(self, path: str = ""):
        """
        导航到指定路径

        Args:
            path: URL路径（如 "/login", "/dashboard"）
        """
        url = f"{self.base_url}{path}"
        self.page.goto(url, wait_until="networkidle")

    def wait_for_url(self, url_pattern: str, timeout: int = 30000):
        """
        等待URL变化

        Args:
            url_pattern: URL模式（支持glob pattern）
            timeout: 超时时间（毫秒）
        """
        self.page.wait_for_url(url_pattern, timeout=timeout)

    def wait_for_selector(self, selector: str, timeout: int = 30000):
        """
        等待选择器出现

        Args:
            selector: CSS选择器
            timeout: 超时时间（毫秒）
        """
        self.page.wait_for_selector(selector, timeout=timeout)

    def click(self, selector: str, timeout: int = 30000):
        """
        点击元素

        Args:
            selector: CSS选择器
            timeout: 超时时间（毫秒）
        """
        self.page.click(selector, timeout=timeout)

    def fill(self, selector: str, value: str, timeout: int = 30000):
        """
        填充输入框

        Args:
            selector: CSS选择器
            value: 填充值
            timeout: 超时时间（毫秒）
        """
        self.page.fill(selector, value, timeout=timeout)

    def select_option(self, selector: str, value: str, timeout: int = 30000):
        """
        选择下拉框选项

        Args:
            selector: CSS选择器
            value: 选项值
            timeout: 超时时间（毫秒）
        """
        self.page.select_option(selector, value, timeout=timeout)

    def get_text(self, selector: str, timeout: int = 30000) -> str:
        """
        获取元素文本

        Args:
            selector: CSS选择器
            timeout: 超时时间（毫秒）

        Returns:
            元素的文本内容
        """
        element = self.page.wait_for_selector(selector, timeout=timeout)
        return element.text_content() or ""

    def is_visible(self, selector: str, timeout: int = 5000) -> bool:
        """
        检查元素是否可见

        Args:
            selector: CSS选择器
            timeout: 超时时间（毫秒）

        Returns:
            True如果元素可见，否则False
        """
        try:
            self.page.wait_for_selector(selector, state="visible", timeout=timeout)
            return True
        except Exception:
            return False

    def take_screenshot(self, name: str):
        """
        截图

        Args:
            name: 截图文件名（不含扩展名）
        """
        self.page.screenshot(path=f"tests/e2e/screenshots/{name}.png")

    def wait_for_api_response(self, url_pattern: str, timeout: int = 30000):
        """
        等待API响应

        Args:
            url_pattern: API URL模式（如 "**/api/v1/auth/token"）
            timeout: 超时时间（毫秒）

        Returns:
            Response对象
        """
        with self.page.expect_response(url_pattern, timeout=timeout) as response_info:
            return response_info.value

    def get_current_url(self) -> str:
        """获取当前URL"""
        return self.page.url

    def reload(self):
        """重新加载页面"""
        self.page.reload(wait_until="networkidle")

    def go_back(self):
        """后退"""
        self.page.go_back(wait_until="networkidle")

    def go_forward(self):
        """前进"""
        self.page.go_forward(wait_until="networkidle")

    def wait(self, milliseconds: int):
        """
        等待指定时间

        Args:
            milliseconds: 等待时间（毫秒）
        """
        self.page.wait_for_timeout(milliseconds)

    def evaluate(self, script: str):
        """
        执行JavaScript

        Args:
            script: JavaScript代码

        Returns:
            脚本返回值
        """
        return self.page.evaluate(script)

    def get_locator(self, selector: str):
        """
        获取定位器

        Args:
            selector: CSS选择器

        Returns:
            Locator对象
        """
        return self.page.locator(selector)
