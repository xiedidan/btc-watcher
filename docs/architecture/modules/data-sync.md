# 历史数据同步系统设计

## 同步架构概览

```
远程价格服务器              本地BTC Watcher
┌─────────────────┐         ┌─────────────────┐
│  Price Service  │────────▶│  Sync Service   │
│  (数据采集)      │ HTTP API │  (数据同步)      │
└─────────────────┘         └─────────────────┘
│                                    │
├─ PostgreSQL                        ├─ PostgreSQL
├─ Redis Cache                       ├─ Redis Cache
└─ REST API                          └─ Sync Manager
```

## 核心功能设计

### 1. 远程数据API接口

```python
# price-service/api/data_export.py
from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import List, Optional
from datetime import datetime, timedelta

from ..models import TradingPair, PriceTicker, Kline
from ..database import get_async_session
from ..schemas import TickerExportResponse, KlineExportResponse

app = FastAPI(title="Price Data Export API")

@app.get("/api/v1/data/tickers/export")
async def export_ticker_data(
    symbol: str = Query(..., description="交易对符号"),
    exchange: str = Query(..., description="交易所名称"),
    start_time: datetime = Query(..., description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    limit: int = Query(1000, le=5000, description="单次返回记录数"),
    offset: int = Query(0, description="偏移量"),
    session: AsyncSession = Depends(get_async_session)
) -> TickerExportResponse:
    """导出ticker历史数据"""

    # 构建查询
    query = (
        select(PriceTicker)
        .join(TradingPair)
        .join(Exchange)
        .where(and_(
            TradingPair.symbol == symbol,
            Exchange.name == exchange,
            PriceTicker.timestamp >= start_time
        ))
    )

    if end_time:
        query = query.where(PriceTicker.timestamp <= end_time)

    # 添加排序和分页
    query = query.order_by(PriceTicker.timestamp).offset(offset).limit(limit)

    # 执行查询
    result = await session.execute(query)
    tickers = result.scalars().all()

    # 获取总数
    count_query = select(func.count(PriceTicker.id)).select_from(
        PriceTicker.join(TradingPair).join(Exchange)
    ).where(and_(
        TradingPair.symbol == symbol,
        Exchange.name == exchange,
        PriceTicker.timestamp >= start_time
    ))
    if end_time:
        count_query = count_query.where(PriceTicker.timestamp <= end_time)

    total_count = await session.scalar(count_query)

    return TickerExportResponse(
        data=tickers,
        total=total_count,
        limit=limit,
        offset=offset,
        has_more=offset + len(tickers) < total_count
    )

@app.get("/api/v1/data/klines/export")
async def export_kline_data(
    symbol: str = Query(...),
    exchange: str = Query(...),
    timeframe: str = Query(..., description="时间周期"),
    start_time: datetime = Query(...),
    end_time: Optional[datetime] = Query(None),
    limit: int = Query(1000, le=10000),
    offset: int = Query(0),
    session: AsyncSession = Depends(get_async_session)
) -> KlineExportResponse:
    """导出K线历史数据"""

    query = (
        select(Kline)
        .join(TradingPair)
        .join(Exchange)
        .where(and_(
            TradingPair.symbol == symbol,
            Exchange.name == exchange,
            Kline.timeframe == timeframe,
            Kline.open_time >= start_time
        ))
    )

    if end_time:
        query = query.where(Kline.open_time <= end_time)

    query = query.order_by(Kline.open_time).offset(offset).limit(limit)

    result = await session.execute(query)
    klines = result.scalars().all()

    # 获取总数
    count_query = select(func.count(Kline.id)).select_from(
        Kline.join(TradingPair).join(Exchange)
    ).where(and_(
        TradingPair.symbol == symbol,
        Exchange.name == exchange,
        Kline.timeframe == timeframe,
        Kline.open_time >= start_time
    ))
    if end_time:
        count_query = count_query.where(Kline.open_time <= end_time)

    total_count = await session.scalar(count_query)

    return KlineExportResponse(
        data=klines,
        total=total_count,
        limit=limit,
        offset=offset,
        has_more=offset + len(klines) < total_count
    )

@app.get("/api/v1/data/sync/status")
async def get_data_sync_status(
    session: AsyncSession = Depends(get_async_session)
):
    """获取数据同步状态"""

    # 获取各个数据表的最新时间戳
    latest_ticker = await session.scalar(
        select(func.max(PriceTicker.timestamp))
    )

    latest_klines = {}
    for timeframe in ['1m', '5m', '1h', '1d']:
        latest_time = await session.scalar(
            select(func.max(Kline.open_time))
            .where(Kline.timeframe == timeframe)
        )
        latest_klines[timeframe] = latest_time

    return {
        "latest_ticker_time": latest_ticker,
        "latest_kline_times": latest_klines,
        "total_tickers": await session.scalar(select(func.count(PriceTicker.id))),
        "total_klines": await session.scalar(select(func.count(Kline.id)))
    }
```

