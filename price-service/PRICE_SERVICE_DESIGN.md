# 价格订阅服务 (Price Service)

## 服务架构

```
Price Service
├── WebSocket Collectors (多交易所)
│   ├── BinanceCollector
│   ├── OKXCollector
│   └── BybitCollector
├── Data Processors
│   ├── TickerProcessor (实时价格)
│   ├── KlineProcessor (K线数据)
│   └── DataValidator (数据验证)
├── Storage Layer
│   ├── DatabaseWriter (批量写入)
│   ├── RedisCache (实时缓存)
│   └── DataAggregator (数据聚合)
└── API Layer
    ├── Real-time API (实时数据查询)
    ├── Historical API (历史数据查询)
    └── Sync API (数据同步接口)
```

## 核心组件设计

### 1. 交易所数据收集器基类

```python
# price-service/collectors/base.py
import asyncio
import json
import websockets
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Callable
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class BaseExchangeCollector(ABC):
    """交易所数据收集器基类"""

    def __init__(self, exchange_name: str, config: Dict):
        self.exchange_name = exchange_name
        self.config = config
        self.ws_url = config.get('websocket_url')
        self.subscribed_symbols = set()
        self.websocket = None
        self.running = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10

        # 回调函数
        self.on_ticker = None
        self.on_kline = None
        self.on_error = None

    async def start(self, symbols: List[str]):
        """启动数据收集"""
        self.subscribed_symbols = set(symbols)
        self.running = True

        while self.running:
            try:
                await self._connect_and_subscribe()
                await self._listen_messages()
            except Exception as e:
                logger.error(f"{self.exchange_name} collector error: {e}")
                if self.reconnect_attempts < self.max_reconnect_attempts:
                    self.reconnect_attempts += 1
                    wait_time = min(60, 5 * self.reconnect_attempts)
                    logger.info(f"Reconnecting in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error("Max reconnection attempts reached")
                    break

    async def stop(self):
        """停止数据收集"""
        self.running = False
        if self.websocket:
            await self.websocket.close()

    async def _connect_and_subscribe(self):
        """连接WebSocket并订阅数据"""
        self.websocket = await websockets.connect(self.ws_url)
        logger.info(f"Connected to {self.exchange_name} WebSocket")

        # 订阅数据流
        subscribe_message = self._build_subscribe_message(self.subscribed_symbols)
        await self.websocket.send(json.dumps(subscribe_message))
        logger.info(f"Subscribed to {len(self.subscribed_symbols)} symbols")

    async def _listen_messages(self):
        """监听WebSocket消息"""
        async for message in self.websocket:
            try:
                data = json.loads(message)
                await self._process_message(data)
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                if self.on_error:
                    await self.on_error(e, message)

    @abstractmethod
    def _build_subscribe_message(self, symbols: List[str]) -> Dict:
        """构建订阅消息（各交易所实现不同）"""
        pass

    @abstractmethod
    async def _process_message(self, data: Dict):
        """处理接收到的消息（各交易所实现不同）"""
        pass

    def set_callbacks(self, on_ticker: Callable = None, on_kline: Callable = None, on_error: Callable = None):
        """设置回调函数"""
        self.on_ticker = on_ticker
        self.on_kline = on_kline
        self.on_error = on_error
```

### 2. Binance数据收集器

