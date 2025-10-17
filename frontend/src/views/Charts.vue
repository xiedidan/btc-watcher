<template>
  <div class="charts-view">
    <!-- 左侧：货币对列表 -->
    <div class="left-panel">
      <div class="panel-header">
        <span>{{ t('charts.pairList') }}</span>
      </div>

      <!-- 搜索框 -->
      <div class="search-box">
        <el-input
          v-model="searchQuery"
          :placeholder="t('charts.searchPair')"
          size="small"
          clearable
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </div>

      <!-- 货币对列表 -->
      <div class="pair-list">
        <div
          v-for="pair in filteredPairs"
          :key="pair.symbol"
          class="pair-item"
          :class="{ active: selectedPair === pair.symbol }"
          @click="selectPair(pair.symbol)"
        >
          <div class="pair-info">
            <span class="pair-symbol">{{ pair.symbol }}</span>
            <span class="pair-price">${{ pair.lastPrice?.toFixed(2) || '-' }}</span>
          </div>
          <div class="pair-change" :class="pair.priceChange >= 0 ? 'positive' : 'negative'">
            {{ pair.priceChange >= 0 ? '+' : '' }}{{ pair.priceChange?.toFixed(2) || 0 }}%
          </div>
        </div>
      </div>
    </div>

    <!-- 中间：K线图表 -->
    <div class="center-panel">
      <!-- 工具栏 -->
      <div class="chart-toolbar">
        <div class="toolbar-left">
          <span class="chart-title">{{ selectedPair }}</span>
          <el-tag size="small" type="info" style="margin-left: 8px">{{ currentTimeframe }}</el-tag>
        </div>

        <div class="toolbar-center">
          <!-- 时间周期选择 -->
          <el-radio-group v-model="currentTimeframe" size="small" @change="handleTimeframeChange">
            <el-radio-button label="1m">1m</el-radio-button>
            <el-radio-button label="5m">5m</el-radio-button>
            <el-radio-button label="15m">15m</el-radio-button>
            <el-radio-button label="1h">1h</el-radio-button>
            <el-radio-button label="4h">4h</el-radio-button>
            <el-radio-button label="1d">1d</el-radio-button>
          </el-radio-group>
        </div>

        <div class="toolbar-right">
          <!-- 技术指标选择 -->
          <el-checkbox-group v-model="activeIndicators" size="small">
            <el-checkbox-button label="MA">MA</el-checkbox-button>
            <el-checkbox-button label="MACD">MACD</el-checkbox-button>
            <el-checkbox-button label="RSI">RSI</el-checkbox-button>
            <el-checkbox-button label="BOLL">BOLL</el-checkbox-button>
            <el-checkbox-button label="VOL">VOL</el-checkbox-button>
          </el-checkbox-group>
        </div>
      </div>

      <!-- K线图 -->
      <div class="chart-container">
        <v-chart :option="candlestickOption" style="height: 100%" autoresize />
      </div>
    </div>

    <!-- 右侧：信号详情面板 -->
    <div class="right-panel">
      <div class="panel-header">
        <span>{{ t('charts.signalDetails') }}</span>
      </div>

      <!-- 信号过滤 -->
      <div class="signal-filters">
        <el-select v-model="signalFilter" size="small" style="width: 100%">
          <el-option :label="t('charts.allSignals')" value="all" />
          <el-option :label="t('charts.buySignals')" value="buy" />
          <el-option :label="t('charts.sellSignals')" value="sell" />
        </el-select>
      </div>

      <!-- 信号列表 -->
      <div class="signal-list">
        <div
          v-for="signal in filteredSignals"
          :key="signal.id"
          class="signal-item"
          @click="highlightSignal(signal)"
        >
          <div class="signal-header">
            <el-tag
              :type="signal.action === 'buy' ? 'success' : 'danger'"
              size="small"
            >
              {{ signal.action === 'buy' ? t('charts.buy') : t('charts.sell') }}
            </el-tag>
            <span class="signal-time">{{ formatTime(signal.created_at) }}</span>
          </div>
          <div class="signal-body">
            <div class="signal-row">
              <span class="label">{{ t('charts.strategy') }}:</span>
              <span class="value">{{ signal.strategy_name || `#${signal.strategy_id}` }}</span>
            </div>
            <div class="signal-row">
              <span class="label">{{ t('charts.price') }}:</span>
              <span class="value">${{ signal.current_rate?.toFixed(2) || '-' }}</span>
            </div>
            <div class="signal-row">
              <span class="label">{{ t('charts.strength') }}:</span>
              <el-progress
                :percentage="Math.round(signal.signal_strength * 100)"
                :color="getStrengthColor(signal.signal_strength)"
                :show-text="false"
                style="flex: 1; margin-left: 8px"
              />
            </div>
          </div>
        </div>

        <el-empty v-if="filteredSignals.length === 0" :description="t('charts.noSignals')" />
      </div>
    </div>

    <!-- 底部：策略列表 -->
    <div class="bottom-panel">
      <div class="strategy-tabs">
        <div
          v-for="strategy in strategies"
          :key="strategy.id"
          class="strategy-tab"
          :class="{ active: activeStrategies.includes(strategy.id) }"
          @click="toggleStrategy(strategy.id)"
        >
          <el-checkbox
            :model-value="activeStrategies.includes(strategy.id)"
            @change="toggleStrategy(strategy.id)"
          />
          <span class="strategy-name">{{ strategy.name }}</span>
          <el-tag
            :type="strategy.status === 'running' ? 'success' : 'info'"
            size="small"
          >
            {{ strategy.status }}
          </el-tag>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Search } from '@element-plus/icons-vue'
