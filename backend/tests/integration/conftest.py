"""
Integration Test Configuration
集成测试配置
"""
import sys
import os
from pathlib import Path
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from httpx import AsyncClient
from fastapi.testclient import TestClient

# 添加backend目录到Python路径
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

# 集成测试环境变量（使用真实的测试数据库）
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///./test_integration.db'
os.environ['REDIS_URL'] = 'redis://localhost:6379/15'
os.environ['SECRET_KEY'] = 'integration_test_secret_key_do_not_use_in_production'
os.environ['JWT_SECRET_KEY'] = 'integration_test_jwt_secret_key'
os.environ['TESTING'] = 'true'

from main import app
from database.session import Base, engine
from database import get_db


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_db():
    """创建测试数据库"""
    # 创建所有表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield

    # 清理
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def db_session(test_db) -> AsyncGenerator[AsyncSession, None]:
    """创建数据库会话"""
    from database.session import SessionLocal

    async with SessionLocal() as session:
        yield session


@pytest.fixture(scope="function")
def client(test_db) -> Generator:
    """创建测试客户端"""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="function")
async def async_client(test_db) -> AsyncGenerator:
    """创建异步测试客户端"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def test_user(db_session):
    """创建测试用户"""
    from models.user import User
    import bcrypt

    password = b"testpass123"
    hashed = bcrypt.hashpw(password, bcrypt.gensalt()).decode('utf-8')

    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=hashed,
        is_active=True,
        is_superuser=False
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # 返回用户和明文密码
    return {"user": user, "password": "testpass123"}


@pytest.fixture
async def admin_user(db_session):
    """创建管理员用户"""
    from models.user import User
    import bcrypt

    password = b"adminpass123"
    hashed = bcrypt.hashpw(password, bcrypt.gensalt()).decode('utf-8')

    user = User(
        username="admin",
        email="admin@example.com",
        hashed_password=hashed,
        is_active=True,
        is_superuser=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return {"user": user, "password": "adminpass123"}


@pytest.fixture
async def auth_headers(client, test_user):
    """获取认证headers"""
    # 登录获取token
    response = client.post(
        "/api/v1/auth/token",
        data={
            "username": test_user["user"].username,
            "password": test_user["password"]
        }
    )

    if response.status_code == 200:
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return {}


@pytest.fixture
async def test_strategy(db_session, test_user):
    """创建测试策略"""
    from models.strategy import Strategy

    strategy = Strategy(
        user_id=test_user["user"].id,
        name="Integration Test Strategy",
        strategy_class="SampleStrategy",
        exchange="binance",
        timeframe="1h",
        pair_whitelist=["BTC/USDT", "ETH/USDT"],
        pair_blacklist=[],
        dry_run=True,
        dry_run_wallet=1000.0,
        max_open_trades=3,
        status="stopped",
        signal_thresholds={"strong": 0.8, "medium": 0.6, "weak": 0.4}
    )
    db_session.add(strategy)
    await db_session.commit()
    await db_session.refresh(strategy)

    return strategy


# 清理测试数据库文件
def pytest_sessionfinish(session, exitstatus):
    """测试会话结束后清理"""
    test_db_file = Path("./test_integration.db")
    if test_db_file.exists():
        try:
            test_db_file.unlink()
        except:
            pass
