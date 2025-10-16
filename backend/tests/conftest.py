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
    import bcrypt

    # 使用短密码并直接使用bcrypt（避免passlib版本兼容问题）
    password = b"test123"
    hashed = bcrypt.hashpw(password, bcrypt.gensalt()).decode('utf-8')

    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=hashed,
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
    manager.max_strategies = 1000

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

@pytest.fixture(autouse=True, scope="session")
def setup_api_dependencies():
    """Setup API dependencies for tests"""
    from unittest.mock import Mock
    from api.v1 import system, strategies, monitoring, notifications
    from core.freqtrade_manager import FreqTradeGatewayManager

    # Create mock manager
    mock_manager = Mock(spec=FreqTradeGatewayManager)
    mock_manager.get_capacity_info.return_value = {
        "max_strategies": 1000,
        "running_strategies": 0,
        "available_slots": 1000,
        "utilization_percent": 0.0,
        "port_range": "8081-9080",
        "can_start_more": True,
        "architecture": "multi_instance_reverse_proxy"
    }
    mock_manager.get_port_pool_status.return_value = {
        "total_ports": 1000,
        "available_ports": 1000,
        "allocated_ports": 0,
        "running_strategies": 0,
        "port_range": "8081-9080",
        "max_concurrent": 1000
    }

    # Create mock monitoring service
    mock_monitoring = Mock()
    mock_monitoring.get_health_status.return_value = {
        "status": "healthy",
        "architecture": "multi_instance_reverse_proxy",
        "services": {}
    }
    mock_monitoring.get_system_metrics.return_value = {
        "cpu": {"percent": 10.0},
        "memory": {"percent": 50.0},
        "disk": {"percent": 30.0}
    }

    # Create mock notification service
    mock_notification = Mock()

    # Inject mocks into modules
    system._ft_manager = mock_manager
    system._monitoring_service = mock_monitoring
    strategies._ft_manager = mock_manager
    monitoring._monitoring_service = mock_monitoring
    notifications._notification_service = mock_notification

    yield

    # Cleanup
    system._ft_manager = None
    system._monitoring_service = None
    strategies._ft_manager = None
    monitoring._monitoring_service = None
    notifications._notification_service = None

