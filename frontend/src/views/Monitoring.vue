<template>
  <div class="monitoring">
    <!-- 系统健康状态 -->
    <el-row :gutter="12" class="health-row">
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>系统健康状态</span>
              <el-button size="small" @click="refreshData">
                <el-icon><Refresh /></el-icon>
                刷新
              </el-button>
            </div>
          </template>

          <el-row :gutter="12">
            <el-col :span="8">
              <div class="metric-card">
                <div class="metric-header">
                  <el-icon :size="24" color="#409EFF"><Odometer /></el-icon>
                  <span class="metric-title">CPU使用率</span>
                </div>
                <div class="metric-content">
                  <el-progress
                    :percentage="cpuUsage"
                    :color="getProgressColor(cpuUsage)"
                    :stroke-width="16"
                  />
                  <div class="metric-value">{{ cpuUsage }}%</div>
                </div>
              </div>
            </el-col>

            <el-col :span="8">
              <div class="metric-card">
                <div class="metric-header">
                  <el-icon :size="24" color="#67C23A"><Coin /></el-icon>
                  <span class="metric-title">内存使用率</span>
                </div>
                <div class="metric-content">
                  <el-progress
                    :percentage="memoryUsage"
                    :color="getProgressColor(memoryUsage)"
                    :stroke-width="16"
                  />
                  <div class="metric-value">{{ memoryUsage }}%</div>
                </div>
              </div>
            </el-col>

            <el-col :span="8">
              <div class="metric-card">
                <div class="metric-header">
                  <el-icon :size="24" color="#E6A23C"><Document /></el-icon>
                  <span class="metric-title">磁盘使用率</span>
                </div>
                <div class="metric-content">
                  <el-progress
                    :percentage="diskUsage"
                    :color="getProgressColor(diskUsage)"
                    :stroke-width="16"
                  />
                  <div class="metric-value">{{ diskUsage }}%</div>
                </div>
              </div>
            </el-col>
          </el-row>
        </el-card>
      </el-col>
    </el-row>

    <!-- 策略和容量统计 -->
    <el-row :gutter="12" class="stats-row">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #409EFF">
              <el-icon><Operation /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ capacity.max_strategies || 999 }}</div>
              <div class="stat-label">最大策略数</div>
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
              <div class="stat-value">{{ capacity.running_strategies || 0 }}</div>
              <div class="stat-label">运行中策略</div>
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
              <div class="stat-value">{{ capacity.available_slots || 999 }}</div>
              <div class="stat-label">可用端口数</div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #F56C6C">
              <el-icon><DataLine /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ capacity.utilization_percent || 0 }}%</div>
              <div class="stat-label">容量使用率</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 系统详细信息 -->
    <el-row :gutter="12" class="details-row">
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>系统详细信息</span>
              <el-tag v-if="lastUpdate" size="small">
                最后更新: {{ lastUpdate }}
              </el-tag>
            </div>
          </template>

          <el-descriptions :column="2" border>
            <el-descriptions-item label="系统负载 (1/5/15分钟)">
              {{ systemLoad }}
            </el-descriptions-item>
            <el-descriptions-item label="CPU核心数">
              {{ cpuCores }}
            </el-descriptions-item>
            <el-descriptions-item label="内存总量" :span="2">
              {{ formatBytes(memoryTotal) }}
            </el-descriptions-item>
            <el-descriptions-item label="内存已用" :span="2">
              {{ formatBytes(memoryUsed) }}
            </el-descriptions-item>
            <el-descriptions-item label="磁盘总量" :span="2">
              {{ formatBytes(diskTotal) }}
            </el-descriptions-item>
            <el-descriptions-item label="磁盘已用" :span="2">
              {{ formatBytes(diskUsed) }}
            </el-descriptions-item>
            <el-descriptions-item label="端口范围" :span="2">
              {{ capacity.port_range || 'N/A' }} (每个策略独占一个端口)
            </el-descriptions-item>
            <el-descriptions-item label="架构模式" :span="2">
              多实例反向代理 ({{ capacity.architecture || 'multi_instance_reverse_proxy' }})
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { systemAPI, monitoringAPI } from '@/api'
import {
  Odometer,
  Coin,
  Document,
  Operation,
  Check,
  Notification,
  DataLine,
  Refresh
} from '@element-plus/icons-vue'

// 系统指标
const cpuUsage = ref(0)
const memoryUsage = ref(0)
const diskUsage = ref(0)
const systemLoad = ref('N/A')
const cpuCores = ref('N/A')
const memoryTotal = ref(0)
const memoryUsed = ref(0)
const diskTotal = ref(0)
const diskUsed = ref(0)

// 容量信息
const capacity = ref({})
const lastUpdate = ref('')

let refreshTimer = null

// 获取系统监控数据
const fetchMonitoringData = async () => {
  try {
    const res = await monitoringAPI.system()

    // 更新基础指标
    if (res.cpu) {
      cpuUsage.value = Math.round(res.cpu.percent || 0)
      cpuCores.value = res.cpu.count || 'N/A'

      // 系统负载（1分钟，5分钟，15分钟）
      if (res.cpu.load_avg && Array.isArray(res.cpu.load_avg)) {
        systemLoad.value = res.cpu.load_avg.map(l => l.toFixed(2)).join(', ')
      }
    }

    if (res.memory) {
      memoryUsage.value = Math.round(res.memory.percent || 0)
      memoryTotal.value = res.memory.total || 0
      memoryUsed.value = res.memory.used || 0
    }

    if (res.disk) {
      diskUsage.value = Math.round(res.disk.percent || 0)
      diskTotal.value = res.disk.total || 0
      diskUsed.value = res.disk.used || 0
    }
  } catch (error) {
    console.error('Failed to fetch monitoring data:', error)
  }
}

// 获取容量信息
const fetchCapacity = async () => {
  try {
    const res = await systemAPI.capacity()
    capacity.value = res
    lastUpdate.value = new Date().toLocaleString('zh-CN')
  } catch (error) {
    console.error('Failed to fetch capacity:', error)
  }
}

// 刷新所有数据
const refreshData = async () => {
  await Promise.all([
    fetchMonitoringData(),
    fetchCapacity()
  ])
}

// 辅助函数
const getProgressColor = (percentage) => {
  if (percentage < 60) return '#67C23A'
  if (percentage < 80) return '#E6A23C'
  return '#F56C6C'
}

const formatBytes = (bytes) => {
  if (!bytes || bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

// 生命周期
onMounted(() => {
  refreshData()
  // 每30秒刷新一次
  refreshTimer = setInterval(refreshData, 30000)
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>

<style scoped>
.monitoring {
  padding: 0;
}

.health-row {
  margin-bottom: 6px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.metric-card {
  padding: 12px;
  border: 1px solid #EBEEF5;
  border-radius: 4px;
  background: #fafafa;
  transition: background-color 0.3s, border-color 0.3s;
}

html.dark .metric-card {
  background: var(--input-bg);
  border-color: var(--border-color);
}

.metric-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
}

.metric-title {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

html.dark .metric-title {
  color: var(--text-primary);
}

.metric-content {
  position: relative;
}

.metric-value {
  text-align: center;
  margin-top: 8px;
  font-size: 20px;
  font-weight: bold;
  color: #303133;
}

html.dark .metric-value {
  color: var(--text-primary);
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

html.dark .stat-value {
  color: var(--text-primary);
}

.stat-label {
  font-size: 12px;
  color: #909399;
}

html.dark .stat-label {
  color: var(--text-secondary);
}

.details-row {
  margin-bottom: 6px;
}
</style>