### 2. 本地同步服务

```python
# sync-service/sync_manager.py
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from ..models import DataSourceNode, SyncStatus, TradingPair, Exchange
from ..database import get_async_session

logger = logging.getLogger(__name__)

class DataSyncManager:
    """数据同步管理器"""

    def __init__(self):
        self.sync_tasks = {}
        self.running = False

    async def start(self):
        """启动同步服务"""
        self.running = True
        logger.info("Data sync manager started")

        # 启动所有配置的同步任务
        async with get_async_session() as session:
            active_nodes = await session.execute(
                select(DataSourceNode).where(DataSourceNode.is_active == True)
            )

            for node in active_nodes.scalars():
                task = asyncio.create_task(self._sync_node_loop(node))
                self.sync_tasks[node.node_id] = task

    async def stop(self):
        """停止同步服务"""
        self.running = False

        # 取消所有同步任务
        for task in self.sync_tasks.values():
            task.cancel()

        if self.sync_tasks:
            await asyncio.gather(*self.sync_tasks.values(), return_exceptions=True)

        logger.info("Data sync manager stopped")

    async def _sync_node_loop(self, node: DataSourceNode):
        """单个节点的同步循环"""
        while self.running:
            try:
                await self._sync_node_data(node)
                await asyncio.sleep(node.sync_interval_minutes * 60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error syncing node {node.node_id}: {e}")
                await asyncio.sleep(60)  # 错误时等待1分钟

    async def _sync_node_data(self, node: DataSourceNode):
        """同步单个节点的数据"""
        logger.info(f"Starting sync from node: {node.node_id}")

        async with get_async_session() as session:
            # 获取需要同步的交易对
            trading_pairs = await session.execute(
                select(TradingPair).where(TradingPair.is_active == True)
            )

            for trading_pair in trading_pairs.scalars():
                try:
                    # 同步ticker数据
                    await self._sync_ticker_data(node, trading_pair, session)

                    # 同步各个时间周期的K线数据
                    for timeframe in ['1m', '5m', '1h', '1d']:
                        await self._sync_kline_data(node, trading_pair, timeframe, session)

                except Exception as e:
                    logger.error(f"Error syncing {trading_pair.symbol}: {e}")

        logger.info(f"Completed sync from node: {node.node_id}")

    async def _sync_ticker_data(self, node: DataSourceNode, trading_pair: TradingPair, session: AsyncSession):
        """同步ticker数据"""

        # 获取同步状态
        sync_status = await self._get_sync_status(
            session, node.node_id, trading_pair.id, 'ticker'
        )

        # 确定同步起始时间
        if sync_status and sync_status.last_sync_timestamp:
            start_time = sync_status.last_sync_timestamp
        else:
            # 首次同步，从1天前开始
            start_time = datetime.utcnow() - timedelta(days=1)

        # 调用远程API获取数据
        async with aiohttp.ClientSession() as client:
            url = f"{node.api_endpoint}/data/tickers/export"
            headers = {}
            if node.api_key:
                headers['Authorization'] = f"Bearer {node.api_key}"

            params = {
                'symbol': trading_pair.symbol,
                'exchange': trading_pair.exchange.name,
                'start_time': start_time.isoformat(),
                'limit': node.max_records_per_sync
            }

            async with client.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    # 批量插入数据
                    if data['data']:
                        await self._insert_ticker_data(session, data['data'], trading_pair.id)

                        # 更新同步状态
                        latest_timestamp = max(
                            datetime.fromisoformat(item['timestamp'])
                            for item in data['data']
                        )
                        await self._update_sync_status(
                            session, node.node_id, trading_pair.id, 'ticker',
                            latest_timestamp, len(data['data'])
                        )

                        logger.info(f"Synced {len(data['data'])} ticker records for {trading_pair.symbol}")
                else:
                    logger.error(f"Failed to fetch ticker data: {response.status}")

    async def _sync_kline_data(self, node: DataSourceNode, trading_pair: TradingPair,
                              timeframe: str, session: AsyncSession):
        """同步K线数据"""

        data_type = f"kline_{timeframe}"
        sync_status = await self._get_sync_status(
            session, node.node_id, trading_pair.id, data_type
        )

        # 确定同步起始时间
        if sync_status and sync_status.last_sync_timestamp:
            start_time = sync_status.last_sync_timestamp
        else:
            # 根据时间周期确定初始同步范围
            if timeframe == '1m':
                start_time = datetime.utcnow() - timedelta(hours=6)
            elif timeframe == '5m':
                start_time = datetime.utcnow() - timedelta(days=1)
            elif timeframe == '1h':
                start_time = datetime.utcnow() - timedelta(days=7)
            else:  # 1d
                start_time = datetime.utcnow() - timedelta(days=30)

        async with aiohttp.ClientSession() as client:
            url = f"{node.api_endpoint}/data/klines/export"
            headers = {}
            if node.api_key:
                headers['Authorization'] = f"Bearer {node.api_key}"

            params = {
                'symbol': trading_pair.symbol,
                'exchange': trading_pair.exchange.name,
                'timeframe': timeframe,
                'start_time': start_time.isoformat(),
                'limit': node.max_records_per_sync
            }

            async with client.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    if data['data']:
                        await self._insert_kline_data(session, data['data'], trading_pair.id)

                        # 更新同步状态
                        latest_timestamp = max(
                            datetime.fromisoformat(item['open_time'])
                            for item in data['data']
                        )
                        await self._update_sync_status(
                            session, node.node_id, trading_pair.id, data_type,
                            latest_timestamp, len(data['data'])
                        )

                        logger.info(f"Synced {len(data['data'])} {timeframe} kline records for {trading_pair.symbol}")

    async def _get_sync_status(self, session: AsyncSession, node_id: str,
                              trading_pair_id: int, data_type: str) -> Optional[SyncStatus]:
        """获取同步状态"""
        result = await session.execute(
            select(SyncStatus).where(and_(
                SyncStatus.source_node_id == node_id,
                SyncStatus.trading_pair_id == trading_pair_id,
                SyncStatus.data_type == data_type
            ))
        )
        return result.scalar_one_or_none()

    async def _update_sync_status(self, session: AsyncSession, node_id: str,
                                 trading_pair_id: int, data_type: str,
                                 last_timestamp: datetime, record_count: int):
        """更新同步状态"""

        sync_status = await self._get_sync_status(session, node_id, trading_pair_id, data_type)

        if sync_status:
            sync_status.last_sync_timestamp = last_timestamp
            sync_status.sync_status = 'completed'
            sync_status.updated_at = datetime.utcnow()
        else:
            sync_status = SyncStatus(
                source_node_id=node_id,
                trading_pair_id=trading_pair_id,
                data_type=data_type,
                last_sync_timestamp=last_timestamp,
                sync_status='completed'
            )
            session.add(sync_status)

        await session.commit()

    async def _insert_ticker_data(self, session: AsyncSession, ticker_data: List[Dict], trading_pair_id: int):
        """批量插入ticker数据"""
        from ..models import PriceTicker

        ticker_objects = []
        for data in ticker_data:
            ticker_objects.append(PriceTicker(
                trading_pair_id=trading_pair_id,
                price=data['price'],
                bid_price=data.get('bid_price'),
                ask_price=data.get('ask_price'),
                volume_24h=data.get('volume_24h'),
                price_change_24h=data.get('price_change_24h'),
                price_change_percent_24h=data.get('price_change_percent_24h'),
                high_24h=data.get('high_24h'),
                low_24h=data.get('low_24h'),
                timestamp=datetime.fromisoformat(data['timestamp'])
            ))

        # 批量插入，忽略重复数据
        for ticker in ticker_objects:
            await session.merge(ticker)

        await session.commit()

    async def _insert_kline_data(self, session: AsyncSession, kline_data: List[Dict], trading_pair_id: int):
        """批量插入K线数据"""
        from ..models import Kline

        kline_objects = []
        for data in kline_data:
            kline_objects.append(Kline(
                trading_pair_id=trading_pair_id,
                timeframe=data['timeframe'],
                open_time=datetime.fromisoformat(data['open_time']),
                close_time=datetime.fromisoformat(data['close_time']),
                open_price=data['open_price'],
                high_price=data['high_price'],
                low_price=data['low_price'],
                close_price=data['close_price'],
                volume=data['volume'],
                quote_volume=data.get('quote_volume'),
                trade_count=data.get('trade_count'),
                taker_buy_volume=data.get('taker_buy_volume'),
                taker_buy_quote_volume=data.get('taker_buy_quote_volume')
            ))

        # 使用ON CONFLICT处理重复数据
        for kline in kline_objects:
            await session.merge(kline)

        await session.commit()
```