```python
# price-service/collectors/binance.py
from .base import BaseExchangeCollector
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class BinanceCollector(BaseExchangeCollector):
    """Binance数据收集器"""

    def _build_subscribe_message(self, symbols: List[str]) -> Dict:
        """构建Binance订阅消息"""
        # 订阅ticker和kline数据
        streams = []
        for symbol in symbols:
            symbol_lower = symbol.lower()
            streams.extend([
                f"{symbol_lower}@ticker",      # 24小时统计
                f"{symbol_lower}@kline_1m",    # 1分钟K线
                f"{symbol_lower}@kline_5m",    # 5分钟K线
                f"{symbol_lower}@kline_1h",    # 1小时K线
                f"{symbol_lower}@kline_1d",    # 日K线
            ])

        return {
            "method": "SUBSCRIBE",
            "params": streams,
            "id": 1
        }

    async def _process_message(self, data: Dict):
        """处理Binance WebSocket消息"""
        if 'stream' not in data or 'data' not in data:
            return

        stream = data['stream']
        msg_data = data['data']

        if '@ticker' in stream:
            await self._process_ticker(msg_data)
        elif '@kline_' in stream:
            await self._process_kline(msg_data, stream)

    async def _process_ticker(self, data: Dict):
        """处理ticker数据"""
        ticker_data = {
            'exchange': self.exchange_name,
            'symbol': data['s'],
            'price': float(data['c']),
            'bid_price': float(data['b']),
            'ask_price': float(data['a']),
            'volume_24h': float(data['v']),
            'price_change_24h': float(data['P']),
            'price_change_percent_24h': float(data['p']),
            'high_24h': float(data['h']),
            'low_24h': float(data['l']),
            'timestamp': datetime.fromtimestamp(data['E'] / 1000)
        }

        if self.on_ticker:
            await self.on_ticker(ticker_data)

    async def _process_kline(self, data: Dict, stream: str):
        """处理K线数据"""
        kline_info = data['k']

        # 只处理已完成的K线
        if not kline_info['x']:
            return

        # 从stream中提取时间周期
        timeframe = stream.split('@kline_')[1]

        kline_data = {
            'exchange': self.exchange_name,
            'symbol': kline_info['s'],
            'timeframe': timeframe,
            'open_time': datetime.fromtimestamp(kline_info['t'] / 1000),
            'close_time': datetime.fromtimestamp(kline_info['T'] / 1000),
            'open_price': float(kline_info['o']),
            'high_price': float(kline_info['h']),
            'low_price': float(kline_info['l']),
            'close_price': float(kline_info['c']),
            'volume': float(kline_info['v']),
            'quote_volume': float(kline_info['q']),
            'trade_count': int(kline_info['n']),
            'taker_buy_volume': float(kline_info['V']),
            'taker_buy_quote_volume': float(kline_info['Q'])
        }

        if self.on_kline:
            await self.on_kline(kline_data)
```

### 3. 数据处理和存储管理器

