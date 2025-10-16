<template>
  <div class="dashboard">
    <!-- 统计卡片 -->
    <el-row :gutter="6" class="stats-row">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #409EFF">
              <el-icon><Operation /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ overview.total_strategies || 0 }}</div>
              <div class="stat-label">{{ t('dashboard.totalStrategies') }}</div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #67C23A">
              <el-icon><Check /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ overview.running_strategies || 0 }}</div>
              <div class="stat-label">{{ t('dashboard.running') }}</div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #E6A23C">
              <el-icon><Notification /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ signalStats.total_signals || 0 }}</div>
              <div class="stat-label">{{ t('dashboard.todaySignals') }}</div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #F56C6C">
              <el-icon><Odometer /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ capacity.utilization_percent?.toFixed(1) || 0 }}%</div>
              <div class="stat-label">
                {{ t('dashboard.strategyCapacity') }}
                <el-tooltip placement="top" :content="t('dashboard.capacityTooltip')">
                  <el-icon style="font-size: 10px; margin-left: 2px; cursor: help"><QuestionFilled /></el-icon>
                </el-tooltip>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="6" class="charts-row">
      <el-col :span="16">
        <el-card>
          <template #header>
            <div class="card-header">
              <div>
                <span style="font-weight: 600">{{ t('dashboard.signalTrend') }}</span>
                <el-tooltip placement="top">
                  <template #content>
                    <div style="max-width: 250px">
                      <div><strong>{{ t('dashboard.signalStats') }}：</strong></div>
                      <div>{{ t('dashboard.signalStatsDesc') }}</div>
                      <div style="margin-top: 8px">
                        <span style="color: #67C23A">● </span>{{ t('dashboard.strongSignals') }}：{{ signalStats.strong_signals || 0 }} 个<br>
                        <span style="color: #E6A23C">● </span>{{ t('dashboard.mediumSignals') }}：{{ signalStats.medium_signals || 0 }} 个<br>
                        <span style="color: #909399">● </span>{{ t('dashboard.weakSignals') }}：{{ signalStats.weak_signals || 0 }} 个
                      </div>
                    </div>
                  </template>
                  <el-icon style="margin-left: 6px; cursor: help; color: #909399"><QuestionFilled /></el-icon>
                </el-tooltip>
              </div>
              <div style="display: flex; gap: 8px; align-items: center">
                <el-select v-model="signalGroupBy" size="small" style="width: 120px" @change="fetchSignalTrend">
                  <el-option :label="t('dashboard.byPair')" value="pair" />
                  <el-option :label="t('dashboard.byStrategy')" value="strategy" />
                  <el-option :label="t('dashboard.overall')" value="all" />
                </el-select>
                <el-radio-group v-model="trendPeriod" size="small" @change="fetchSignalTrend">
                  <el-radio-button :label="24">{{ t('dashboard.hours24') }}</el-radio-button>
                  <el-radio-button :label="72">{{ t('dashboard.days3') }}</el-radio-button>
                  <el-radio-button :label="168">{{ t('dashboard.days7') }}</el-radio-button>
                </el-radio-group>
              </div>
            </div>
          </template>
          <v-chart :option="signalTrendOption" style="height: 220px" />
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card>
          <template #header>
            <span>{{ t('dashboard.signalDistribution') }}</span>
          </template>
          <v-chart :option="signalDistributionOption" style="height: 220px" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 运行中的策略 -->
    <el-card class="strategies-card">
      <template #header>
        <div class="card-header">
          <span>{{ t('dashboard.runningStrategies') }}</span>
          <el-button type="primary" @click="$router.push('/strategies')">
            <el-icon style="margin-right: 4px"><Operation /></el-icon>
            {{ t('dashboard.manageStrategies') }}
          </el-button>
        </div>
      </template>

      <el-table :data="runningStrategies" style="width: 100%">
        <el-table-column prop="id" :label="t('dashboard.id')" width="80" />
        <el-table-column prop="name" :label="t('dashboard.strategyName')" />
        <el-table-column prop="exchange" :label="t('dashboard.exchange')" width="120" />
        <el-table-column prop="port" :label="t('dashboard.port')" width="100" />
        <el-table-column :label="t('dashboard.status')" width="100">
          <template #default="{ row }">
            <el-tag type="success">{{ t('dashboard.running') }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="started_at" :label="t('dashboard.startedAt')" width="180" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useStrategyStore } from '@/stores/strategy'
import { useSystemStore } from '@/stores/system'
import { signalAPI } from '@/api'
import { Operation, Check, Notification, Odometer, QuestionFilled } from '@element-plus/icons-vue'

const { t } = useI18n()

const strategyStore = useStrategyStore()
const systemStore = useSystemStore()

const overview = ref({})
const capacity = ref({})
const signalStats = ref({})
const runningStrategies = ref([])
const trendPeriod = ref(24)
const signalGroupBy = ref('all')