import { useThemeStore } from '@/stores/theme'
import { strategyAPI, signalAPI } from '@/api'

const { t } = useI18n()
const themeStore = useThemeStore()

// 货币对数据
const searchQuery = ref('')
const selectedPair = ref('BTC/USDT')
const availablePairs = ref([
  { symbol: 'BTC/USDT', lastPrice: 45230.50, priceChange: 2.34 },
  { symbol: 'ETH/USDT', lastPrice: 2890.75, priceChange: -1.23 },
  { symbol: 'BNB/USDT', lastPrice: 320.40, priceChange: 0.56 },
  { symbol: 'SOL/USDT', lastPrice: 110.20, priceChange: 3.45 },
  { symbol: 'ADA/USDT', lastPrice: 0.58, priceChange: -0.89 }
])

// 时间周期
const currentTimeframe = ref('1h')

// 技术指标
const activeIndicators = ref(['MA', 'VOL'])

// 信号数据
const signalFilter = ref('all')
const signals = ref([])
const strategies = ref([])
const activeStrategies = ref([])

// K线数据
const candlestickData = ref({
  dates: [],
  values: []
})

// 计算属性
const filteredPairs = computed(() => {
  if (!searchQuery.value) return availablePairs.value
  return availablePairs.value.filter(pair =>
    pair.symbol.toLowerCase().includes(searchQuery.value.toLowerCase())
  )
})

const filteredSignals = computed(() => {
  let result = signals.value.filter(s => s.pair === selectedPair.value)

  if (signalFilter.value !== 'all') {
    result = result.filter(s => s.action === signalFilter.value)
  }

  // 只显示活跃策略的信号
  if (activeStrategies.value.length > 0) {
    result = result.filter(s => activeStrategies.value.includes(s.strategy_id))
  }

  return result.slice(0, 20) // 限制显示20条
})

// 图表颜色配置
const chartColors = computed(() => themeStore.theme === 'dark'
  ? {
      text: '#e0e0e0',
      axis: '#606266',
      up: '#00da3c',
      down: '#ec0000',
      volume: 'rgba(64, 158, 255, 0.3)'
    }
  : {
      text: '#303133',
      axis: '#909399',
      up: '#00da3c',
      down: '#ec0000',
      volume: 'rgba(64, 158, 255, 0.3)'
    }
)

