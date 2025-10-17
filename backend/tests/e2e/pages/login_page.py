"""
Login Page Object
登录页面对象 - 封装登录页面的元素和操作
"""
from playwright.sync_api import Page, expect
from .base_page import BasePage


class LoginPage(BasePage):
    """登录页面"""

    def __init__(self, page: Page, base_url: str = "http://localhost:3000"):
        super().__init__(page, base_url)

        # 选择器定义 - 适配Element Plus组件
        self.username_input = ".el-input__inner[placeholder='用户名']"
        self.password_input = ".el-input__inner[type='password'][placeholder='密码']"
        self.login_button = "button.el-button:has-text('登录')"
        self.error_message = ".el-message--error, [role='alert']"
        self.success_message = ".el-message--success"
        self.remember_me_checkbox = "input[type='checkbox'][name='rememberMe']"
        self.forgot_password_link = "a:has-text('忘记密码')"
        self.register_link = ".el-tabs__item:has-text('注册')"

    def goto(self):
        """访问登录页"""
        self.navigate("/login")

    def login(self, username: str, password: str, remember_me: bool = False):
        """
        执行登录操作

        Args:
            username: 用户名
            password: 密码
            remember_me: 是否记住登录状态
        """
        # 填写用户名
        self.fill(self.username_input, username)

        # 填写密码
        self.fill(self.password_input, password)

        # 勾选记住我（如果需要）
        if remember_me:
            self.click(self.remember_me_checkbox)

        # 点击登录按钮
        self.click(self.login_button)

    def get_error_message(self) -> str:
        """
        获取错误消息

        Returns:
            错误消息文本
        """
        try:
            return self.get_text(self.error_message, timeout=5000)
        except Exception:
            return ""

    def get_success_message(self) -> str:
        """
        获取成功消息

        Returns:
            成功消息文本
        """
        try:
            return self.get_text(self.success_message, timeout=5000)
        except Exception:
            return ""

    def is_login_successful(self) -> bool:
        """
        验证登录是否成功（通过URL跳转判断）

        Returns:
            True如果登录成功，否则False
        """
        try:
            # 等待离开登录页面
            self.page.wait_for_timeout(3000)
            current_url = self.get_current_url()
            # 登录成功后会跳转到根路径或dashboard
            return "login" not in current_url and (
                current_url.endswith("/") or
                "dashboard" in current_url or
                "home" in current_url
            )
        except Exception as e:
            print(f"Login check exception: {e}")
            return False

    def has_error(self) -> bool:
        """
        检查是否有错误消息

        Returns:
            True如果有错误消息，否则False
        """
        return self.is_visible(self.error_message)

    def click_forgot_password(self):
        """点击忘记密码链接"""
        self.click(self.forgot_password_link)

    def click_register(self):
        """点击注册链接"""
        self.click(self.register_link)

    def wait_for_login_form(self):
        """等待登录表单加载"""
        self.wait_for_selector(self.username_input)
        self.wait_for_selector(self.password_input)
        self.wait_for_selector(self.login_button)

    def is_username_field_visible(self) -> bool:
        """检查用户名输入框是否可见"""
        return self.is_visible(self.username_input)

    def is_password_field_visible(self) -> bool:
        """检查密码输入框是否可见"""
        return self.is_visible(self.password_input)

    def is_login_button_visible(self) -> bool:
        """检查登录按钮是否可见"""
        return self.is_visible(self.login_button)

    def clear_username(self):
        """清空用户名输入框"""
        self.page.fill(self.username_input, "")

    def clear_password(self):
        """清空密码输入框"""
        self.page.fill(self.password_input, "")
