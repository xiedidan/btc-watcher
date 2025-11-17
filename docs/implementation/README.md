# BTC Watcher 项目结构与实现指南

## 项目目录结构

```
btc-watcher/
├── docker-compose.yml          # Docker编排配置
├── docker-compose.prod.yml     # 生产环境配置
├── .env.example               # 环境变量模板
├── README.md                  # 项目说明文档
├── scripts/                   # 部署和管理脚本
│   ├── start.sh              # 启动脚本
│   ├── stop.sh               # 停止脚本
│   ├── backup.sh             # 备份脚本
│   └── restore.sh            # 恢复脚本
├── frontend/                  # Vue.js前端应用
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   ├── vite.config.ts
│   ├── src/
│   │   ├── main.ts
│   │   ├── App.vue
│   │   ├── router/
│   │   ├── stores/
│   │   ├── views/
│   │   ├── components/
│   │   └── utils/
│   └── public/
├── backend/                   # FastAPI后端应用
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── app/
│   │   ├── __init__.py
│   │   ├── core/             # 核心配置
│   │   ├── models/           # 数据库模型
│   │   ├── schemas/          # Pydantic模式
│   │   ├── api/             # API路由
│   │   ├── services/        # 业务逻辑
│   │   ├── utils/           # 工具函数
│   │   └── db/              # 数据库配置
│   ├── alembic/             # 数据库迁移
│   └── tests/               # 测试文件
├── freqtrade/               # FreqTrade策略服务
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── user_data/
│   │   ├── strategies/      # 策略文件
│   │   └── logs/            # 日志文件
│   ├── config/              # 配置文件
│   └── scripts/             # 管理脚本
├── notification/            # 通知服务
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── channels/            # 通知渠道实现
│   └── templates/           # 消息模板
├── nginx/                   # Nginx配置
│   ├── Dockerfile
│   └── nginx.conf
└── data/                    # 持久化数据目录
    ├── postgres/            # PostgreSQL数据
    ├── redis/               # Redis数据
    └── logs/                # 日志文件
```

## 核心模块设计

### 1. 后端API模块

#### 1.1 应用初始化 (main.py)
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from app.core.config import settings
from app.api.main import api_router
from app.db.database import engine
from app.models import Base

# 创建数据表
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="BTC Watcher API",
    description="Cryptocurrency monitoring and alerting system",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# 中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 路由注册