// K线图配置
const candlestickOption = computed(() => {
  const colors = chartColors.value

  return {
    animation: false,
    legend: {
      bottom: 0,
      left: 'center',
      data: ['K线', 'MA5', 'MA10', 'MA20', 'MA30', '成交量'],
      textStyle: { color: colors.text }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      backgroundColor: themeStore.theme === 'dark' ? '#2a2a2a' : '#fff',
      borderColor: themeStore.theme === 'dark' ? '#404040' : '#dcdfe6',
      textStyle: { color: colors.text }
    },
    axisPointer: {
      link: [{ xAxisIndex: 'all' }],
      label: {
        backgroundColor: '#777'
      }
    },
    grid: [
      {
        left: '10%',
        right: '8%',
        height: '50%'
      },
      {
        left: '10%',
        right: '8%',
        top: '63%',
        height: '16%'
      }
    ],
    xAxis: [
      {
        type: 'category',
        data: candlestickData.value.dates,
        boundaryGap: false,
        axisLine: { onZero: false, lineStyle: { color: colors.axis } },
        splitLine: { show: false },
        min: 'dataMin',
        max: 'dataMax',
        axisPointer: { z: 100 }
      },
      {
        type: 'category',
        gridIndex: 1,
        data: candlestickData.value.dates,
        boundaryGap: false,
        axisLine: { onZero: false, lineStyle: { color: colors.axis } },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        min: 'dataMin',
        max: 'dataMax'
      }
    ],
    yAxis: [
      {
        scale: true,
        splitArea: { show: true },
        axisLine: { lineStyle: { color: colors.axis } },
        splitLine: { lineStyle: { color: themeStore.theme === 'dark' ? '#404040' : '#e5e5e5' } }
      },
      {
        scale: true,
        gridIndex: 1,
        splitNumber: 2,
        axisLabel: { show: false },
        axisLine: { show: false, lineStyle: { color: colors.axis } },
        axisTick: { show: false },
        splitLine: { show: false }
      }
    ],
    dataZoom: [
      {
        type: 'inside',
        xAxisIndex: [0, 1],
        start: 70,
        end: 100
      },
      {
        show: true,
        xAxisIndex: [0, 1],
        type: 'slider',
        top: '85%',
        start: 70,
        end: 100
      }
    ],
    series: [
      {
        name: 'K线',
        type: 'candlestick',
        data: candlestickData.value.values,
        itemStyle: {
          color: colors.up,
          color0: colors.down,
          borderColor: undefined,
          borderColor0: undefined
        },
        markPoint: {
          label: {
            formatter: function (param) {
              return param != null ? Math.round(param.value) + '' : ''
            }
          },
          data: generateSignalMarkers()
        }
      },
      // 成交量
      {
        name: '成交量',
        type: 'bar',
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: generateVolumeData(),
        itemStyle: {
          color: colors.volume
        }
      }
    ]
  }
})

// 生成模拟K线数据
const generateMockData = () => {
  const dates = []
  const values = []
  const basePrice = selectedPair.value === 'BTC/USDT' ? 45000 : 2800
  const now = new Date()

  for (let i = 100; i >= 0; i--) {
    const date = new Date(now.getTime() - i * 3600000) // 每小时
    dates.push(date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }))

    const open = basePrice + Math.random() * 500 - 250
    const close = open + Math.random() * 200 - 100
    const low = Math.min(open, close) - Math.random() * 50
    const high = Math.max(open, close) + Math.random() * 50

    values.push([open, close, low, high])
  }

  candlestickData.value = { dates, values }
}

// 生成信号标记点
const generateSignalMarkers = () => {
  if (!filteredSignals.value.length) return []

  return filteredSignals.value.map(signal => {
    const signalTime = new Date(signal.created_at)
    const timeStr = signalTime.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    const index = candlestickData.value.dates.indexOf(timeStr)

    if (index === -1) return null

    return {
      name: signal.action === 'buy' ? '买入' : '卖出',
      coord: [index, signal.current_rate],
      value: signal.current_rate,
      itemStyle: {
        color: signal.action === 'buy' ? '#00da3c' : '#ec0000'
      },
      symbol: signal.action === 'buy' ? 'arrow' : 'arrow',
      symbolRotate: signal.action === 'buy' ? 0 : 180,
      symbolSize: 15
    }
  }).filter(m => m !== null)
}

// 生成成交量数据
const generateVolumeData = () => {
  return candlestickData.value.values.map(() => Math.random() * 1000000)
}

// 方法
const selectPair = (symbol) => {
  selectedPair.value = symbol
  generateMockData()
  fetchSignals()
}

const handleTimeframeChange = () => {
  generateMockData()
}

const toggleStrategy = (strategyId) => {
  const index = activeStrategies.value.indexOf(strategyId)
  if (index > -1) {
    activeStrategies.value.splice(index, 1)
  } else {
    activeStrategies.value.push(strategyId)
  }
}

const highlightSignal = (signal) => {
  console.log('Highlight signal:', signal)
  // TODO: 实现信号高亮显示
}

const formatTime = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const getStrengthColor = (strength) => {
  if (strength >= 0.8) return '#67C23A'
  if (strength >= 0.6) return '#E6A23C'
  if (strength >= 0.4) return '#F56C6C'
  return '#909399'
}

