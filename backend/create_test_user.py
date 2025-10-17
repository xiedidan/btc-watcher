"""
创建E2E测试用户
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
from database.session import Base
from models.user import User
from config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_test_user():
    """创建测试用户"""
    # Transform DATABASE_URL for async operation
    database_url = settings.DATABASE_URL
    if "postgresql://" in database_url:
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
    elif "sqlite://" in database_url:
        database_url = database_url.replace("sqlite://", "sqlite+aiosqlite://")

    engine = create_async_engine(database_url, echo=True)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # 检查用户是否已存在
        from sqlalchemy import select
        result = await session.execute(
            select(User).where(User.username == "testuser")
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            print("Test user already exists")
            return
        
        # 创建新用户
        hashed_password = pwd_context.hash("testpass123")
        test_user = User(
            username="testuser",
            email="testuser@example.com",
            hashed_password=hashed_password,
            is_active=True
        )
        
        session.add(test_user)
        await session.commit()
        print("Test user created successfully")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(create_test_user())
