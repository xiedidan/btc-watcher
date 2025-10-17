"""
Security Tests Configuration
安全测试配置
"""
import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import integration test fixtures
from integration.conftest import *  # noqa: F401, F403