```python
# price-service/processors/data_manager.py
import asyncio
import logging
from typing import Dict, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import redis.asyncio as redis

from ..models import TradingPair, PriceTicker, Kline
from ..database import get_async_session

logger = logging.getLogger(__name__)

class PriceDataManager:
    """价格数据管理器"""

    def __init__(self, redis_url: str, batch_size: int = 100):
        self.redis = redis.from_url(redis_url)
        self.batch_size = batch_size

        # 批量写入缓存
        self.ticker_buffer = []
        self.kline_buffer = []

        # 定时任务
        self.flush_task = None
        self.running = False

    async def start(self):
        """启动数据管理器"""
        self.running = True
        self.flush_task = asyncio.create_task(self._flush_loop())
        logger.info("Price data manager started")

    async def stop(self):
        """停止数据管理器"""
        self.running = False
        if self.flush_task:
            self.flush_task.cancel()

        # 刷新剩余数据
        await self._flush_all_buffers()
        await self.redis.close()
        logger.info("Price data manager stopped")

    async def process_ticker(self, ticker_data: Dict):
        """处理ticker数据"""
        # 1. 立即缓存到Redis
        await self._cache_ticker(ticker_data)

        # 2. 加入批量写入队列
        self.ticker_buffer.append(ticker_data)

        # 3. 检查是否需要立即刷新
        if len(self.ticker_buffer) >= self.batch_size:
            await self._flush_ticker_buffer()

    async def process_kline(self, kline_data: Dict):
        """处理K线数据"""
        # 1. 缓存到Redis
        await self._cache_kline(kline_data)

        # 2. 加入批量写入队列
        self.kline_buffer.append(kline_data)

        # 3. 检查是否需要立即刷新
        if len(self.kline_buffer) >= self.batch_size:
            await self._flush_kline_buffer()

    async def _cache_ticker(self, ticker_data: Dict):
        """缓存ticker数据到Redis"""
        key = f"ticker:{ticker_data['exchange']}:{ticker_data['symbol']}"
        value = {
            'price': ticker_data['price'],
            'bid': ticker_data['bid_price'],
            'ask': ticker_data['ask_price'],
            'volume_24h': ticker_data['volume_24h'],
            'change_24h': ticker_data['price_change_percent_24h'],
            'high_24h': ticker_data['high_24h'],
            'low_24h': ticker_data['low_24h'],
            'timestamp': ticker_data['timestamp'].isoformat()
        }

        await self.redis.hset(key, mapping=value)
        await self.redis.expire(key, 300)  # 5分钟过期

    async def _cache_kline(self, kline_data: Dict):
        """缓存K线数据到Redis"""
        key = f"kline:{kline_data['exchange']}:{kline_data['symbol']}:{kline_data['timeframe']}"
        value = {
            'open': kline_data['open_price'],
            'high': kline_data['high_price'],
            'low': kline_data['low_price'],
            'close': kline_data['close_price'],
            'volume': kline_data['volume'],
            'open_time': kline_data['open_time'].isoformat(),
            'close_time': kline_data['close_time'].isoformat()
        }

        await self.redis.hset(key, mapping=value)
        await self.redis.expire(key, 3600)  # 1小时过期

    async def _flush_loop(self):
        """定时刷新缓冲区"""
        while self.running:
            try:
                await asyncio.sleep(10)  # 每10秒刷新一次
                await self._flush_all_buffers()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in flush loop: {e}")

    async def _flush_all_buffers(self):
        """刷新所有缓冲区"""
        await asyncio.gather(
            self._flush_ticker_buffer(),
            self._flush_kline_buffer(),
            return_exceptions=True
        )

    async def _flush_ticker_buffer(self):
        """批量写入ticker数据"""
        if not self.ticker_buffer:
            return

        try:
            async with get_async_session() as session:
                # 批量插入ticker数据
                ticker_objects = []
                for data in self.ticker_buffer:
                    # 查找trading_pair_id
                    trading_pair = await self._get_trading_pair(
                        session, data['exchange'], data['symbol']
                    )
                    if trading_pair:
                        ticker_objects.append(PriceTicker(
                            trading_pair_id=trading_pair.id,
                            price=data['price'],
                            bid_price=data['bid_price'],
                            ask_price=data['ask_price'],
                            volume_24h=data['volume_24h'],
                            price_change_24h=data['price_change_24h'],
                            price_change_percent_24h=data['price_change_percent_24h'],
                            high_24h=data['high_24h'],
                            low_24h=data['low_24h'],
                            timestamp=data['timestamp']
                        ))

                if ticker_objects:
                    session.add_all(ticker_objects)
                    await session.commit()
                    logger.info(f"Flushed {len(ticker_objects)} ticker records")

            self.ticker_buffer.clear()

        except Exception as e:
            logger.error(f"Error flushing ticker buffer: {e}")

    async def _flush_kline_buffer(self):
        """批量写入K线数据"""
        if not self.kline_buffer:
            return

        try:
            async with get_async_session() as session:
                kline_objects = []
                for data in self.kline_buffer:
                    trading_pair = await self._get_trading_pair(
                        session, data['exchange'], data['symbol']
                    )
                    if trading_pair:
                        kline_objects.append(Kline(
                            trading_pair_id=trading_pair.id,
                            timeframe=data['timeframe'],
                            open_time=data['open_time'],
                            close_time=data['close_time'],
                            open_price=data['open_price'],
                            high_price=data['high_price'],
                            low_price=data['low_price'],
                            close_price=data['close_price'],
                            volume=data['volume'],
                            quote_volume=data['quote_volume'],
                            trade_count=data['trade_count'],
                            taker_buy_volume=data['taker_buy_volume'],
                            taker_buy_quote_volume=data['taker_buy_quote_volume']
                        ))

                if kline_objects:
                    # 使用ON CONFLICT处理重复数据
                    for kline in kline_objects:
                        await session.merge(kline)
                    await session.commit()
                    logger.info(f"Flushed {len(kline_objects)} kline records")

            self.kline_buffer.clear()

        except Exception as e:
            logger.error(f"Error flushing kline buffer: {e}")

    async def _get_trading_pair(self, session: AsyncSession, exchange: str, symbol: str):
        """获取交易对信息"""
        result = await session.execute(
            select(TradingPair)
            .join(TradingPair.exchange)
            .where(and_(
                TradingPair.symbol == symbol,
                Exchange.name == exchange
            ))
        )
        return result.scalar_one_or_none()
```

### 4. 主服务协调器