### 3. 同步配置管理API

```python
# backend/api/sync_management.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..schemas import DataSourceNodeCreate, DataSourceNodeUpdate, SyncStatusResponse
from ..services import sync_service
from ..database import get_db

router = APIRouter(prefix="/api/v1/sync", tags=["data-sync"])

@router.post("/nodes", response_model=DataSourceNode)
async def create_sync_node(
    node_data: DataSourceNodeCreate,
    db: Session = Depends(get_db)
):
    """添加数据同步节点"""
    return await sync_service.create_node(db, node_data)

@router.get("/nodes", response_model=List[DataSourceNode])
async def list_sync_nodes(db: Session = Depends(get_db)):
    """获取同步节点列表"""
    return await sync_service.get_nodes(db)

@router.put("/nodes/{node_id}")
async def update_sync_node(
    node_id: str,
    node_data: DataSourceNodeUpdate,
    db: Session = Depends(get_db)
):
    """更新同步节点配置"""
    return await sync_service.update_node(db, node_id, node_data)

@router.post("/nodes/{node_id}/test")
async def test_sync_node(node_id: str, db: Session = Depends(get_db)):
    """测试同步节点连接"""
    return await sync_service.test_node_connection(db, node_id)

@router.post("/nodes/{node_id}/sync")
async def trigger_manual_sync(node_id: str, db: Session = Depends(get_db)):
    """手动触发同步"""
    return await sync_service.manual_sync(db, node_id)

@router.get("/status", response_model=List[SyncStatusResponse])
async def get_sync_status(db: Session = Depends(get_db)):
    """获取同步状态"""
    return await sync_service.get_sync_status(db)
```

