<template>
  <div class="dashboard">
    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #409EFF">
              <el-icon><Operation /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ overview.total_strategies || 0 }}</div>
              <div class="stat-label">总策略数</div>
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
              <div class="stat-label">运行中</div>
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
              <div class="stat-label">今日信号</div>
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
              <div class="stat-label">容量使用率</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="20" class="charts-row">
      <el-col :span="16">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>容量使用趋势</span>
              <el-radio-group v-model="trendPeriod" size="small" @change="fetchCapacityTrend">
                <el-radio-button :label="24">24小时</el-radio-button>
                <el-radio-button :label="72">3天</el-radio-button>
                <el-radio-button :label="168">7天</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <v-chart :option="capacityTrendOption" style="height: 300px" />
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card>
          <template #header>
            <span>信号分布</span>
          </template>
          <v-chart :option="signalDistributionOption" style="height: 300px" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 运行中的策略 -->
    <el-card class="strategies-card">
      <template #header>
        <div class="card-header">
          <span>运行中的策略</span>
          <el-button type="primary" size="small" @click="$router.push('/strategies')">
            管理策略
          </el-button>
        </div>
      </template>

      <el-table :data="runningStrategies" style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="策略名称" />
        <el-table-column prop="exchange" label="交易所" width="120" />
        <el-table-column prop="port" label="端口" width="100" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag type="success">运行中</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="started_at" label="启动时间" width="180" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useStrategyStore } from '@/stores/strategy'
import { useSystemStore } from '@/stores/system'
import { signalAPI } from '@/api'

const strategyStore = useStrategyStore()
const systemStore = useSystemStore()

const overview = ref({})
const capacity = ref({})
const signalStats = ref({})
const runningStrategies = ref([])
const trendPeriod = ref(24)

const capacityTrendOption = ref({
  title: { text: '' },
  tooltip: {
    trigger: 'axis',
    formatter: '{b}<br/>使用率: {c}%'
  },
  xAxis: {
    type: 'category',
    data: []
  },
  yAxis: {
    type: 'value',
    name: '使用率 (%)',
    min: 0,
    max: 100
  },
  series: [{
    data: [],
    type: 'line',
    smooth: true,
    areaStyle: {
      color: 'rgba(64, 158, 255, 0.2)'
    },
    lineStyle: {
      color: '#409EFF'
    }
  }]
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
      { value: signalData.strong_signals, name: '强信号', itemStyle: { color: '#67C23A' } },
      { value: signalData.medium_signals, name: '中等信号', itemStyle: { color: '#E6A23C' } },
      { value: signalData.weak_signals, name: '弱信号', itemStyle: { color: '#909399' } }
    ]
  } catch (error) {
    console.error('Failed to fetch dashboard data:', error)
  }
}

const fetchCapacityTrend = async () => {
  try {
    const trendData = await systemStore.fetchCapacityTrend(trendPeriod.value)

    capacityTrendOption.value.xAxis.data = trendData.data_points.map(d => {
      const date = new Date(d.timestamp)
      return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    })

    capacityTrendOption.value.series[0].data = trendData.data_points.map(d =>
      d.utilization_percent.toFixed(2)
    )
  } catch (error) {
    console.error('Failed to fetch capacity trend:', error)
  }
}

onMounted(() => {
  fetchDashboardData()
  fetchCapacityTrend()

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
  margin-bottom: 20px;
}

.stat-card {
  cursor: pointer;
  transition: all 0.3s;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 28px;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
  line-height: 1;
  margin-bottom: 8px;
}

.stat-label {
  font-size: 14px;
  color: #909399;
}

.charts-row {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.strategies-card {
  margin-top: 20px;
}
</style>
