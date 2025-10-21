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
          <el-tag v-if="dataSource" size="small" :type="dataSource === 'redis' ? 'success' : (dataSource === 'database' ? 'warning' : 'danger')" style="margin-left: 8px">
            {{ dataSource === 'redis' ? '缓存' : (dataSource === 'database' ? '数据库' : 'API') }}
          </el-tag>
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

        <!-- 技术指标选择器 - 第二期实现 -->
        <!--
        <div class="toolbar-right">
          <el-checkbox-group v-model="activeIndicators" size="small">
            <el-checkbox-button label="MA">MA</el-checkbox-button>
            <el-checkbox-button label="MACD">MACD</el-checkbox-button>
            <el-checkbox-button label="RSI">RSI</el-checkbox-button>
            <el-checkbox-button label="BOLL">BOLL</el-checkbox-button>
            <el-checkbox-button label="VOL">VOL</el-checkbox-button>
          </el-checkbox-group>
        </div>
        -->
      </div>

      <!-- K线图 -->
      <div class="chart-container">
        <v-chart
          v-if="candlestickData.dates && candlestickData.dates.length > 0"
          ref="chartRef"
          :option="candlestickOption"
          :init-options="{ renderer: 'canvas' }"
          :update-options="{ notMerge: true, lazyUpdate: false }"
          style="height: 100%"
          autoresize
        />
        <div v-else class="loading-placeholder">
          <el-icon :size="40" class="is-loading"><Loading /></el-icon>
          <p>{{ t('common.loading') }}</p>
        </div>
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
import { Search, Loading } from '@element-plus/icons-vue'
import { useThemeStore } from '@/stores/theme'
import { strategyAPI, signalAPI, marketDataAPI } from '@/api'
import { ElMessage } from 'element-plus'

const { t } = useI18n()
const themeStore = useThemeStore()

// 图表引用
const chartRef = ref(null)

// 加载状态
const loading = ref(false)
const dataSource = ref('') // redis, database, or api

// 货币对数据
const searchQuery = ref('')
const selectedPair = ref('BTC/USDT')
const availablePairs = ref([
  { symbol: 'BTC/USDT', lastPrice: 0, priceChange: 0 },
  { symbol: 'ETH/USDT', lastPrice: 0, priceChange: 0 },
  { symbol: 'BNB/USDT', lastPrice: 0, priceChange: 0 },
  { symbol: 'SOL/USDT', lastPrice: 0, priceChange: 0 },
  { symbol: 'ADA/USDT', lastPrice: 0, priceChange: 0 }
])

// 时间周期
const currentTimeframe = ref('1h')

// 技术指标
const activeIndicators = ref(['MA', 'VOL'])
const indicatorData = ref({}) // 存储技术指标数据

// 信号数据
const signalFilter = ref('all')
const signals = ref([])
const strategies = ref([])
const activeStrategies = ref([])

