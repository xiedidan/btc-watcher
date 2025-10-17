"""
Signal Page Object
信号页面对象

This module contains the page object for the BTC Watcher signal monitoring page.
"""
from playwright.sync_api import Page, expect
from .base_page import BasePage
from typing import Optional, List, Dict


class SignalPage(BasePage):
    """
    Signal Page Object
    信号页面对象

    封装信号监控页面的元素和操作。
    """

    def __init__(self, page: Page, base_url: str = "http://localhost:3000"):
        """
        Initialize Signal Page
        初始化信号页面

        Args:
            page: Playwright page instance
            base_url: Base URL of the application
        """
        super().__init__(page, base_url)

        # Page selectors / 页面选择器
        self.page_title = "h1:has-text('信号'), h1:has-text('Signals'), .page-title"
        self.signals_container = ".signals-container, [data-testid='signals']"

        # Signal list / 信号列表
        self.signal_table = "table, .signal-table, [data-testid='signal-table']"
        self.signal_row = "tr.signal-row, tbody tr, [data-testid='signal-row']"
        self.signal_card = ".signal-card, [data-testid='signal-card']"

        # Signal row columns / 信号行列
        self.signal_pair_column = "td.signal-pair, [data-testid='signal-pair']"
        self.signal_action_column = "td.signal-action, [data-testid='signal-action']"
        self.signal_strength_column = "td.signal-strength, [data-testid='signal-strength']"
        self.signal_time_column = "td.signal-time, [data-testid='signal-time']"
        self.signal_strategy_column = "td.signal-strategy, [data-testid='signal-strategy']"

        # Action badges / 操作标签
        self.action_buy = ".action-buy, .badge-success, [data-action='buy']"
        self.action_sell = ".action-sell, .badge-danger, [data-action='sell']"

        # Strength badges / 强度标签
        self.strength_strong = ".strength-strong, [data-strength='strong']"
        self.strength_medium = ".strength-medium, [data-strength='medium']"
        self.strength_weak = ".strength-weak, [data-strength='weak']"

        # Filters / 过滤器
        self.filter_panel = ".filter-panel, [data-testid='filters']"
        self.pair_filter = "select[name='pair'], [data-testid='pair-filter']"
        self.action_filter = "select[name='action'], [data-testid='action-filter']"
        self.strength_filter = "select[name='strength'], [data-testid='strength-filter']"
        self.strategy_filter = "select[name='strategy'], [data-testid='strategy-filter']"
        self.date_from_filter = "input[name='date_from'], [data-testid='date-from']"
        self.date_to_filter = "input[name='date_to'], [data-testid='date-to']"
        self.apply_filters_button = "button:has-text('应用'), button:has-text('Apply'), [data-testid='apply-filters']"
        self.reset_filters_button = "button:has-text('重置'), button:has-text('Reset'), [data-testid='reset-filters']"

        # Search / 搜索
        self.search_input = "input[placeholder*='搜索'], input[placeholder*='Search'], [data-testid='search']"

        # Pagination / 分页
        self.pagination = ".pagination, [data-testid='pagination']"
        self.page_info = ".page-info, [data-testid='page-info']"
        self.prev_page_button = "button:has-text('上一页'), button:has-text('Previous'), [data-testid='prev-page']"
        self.next_page_button = "button:has-text('下一页'), button:has-text('Next'), [data-testid='next-page']"
        self.page_number_button = ".page-number, [data-testid='page-number']"

        # Signal details modal / 信号详情模态框
        self.details_modal = ".signal-details-modal, [data-testid='signal-details']"
        self.details_pair = "[data-testid='details-pair']"
        self.details_action = "[data-testid='details-action']"
        self.details_strength = "[data-testid='details-strength']"
        self.details_price = "[data-testid='details-price']"
        self.details_indicators = "[data-testid='details-indicators']"
        self.details_metadata = "[data-testid='details-metadata']"
        self.close_details_button = "button:has-text('关闭'), button:has-text('Close'), [data-testid='close-details']"

        # Statistics / 统计信息
        self.stats_panel = ".stats-panel, [data-testid='stats']"
        self.total_signals_stat = "[data-testid='total-signals']"
        self.buy_signals_stat = "[data-testid='buy-signals']"
        self.sell_signals_stat = "[data-testid='sell-signals']"
        self.strong_signals_stat = "[data-testid='strong-signals']"

        # Actions / 操作按钮
        self.refresh_button = "button:has-text('刷新'), button:has-text('Refresh'), [data-testid='refresh']"
        self.export_button = "button:has-text('导出'), button:has-text('Export'), [data-testid='export']"

        # Empty state / 空状态
        self.empty_state = ".empty-state, [data-testid='empty-state']"

        # Loading state / 加载状态
        self.loading_spinner = ".spinner, .loading, [data-testid='loading']"

    def goto(self):
        """
        Navigate to signals page
        导航到信号页面
        """
        self.navigate("/signals")
        self.wait_for_page_load()

    def wait_for_page_load(self, timeout: int = 30000):
        """
        Wait for signals page to load
        等待信号页面加载

        Args:
            timeout: Timeout in milliseconds
        """
        try:
            self.wait_for_selector(self.page_title, timeout=timeout)
            self.page.wait_for_timeout(1000)
        except Exception as e:
            print(f"Warning: Signal page load timeout - {e}")

    def is_page_visible(self) -> bool:
        """
        Check if signals page is visible
        检查信号页面是否可见

        Returns:
            True if page is visible
        """
        return self.is_visible(self.page_title) or self.is_visible(self.signals_container)

    # Signal list methods / 信号列表方法

    def get_signals_count(self) -> int:
        """
        Get number of signals displayed
        获取显示的信号数量

        Returns:
            Number of signal rows or cards
        """
        # Try table rows first
        count = self.page.locator(self.signal_row).count()
        if count > 0:
            return count

        # Try cards
        return self.page.locator(self.signal_card).count()

    def is_empty_state_visible(self) -> bool:
        """
        Check if empty state is displayed
        检查是否显示空状态

        Returns:
            True if empty state is visible
        """
        return self.is_visible(self.empty_state)

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

    def get_signal_pairs(self) -> List[str]:
        """
        Get all signal pairs from the list
        获取列表中所有信号交易对

        Returns:
            List of trading pairs
        """
        pairs = []
        rows = self.page.locator(self.signal_row)
        count = rows.count()

        for i in range(count):
            row = rows.nth(i)
            pair_cell = row.locator(self.signal_pair_column).first
            if pair_cell.count() > 0:
                pairs.append(pair_cell.text_content().strip())

        return pairs

    def get_signal_actions(self) -> List[str]:
        """
        Get all signal actions from the list
        获取列表中所有信号操作

        Returns:
            List of actions (buy/sell)
        """
        actions = []
        rows = self.page.locator(self.signal_row)
        count = rows.count()

        for i in range(count):
            row = rows.nth(i)
            action_cell = row.locator(self.signal_action_column).first
            if action_cell.count() > 0:
                actions.append(action_cell.text_content().strip().lower())

        return actions

    def get_signal_by_pair(self, pair: str):
        """
        Get first signal row matching the pair
        根据交易对获取第一个匹配的信号行

        Args:
            pair: Trading pair (e.g., "BTC/USDT")

        Returns:
            Locator for the signal row, or None if not found
        """
        rows = self.page.locator(self.signal_row)
        count = rows.count()

        for i in range(count):
            row = rows.nth(i)
            if pair in row.text_content():
                return row

        return None

    # Filter methods / 过滤方法

    def filter_by_pair(self, pair: str):
        """
        Filter signals by trading pair
        按交易对过滤信号

        Args:
            pair: Trading pair to filter by
        """
        if self.is_visible(self.pair_filter):
            self.select_option(self.pair_filter, pair)
            self.apply_filters()

    def filter_by_action(self, action: str):
        """
        Filter signals by action
        按操作过滤信号

        Args:
            action: Action to filter by (buy/sell/all)
        """
        if self.is_visible(self.action_filter):
            self.select_option(self.action_filter, action)
            self.apply_filters()

    def filter_by_strength(self, strength: str):
        """
        Filter signals by strength level
        按强度级别过滤信号

        Args:
            strength: Strength to filter by (strong/medium/weak/all)
        """
        if self.is_visible(self.strength_filter):
            self.select_option(self.strength_filter, strength)
            self.apply_filters()

    def filter_by_strategy(self, strategy: str):
        """
        Filter signals by strategy
        按策略过滤信号

        Args:
            strategy: Strategy name or ID to filter by
        """
        if self.is_visible(self.strategy_filter):
            self.select_option(self.strategy_filter, strategy)
            self.apply_filters()

    def filter_by_date_range(self, date_from: str, date_to: str):
        """
        Filter signals by date range
        按日期范围过滤信号

        Args:
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)
        """
        if self.is_visible(self.date_from_filter):
            self.fill(self.date_from_filter, date_from)

        if self.is_visible(self.date_to_filter):
            self.fill(self.date_to_filter, date_to)

        self.apply_filters()

    def apply_filters(self):
        """
        Apply filters
        应用过滤器
        """
        if self.is_visible(self.apply_filters_button):
            self.click(self.apply_filters_button)
            self.page.wait_for_timeout(1000)

    def reset_filters(self):
        """
        Reset all filters
        重置所有过滤器
        """
        if self.is_visible(self.reset_filters_button):
            self.click(self.reset_filters_button)
            self.page.wait_for_timeout(1000)

    def search_signal(self, search_term: str):
        """
        Search for signals
        搜索信号

        Args:
            search_term: Search term to enter
        """
        if self.is_visible(self.search_input):
            self.fill(self.search_input, search_term)
            self.page.wait_for_timeout(1000)

    # Pagination methods / 分页方法

    def is_pagination_visible(self) -> bool:
        """
        Check if pagination is visible
        检查分页是否可见

        Returns:
            True if pagination is visible
        """
        return self.is_visible(self.pagination)

    def get_page_info(self) -> str:
        """
        Get page info text (e.g., "1-20 of 100")
        获取分页信息文本

        Returns:
            Page info string
        """
        if self.is_visible(self.page_info):
            return self.get_text(self.page_info)
        return ""

    def go_to_next_page(self):
        """
        Go to next page
        转到下一页
        """
        if self.is_visible(self.next_page_button):
            self.click(self.next_page_button)
            self.page.wait_for_timeout(1000)

    def go_to_previous_page(self):
        """
        Go to previous page
        转到上一页
        """
        if self.is_visible(self.prev_page_button):
            self.click(self.prev_page_button)
            self.page.wait_for_timeout(1000)

    def go_to_page(self, page_number: int):
        """
        Go to specific page
        转到指定页面

        Args:
            page_number: Page number to navigate to
        """
        page_buttons = self.page.locator(self.page_number_button)
        count = page_buttons.count()

        for i in range(count):
            button = page_buttons.nth(i)
            if str(page_number) in button.text_content():
                button.click()
                self.page.wait_for_timeout(1000)
                return

    # Signal details methods / 信号详情方法

    def view_signal_details(self, index: int = 0):
        """
        View signal details
        查看信号详情

        Args:
            index: Index of the signal to view (0-based)
        """
        row = self.get_signal_row(index)
        if row:
            row.click()
            self.wait_for_details_modal()

    def wait_for_details_modal(self, timeout: int = 10000):
        """
        Wait for signal details modal to appear
        等待信号详情模态框出现

        Args:
            timeout: Timeout in milliseconds
        """
        self.wait_for_selector(self.details_modal, timeout=timeout)

    def is_details_modal_visible(self) -> bool:
        """
        Check if signal details modal is visible
        检查信号详情模态框是否可见

        Returns:
            True if modal is visible
        """
        return self.is_visible(self.details_modal)

    def get_signal_details(self) -> Dict[str, str]:
        """
        Get signal details from modal
        从模态框获取信号详情

        Returns:
            Dictionary with signal details
        """
        if not self.is_details_modal_visible():
            return {}

        details = {}

        if self.is_visible(self.details_pair):
            details["pair"] = self.get_text(self.details_pair)

        if self.is_visible(self.details_action):
            details["action"] = self.get_text(self.details_action)

        if self.is_visible(self.details_strength):
            details["strength"] = self.get_text(self.details_strength)

        if self.is_visible(self.details_price):
            details["price"] = self.get_text(self.details_price)

        if self.is_visible(self.details_indicators):
            details["indicators"] = self.get_text(self.details_indicators)

        if self.is_visible(self.details_metadata):
            details["metadata"] = self.get_text(self.details_metadata)

        return details

    def close_details_modal(self):
        """
        Close signal details modal
        关闭信号详情模态框
        """
        if self.is_visible(self.close_details_button):
            self.click(self.close_details_button)
            self.page.wait_for_timeout(500)

    # Statistics methods / 统计方法

    def is_stats_panel_visible(self) -> bool:
        """
        Check if statistics panel is visible
        检查统计面板是否可见

        Returns:
            True if stats panel is visible
        """
        return self.is_visible(self.stats_panel)

    def get_total_signals(self) -> str:
        """
        Get total signals count from stats
        从统计获取信号总数

        Returns:
            Total signals count as string
        """
        if self.is_visible(self.total_signals_stat):
            return self.get_text(self.total_signals_stat)
        return "0"

    def get_buy_signals_count(self) -> str:
        """
        Get buy signals count from stats
        从统计获取买入信号数

        Returns:
            Buy signals count as string
        """
        if self.is_visible(self.buy_signals_stat):
            return self.get_text(self.buy_signals_stat)
        return "0"

    def get_sell_signals_count(self) -> str:
        """
        Get sell signals count from stats
        从统计获取卖出信号数

        Returns:
            Sell signals count as string
        """
        if self.is_visible(self.sell_signals_stat):
            return self.get_text(self.sell_signals_stat)
        return "0"

    def get_strong_signals_count(self) -> str:
        """
        Get strong signals count from stats
        从统计获取强信号数

        Returns:
            Strong signals count as string
        """
        if self.is_visible(self.strong_signals_stat):
            return self.get_text(self.strong_signals_stat)
        return "0"

    # Action methods / 操作方法

    def click_refresh(self):
        """
        Click refresh button
        点击刷新按钮
        """
        if self.is_visible(self.refresh_button):
            self.click(self.refresh_button)
            self.page.wait_for_timeout(1000)

    def click_export(self):
        """
        Click export button
        点击导出按钮
        """
        if self.is_visible(self.export_button):
            with self.page.expect_download() as download_info:
                self.click(self.export_button)
            download = download_info.value
            return download

    # Validation methods / 验证方法

    def count_signals_by_action(self, action: str) -> int:
        """
        Count signals with specific action
        统计特定操作的信号数量

        Args:
            action: Action to count (buy/sell)

        Returns:
            Count of signals with the action
        """
        actions = self.get_signal_actions()
        return actions.count(action.lower())

    def count_signals_by_pair(self, pair: str) -> int:
        """
        Count signals for specific trading pair
        统计特定交易对的信号数量

        Args:
            pair: Trading pair

        Returns:
            Count of signals for the pair
        """
        pairs = self.get_signal_pairs()
        return pairs.count(pair)

    def is_loading(self) -> bool:
        """
        Check if page is loading
        检查页面是否正在加载

        Returns:
            True if loading spinner is visible
        """
        return self.is_visible(self.loading_spinner)