app.include_router(api_router, prefix=settings.API_V1_STR)
```

#### 1.2 配置管理 (app/core/config.py)
```python
from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    # API配置
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8天

    # 数据库配置
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: Optional[str] = None

    # Redis配置
    REDIS_URL: str = "redis://redis:6379/0"

    # CORS配置
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # FreqTrade配置
    FREQTRADE_CONFIG_DIR: str = "/app/freqtrade/config"
    FREQTRADE_SIGNALS_DIR: str = "/app/signals"

    # 通知服务配置
    NOTIFICATION_SERVICE_URL: str = "http://notification:8001"

    @property
    def database_url(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"

    class Config:
        env_file = ".env"

settings = Settings()
```

#### 1.3 数据库模型 (app/models/)
```python
# app/models/currency_pair.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.db.base_class import Base

class CurrencyPair(Base):
    __tablename__ = "currency_pairs"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), unique=True, index=True, nullable=False)
    exchange = Column(String(20), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# app/models/strategy.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON
from app.db.base_class import Base

class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    config_json = Column(JSON, nullable=False)
    status = Column(String(20), default="stopped")  # running, stopped, error
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

#### 1.4 API路由 (app/api/)
```python
# app/api/endpoints/strategies.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app import schemas, models, services
from app.db.database import get_db

router = APIRouter()

@router.get("/", response_model=List[schemas.Strategy])
def read_strategies(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """获取策略列表"""
    strategies = services.strategy.get_multi(db, skip=skip, limit=limit)
    return strategies

@router.post("/", response_model=schemas.Strategy)
def create_strategy(
    strategy_in: schemas.StrategyCreate,
    db: Session = Depends(get_db)
):
    """创建新策略"""
    strategy = services.strategy.create(db, obj_in=strategy_in)
    return strategy

@router.post("/{strategy_id}/start")
async def start_strategy(
    strategy_id: int,
    db: Session = Depends(get_db)
):
    """启动策略"""
    strategy = services.strategy.get(db, id=strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    success = await services.freqtrade.start_strategy(strategy)
    if success:
        services.strategy.update(db, db_obj=strategy, obj_in={"status": "running"})
        return {"status": "started"}
    else:
        raise HTTPException(status_code=500, detail="Failed to start strategy")
```

### 2. 前端应用模块

#### 2.1 路由配置 (src/router/index.ts)
```typescript
import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '@/views/Dashboard.vue'
import Strategies from '@/views/Strategies.vue'
import CurrencyPairs from '@/views/CurrencyPairs.vue'
import Charts from '@/views/Charts.vue'
import Notifications from '@/views/Notifications.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: Dashboard
    },
    {
      path: '/strategies',
      name: 'strategies',
      component: Strategies
    },
    {
      path: '/pairs',
      name: 'currency-pairs',
      component: CurrencyPairs
    },
    {
      path: '/charts/:symbol?',
      name: 'charts',
      component: Charts,
      props: true
    },
    {
      path: '/notifications',
      name: 'notifications',
      component: Notifications
    }
  ]
})

export default router
```

#### 2.2 状态管理 (src/stores/)
```typescript
// src/stores/strategy.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { strategyApi } from '@/api/strategy'

export const useStrategyStore = defineStore('strategy', () => {
  const strategies = ref<Strategy[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const activeStrategies = computed(() =>
    strategies.value.filter(s => s.status === 'running')
  )

  const fetchStrategies = async () => {
    loading.value = true
    try {
      strategies.value = await strategyApi.getStrategies()
    } catch (err) {
      error.value = '获取策略列表失败'
    } finally {
      loading.value = false
    }
  }

  const startStrategy = async (id: number) => {
    try {
      await strategyApi.startStrategy(id)
      await fetchStrategies()
    } catch (err) {
      throw new Error('启动策略失败')
    }
  }

  return {
    strategies,
    loading,
    error,
    activeStrategies,
    fetchStrategies,
    startStrategy
  }
})
```

#### 2.3 图表组件 (src/components/Chart.vue)
```vue
<template>
  <div class="chart-container">
    <div ref="chartContainer" class="chart"></div>
    <div class="chart-controls">
      <el-select v-model="selectedTimeframe" @change="updateChart">
        <el-option label="1分钟" value="1m" />
        <el-option label="5分钟" value="5m" />
        <el-option label="15分钟" value="15m" />
        <el-option label="1小时" value="1h" />
        <el-option label="4小时" value="4h" />
        <el-option label="1天" value="1d" />
      </el-select>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { createChart, IChartApi } from 'lightweight-charts'
import { marketApi } from '@/api/market'

interface Props {
  symbol: string
}

const props = defineProps<Props>()
const chartContainer = ref<HTMLDivElement>()
const selectedTimeframe = ref('1h')
let chart: IChartApi | null = null

const initChart = () => {
  if (!chartContainer.value) return

  chart = createChart(chartContainer.value, {
    width: chartContainer.value.clientWidth,
    height: 400,
    layout: {
      backgroundColor: '#ffffff',
      textColor: '#333',
    },
    grid: {
      vertLines: { color: '#ebebeb' },
      horzLines: { color: '#ebebeb' },
    },
  })

  const candlestickSeries = chart.addCandlestickSeries()
  loadChartData(candlestickSeries)
}

const loadChartData = async (series: any) => {
  try {
    const klines = await marketApi.getKlines(props.symbol, selectedTimeframe.value)
    const data = klines.map(k => ({
      time: k.timestamp / 1000,
      open: k.open,
      high: k.high,
      low: k.low,
      close: k.close,
    }))
    series.setData(data)
  } catch (error) {
    console.error('加载图表数据失败:', error)
  }
}

onMounted(() => {
  initChart()
})

onUnmounted(() => {
  if (chart) {
    chart.remove()
  }
})

watch(() => props.symbol, () => {
  if (chart) {
    chart.remove()
    initChart()
  }
})
</script>
```

### 3. FreqTrade策略模块

#### 3.1 策略基类 (user_data/strategies/base_strategy.py)
```python
from freqtrade.strategy import IStrategy, DecimalParameter, IntParameter
from pandas import DataFrame
import json
import os
from datetime import datetime

class BaseMonitorStrategy(IStrategy):
    """监控策略基类"""

    # 策略配置
    timeframe = '5m'
    can_short = False
    startup_candle_count = 30

    # 信号输出配置
    signal_file_path = '/app/signals/signals.json'

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self.strategy_name = self.__class__.__name__

    def emit_signal(self, signal_type: str, pair: str, rate: float, metadata: dict = None):
        """发出交易信号"""
        signal = {
            'timestamp': datetime.utcnow().isoformat(),
            'strategy': self.strategy_name,
            'pair': pair,
            'signal_type': signal_type,  # 'buy', 'sell', 'stop_loss'
            'price': rate,
            'metadata': metadata or {}
        }

        # 追加写入信号文件
        os.makedirs(os.path.dirname(self.signal_file_path), exist_ok=True)
        with open(self.signal_file_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(signal) + '\n')

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """买入信号逻辑"""
        conditions = self.get_buy_conditions(dataframe, metadata)

        if len(conditions) > 0:
            dataframe.loc[
                reduce(lambda x, y: x & y, conditions),
                'buy'
            ] = 1

            # 发出买入信号
            if dataframe['buy'].iloc[-1] == 1:
                self.emit_signal(
                    'buy',
                    metadata['pair'],
                    dataframe['close'].iloc[-1],
                    self.get_signal_metadata(dataframe, metadata)
                )

        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """卖出信号逻辑"""
        conditions = self.get_sell_conditions(dataframe, metadata)

        if len(conditions) > 0:
            dataframe.loc[
                reduce(lambda x, y: x & y, conditions),
                'sell'
            ] = 1

            # 发出卖出信号
            if dataframe['sell'].iloc[-1] == 1:
                self.emit_signal(
                    'sell',
                    metadata['pair'],
                    dataframe['close'].iloc[-1],
                    self.get_signal_metadata(dataframe, metadata)
                )

        return dataframe

    def get_buy_conditions(self, dataframe: DataFrame, metadata: dict) -> list:
        """子类实现具体的买入条件"""
        raise NotImplementedError

    def get_sell_conditions(self, dataframe: DataFrame, metadata: dict) -> list:
        """子类实现具体的卖出条件"""
        raise NotImplementedError

    def get_signal_metadata(self, dataframe: DataFrame, metadata: dict) -> dict:
        """获取信号元数据"""
        return {
            'rsi': dataframe['rsi'].iloc[-1] if 'rsi' in dataframe else None,
            'macd': dataframe['macd'].iloc[-1] if 'macd' in dataframe else None,
        }
```

### 4. 通知服务模块

#### 4.1 通知渠道实现 (channels/)
```python
# channels/telegram.py
import aiohttp
import asyncio
from typing import Dict, Any
from .base import NotificationChannel

class TelegramChannel(NotificationChannel):
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

    async def send(self, message: str, metadata: Dict[str, Any] = None) -> bool:
        url = f"{self.base_url}/sendMessage"
        data = {
            'chat_id': self.chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=data) as response:
                    return response.status == 200
            except Exception as e:
                print(f"Telegram发送失败: {e}")
                return False

# channels/wechat.py
class WeChatChannel(NotificationChannel):
    def __init__(self, corp_id: str, agent_id: str, secret: str):
        self.corp_id = corp_id
        self.agent_id = agent_id
        self.secret = secret
        self.access_token = None

    async def get_access_token(self):
        """获取企业微信access_token"""
        url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken"
        params = {
            'corpid': self.corp_id,
            'corpsecret': self.secret
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()
                return data.get('access_token')

    async def send(self, message: str, metadata: Dict[str, Any] = None) -> bool:
        if not self.access_token:
            self.access_token = await self.get_access_token()

        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={self.access_token}"
        data = {
            'touser': '@all',
            'msgtype': 'text',
            'agentid': self.agent_id,
            'text': {
                'content': message
            }
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=data) as response:
                    result = await response.json()
                    return result.get('errcode') == 0
            except Exception as e:
                print(f"微信发送失败: {e}")
                return False
```

这个实现指南提供了详细的项目结构和核心模块的代码示例。接下来我将创建Docker部署配置文件。