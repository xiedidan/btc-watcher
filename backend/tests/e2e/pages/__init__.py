"""
Page Objects
页面对象模型 - 封装页面元素和操作
"""
from .base_page import BasePage
from .login_page import LoginPage
from .dashboard_page import DashboardPage
from .strategy_page import StrategyPage
from .signal_page import SignalPage

__all__ = [
    "BasePage",
    "LoginPage",
    "DashboardPage",
    "StrategyPage",
    "SignalPage",
]
