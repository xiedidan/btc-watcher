"""
Dashboard Page Object
仪表盘页面对象

This module contains the page object for the BTC Watcher dashboard page.
"""
from playwright.sync_api import Page, expect
from .base_page import BasePage


class DashboardPage(BasePage):
    """
    Dashboard Page Object
    仪表盘页面对象

    封装仪表盘页面的元素和操作。
    """

    def __init__(self, page: Page, base_url: str = "http://localhost:3000"):
        """
        Initialize Dashboard Page
        初始化仪表盘页面

        Args:
            page: Playwright page instance
            base_url: Base URL of the application
        """
        super().__init__(page, base_url)

        # Page selectors / 页面选择器
        self.page_title = "h1, h2, .page-title"
        self.dashboard_container = ".dashboard-container, [data-testid='dashboard']"

        # Metric cards / 指标卡片
        self.metric_card = ".metric-card, .stat-card, [data-testid='metric-card']"
        self.total_strategies_metric = "[data-testid='total-strategies'], .metric-strategies"
        self.active_strategies_metric = "[data-testid='active-strategies'], .metric-active-strategies"
        self.total_signals_metric = "[data-testid='total-signals'], .metric-signals"
        self.today_signals_metric = "[data-testid='today-signals'], .metric-today-signals"

        # Navigation links / 导航链接
        self.strategies_link = "a[href*='strategies'], button:has-text('策略'), button:has-text('Strategies')"
        self.signals_link = "a[href*='signals'], button:has-text('信号'), button:has-text('Signals')"
        self.settings_link = "a[href*='settings'], button:has-text('设置'), button:has-text('Settings')"

        # Recent signals table / 最近信号表格
        self.signals_table = "table, .signals-table, [data-testid='signals-table']"
        self.signal_row = "tr.signal-row, tbody tr, [data-testid='signal-row']"

        # Actions / 操作按钮
        self.create_strategy_button = "button:has-text('创建策略'), button:has-text('Create Strategy'), [data-testid='create-strategy']"
        self.refresh_button = "button:has-text('刷新'), button:has-text('Refresh'), [data-testid='refresh']"

        # User menu / 用户菜单
        self.user_menu = "[aria-label='用户菜单'], [aria-label='User menu'], .user-menu"
        self.logout_button = "button:has-text('登出'), button:has-text('Logout'), a:has-text('登出'), a:has-text('Logout')"

    def goto(self):
        """
        Navigate to dashboard page
        导航到仪表盘页面
        """
        self.navigate("/dashboard")
        self.wait_for_dashboard_load()

    def wait_for_dashboard_load(self, timeout: int = 30000):
        """
        Wait for dashboard to load completely
        等待仪表盘完全加载

        Args:
            timeout: Timeout in milliseconds
        """
        try:
            # Wait for page title
            self.wait_for_selector(self.page_title, timeout=timeout)

            # Wait for at least one metric card
            self.wait_for_selector(self.metric_card, timeout=timeout)
        except Exception as e:
            print(f"Warning: Dashboard load timeout - {e}")

    def is_dashboard_visible(self) -> bool:
        """
        Check if dashboard is visible
        检查仪表盘是否可见

        Returns:
            True if dashboard is visible
        """
        return self.is_visible(self.page_title) or self.is_visible(self.dashboard_container)

    def get_page_title(self) -> str:
        """
        Get dashboard page title
        获取仪表盘页面标题

        Returns:
            Page title text
        """
        return self.get_text(self.page_title)

    # Metric card methods / 指标卡片方法

    def get_metrics_count(self) -> int:
        """
        Get number of metric cards displayed
        获取显示的指标卡片数量

        Returns:
            Number of metric cards
        """
        return self.page.locator(self.metric_card).count()

    def get_total_strategies(self) -> str:
        """
        Get total strategies count from metric card
        从指标卡片获取策略总数

        Returns:
            Strategies count as string
        """
        try:
            return self.get_text(self.total_strategies_metric)
        except Exception:
            return "0"

    def get_active_strategies(self) -> str:
        """
        Get active strategies count from metric card
        从指标卡片获取活跃策略数

        Returns:
            Active strategies count as string
        """
        try:
            return self.get_text(self.active_strategies_metric)
        except Exception:
            return "0"

    def get_total_signals(self) -> str:
        """
        Get total signals count from metric card
        从指标卡片获取信号总数

        Returns:
            Signals count as string
        """
        try:
            return self.get_text(self.total_signals_metric)
        except Exception:
            return "0"

    def get_today_signals(self) -> str:
        """
        Get today's signals count from metric card
        从指标卡片获取今日信号数

        Returns:
            Today's signals count as string
        """
        try:
            return self.get_text(self.today_signals_metric)
        except Exception:
            return "0"

    # Navigation methods / 导航方法

    def navigate_to_strategies(self):
        """
        Navigate to strategies page
        导航到策略页面
        """
        self.click(self.strategies_link)
        self.wait_for_url("**/strategies")

    def navigate_to_signals(self):
        """
        Navigate to signals page
        导航到信号页面
        """
        self.click(self.signals_link)
        self.wait_for_url("**/signals")

    def navigate_to_settings(self):
        """
        Navigate to settings page
        导航到设置页面
        """
        self.click(self.settings_link)
        self.wait_for_url("**/settings")

    # Recent signals methods / 最近信号方法

    def is_signals_table_visible(self) -> bool:
        """
        Check if recent signals table is visible
        检查最近信号表格是否可见

        Returns:
            True if table is visible
        """
        return self.is_visible(self.signals_table)

    def get_recent_signals_count(self) -> int:
        """
        Get count of recent signals displayed
        获取显示的最近信号数量

        Returns:
            Number of signal rows
        """
        if not self.is_signals_table_visible():
            return 0
        return self.page.locator(self.signal_row).count()

    def get_signal_row(self, index: int = 0):
        """
        Get a specific signal row
        获取特定的信号行

        Args:
            index: Row index (0-based)

        Returns:
            Locator for the signal row
        """
        return self.page.locator(self.signal_row).nth(index)

    # Action methods / 操作方法

    def click_create_strategy(self):
        """
        Click create strategy button
        点击创建策略按钮
        """
        self.click(self.create_strategy_button)
        self.wait_for_url("**/strategies/create")

    def click_refresh(self):
        """
        Click refresh button
        点击刷新按钮
        """
        if self.is_visible(self.refresh_button):
            self.click(self.refresh_button)
            # Wait for any loading indicators to disappear
            self.page.wait_for_timeout(1000)

    # User menu methods / 用户菜单方法

    def open_user_menu(self):
        """
        Open user menu
        打开用户菜单
        """
        if self.is_visible(self.user_menu):
            self.click(self.user_menu)
            self.page.wait_for_timeout(500)

    def logout(self):
        """
        Logout from application
        从应用登出
        """
        self.open_user_menu()

        # Try to find and click logout button
        logout_selectors = [
            "button:has-text('登出')",
            "button:has-text('退出')",
            "button:has-text('Logout')",
            "a:has-text('登出')",
            "a:has-text('退出')",
            "a:has-text('Logout')",
        ]

        for selector in logout_selectors:
            if self.is_visible(selector):
                self.click(selector)
                self.wait_for_url("**/login")
                return

        raise Exception("Logout button not found")

    # Validation methods / 验证方法

    def validate_dashboard_structure(self) -> bool:
        """
        Validate basic dashboard structure
        验证基本的仪表盘结构

        Returns:
            True if all basic elements are present
        """
        checks = []

        # Check page title
        checks.append(self.is_visible(self.page_title))

        # Check at least one metric card
        checks.append(self.get_metrics_count() > 0)

        # All checks should pass
        return all(checks)

    def wait_for_metrics_to_load(self, timeout: int = 10000):
        """
        Wait for metrics to load (non-zero values)
        等待指标加载（非零值）

        Args:
            timeout: Timeout in milliseconds
        """
        import time
        start_time = time.time()

        while time.time() - start_time < (timeout / 1000):
            if self.get_metrics_count() > 0:
                return
            self.page.wait_for_timeout(500)

        raise TimeoutError(f"Metrics did not load within {timeout}ms")
