#!/usr/bin/env python
"""
Test script to verify proxy configuration for K-line data fetching
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from services.ccxt_manager import CCXTManager
from config import settings

async def test_proxy_kline():
    """Test K-line data fetching with proxy"""
    # Setup database session
    database_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Create CCXT manager
        ccxt_manager = CCXTManager(session)

        print("=" * 60)
        print("Testing K-line Data Fetching with Proxy")
        print("=" * 60)

        try:
            # Initialize exchange with proxy
            print("\n1. Initializing Binance exchange with proxy...")
            exchange = await ccxt_manager.initialize_exchange(
                "binance",
                use_proxy=True
            )
            print(f"   ✅ Exchange initialized: {exchange.id}")

            # Fetch K-line data
            print("\n2. Fetching BTC/USDT 1h K-line data (limit=10)...")
            ohlcv = await ccxt_manager.fetch_ohlcv(
                exchange_name="binance",
                symbol="BTC/USDT",
                timeframe="1h",
                limit=10
            )

            print(f"   ✅ Fetched {len(ohlcv)} candles")
            print("\n   Latest 3 candles:")
            for i, candle in enumerate(ohlcv[-3:]):
                timestamp, open_price, high, low, close, volume = candle
                from datetime import datetime
                dt = datetime.fromtimestamp(timestamp / 1000)
                print(f"   [{i+1}] {dt.strftime('%Y-%m-%d %H:%M')} | "
                      f"O:{open_price:.2f} H:{high:.2f} L:{low:.2f} C:{close:.2f} V:{volume:.2f}")

            # Test ticker
            print("\n3. Fetching BTC/USDT ticker...")
            ticker = await ccxt_manager.fetch_ticker("binance", "BTC/USDT")
            print(f"   ✅ Current price: ${ticker.get('last', 0):.2f}")
            print(f"   📊 24h High: ${ticker.get('high', 0):.2f}")
            print(f"   📊 24h Low: ${ticker.get('low', 0):.2f}")
            print(f"   📊 24h Volume: {ticker.get('quoteVolume', 0):,.0f} USDT")

            # Close connections
            await ccxt_manager.close_all_exchanges()

            print("\n" + "=" * 60)
            print("✅ All tests passed! Proxy is working correctly!")
            print("=" * 60)

        except Exception as e:
            print(f"\n❌ Error: {e}")
            print(f"   Type: {type(e).__name__}")
            import traceback
            traceback.print_exc()

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_proxy_kline())