### 4. Web界面同步管理

```vue
<!-- frontend/src/views/DataSync.vue -->
<template>
  <div class="data-sync-page">
    <el-card class="sync-nodes-card">
      <template #header>
        <div class="card-header">
          <span>数据源节点管理</span>
          <el-button type="primary" @click="showAddNodeDialog = true">
            添加节点
          </el-button>
        </div>
      </template>

      <el-table :data="syncNodes" style="width: 100%">
        <el-table-column prop="name" label="节点名称" width="150" />
        <el-table-column prop="api_endpoint" label="API地址" width="300" />
        <el-table-column prop="sync_interval_minutes" label="同步间隔(分钟)" width="120" />
        <el-table-column prop="is_active" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'">
              {{ row.is_active ? '活跃' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="250">
          <template #default="{ row }">
            <el-button size="small" @click="testConnection(row.node_id)">
              测试连接
            </el-button>
            <el-button size="small" type="primary" @click="manualSync(row.node_id)">
              手动同步
            </el-button>
            <el-button size="small" @click="editNode(row)">
              编辑
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card class="sync-status-card">
      <template #header>
        <span>同步状态</span>
      </template>

      <el-table :data="syncStatuses" style="width: 100%">
        <el-table-column prop="node_name" label="节点" width="150" />
        <el-table-column prop="trading_pair" label="交易对" width="120" />
        <el-table-column prop="data_type" label="数据类型" width="120" />
        <el-table-column prop="last_sync_timestamp" label="最后同步时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.last_sync_timestamp) }}
          </template>
        </el-table-column>
        <el-table-column prop="sync_status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.sync_status)">
              {{ getStatusText(row.sync_status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="error_message" label="错误信息" show-overflow-tooltip />
      </el-table>
    </el-card>

    <!-- 添加节点对话框 -->
    <el-dialog v-model="showAddNodeDialog" title="添加数据源节点" width="500px">
      <el-form :model="nodeForm" :rules="nodeFormRules" label-width="120px">
        <el-form-item label="节点名称" prop="name">
          <el-input v-model="nodeForm.name" placeholder="请输入节点名称" />
        </el-form-item>
        <el-form-item label="API地址" prop="api_endpoint">
          <el-input v-model="nodeForm.api_endpoint" placeholder="http://remote-server:8000/api/v1" />
        </el-form-item>
        <el-form-item label="API密钥" prop="api_key">
          <el-input v-model="nodeForm.api_key" type="password" placeholder="可选" />
        </el-form-item>
        <el-form-item label="同步间隔" prop="sync_interval_minutes">
          <el-input-number v-model="nodeForm.sync_interval_minutes" :min="1" :max="1440" />
          <span style="margin-left: 10px; color: #999;">分钟</span>
        </el-form-item>
        <el-form-item label="优先级" prop="priority">
          <el-input-number v-model="nodeForm.priority" :min="1" :max="10" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showAddNodeDialog = false">取消</el-button>
        <el-button type="primary" @click="addNode">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { syncApi } from '@/api/sync'

// 数据响应式变量
const syncNodes = ref([])
const syncStatuses = ref([])
const showAddNodeDialog = ref(false)

const nodeForm = ref({
  name: '',
  api_endpoint: '',
  api_key: '',
  sync_interval_minutes: 5,
  priority: 1
})

const nodeFormRules = {
  name: [{ required: true, message: '请输入节点名称', trigger: 'blur' }],
  api_endpoint: [{ required: true, message: '请输入API地址', trigger: 'blur' }]
}

// 页面方法
const fetchSyncNodes = async () => {
  try {
    syncNodes.value = await syncApi.getSyncNodes()
  } catch (error) {
    ElMessage.error('获取同步节点失败')
  }
}

const fetchSyncStatus = async () => {
  try {
    syncStatuses.value = await syncApi.getSyncStatus()
  } catch (error) {
    ElMessage.error('获取同步状态失败')
  }
}

const testConnection = async (nodeId: string) => {
  try {
    await syncApi.testConnection(nodeId)
    ElMessage.success('连接测试成功')
  } catch (error) {
    ElMessage.error('连接测试失败')
  }
}

const manualSync = async (nodeId: string) => {
  try {
    await syncApi.manualSync(nodeId)
    ElMessage.success('同步任务已启动')
    // 刷新状态
    setTimeout(fetchSyncStatus, 1000)
  } catch (error) {
    ElMessage.error('启动同步失败')
  }
}

const addNode = async () => {
  try {
    await syncApi.createSyncNode(nodeForm.value)
    ElMessage.success('节点添加成功')
    showAddNodeDialog.value = false
    nodeForm.value = { name: '', api_endpoint: '', api_key: '', sync_interval_minutes: 5, priority: 1 }
    fetchSyncNodes()
  } catch (error) {
    ElMessage.error('添加节点失败')
  }
}

// 工具方法
const formatDateTime = (timestamp: string) => {
  return timestamp ? new Date(timestamp).toLocaleString() : '-'
}

const getStatusType = (status: string) => {
  const typeMap = {
    'completed': 'success',
    'syncing': 'warning',
    'failed': 'danger',
    'pending': 'info'
  }
  return typeMap[status] || 'info'
}

const getStatusText = (status: string) => {
  const textMap = {
    'completed': '完成',
    'syncing': '同步中',
    'failed': '失败',
    'pending': '待同步'
  }
  return textMap[status] || status
}

// 页面加载
onMounted(() => {
  fetchSyncNodes()
  fetchSyncStatus()

  // 定时刷新状态
  setInterval(fetchSyncStatus, 30000) // 每30秒刷新一次
})
</script>
```

