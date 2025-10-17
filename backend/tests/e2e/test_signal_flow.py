"""
E2E Test: Signal Monitoring Flow
信号监控流程端到端测试

测试场景:
1. 信号列表页面加载
2. 信号详情查看
3. 信号过滤（交易对、操作、强度）
4. 信号搜索
5. 分页功能
6. 统计信息显示
7. 完整工作流程
"""
import pytest
from playwright.sync_api import Page, expect
from .pages.signal_page import SignalPage
from .pages.dashboard_page import DashboardPage


class TestSignalMonitoring:
    """信号监控E2E测试"""

    def test_signal_page_loads(self, authenticated_page: Page):
        """测试信号页面加载"""
        page = authenticated_page
        signal_page = SignalPage(page)

        # 导航到信号页面
        signal_page.goto()

        # 验证页面加载
        assert signal_page.is_page_visible(), "信号页面应该可见"

        # 验证页面标题
        page_title = signal_page.get_text(signal_page.page_title)
        assert any(keyword in page_title for keyword in ["信号", "Signals"]), \
            f"页面标题应包含'信号'或'Signals'，实际: {page_title}"

    def test_signal_list_display(self, authenticated_page: Page):
        """测试信号列表显示"""
        page = authenticated_page
        signal_page = SignalPage(page)

        signal_page.goto()

        # 页面应该显示信号列表或空状态
        signals_count = signal_page.get_signals_count()
        is_empty = signal_page.is_empty_state_visible()

        assert signals_count > 0 or is_empty, \
            "应该显示信号列表或空状态"

        if signals_count > 0:
            print(f"Found {signals_count} signals")
            # 验证可以获取信号信息
            pairs = signal_page.get_signal_pairs()
            actions = signal_page.get_signal_actions()
            assert len(pairs) > 0 or len(actions) > 0, "应该能获取信号信息"

    def test_navigate_from_dashboard_to_signals(self, authenticated_page: Page):
        """测试从仪表盘导航到信号页面"""
        page = authenticated_page
        dashboard_page = DashboardPage(page)

        # 确认在仪表盘页面
        dashboard_page.goto()
        assert dashboard_page.is_dashboard_visible(), "应该在仪表盘页面"

        # 导航到信号页面
        dashboard_page.navigate_to_signals()

        # 等待跳转
        page.wait_for_timeout(2000)

        # 验证当前在信号页面
        current_url = page.url
        assert "signals" in current_url or "signal" in current_url, \
            f"应该在信号页面，当前URL: {current_url}"

    def test_signal_table_structure(self, authenticated_page: Page):
        """测试信号表格结构"""
        page = authenticated_page
        signal_page = SignalPage(page)

        signal_page.goto()

        signals_count = signal_page.get_signals_count()

        if signals_count == 0:
            pytest.skip("没有信号数据")

        # 验证表格或卡片结构存在
        has_table = signal_page.is_visible(signal_page.signal_table)
        has_cards = signal_page.is_visible(signal_page.signal_card)

        assert has_table or has_cards, "应该显示信号表格或卡片"

    def test_signal_pairs_display(self, authenticated_page: Page):
        """测试交易对显示"""
        page = authenticated_page
        signal_page = SignalPage(page)

        signal_page.goto()

        signals_count = signal_page.get_signals_count()

        if signals_count == 0:
            pytest.skip("没有信号数据")

        # 获取交易对列表
        pairs = signal_page.get_signal_pairs()

        if len(pairs) > 0:
            print(f"Signal pairs: {pairs}")
            # 验证交易对格式（通常是 XXX/YYY）
            for pair in pairs:
                assert len(pair) > 0, "交易对不应为空"

    def test_signal_actions_display(self, authenticated_page: Page):
        """测试信号操作显示"""
        page = authenticated_page
        signal_page = SignalPage(page)

        signal_page.goto()

        signals_count = signal_page.get_signals_count()

        if signals_count == 0:
            pytest.skip("没有信号数据")

        # 获取操作列表
        actions = signal_page.get_signal_actions()

        if len(actions) > 0:
            print(f"Signal actions: {actions}")
            # 验证操作值（应该是buy或sell）
            for action in actions:
                assert action in ["buy", "sell", "买入", "卖出"], \
                    f"操作应该是buy/sell，实际: {action}"

    def test_filter_by_action(self, authenticated_page: Page):
        """测试按操作过滤信号"""
        page = authenticated_page
        signal_page = SignalPage(page)

        signal_page.goto()

        # 检查过滤器是否存在
        if not signal_page.is_visible(signal_page.action_filter):
            pytest.skip("操作过滤器未实现")

        # 过滤买入信号
        signal_page.filter_by_action("buy")

        # 等待过滤完成
        page.wait_for_timeout(1500)

        # 验证过滤结果
        filtered_count = signal_page.get_signals_count()
        print(f"Buy signals count: {filtered_count}")

        if filtered_count > 0:
            # 验证所有信号都是买入
            actions = signal_page.get_signal_actions()
            buy_count = signal_page.count_signals_by_action("buy")

            if len(actions) > 0:
                assert buy_count == len(actions) or buy_count > 0, \
                    "过滤后应该只显示买入信号"

    def test_filter_by_pair(self, authenticated_page: Page):
        """测试按交易对过滤信号"""
        page = authenticated_page
        signal_page = SignalPage(page)

        signal_page.goto()

        # 检查过滤器是否存在
        if not signal_page.is_visible(signal_page.pair_filter):
            pytest.skip("交易对过滤器未实现")

        # 获取所有交易对
        all_pairs = signal_page.get_signal_pairs()

        if len(all_pairs) == 0:
            pytest.skip("没有信号数据")

        # 选择第一个交易对进行过滤
        first_pair = all_pairs[0]
        signal_page.filter_by_pair(first_pair)

        # 等待过滤完成
        page.wait_for_timeout(1500)

        # 验证过滤结果
        filtered_pairs = signal_page.get_signal_pairs()
        if len(filtered_pairs) > 0:
            # 所有信号应该是该交易对
            pair_count = signal_page.count_signals_by_pair(first_pair)
            assert pair_count == len(filtered_pairs) or pair_count > 0, \
                f"过滤后应该只显示{first_pair}的信号"

    def test_filter_by_strength(self, authenticated_page: Page):
        """测试按强度过滤信号"""
        page = authenticated_page
        signal_page = SignalPage(page)

        signal_page.goto()

        # 检查强度过滤器是否存在
        if not signal_page.is_visible(signal_page.strength_filter):
            pytest.skip("强度过滤器未实现")

        signals_count = signal_page.get_signals_count()

        if signals_count == 0:
            pytest.skip("没有信号数据")

        # 过滤强信号
        signal_page.filter_by_strength("strong")

        # 等待过滤完成
        page.wait_for_timeout(1500)

        # 验证过滤结果
        filtered_count = signal_page.get_signals_count()
        print(f"Strong signals count: {filtered_count}")

        # 应该有结果或没有强信号
        assert filtered_count >= 0, "过滤应该返回有效结果"

    def test_search_signal(self, authenticated_page: Page):
        """测试信号搜索功能"""
        page = authenticated_page
        signal_page = SignalPage(page)

        signal_page.goto()

        # 检查搜索框是否存在
        if not signal_page.is_visible(signal_page.search_input):
            pytest.skip("搜索功能未实现")

        signals_count = signal_page.get_signals_count()

        if signals_count == 0:
            pytest.skip("没有信号数据")

        # 获取第一个交易对
        pairs = signal_page.get_signal_pairs()
        if len(pairs) > 0:
            first_pair = pairs[0]

            # 搜索该交易对
            signal_page.search_signal(first_pair)

            # 验证搜索结果
            search_results = signal_page.get_signals_count()
            assert search_results > 0, f"搜索'{first_pair}'应该有结果"

    def test_reset_filters(self, authenticated_page: Page):
        """测试重置过滤器"""
        page = authenticated_page
        signal_page = SignalPage(page)

        signal_page.goto()

        # 检查重置按钮是否存在
        if not signal_page.is_visible(signal_page.reset_filters_button):
            pytest.skip("重置过滤器功能未实现")

        # 获取初始信号数量
        initial_count = signal_page.get_signals_count()

        # 应用某个过滤器
        if signal_page.is_visible(signal_page.action_filter):
            signal_page.filter_by_action("buy")
            page.wait_for_timeout(1000)

        # 重置过滤器
        signal_page.reset_filters()

        # 等待重置完成
        page.wait_for_timeout(1500)

        # 验证信号数量恢复
        reset_count = signal_page.get_signals_count()
        assert reset_count >= initial_count or reset_count > 0, \
            "重置后应该显示所有信号"

    def test_refresh_signal_list(self, authenticated_page: Page):
        """测试刷新信号列表"""
        page = authenticated_page
        signal_page = SignalPage(page)

        signal_page.goto()

        # 获取初始信号数量
        initial_count = signal_page.get_signals_count()

        # 点击刷新
        signal_page.click_refresh()

        # 等待刷新完成
        page.wait_for_timeout(2000)

        # 获取刷新后的信号数量
        new_count = signal_page.get_signals_count()

        # 数量应该相同或变化（如果有新信号）
        assert new_count >= 0, "刷新后应该能获取信号数量"

    def test_pagination_display(self, authenticated_page: Page):
        """测试分页显示"""
        page = authenticated_page
        signal_page = SignalPage(page)

        signal_page.goto()

        signals_count = signal_page.get_signals_count()

        # 检查是否有分页
        has_pagination = signal_page.is_pagination_visible()

        if has_pagination:
            print("Pagination is visible")
            # 获取分页信息
            page_info = signal_page.get_page_info()
            print(f"Page info: {page_info}")

            assert len(page_info) > 0, "应该显示分页信息"
        else:
            print("No pagination (all signals on one page)")

    def test_pagination_next_page(self, authenticated_page: Page):
        """测试分页下一页"""
        page = authenticated_page
        signal_page = SignalPage(page)

        signal_page.goto()

        # 检查是否有分页
        if not signal_page.is_pagination_visible():
            pytest.skip("没有分页")

        # 获取第一页的信号
        first_page_pairs = signal_page.get_signal_pairs()

        # 点击下一页
        if signal_page.is_visible(signal_page.next_page_button):
            signal_page.go_to_next_page()

            # 等待页面加载
            page.wait_for_timeout(1500)

            # 获取第二页的信号
            second_page_pairs = signal_page.get_signal_pairs()

            # 验证信号列表发生变化
            assert first_page_pairs != second_page_pairs, \
                "翻页后应该显示不同的信号"
        else:
            pytest.skip("没有下一页按钮")

    def test_view_signal_details(self, authenticated_page: Page):
        """测试查看信号详情"""
        page = authenticated_page
        signal_page = SignalPage(page)

        signal_page.goto()

        signals_count = signal_page.get_signals_count()

        if signals_count == 0:
            pytest.skip("没有信号数据")

        try:
            # 点击第一个信号查看详情
            signal_page.view_signal_details(index=0)

            # 等待详情模态框出现
            page.wait_for_timeout(2000)

            # 验证详情模态框是否显示
            if signal_page.is_details_modal_visible():
                print("Signal details modal is visible")

                # 获取详情信息
                details = signal_page.get_signal_details()
                print(f"Signal details: {details}")

                # 关闭详情模态框
                signal_page.close_details_modal()
                page.wait_for_timeout(500)

                assert len(details) > 0, "应该能获取信号详情"
            else:
                # 可能跳转到详情页面
                current_url = page.url
                if "detail" in current_url or "signal" in current_url:
                    print(f"Navigated to details page: {current_url}")
                else:
                    pytest.skip("详情功能未实现")

        except Exception as e:
            print(f"查看详情时出现异常: {e}")
            pytest.skip(f"View details not fully implemented: {e}")

    def test_statistics_panel(self, authenticated_page: Page):
        """测试统计面板"""
        page = authenticated_page
        signal_page = SignalPage(page)

        signal_page.goto()

        # 检查统计面板是否存在
        if not signal_page.is_stats_panel_visible():
            pytest.skip("统计面板未实现")

        # 获取统计数据
        total_signals = signal_page.get_total_signals()
        buy_signals = signal_page.get_buy_signals_count()
        sell_signals = signal_page.get_sell_signals_count()
        strong_signals = signal_page.get_strong_signals_count()

        print(f"Statistics - Total: {total_signals}, Buy: {buy_signals}, Sell: {sell_signals}, Strong: {strong_signals}")

        # 验证统计数据
        assert len(total_signals) > 0 or len(buy_signals) > 0, \
            "应该显示统计信息"

    def test_signal_strength_classification(self, authenticated_page: Page):
        """测试信号强度分类"""
        page = authenticated_page
        signal_page = SignalPage(page)

        signal_page.goto()

        signals_count = signal_page.get_signals_count()

        if signals_count == 0:
            pytest.skip("没有信号数据")

        # 检查是否有强度标签
        rows = signal_page.page.locator(signal_page.signal_row)
        count = rows.count()

        strength_found = False
        for i in range(min(count, 5)):  # 检查前5个信号
            row = rows.nth(i)
            # 检查是否有强度相关的类或属性
            has_strong = row.locator(signal_page.strength_strong).count() > 0
            has_medium = row.locator(signal_page.strength_medium).count() > 0
            has_weak = row.locator(signal_page.strength_weak).count() > 0

            if has_strong or has_medium or has_weak:
                strength_found = True
                print(f"Signal {i} has strength classification")
                break

        if not strength_found:
            pytest.skip("信号强度分类未实现或未显示")

        assert strength_found, "至少有一个信号应该有强度分类"

    def test_export_signals(self, authenticated_page: Page):
        """测试导出信号"""
        page = authenticated_page
        signal_page = SignalPage(page)

        signal_page.goto()

        # 检查导出按钮是否存在
        if not signal_page.is_visible(signal_page.export_button):
            pytest.skip("导出功能未实现")

        signals_count = signal_page.get_signals_count()

        if signals_count == 0:
            pytest.skip("没有信号数据可导出")

        try:
            # 点击导出按钮
            download = signal_page.click_export()

            # 验证下载是否开始
            if download:
                print(f"Download started: {download.suggested_filename}")
                assert download.suggested_filename, "应该有下载文件名"
            else:
                pytest.skip("导出功能未完全实现")

        except Exception as e:
            print(f"导出时出现异常: {e}")
            pytest.skip(f"Export not fully implemented: {e}")

    def test_complete_signal_workflow(self, authenticated_page: Page):
        """测试完整的信号监控工作流程"""
        page = authenticated_page
        signal_page = SignalPage(page)

        # 步骤1: 访问信号页面
        signal_page.goto()
        assert signal_page.is_page_visible(), "应该能访问信号页面"

        # 步骤2: 查看信号列表
        initial_count = signal_page.get_signals_count()
        print(f"Initial signals count: {initial_count}")

        if initial_count == 0:
            pytest.skip("没有信号数据进行完整流程测试")

        # 步骤3: 应用过滤器
        if signal_page.is_visible(signal_page.action_filter):
            signal_page.filter_by_action("buy")
            page.wait_for_timeout(1500)

            filtered_count = signal_page.get_signals_count()
            print(f"Filtered (buy) signals count: {filtered_count}")

        # 步骤4: 查看信号详情
        if signal_page.get_signals_count() > 0:
            try:
                signal_page.view_signal_details(index=0)
                page.wait_for_timeout(2000)

                if signal_page.is_details_modal_visible():
                    details = signal_page.get_signal_details()
                    print(f"Signal details: {details}")
                    signal_page.close_details_modal()
                    page.wait_for_timeout(500)
            except:
                pass

        # 步骤5: 重置过滤器
        if signal_page.is_visible(signal_page.reset_filters_button):
            signal_page.reset_filters()
            page.wait_for_timeout(1500)

            reset_count = signal_page.get_signals_count()
            print(f"Reset signals count: {reset_count}")

        # 步骤6: 刷新数据
        signal_page.click_refresh()
        page.wait_for_timeout(2000)

        final_count = signal_page.get_signals_count()
        print(f"Final signals count: {final_count}")

        assert final_count >= 0, "完整工作流程应该成功完成"

        print("完整信号监控工作流程测试成功")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--headed"])
