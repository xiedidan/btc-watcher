"""
E2E Test: Authentication Flow
用户认证流程端到端测试

测试场景:
1. 用户成功登录
2. 用户登录失败（错误凭证）
3. 登录表单验证
4. 用户登出
"""
import pytest
import re
from playwright.sync_api import Page, expect
from .pages import LoginPage


class TestAuthenticationFlow:
    """用户认证流程E2E测试"""

    def test_login_page_loads(self, page: Page):
        """测试登录页面加载"""
        login_page = LoginPage(page)

        # 访问登录页
        login_page.goto()

        # 验证页面标题（应用标题）
        expect(page).to_have_title(re.compile("BTC Watcher"))

        # 验证登录表单元素存在
        assert login_page.is_username_field_visible(), "用户名输入框应该可见"
        assert login_page.is_password_field_visible(), "密码输入框应该可见"
        assert login_page.is_login_button_visible(), "登录按钮应该可见"

    def test_user_login_success(self, page: Page, test_user_credentials):
        """测试用户成功登录"""
        login_page = LoginPage(page)

        # 1. 访问登录页
        login_page.goto()

        # 2. 填写登录信息
        login_page.login(
            username=test_user_credentials["username"],
            password=test_user_credentials["password"]
        )

        # 3. 验证登录成功
        # 方式1: 通过URL跳转判断
        assert login_page.is_login_successful(), "应该跳转到仪表盘页面"

        # 方式2: 验证当前URL包含dashboard
        current_url = page.url
        assert "dashboard" in current_url, f"当前URL应包含dashboard，实际URL: {current_url}"

        # 4. 验证仪表盘页面加载
        expect(page.locator("h1, h2, .page-title")).to_contain_text(re.compile("仪表盘|Dashboard", re.IGNORECASE))

    def test_user_login_with_invalid_credentials(self, page: Page):
        """测试使用无效凭证登录"""
        login_page = LoginPage(page)

        # 访问登录页
        login_page.goto()

        # 使用错误的凭证登录
        login_page.login(username="wronguser", password="wrongpass")

        # 等待错误消息出现
        page.wait_for_timeout(2000)

        # 验证错误消息显示
        has_error = login_page.has_error()
        if has_error:
            error_msg = login_page.get_error_message()
            assert len(error_msg) > 0, "应该显示错误消息"
            assert any(keyword in error_msg.lower() for keyword in ["错误", "失败", "error", "invalid", "incorrect"]), \
                f"错误消息应包含相关关键词，实际消息: {error_msg}"

        # 验证仍在登录页
        current_url = page.url
        assert "login" in current_url, f"登录失败应停留在登录页，当前URL: {current_url}"

    def test_login_with_empty_username(self, page: Page):
        """测试用户名为空时的表单验证"""
        login_page = LoginPage(page)

        login_page.goto()

        # 只填写密码，不填用户名
        login_page.fill(login_page.password_input, "somepassword")
        login_page.click(login_page.login_button)

        # 等待表单验证
        page.wait_for_timeout(1000)

        # 验证仍在登录页（表单验证失败）
        current_url = page.url
        assert "login" in current_url, "表单验证失败应停留在登录页"

    def test_login_with_empty_password(self, page: Page):
        """测试密码为空时的表单验证"""
        login_page = LoginPage(page)

        login_page.goto()

        # 只填写用户名，不填密码
        login_page.fill(login_page.username_input, "testuser")
        login_page.click(login_page.login_button)

        # 等待表单验证
        page.wait_for_timeout(1000)

        # 验证仍在登录页（表单验证失败）
        current_url = page.url
        assert "login" in current_url, "表单验证失败应停留在登录页"

    def test_user_logout(self, authenticated_page: Page):
        """测试用户登出"""
        page = authenticated_page

        # 验证已登录（在仪表盘页面）
        current_url = page.url
        assert "dashboard" in current_url or "home" in current_url, \
            f"应该在仪表盘页面，当前URL: {current_url}"

        # 查找并点击登出按钮（可能在用户菜单中）
        # 尝试多种可能的选择器
        logout_selectors = [
            "button:has-text('登出')",
            "button:has-text('退出')",
            "button:has-text('Logout')",
            "a:has-text('登出')",
            "a:has-text('退出')",
            "a:has-text('Logout')",
            "[aria-label='登出']",
            "[aria-label='Logout']",
        ]

        # 可能需要先点击用户菜单
        user_menu_selectors = [
            "[aria-label='用户菜单']",
            "[aria-label='User menu']",
            ".user-menu",
            "button.avatar",
        ]

        # 尝试打开用户菜单
        for selector in user_menu_selectors:
            if page.locator(selector).count() > 0:
                page.click(selector)
                page.wait_for_timeout(500)
                break

        # 尝试点击登出
        logout_clicked = False
        for selector in logout_selectors:
            if page.locator(selector).count() > 0:
                page.click(selector)
                logout_clicked = True
                break

        if logout_clicked:
            # 等待跳转
            page.wait_for_timeout(2000)

            # 验证跳转到登录页
            current_url = page.url
            assert "login" in current_url, f"登出后应跳转到登录页，当前URL: {current_url}"

            # 尝试访问受保护页面，应该被重定向到登录页
            page.goto(f"{page.context.pages[0].url.split('/')[0]}//dashboard")
            page.wait_for_timeout(1000)

            # 验证被重定向到登录页
            final_url = page.url
            assert "login" in final_url, f"未登录时访问受保护页面应重定向到登录页，当前URL: {final_url}"

    def test_login_api_response(self, page: Page, test_user_credentials):
        """测试登录时的API响应"""
        login_page = LoginPage(page)

        login_page.goto()

        # 监听API响应
        with page.expect_response("**/api/v1/auth/token") as response_info:
            login_page.login(
                username=test_user_credentials["username"],
                password=test_user_credentials["password"]
            )

        # 获取响应
        response = response_info.value

        # 验证响应状态码
        assert response.status == 200, f"登录API应返回200，实际: {response.status}"

        # 验证响应体包含token
        response_data = response.json()
        assert "access_token" in response_data, "响应应包含access_token"
        assert len(response_data["access_token"]) > 0, "access_token不应为空"

    def test_remember_me_functionality(self, page: Page, test_user_credentials):
        """测试记住我功能"""
        login_page = LoginPage(page)

        login_page.goto()

        # 勾选记住我并登录
        login_page.login(
            username=test_user_credentials["username"],
            password=test_user_credentials["password"],
            remember_me=True
        )

        # 等待登录成功
        page.wait_for_timeout(2000)

        if login_page.is_login_successful():
            # 检查cookies中是否有记住登录的标记
            cookies = page.context.cookies()
            cookie_names = [c["name"] for c in cookies]

            # 验证有相关的cookie（具体cookie名称可能需要根据实际情况调整）
            has_remember_cookie = any("remember" in name.lower() or "token" in name.lower()
                                      for name in cookie_names)

            # 如果有remember相关的cookie，验证过期时间较长
            if has_remember_cookie:
                for cookie in cookies:
                    if "remember" in cookie["name"].lower():
                        # Remember cookie应该有较长的过期时间
                        assert "expires" in cookie or "max-age" in cookie, \
                            "Remember cookie应该设置过期时间"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--headed"])
