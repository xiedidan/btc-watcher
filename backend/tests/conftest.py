"""
单元测试配置文件
Unit Test Configuration
"""
import sys
import os
from pathlib import Path

# 添加backend目录到Python路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# 测试环境变量
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'  # 使用内存数据库进行测试
os.environ['REDIS_URL'] = 'redis://localhost:6379/15'  # 使用测试数据库
os.environ['SECRET_KEY'] = 'test_secret_key_for_unit_testing'
os.environ['TESTING'] = 'true'

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# 测试数据库引擎
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="session")
def engine():
    """创建测试数据库引擎"""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    return engine

@pytest.fixture(scope="function")
def db_session(engine):
    """创建数据库会话"""
    from database.session import Base

    # 创建所有表
    Base.metadata.create_all(bind=engine)

    # 创建会话
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    yield session

    # 清理
    session.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def sample_user(db_session):
    """创建测试用户"""
    from models.user import User
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=pwd_context.hash("testpass123"),
        is_active=True,
        is_superuser=False
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return user

@pytest.fixture
def sample_strategy(db_session, sample_user):
    """创建测试策略"""
    from models.strategy import Strategy

    strategy = Strategy(
        user_id=sample_user.id,
        name="Test Strategy",
        strategy_class="SampleStrategy",
        exchange="binance",
        timeframe="1h",
        pair_whitelist=["BTC/USDT"],
        pair_blacklist=[],
        dry_run=True,
        dry_run_wallet=1000.0,
        max_open_trades=3,
        status="stopped",
        signal_thresholds={"strong": 0.8, "medium": 0.6, "weak": 0.4}
    )
    db_session.add(strategy)
    db_session.commit()
    db_session.refresh(strategy)

    return strategy

@pytest.fixture
def mock_freqtrade_manager():
    """Mock FreqTrade管理器"""
    from unittest.mock import Mock

    manager = Mock()
    manager.strategy_processes = {}
    manager.strategy_ports = {}
    manager.port_pool = set(range(8081, 9081))
    manager.base_port = 8081
    manager.max_port = 9080
    manager.max_strategies = 999

    return manager

@pytest.fixture
def temp_freqtrade_paths(tmp_path, monkeypatch):
    """创建临时目录用于FreqTrade测试"""
    # 创建临时目录
    base_config_path = tmp_path / "freqtrade_configs"
    strategies_path = tmp_path / "user_data" / "strategies"
    logs_path = tmp_path / "logs" / "freqtrade"
    gateway_routes_path = tmp_path / "gateway_routes.json"

    base_config_path.mkdir(parents=True, exist_ok=True)
    strategies_path.mkdir(parents=True, exist_ok=True)
    logs_path.mkdir(parents=True, exist_ok=True)

    # Patch Path对象
    def mock_path_init(self, original_init):
        def wrapper(path_str):
            if path_str == "/app/freqtrade_configs":
                return original_init(str(base_config_path))
            elif path_str == "/app/user_data/strategies":
                return original_init(str(strategies_path))
            elif path_str == "/app/logs/freqtrade":
                return original_init(str(logs_path))
            elif path_str == "/app/gateway_routes.json":
                return original_init(str(gateway_routes_path))
            return original_init(path_str)
        return wrapper

    return {
        "base_config_path": base_config_path,
        "strategies_path": strategies_path,
        "logs_path": logs_path,
        "gateway_routes_path": gateway_routes_path
    }