### 5. Docker部署配置更新

```yaml
# docker-compose.yml 中添加price-service和sync-service

services:
  # 现有服务...

  # 价格订阅服务
  price-service:
    build:
      context: ./price-service
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
      - REDIS_URL=redis://redis:6379/0
      - ENABLE_BINANCE=true
      - ENABLE_OKX=true
      - LOG_LEVEL=INFO
    volumes:
      - ./data/logs/price-service:/var/log/price-service
    depends_on:
      - db
      - redis
    restart: unless-stopped
    networks:
      - btc-watcher

  # 数据同步服务
  sync-service:
    build:
      context: ./sync-service
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - ./data/logs/sync-service:/var/log/sync-service
    depends_on:
      - db
      - redis
    restart: unless-stopped
    networks:
      - btc-watcher
    profiles:
      - sync  # 默认不启动，按需启用
```

这个历史数据同步系统的特点：

1. **分布式架构**: 支持多个远程数据源
2. **增量同步**: 基于时间戳的增量数据同步
3. **状态追踪**: 详细的同步状态记录和监控
4. **容错机制**: 网络断开自动重连，失败重试
5. **Web管理**: 直观的同步配置和状态管理界面
6. **按需启用**: 可选择性部署同步服务

接下来我将更新整体项目架构文档。