const signalTrendOption = ref({
  title: { text: '' },
  tooltip: {
    trigger: 'axis',
    formatter: (params) => {
      let result = `${params[0].name}<br/>`
      params.forEach(item => {
        result += `<span style="color: ${item.color}">● </span>${item.seriesName}: ${item.value}<br/>`
      })
      return result
    }
  },
  legend: {
    data: [],
    bottom: '0%',
    left: 'center'
  },
  xAxis: {
    type: 'category',
    data: []
  },
  yAxis: {
    type: 'value',
    name: '',
    minInterval: 1
  },
  grid: {
    left: '3%',
    right: '4%',
    bottom: '10%',
    containLabel: true
  },
  series: [
    {
      name: '',
      data: [],
      type: 'line',
      smooth: true,
      lineStyle: { color: '#67C23A', width: 2 },
      itemStyle: { color: '#67C23A' }
    },
    {
      name: '',
      data: [],
      type: 'line',
      smooth: true,
      lineStyle: { color: '#E6A23C', width: 2 },
      itemStyle: { color: '#E6A23C' }
    },
    {
      name: '',
      data: [],
      type: 'line',
      smooth: true,
      lineStyle: { color: '#909399', width: 2 },
      itemStyle: { color: '#909399' }
    }
  ]
})

const signalDistributionOption = ref({
  tooltip: {
    trigger: 'item',
    formatter: '{b}: {c} ({d}%)'
  },
  legend: {
    bottom: '0%',
    left: 'center'
  },
  series: [
    {
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 10,
        borderColor: '#fff',
        borderWidth: 2
      },
      label: {
        show: false
      },
      emphasis: {
        label: {
          show: true,
          fontSize: 16,
          fontWeight: 'bold'
        }
      },
      data: []
    }
  ]
})

let refreshTimer = null

const fetchDashboardData = async () => {
  try {
    // 获取策略概览
    const overviewData = await strategyStore.fetchOverview()
    overview.value = overviewData.summary
    runningStrategies.value = overviewData.strategies.filter(s => s.status === 'running')

    // 获取容量信息
    const capacityData = await systemStore.fetchCapacity()
    capacity.value = capacityData

    // 获取信号统计
    const signalData = await signalAPI.statistics({ hours: 24 })
    signalStats.value = signalData

    // 更新信号分布图表
    signalDistributionOption.value.series[0].data = [
      { value: signalData.strong_signals, name: t('dashboard.strongSignals'), itemStyle: { color: '#67C23A' } },
      { value: signalData.medium_signals, name: t('dashboard.mediumSignals'), itemStyle: { color: '#E6A23C' } },
      { value: signalData.weak_signals, name: t('dashboard.weakSignals'), itemStyle: { color: '#909399' } }
    ]
  } catch (error) {
    console.error('Failed to fetch dashboard data:', error)
  }
}

const fetchSignalTrend = async () => {
  try {
    const trendData = await signalAPI.trend({
      hours: trendPeriod.value,
      group_by: signalGroupBy.value
    })

    // Update chart labels
    signalTrendOption.value.yAxis.name = t('dashboard.signalQuantity')
    signalTrendOption.value.legend.data = [
      t('dashboard.strongSignals'),
      t('dashboard.mediumSignals'),
      t('dashboard.weakSignals')
    ]
    signalTrendOption.value.series[0].name = t('dashboard.strongSignals')
    signalTrendOption.value.series[1].name = t('dashboard.mediumSignals')
    signalTrendOption.value.series[2].name = t('dashboard.weakSignals')

    // Extract time labels
    signalTrendOption.value.xAxis.data = trendData.data_points.map(d => {
      const date = new Date(d.timestamp)
      if (trendPeriod.value === 24) {
        return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
      } else {
        return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
      }
    })

    // Extract signal counts for each series
    signalTrendOption.value.series[0].data = trendData.data_points.map(d => d.strong_signals || 0)
    signalTrendOption.value.series[1].data = trendData.data_points.map(d => d.medium_signals || 0)
    signalTrendOption.value.series[2].data = trendData.data_points.map(d => d.weak_signals || 0)
  } catch (error) {
    console.error('Failed to fetch signal trend:', error)
  }
}

onMounted(() => {
  fetchDashboardData()
  fetchSignalTrend()

  // 每30秒刷新一次
  refreshTimer = setInterval(fetchDashboardData, 30000)
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>

<style scoped>
.dashboard {
  padding: 0;
}

.stats-row {
  margin-bottom: 6px;
}

.stat-card {
  cursor: pointer;
  transition: all 0.3s;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 10px;
}

.stat-icon {
  width: 40px;
  height: 40px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 20px;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 22px;
  font-weight: bold;
  color: #303133;
  line-height: 1;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 12px;
  color: #909399;
}

.charts-row {
  margin-bottom: 6px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.strategies-card {
  margin-top: 6px;
}
</style>