```python
# price-service/main.py
import asyncio
import logging
import signal
from typing import Dict, List
from contextlib import asynccontextmanager

from .collectors.binance import BinanceCollector
from .collectors.okx import OKXCollector
from .collectors.bybit import BybitCollector
from .processors.data_manager import PriceDataManager
from .config import settings

logger = logging.getLogger(__name__)

class PriceService:
    """价格订阅服务主协调器"""

    def __init__(self):
        self.collectors = {}
        self.data_manager = None
        self.running = False

    async def start(self):
        """启动价格服务"""
        logger.info("Starting Price Service...")

        # 1. 启动数据管理器
        self.data_manager = PriceDataManager(
            redis_url=settings.REDIS_URL,
            batch_size=settings.BATCH_SIZE
        )
        await self.data_manager.start()

        # 2. 初始化收集器
        await self._init_collectors()

        # 3. 启动所有收集器
        collector_tasks = []
        for name, collector in self.collectors.items():
            task = asyncio.create_task(
                collector.start(settings.MONITORED_SYMBOLS)
            )
            collector_tasks.append(task)

        logger.info(f"Started {len(self.collectors)} collectors")

        # 4. 等待所有任务完成
        try:
            await asyncio.gather(*collector_tasks)
        except asyncio.CancelledError:
            logger.info("Price service shutting down...")
        finally:
            await self.stop()

    async def stop(self):
        """停止价格服务"""
        logger.info("Stopping Price Service...")

        # 停止所有收集器
        stop_tasks = []
        for collector in self.collectors.values():
            stop_tasks.append(collector.stop())

        if stop_tasks:
            await asyncio.gather(*stop_tasks, return_exceptions=True)

        # 停止数据管理器
        if self.data_manager:
            await self.data_manager.stop()

        logger.info("Price Service stopped")

    async def _init_collectors(self):
        """初始化数据收集器"""
        # Binance收集器
        if settings.ENABLE_BINANCE:
            binance_collector = BinanceCollector(
                exchange_name='binance',
                config=settings.BINANCE_CONFIG
            )
            binance_collector.set_callbacks(
                on_ticker=self.data_manager.process_ticker,
                on_kline=self.data_manager.process_kline,
                on_error=self._handle_collector_error
            )
            self.collectors['binance'] = binance_collector

        # OKX收集器
        if settings.ENABLE_OKX:
            okx_collector = OKXCollector(
                exchange_name='okx',
                config=settings.OKX_CONFIG
            )
            okx_collector.set_callbacks(
                on_ticker=self.data_manager.process_ticker,
                on_kline=self.data_manager.process_kline,
                on_error=self._handle_collector_error
            )
            self.collectors['okx'] = okx_collector

    async def _handle_collector_error(self, error: Exception, message: str = None):
        """处理收集器错误"""
        logger.error(f"Collector error: {error}")
        if message:
            logger.debug(f"Error message: {message}")

# 全局服务实例
price_service = PriceService()

@asynccontextmanager
async def lifespan(app):
    """FastAPI应用生命周期管理"""
    # 启动
    asyncio.create_task(price_service.start())
    yield
    # 关闭
    await price_service.stop()

# 信号处理
def signal_handler(signum, frame):
    logger.info(f"Received signal {signum}")
    asyncio.create_task(price_service.stop())

if __name__ == "__main__":
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 运行服务
    asyncio.run(price_service.start())
```

### 5. 配置文件

```python
# price-service/config.py
from pydantic_settings import BaseSettings
from typing import List, Dict

class Settings(BaseSettings):
    # 数据库配置
    DATABASE_URL: str
    REDIS_URL: str = "redis://redis:6379/0"

    # 服务配置
    BATCH_SIZE: int = 100
    FLUSH_INTERVAL: int = 10  # 秒

    # 交易所配置
    ENABLE_BINANCE: bool = True
    ENABLE_OKX: bool = True
    ENABLE_BYBIT: bool = False

    # 监控的交易对
    MONITORED_SYMBOLS: List[str] = [
        "BTCUSDT", "ETHUSDT", "ADAUSDT", "DOTUSDT", "LINKUSDT"
    ]

    # 交易所WebSocket配置
    BINANCE_CONFIG: Dict = {
        "websocket_url": "wss://stream.binance.com:9443/ws",
        "rate_limit": 1200
    }

    OKX_CONFIG: Dict = {
        "websocket_url": "wss://ws.okx.com:8443/ws/v5/public",
        "rate_limit": 600
    }

    BYBIT_CONFIG: Dict = {
        "websocket_url": "wss://stream.bybit.com/v5/public/spot",
        "rate_limit": 600
    }

    # 日志配置
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"

settings = Settings()
```

这个价格订阅服务设计具有以下特点：

1. **高性能**: 异步WebSocket + 批量写入 + Redis缓存
2. **高可靠**: 自动重连 + 错误处理 + 数据验证
3. **可扩展**: 插件式交易所支持 + 模块化设计
4. **资源友好**: 批量处理减少数据库压力
5. **监控友好**: 详细的日志和错误处理

接下来我将设计历史数据同步功能。