// K线数据
const candlestickData = ref({
  dates: [],
  values: [],
  volumes: []
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

  // 如果没有数据，返回空配置
  if (!candlestickData.value ||
      !candlestickData.value.dates ||
      !candlestickData.value.values ||
      !candlestickData.value.volumes ||
      candlestickData.value.dates.length === 0) {
    return {
      title: {
        text: t('charts.noData'),
        left: 'center',
        top: 'center',
        textStyle: { color: colors.text }
      }
    }
  }

  // 构建grid配置（根据激活的指标调整布局）
  const grids = [
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
  ]

  // 如果有MACD或RSI，需要额外的子图
  let hasSubplot = false
  if (activeIndicators.value.includes('MACD') || activeIndicators.value.includes('RSI')) {
    hasSubplot = true
    // 调整主图和成交量图的高度
    grids[0].height = '40%'
    grids[1].top = '53%'
    grids[1].height = '12%'
    // 添加MACD/RSI子图
    grids.push({
      left: '10%',
      right: '8%',
      top: '68%',
      height: '15%'
    })
  }

  // 构建xAxis配置
  const xAxisConfig = [
    {
      type: 'category',
      data: candlestickData.value.dates,
      boundaryGap: true,
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
      boundaryGap: true,
      axisLine: { onZero: false, lineStyle: { color: colors.axis } },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: { show: false },
      min: 'dataMin',
      max: 'dataMax'
    }
  ]

  if (hasSubplot) {
    xAxisConfig.push({
      type: 'category',
      gridIndex: 2,
      data: candlestickData.value.dates,
      boundaryGap: true,
      axisLine: { onZero: false, lineStyle: { color: colors.axis } },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: { show: false },
      min: 'dataMin',
      max: 'dataMax'
    })
  }

  // 构建yAxis配置
  const yAxisConfig = [
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
  ]

  if (hasSubplot) {
    yAxisConfig.push({
      scale: true,
      gridIndex: 2,
      splitNumber: 2,
      axisLine: { lineStyle: { color: colors.axis } },
      splitLine: { lineStyle: { color: themeStore.theme === 'dark' ? '#404040' : '#e5e5e5' } }
    })
  }

  // 构建dataZoom配置 - 使用固定初始值，让ECharts自己管理状态
  // 根据实际xAxis数量动态生成xAxisIndex数组
  const xAxisCount = xAxisConfig.length  // 使用实际的xAxis数组长度
  const xAxisIndices = Array.from({ length: xAxisCount }, (_, i) => i)

  const dataZoomConfig = [
    {
      id: 'dataZoomX',
      type: 'inside',
      xAxisIndex: xAxisIndices,
      start: 70,
      end: 100,
      zoomOnMouseWheel: true,
      moveOnMouseMove: true,
      minSpan: 5,  // 最小跨度5%
      maxSpan: 100  // 最大跨度100%
    },
    {
      id: 'dataZoomSlider',
      show: true,
      xAxisIndex: xAxisIndices,
      type: 'slider',
      top: hasSubplot ? '88%' : '85%',
      start: 70,
      end: 100,
      height: 20,
      borderColor: 'transparent',
      fillerColor: 'rgba(64, 158, 255, 0.2)',
      handleSize: '80%',
      textStyle: { color: colors.text },
      minSpan: 5,
      maxSpan: 100
    }
  ]

  // 构建series数组
  const series = [
    // K线
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

  // 技术指标渲染 - 第二期实现
  /*
  // 添加MA指标
  if (activeIndicators.value.includes('MA') && indicatorData.value.MA && indicatorData.value.MA.values) {
    const maData = indicatorData.value.MA.values
    if (maData && maData.ma5) {
      series.push({
        name: 'MA5',
        type: 'line',
        data: maData.ma5,
        smooth: true,
        lineStyle: { width: 1, color: '#1E90FF' },
        showSymbol: false
      })
    }
    if (maData && maData.ma10) {
      series.push({
        name: 'MA10',
        type: 'line',
        data: maData.ma10,
        smooth: true,
        lineStyle: { width: 1, color: '#FF69B4' },
        showSymbol: false
      })
    }
    if (maData && maData.ma20) {
      series.push({
        name: 'MA20',
        type: 'line',
        data: maData.ma20,
        smooth: true,
        lineStyle: { width: 1, color: '#FFD700' },
        showSymbol: false
      })
    }
    if (maData && maData.ma30) {
      series.push({
        name: 'MA30',
        type: 'line',
        data: maData.ma30,
        smooth: true,
        lineStyle: { width: 1, color: '#00FF7F' },
        showSymbol: false
      })
    }
  }

  // 添加BOLL指标
  if (activeIndicators.value.includes('BOLL') && indicatorData.value.BOLL && indicatorData.value.BOLL.values) {
    const bollData = indicatorData.value.BOLL.values
    if (bollData && bollData.upper) {
      series.push({
        name: 'BOLL上轨',
        type: 'line',
        data: bollData.upper,
        smooth: true,
        lineStyle: { width: 1, color: '#FF6B6B', type: 'dashed' },
        showSymbol: false
      })
    }
    if (bollData && bollData.middle) {
      series.push({
        name: 'BOLL中轨',
        type: 'line',
        data: bollData.middle,
        smooth: true,
        lineStyle: { width: 1, color: '#4ECDC4' },
        showSymbol: false
      })
    }
    if (bollData && bollData.lower) {
      series.push({
        name: 'BOLL下轨',
        type: 'line',
        data: bollData.lower,
        smooth: true,
        lineStyle: { width: 1, color: '#95E1D3', type: 'dashed' },
        showSymbol: false
      })
    }
  }

  // 添加MACD指标（显示在子图中）
  if (activeIndicators.value.includes('MACD') && indicatorData.value.MACD && indicatorData.value.MACD.values && hasSubplot) {
    const macdData = indicatorData.value.MACD.values
    if (xAxisConfig.length < 3 || yAxisConfig.length < 3) {
      console.error('❌ MACD需要3个axis，但实际只有', xAxisConfig.length, 'xAxis和', yAxisConfig.length, 'yAxis')
      return
    }
    if (macdData && macdData.macd) {
      series.push({
        name: 'MACD',
        type: 'line',
        xAxisIndex: 2,
        yAxisIndex: 2,
        data: macdData.macd,
        smooth: true,
        lineStyle: { width: 1, color: '#FF6B6B' },
        showSymbol: false
      })
    }
    if (macdData && macdData.signal) {
      series.push({
        name: 'Signal',
        type: 'line',
        xAxisIndex: 2,
        yAxisIndex: 2,
        data: macdData.signal,
        smooth: true,
        lineStyle: { width: 1, color: '#4ECDC4' },
        showSymbol: false
      })
    }
    if (macdData && macdData.histogram) {
      series.push({
        name: 'Histogram',
        type: 'bar',
        xAxisIndex: 2,
        yAxisIndex: 2,
        data: macdData.histogram,
        itemStyle: {
          color: function (params) {
            return params.value >= 0 ? '#00da3c' : '#ec0000'
          }
        }
      })
    }
  }

  // 添加RSI指标（显示在子图中）
  if (activeIndicators.value.includes('RSI') && indicatorData.value.RSI && indicatorData.value.RSI.values && hasSubplot) {
    const rsiData = indicatorData.value.RSI.values
    if (xAxisConfig.length < 3 || yAxisConfig.length < 3) {
      console.error('❌ RSI需要3个axis，但实际只有', xAxisConfig.length, 'xAxis和', yAxisConfig.length, 'yAxis')
      return
    }
    if (rsiData && rsiData.rsi) {
      series.push({
        name: 'RSI',
        type: 'line',
        xAxisIndex: 2,
        yAxisIndex: 2,
        data: rsiData.rsi,
        smooth: true,
        lineStyle: { width: 2, color: '#9966FF' },
        showSymbol: false,
        markLine: {
          silent: true,
          lineStyle: { type: 'dashed', color: '#888' },
          data: [
            { yAxis: 70, label: { position: 'end', formatter: '70' } },
            { yAxis: 30, label: { position: 'end', formatter: '30' } }
          ]
        }
      })
    }
  }
  */

  // 动态构建图例数据（基于实际添加的series）
  const legendData = series
    .filter(s => s.name) // 只保留有name的series
    .map(s => s.name)    // 提取name

  const config = {
    animation: false,
    legend: {
      bottom: 0,
      left: 'center',
      data: legendData,
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
    grid: grids,
    xAxis: xAxisConfig,
    yAxis: yAxisConfig,
    dataZoom: dataZoomConfig,
    series: series
  }

  // 验证配置完整性
  console.log('📊 ECharts配置:', {
    grids: config.grid.length,
    xAxis: config.xAxis.length,
    yAxis: config.yAxis.length,
    series: config.series.length,
    dataZoom: config.dataZoom.length,
    hasSubplot
  })

  // 验证series引用的axis索引是否存在
  const maxXAxisIndex = Math.max(...series.map(s => s.xAxisIndex || 0))
  const maxYAxisIndex = Math.max(...series.map(s => s.yAxisIndex || 0))
  if (maxXAxisIndex >= xAxisConfig.length) {
    console.error('❌ Series引用了不存在的xAxis:', maxXAxisIndex, '>=', xAxisConfig.length)
  }
  if (maxYAxisIndex >= yAxisConfig.length) {
    console.error('❌ Series引用了不存在的yAxis:', maxYAxisIndex, '>=', yAxisConfig.length)
  }

  return config
})

// 获取K线数据
const fetchKlineData = async () => {
  loading.value = true
  try {
    const response = await marketDataAPI.getKlines({
      symbol: selectedPair.value,
      timeframe: currentTimeframe.value,
      exchange: 'binance',
      limit: 200
    })

    // 验证响应数据
    if (!response || !response.data || !Array.isArray(response.data)) {
      console.warn('⚠️ K线数据格式不正确:', response)
      ElMessage.warning('K线数据格式不正确')
      return
    }

    dataSource.value = response.source

    // 转换API返回的数据格式 [[timestamp, open, high, low, close, volume], ...]
    const dates = []
    const values = []
    const volumes = []

    response.data.forEach(candle => {
      const [timestamp, open, high, low, close, volume] = candle
      const date = new Date(timestamp)

      // 根据时间周期选择合适的日期格式
      let dateStr
      if (currentTimeframe.value === '1d') {
        // 日线：显示年-月-日
        dateStr = date.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
      } else if (currentTimeframe.value === '1m' || currentTimeframe.value === '5m' || currentTimeframe.value === '15m') {
        // 分钟线：显示月-日 时:分
        dateStr = `${date.getMonth() + 1}-${date.getDate()} ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
      } else {
        // 小时线：显示月-日 时:分
        dateStr = `${date.getMonth() + 1}-${date.getDate()} ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
      }

      dates.push(dateStr)
      values.push([open, close, low, high]) // ECharts格式: [open, close, low, high]
      volumes.push(volume)
    })

    candlestickData.value = { dates, values, volumes }

    console.log('📊 K线数据已加载:', {
      货币对: selectedPair.value,
      时间周期: currentTimeframe.value,
      数据来源: dataSource.value,
      数据点数: values.length,
      时间范围: dates.length > 0 ? `${dates[0]} ~ ${dates[dates.length - 1]}` : '无'
    })
  } catch (error) {
    console.error('Failed to fetch kline data:', error)
    ElMessage.error('Failed to load K-line data')
  } finally {
    loading.value = false
  }
}

// 获取技术指标数据 - 第二期实现
/*
const fetchIndicators = async () => {
  if (!selectedPair.value) {
    console.warn('⚠️ 未选择货币对，跳过指标获取')
    return
  }

  try {
    const response = await marketDataAPI.getAllIndicators({
      symbol: selectedPair.value,
      timeframe: currentTimeframe.value,
      exchange: 'binance'
    })

    // 验证响应数据
    if (response && typeof response === 'object' && response.indicators) {
      // 后端已经返回了values字段，直接使用即可
      indicatorData.value = response.indicators
      console.log('📈 技术指标已加载:', Object.keys(indicatorData.value))
    } else {
      console.warn('⚠️ 技术指标数据格式不正确:', response)
      indicatorData.value = {}
    }
  } catch (error) {
    console.error('Failed to fetch indicators:', error)
    // 清空指标数据以避免使用旧数据
    indicatorData.value = {}
  }
}
*/

// 生成信号标记点
const generateSignalMarkers = () => {
  if (!filteredSignals.value.length) return []
  if (!candlestickData.value || !candlestickData.value.dates) return []

  return filteredSignals.value.map(signal => {
    const signalTime = new Date(signal.created_at)

    // 根据时间周期格式化信号时间，与K线数据格式保持一致
    let timeStr
    if (currentTimeframe.value === '1d') {
      timeStr = signalTime.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
    } else if (currentTimeframe.value === '1m' || currentTimeframe.value === '5m' || currentTimeframe.value === '15m') {
      timeStr = `${signalTime.getMonth() + 1}-${signalTime.getDate()} ${signalTime.getHours().toString().padStart(2, '0')}:${signalTime.getMinutes().toString().padStart(2, '0')}`
    } else {
      timeStr = `${signalTime.getMonth() + 1}-${signalTime.getDate()} ${signalTime.getHours().toString().padStart(2, '0')}:${signalTime.getMinutes().toString().padStart(2, '0')}`
    }

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
  return candlestickData.value.volumes || []
}

// 方法
const selectPair = async (symbol) => {
  selectedPair.value = symbol
  // 切换货币对时保持缩放比例和位置
  await fetchKlineData()
  // await fetchIndicators() // 第二期实现
  fetchSignals()
}

const handleTimeframeChange = async () => {
  // 切换时间周期时重新加载数据
  // 刷新所有货币对价格（不等待，后台执行）
  fetchAllPairsPrices()
  // 刷新当前货币对的K线和指标
  await fetchKlineData()
  // await fetchIndicators() // 第二期实现
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

// 批量加载所有货币对的最新价格
const fetchAllPairsPrices = async () => {
  try {
    // 为每个货币对获取最新的K线数据，使用当前选择的时间周期
    const pricePromises = availablePairs.value.map(async (pair) => {
      try {
        const response = await marketDataAPI.getKlines({
          symbol: pair.symbol,
          timeframe: currentTimeframe.value, // 使用当前时间周期计算涨跌幅
          exchange: 'binance',
          limit: 2 // 需要最新2根K线来计算涨跌幅
        })

        if (response.data && response.data.length >= 2) {
          const latestCandle = response.data[response.data.length - 1]
          const previousCandle = response.data[response.data.length - 2]

          const currentPrice = latestCandle[4] // close price
          const previousPrice = previousCandle[4]
          const priceChange = ((currentPrice - previousPrice) / previousPrice) * 100

          return {
            symbol: pair.symbol,
            lastPrice: currentPrice,
            priceChange: priceChange
          }
        }
        return null
      } catch (error) {
        console.error(`Failed to fetch price for ${pair.symbol}:`, error)
        return null
      }
    })

    const results = await Promise.all(pricePromises)

    // 更新货币对数据
    results.forEach((result) => {
      if (result) {
        const pairIndex = availablePairs.value.findIndex(p => p.symbol === result.symbol)
        if (pairIndex !== -1) {
          availablePairs.value[pairIndex].lastPrice = result.lastPrice
          availablePairs.value[pairIndex].priceChange = result.priceChange
        }
      }
    })

    console.log('💰 货币对价格已更新')
  } catch (error) {
    console.error('Failed to fetch pairs prices:', error)
  }
}

let refreshTimer = null

onMounted(async () => {
  // 初始化数据
  fetchAllPairsPrices() // 立即加载所有货币对价格（不等待）
  await fetchKlineData()
  // await fetchIndicators() // 第二期实现
  fetchStrategies()
  fetchSignals()

  // 每10秒刷新数据
  refreshTimer = setInterval(async () => {
    fetchAllPairsPrices() // 刷新所有货币对价格
    await fetchKlineData() // 刷新K线数据
    // await fetchIndicators() // 刷新指标数据 - 第二期实现
    fetchSignals() // 刷新信号
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

.loading-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-secondary);
  gap: 12px;
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