// 获取数据
const fetchStrategies = async () => {
  try {
    const res = await strategyAPI.list()
    strategies.value = res.strategies || []
    // 默认激活所有运行中的策略
    activeStrategies.value = strategies.value
      .filter(s => s.status === 'running')
      .map(s => s.id)
  } catch (error) {
    console.error('Failed to fetch strategies:', error)
  }
}

const fetchSignals = async () => {
  try {
    const res = await signalAPI.list({
      pair: selectedPair.value,
      hours: 24
    })
    signals.value = res.signals || []
  } catch (error) {
    console.error('Failed to fetch signals:', error)
  }
}

let refreshTimer = null

onMounted(() => {
  generateMockData()
  fetchStrategies()
  fetchSignals()

  // 每10秒刷新数据
  refreshTimer = setInterval(() => {
    fetchSignals()
    // 模拟价格更新
    availablePairs.value.forEach(pair => {
      pair.lastPrice = pair.lastPrice * (1 + (Math.random() - 0.5) * 0.001)
      pair.priceChange = (Math.random() - 0.5) * 5
    })
  }, 10000)
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>

<style scoped>
.charts-view {
  display: grid;
  grid-template-columns: 200px 1fr 250px;
  grid-template-rows: 1fr 80px;
  gap: 6px;
  height: calc(100vh - 52px);
  padding: 0;
}

/* 左侧面板 */
.left-panel {
  display: flex;
  flex-direction: column;
  background: var(--card-bg);
  border-radius: 4px;
  overflow: hidden;
}

.panel-header {
  padding: 10px 12px;
  font-weight: 600;
  border-bottom: 1px solid var(--border-color);
}

.search-box {
  padding: 8px;
}

.pair-list {
  flex: 1;
  overflow-y: auto;
}

.pair-item {
  padding: 8px 12px;
  cursor: pointer;
  border-bottom: 1px solid var(--border-color);
  transition: background-color 0.2s;
}

.pair-item:hover {
  background-color: rgba(64, 158, 255, 0.1);
}

.pair-item.active {
  background-color: rgba(64, 158, 255, 0.2);
}

.pair-info {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
}

.pair-symbol {
  font-weight: 600;
  font-size: 13px;
}

.pair-price {
  font-size: 12px;
  color: var(--text-secondary);
}

.pair-change {
  font-size: 12px;
  font-weight: 500;
}

.pair-change.positive {
  color: #67C23A;
}

.pair-change.negative {
  color: #F56C6C;
}

/* 中间面板 */
.center-panel {
  display: flex;
  flex-direction: column;
  background: var(--card-bg);
  border-radius: 4px;
}

.chart-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  border-bottom: 1px solid var(--border-color);
  gap: 12px;
}

.toolbar-left {
  display: flex;
  align-items: center;
}

.chart-title {
  font-size: 16px;
  font-weight: 600;
}

.toolbar-center {
  flex: 1;
  display: flex;
  justify-content: center;
}

.toolbar-right {
  display: flex;
  gap: 8px;
}

.chart-container {
  flex: 1;
  min-height: 0;
  padding: 8px;
}

/* 右侧面板 */
.right-panel {
  display: flex;
  flex-direction: column;
  background: var(--card-bg);
  border-radius: 4px;
  overflow: hidden;
}

.signal-filters {
  padding: 8px;
}

.signal-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.signal-item {
  background: var(--input-bg);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  padding: 8px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.signal-item:hover {
  border-color: var(--el-color-primary);
  transform: translateX(2px);
}

.signal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.signal-time {
  font-size: 11px;
  color: var(--text-tertiary);
}

.signal-body {
  font-size: 12px;
}

.signal-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.signal-row .label {
  color: var(--text-secondary);
  min-width: 50px;
}

.signal-row .value {
  color: var(--text-primary);
  font-weight: 500;
}

/* 底部面板 */
.bottom-panel {
  grid-column: 1 / -1;
  background: var(--card-bg);
  border-radius: 4px;
  padding: 8px;
  overflow-x: auto;
}

.strategy-tabs {
  display: flex;
  gap: 8px;
}

.strategy-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: var(--input-bg);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.strategy-tab:hover {
  border-color: var(--el-color-primary);
}

.strategy-tab.active {
  background: rgba(64, 158, 255, 0.1);
  border-color: var(--el-color-primary);
}

.strategy-name {
  font-size: 13px;
  font-weight: 500;
}
</style>
