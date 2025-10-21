#!/usr/bin/env python
"""
Script to add proxy configuration to database
"""
import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from models.proxy import Proxy
from config import settings

async def add_proxy():
    """Add proxy to database"""
    # Convert DATABASE_URL to use asyncpg driver
    database_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

    # Create async engine
    engine = create_async_engine(
        database_url,
        echo=False
    )

    # Create async session
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        # Check if proxy already exists
        result = await session.execute(
            select(Proxy).where(Proxy.host == "127.0.0.1").where(Proxy.port == 10808)
        )
        existing_proxy = result.scalar_one_or_none()

        if existing_proxy:
            print(f"Proxy already exists: {existing_proxy}")
            print("Updating proxy status...")
            existing_proxy.is_active = True
            existing_proxy.is_healthy = True
            existing_proxy.priority = 1
            await session.commit()
            print("✅ Proxy updated successfully!")
            return

        # Create new proxy
        proxy = Proxy(
            name="Local HTTP Proxy",
            proxy_type="http",
            host="127.0.0.1",
            port=10808,
            priority=1,
            is_active=True,
            is_healthy=True,
            health_check_url="https://api.binance.com/api/v3/ping",
            max_consecutive_failures=3,
            health_check_interval=3600
        )

        session.add(proxy)
        await session.commit()
        await session.refresh(proxy)

        print(f"✅ Proxy added successfully!")
        print(f"   ID: {proxy.id}")
        print(f"   Name: {proxy.name}")
        print(f"   URL: http://{proxy.host}:{proxy.port}")
        print(f"   Type: {proxy.proxy_type}")
        print(f"   Priority: {proxy.priority}")
        print(f"   Status: Active={proxy.is_active}, Healthy={proxy.is_healthy}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(add_proxy())
