"""
Strategy Page Object
策略页面对象

This module contains the page object for the BTC Watcher strategy management page.
"""
from playwright.sync_api import Page, expect
from .base_page import BasePage
from typing import Optional, List


class StrategyPage(BasePage):
    """
    Strategy Page Object
    策略页面对象

    封装策略管理页面的元素和操作。
    """

    def __init__(self, page: Page, base_url: str = "http://localhost:3000"):
        """
        Initialize Strategy Page
        初始化策略页面

        Args:
            page: Playwright page instance
            base_url: Base URL of the application
        """
        super().__init__(page, base_url)

        # Page selectors / 页面选择器
        self.page_title = "h1:has-text('策略'), h1:has-text('Strategies'), .page-title"
        self.strategies_container = ".strategies-container, [data-testid='strategies']"

        # Strategy list / 策略列表
        self.strategy_table = "table, .strategy-table, [data-testid='strategy-table']"
        self.strategy_row = "tr.strategy-row, tbody tr, [data-testid='strategy-row']"
        self.strategy_card = ".strategy-card, [data-testid='strategy-card']"

        # Strategy row columns / 策略行列
        self.strategy_name_column = "td.strategy-name, [data-testid='strategy-name']"
        self.strategy_status_column = "td.strategy-status, [data-testid='strategy-status']"
        self.strategy_actions_column = "td.strategy-actions, [data-testid='strategy-actions']"

        # Status badges / 状态标签
        self.status_running = ".status-running, .badge-success, [data-status='running']"
        self.status_stopped = ".status-stopped, .badge-secondary, [data-status='stopped']"
        self.status_error = ".status-error, .badge-danger, [data-status='error']"

        # Actions / 操作按钮
        self.create_button = "button:has-text('创建策略'), button:has-text('Create Strategy'), [data-testid='create-strategy']"
        self.start_button = "button:has-text('启动'), button:has-text('Start'), [data-action='start']"
        self.stop_button = "button:has-text('停止'), button:has-text('Stop'), [data-action='stop']"
        self.delete_button = "button:has-text('删除'), button:has-text('Delete'), [data-action='delete']"
        self.view_button = "button:has-text('查看'), button:has-text('View'), [data-action='view']"
        self.edit_button = "button:has-text('编辑'), button:has-text('Edit'), [data-action='edit']"

        # Filters and search / 过滤和搜索
        self.search_input = "input[placeholder*='搜索'], input[placeholder*='Search'], [data-testid='search']"
        self.status_filter = "select.status-filter, [data-testid='status-filter']"
        self.refresh_button = "button:has-text('刷新'), button:has-text('Refresh'), [data-testid='refresh']"

        # Create/Edit form / 创建/编辑表单
        self.form_modal = ".modal, .dialog, [data-testid='strategy-form']"
        self.name_input = "input[name='name'], [data-testid='strategy-name-input']"
        self.description_input = "textarea[name='description'], [data-testid='strategy-description']"
        self.config_input = "textarea[name='config'], [data-testid='strategy-config']"
        self.submit_button = "button[type='submit'], button:has-text('提交'), button:has-text('Submit')"
        self.cancel_button = "button:has-text('取消'), button:has-text('Cancel')"

        # Confirmation dialog / 确认对话框
        self.confirm_dialog = ".confirm-dialog, [data-testid='confirm-dialog']"
        self.confirm_yes_button = "button:has-text('确认'), button:has-text('Yes'), button:has-text('确定')"
        self.confirm_no_button = "button:has-text('取消'), button:has-text('No'), button:has-text('Cancel')"

        # Messages / 消息提示
        self.success_message = ".alert-success, .toast-success, [data-testid='success-message']"
        self.error_message = ".alert-error, .toast-error, [data-testid='error-message']"

        # Empty state / 空状态
        self.empty_state = ".empty-state, [data-testid='empty-state']"

        # Loading state / 加载状态
        self.loading_spinner = ".spinner, .loading, [data-testid='loading']"

    def goto(self):
        """
        Navigate to strategies page
        导航到策略页面
        """
        self.navigate("/strategies")
        self.wait_for_page_load()

    def wait_for_page_load(self, timeout: int = 30000):
        """
        Wait for strategies page to load
        等待策略页面加载

        Args:
            timeout: Timeout in milliseconds
        """
        try:
            self.wait_for_selector(self.page_title, timeout=timeout)
            # Wait for either table or empty state
            self.page.wait_for_timeout(1000)
        except Exception as e:
            print(f"Warning: Strategy page load timeout - {e}")

    def is_page_visible(self) -> bool:
        """
        Check if strategies page is visible
        检查策略页面是否可见

        Returns:
            True if page is visible
        """
        return self.is_visible(self.page_title) or self.is_visible(self.strategies_container)

    # Strategy list methods / 策略列表方法

    def get_strategies_count(self) -> int:
        """
        Get number of strategies displayed
        获取显示的策略数量

        Returns:
            Number of strategy rows or cards
        """
        # Try table rows first
        count = self.page.locator(self.strategy_row).count()
        if count > 0:
            return count

        # Try cards
        return self.page.locator(self.strategy_card).count()

    def is_empty_state_visible(self) -> bool:
        """
        Check if empty state is displayed
        检查是否显示空状态

        Returns:
            True if empty state is visible
        """
        return self.is_visible(self.empty_state)

    def get_strategy_row_by_name(self, strategy_name: str):
        """
        Get strategy row by strategy name
        根据策略名称获取策略行

        Args:
            strategy_name: Name of the strategy

        Returns:
            Locator for the strategy row, or None if not found
        """
        rows = self.page.locator(self.strategy_row)
        count = rows.count()

        for i in range(count):
            row = rows.nth(i)
            if strategy_name in row.text_content():
                return row

        return None

    def get_strategy_names(self) -> List[str]:
        """
        Get all strategy names from the list
        获取列表中所有策略名称

        Returns:
            List of strategy names
        """
        names = []
        rows = self.page.locator(self.strategy_row)
        count = rows.count()

        for i in range(count):
            row = rows.nth(i)
            name_cell = row.locator(self.strategy_name_column).first
            if name_cell.count() > 0:
                names.append(name_cell.text_content().strip())

        return names

    def get_strategy_status(self, strategy_name: str) -> Optional[str]:
        """
        Get status of a strategy
        获取策略状态

        Args:
            strategy_name: Name of the strategy

        Returns:
            Status string (running/stopped/error) or None
        """
        row = self.get_strategy_row_by_name(strategy_name)
        if not row:
            return None

        # Check for status badges
        if row.locator(self.status_running).count() > 0:
            return "running"
        elif row.locator(self.status_stopped).count() > 0:
            return "stopped"
        elif row.locator(self.status_error).count() > 0:
            return "error"

        # Fallback: get text from status column
        status_cell = row.locator(self.strategy_status_column).first
        if status_cell.count() > 0:
            return status_cell.text_content().strip().lower()

        return None

    # Search and filter methods / 搜索和过滤方法

    def search_strategy(self, search_term: str):
        """
        Search for strategies
        搜索策略

        Args:
            search_term: Search term to enter
        """
        if self.is_visible(self.search_input):
            self.fill(self.search_input, search_term)
            self.page.wait_for_timeout(1000)  # Wait for search to apply

    def filter_by_status(self, status: str):
        """
        Filter strategies by status
        按状态过滤策略

        Args:
            status: Status to filter by (running/stopped/all)
        """
        if self.is_visible(self.status_filter):
            self.select_option(self.status_filter, status)
            self.page.wait_for_timeout(1000)  # Wait for filter to apply

    def click_refresh(self):
        """
        Click refresh button
        点击刷新按钮
        """
        if self.is_visible(self.refresh_button):
            self.click(self.refresh_button)
            self.page.wait_for_timeout(1000)

    # Create strategy methods / 创建策略方法

    def click_create_strategy(self):
        """
        Click create strategy button
        点击创建策略按钮
        """
        self.click(self.create_button)
        self.wait_for_form_visible()

    def wait_for_form_visible(self, timeout: int = 10000):
        """
        Wait for strategy form to be visible
        等待策略表单可见

        Args:
            timeout: Timeout in milliseconds
        """
        self.wait_for_selector(self.form_modal, timeout=timeout)

    def is_form_visible(self) -> bool:
        """
        Check if strategy form is visible
        检查策略表单是否可见

        Returns:
            True if form is visible
        """
        return self.is_visible(self.form_modal)

    def create_strategy(self, name: str, description: str = "", config: str = ""):
        """
        Create a new strategy
        创建新策略

        Args:
            name: Strategy name
            description: Strategy description
            config: Strategy configuration (JSON string)
        """
        # Click create button
        self.click_create_strategy()

        # Fill form
        self.fill(self.name_input, name)

        if description:
            self.fill(self.description_input, description)

        if config:
            self.fill(self.config_input, config)

        # Submit
        self.click(self.submit_button)

        # Wait for form to close or success message
        self.page.wait_for_timeout(2000)

    def cancel_form(self):
        """
        Cancel form (close without saving)
        取消表单（关闭但不保存）
        """
        self.click(self.cancel_button)
        self.page.wait_for_timeout(500)

    # Strategy actions / 策略操作

    def start_strategy(self, strategy_name: str, confirm: bool = True):
        """
        Start a strategy
        启动策略

        Args:
            strategy_name: Name of the strategy
            confirm: Whether to confirm the action
        """
        row = self.get_strategy_row_by_name(strategy_name)
        if not row:
            raise ValueError(f"Strategy '{strategy_name}' not found")

        # Find and click start button in this row
        start_btn = row.locator(self.start_button).first
        if start_btn.count() > 0:
            start_btn.click()

            # Handle confirmation dialog if present
            if confirm and self.is_visible(self.confirm_dialog):
                self.confirm_action()

            self.page.wait_for_timeout(2000)
        else:
            raise ValueError(f"Start button not found for strategy '{strategy_name}'")

    def stop_strategy(self, strategy_name: str, confirm: bool = True):
        """
        Stop a strategy
        停止策略

        Args:
            strategy_name: Name of the strategy
            confirm: Whether to confirm the action
        """
        row = self.get_strategy_row_by_name(strategy_name)
        if not row:
            raise ValueError(f"Strategy '{strategy_name}' not found")

        # Find and click stop button in this row
        stop_btn = row.locator(self.stop_button).first
        if stop_btn.count() > 0:
            stop_btn.click()

            # Handle confirmation dialog if present
            if confirm and self.is_visible(self.confirm_dialog):
                self.confirm_action()

            self.page.wait_for_timeout(2000)
        else:
            raise ValueError(f"Stop button not found for strategy '{strategy_name}'")

    def delete_strategy(self, strategy_name: str, confirm: bool = True):
        """
        Delete a strategy
        删除策略

        Args:
            strategy_name: Name of the strategy
            confirm: Whether to confirm the deletion
        """
        row = self.get_strategy_row_by_name(strategy_name)
        if not row:
            raise ValueError(f"Strategy '{strategy_name}' not found")

        # Find and click delete button in this row
        delete_btn = row.locator(self.delete_button).first
        if delete_btn.count() > 0:
            delete_btn.click()

            # Handle confirmation dialog
            if confirm and self.is_visible(self.confirm_dialog):
                self.confirm_action()

            self.page.wait_for_timeout(2000)
        else:
            raise ValueError(f"Delete button not found for strategy '{strategy_name}'")

    def view_strategy(self, strategy_name: str):
        """
        View strategy details
        查看策略详情

        Args:
            strategy_name: Name of the strategy
        """
        row = self.get_strategy_row_by_name(strategy_name)
        if not row:
            raise ValueError(f"Strategy '{strategy_name}' not found")

        # Find and click view button
        view_btn = row.locator(self.view_button).first
        if view_btn.count() > 0:
            view_btn.click()
            self.page.wait_for_timeout(1000)
        else:
            # Try clicking the strategy name
            name_cell = row.locator(self.strategy_name_column).first
            if name_cell.count() > 0:
                name_cell.click()
                self.page.wait_for_timeout(1000)

    # Confirmation dialog methods / 确认对话框方法

    def confirm_action(self):
        """
        Confirm an action in confirmation dialog
        在确认对话框中确认操作
        """
        self.click(self.confirm_yes_button)
        self.page.wait_for_timeout(500)

    def cancel_action(self):
        """
        Cancel an action in confirmation dialog
        在确认对话框中取消操作
        """
        self.click(self.confirm_no_button)
        self.page.wait_for_timeout(500)

    # Message methods / 消息方法

    def has_success_message(self) -> bool:
        """
        Check if success message is displayed
        检查是否显示成功消息

        Returns:
            True if success message is visible
        """
        return self.is_visible(self.success_message)

    def has_error_message(self) -> bool:
        """
        Check if error message is displayed
        检查是否显示错误消息

        Returns:
            True if error message is visible
        """
        return self.is_visible(self.error_message)

    def get_success_message(self) -> str:
        """
        Get success message text
        获取成功消息文本

        Returns:
            Success message text
        """
        if self.has_success_message():
            return self.get_text(self.success_message)
        return ""

    def get_error_message(self) -> str:
        """
        Get error message text
        获取错误消息文本

        Returns:
            Error message text
        """
        if self.has_error_message():
            return self.get_text(self.error_message)
        return ""

    # Validation methods / 验证方法

    def wait_for_strategy_status(self, strategy_name: str, expected_status: str, timeout: int = 30000) -> bool:
        """
        Wait for strategy to reach expected status
        等待策略达到预期状态

        Args:
            strategy_name: Name of the strategy
            expected_status: Expected status (running/stopped/error)
            timeout: Timeout in milliseconds

        Returns:
            True if status matches, False otherwise
        """
        import time
        start_time = time.time()

        while time.time() - start_time < (timeout / 1000):
            current_status = self.get_strategy_status(strategy_name)
            if current_status == expected_status:
                return True

            self.page.wait_for_timeout(1000)
            self.click_refresh()

        return False

    def is_loading(self) -> bool:
        """
        Check if page is loading
        检查页面是否正在加载

        Returns:
            True if loading spinner is visible
        """
        return self.is_visible(self.loading_spinner)
