<template>
  <div class="signals">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>交易信号</span>
          <el-space>
            <el-tag>今日信号: {{ statistics.total_signals || 0 }}</el-tag>
            <el-tag type="success">强信号: {{ statistics.strong_signals || 0 }}</el-tag>
          </el-space>
        </div>
      </template>

      <!-- 筛选条件 -->
      <el-form :inline="true" class="search-form">
        <el-form-item label="交易对">
          <el-input v-model="searchForm.pair" placeholder="BTC/USDT" clearable style="width: 150px" />
        </el-form-item>

        <el-form-item label="动作">
          <el-select v-model="searchForm.action" placeholder="全部" clearable style="width: 120px">
            <el-option label="全部" value="" />
            <el-option label="买入" value="buy" />
            <el-option label="卖出" value="sell" />
          </el-select>
        </el-form-item>

        <el-form-item label="强度">
          <el-select v-model="searchForm.strength_level" placeholder="全部" clearable style="width: 120px">
            <el-option label="全部" value="" />
            <el-option label="强" value="strong" />
            <el-option label="中" value="medium" />
            <el-option label="弱" value="weak" />
          </el-select>
        </el-form-item>

        <el-form-item label="时间范围">
          <el-select v-model="searchForm.hours" placeholder="24小时" style="width: 120px">
            <el-option label="1小时" :value="1" />
            <el-option label="6小时" :value="6" />
            <el-option label="24小时" :value="24" />
            <el-option label="7天" :value="168" />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="fetchData">查询</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>

      <!-- 信号列表 -->
      <el-table
        :data="signals"
        v-loading="loading"
        style="width: 100%"
      >
        <el-table-column prop="id" label="ID" width="80" />

        <el-table-column prop="pair" label="交易对" width="120" />

        <el-table-column label="动作" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.action === 'buy'" type="success">买入</el-tag>
            <el-tag v-else-if="row.action === 'sell'" type="danger">卖出</el-tag>
            <el-tag v-else type="info">持有</el-tag>
          </template>
        </el-table-column>

        <el-table-column label="信号强度" width="150">
          <template #default="{ row }">
            <el-progress
              :percentage="row.signal_strength * 100"
              :color="getStrengthColor(row.signal_strength)"
              :stroke-width="16"
            >
              <span>{{ (row.signal_strength * 100).toFixed(0) }}%</span>
            </el-progress>
          </template>
        </el-table-column>

        <el-table-column label="强度等级" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.strength_level === 'strong'" type="success">强</el-tag>
            <el-tag v-else-if="row.strength_level === 'medium'" type="warning">中</el-tag>
            <el-tag v-else-if="row.strength_level === 'weak'" type="info">弱</el-tag>
            <el-tag v-else type="info">忽略</el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="current_rate" label="当前价格" width="120">
          <template #default="{ row }">
            ${{ row.current_rate?.toFixed(8) }}
          </template>
        </el-table-column>

        <el-table-column label="盈亏" width="100">
          <template #default="{ row }">
            <span v-if="row.profit_ratio" :style="{ color: row.profit_ratio > 0 ? '#67C23A' : '#F56C6C' }">
              {{ (row.profit_ratio * 100).toFixed(2) }}%
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>

        <el-table-column prop="created_at" label="时间" width="180" />

        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="handleView(row)">
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @current-change="fetchData"
        @size-change="fetchData"
        style="margin-top: 20px; justify-content: center"
      />
    </el-card>

    <!-- 信号详情对话框 -->
    <el-dialog
      v-model="showDetailDialog"
      title="信号详情"
      width="800px"
      destroy-on-close
    >
      <div v-if="currentSignal">
        <!-- 基础信息和技术指标 -->
        <el-row :gutter="16" style="margin-bottom: 20px">
          <el-col :span="12">
            <el-card shadow="never" header="基础信息">
              <el-descriptions :column="1" size="small">
                <el-descriptions-item label="交易对">{{ currentSignal.pair }}</el-descriptions-item>
                <el-descriptions-item label="信号类型">
                  <el-tag v-if="currentSignal.action === 'buy'" type="success">买入 🟢</el-tag>
                  <el-tag v-else-if="currentSignal.action === 'sell'" type="danger">卖出 🔴</el-tag>
                  <el-tag v-else type="info">持有</el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="信号强度">
                  <div style="display: flex; align-items: center; gap: 8px">
                    <el-progress
                      :percentage="currentSignal.signal_strength * 100"
                      :color="getStrengthColor(currentSignal.signal_strength)"
                      :stroke-width="12"
                      :show-text="false"
                      style="flex: 1; max-width: 100px"
                    />
                    <span>{{ (currentSignal.signal_strength * 100).toFixed(1) }}%</span>
                  </div>
                </el-descriptions-item>
                <el-descriptions-item label="强度等级">
                  <el-tag v-if="currentSignal.strength_level === 'strong'" type="success">强烈信号</el-tag>
                  <el-tag v-else-if="currentSignal.strength_level === 'medium'" type="warning">中等信号</el-tag>
                  <el-tag v-else-if="currentSignal.strength_level === 'weak'" type="info">弱信号</el-tag>
                  <el-tag v-else>忽略</el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="触发时间">
                  {{ currentSignal.created_at }}
                </el-descriptions-item>
                <el-descriptions-item label="当前价格">
                  ${{ currentSignal.current_rate?.toFixed(8) }}
                </el-descriptions-item>
                <el-descriptions-item label="策略ID">
                  {{ currentSignal.strategy_id }}
                </el-descriptions-item>
              </el-descriptions>
            </el-card>
          </el-col>

          <el-col :span="12">
            <el-card shadow="never" header="技术指标">
              <el-descriptions :column="1" size="small">
                <el-descriptions-item label="RSI (14)">
                  {{ currentSignal.indicators?.rsi?.toFixed(2) || '-' }}
                </el-descriptions-item>
                <el-descriptions-item label="MACD">
                  {{ currentSignal.indicators?.macd ? currentSignal.indicators.macd.toFixed(4) : '-' }}
                </el-descriptions-item>
                <el-descriptions-item label="MACD Signal">
                  {{ currentSignal.indicators?.macd_signal ? currentSignal.indicators.macd_signal.toFixed(4) : '-' }}
                </el-descriptions-item>
                <el-descriptions-item label="MA Fast (10)">
                  {{ currentSignal.indicators?.ma_fast ? '$' + currentSignal.indicators.ma_fast.toFixed(2) : '-' }}
                </el-descriptions-item>
                <el-descriptions-item label="MA Slow (20)">
                  {{ currentSignal.indicators?.ma_slow ? '$' + currentSignal.indicators.ma_slow.toFixed(2) : '-' }}
                </el-descriptions-item>
                <el-descriptions-item label="Volume 24h">
                  {{ currentSignal.metadata?.volume_24h ? formatVolume(currentSignal.metadata.volume_24h) : '-' }}
                </el-descriptions-item>
                <el-descriptions-item label="Price Change 24h">
                  <span :style="{ color: getPriceChangeColor(currentSignal.metadata?.price_change_24h) }">
                    {{ currentSignal.metadata?.price_change_24h ? (currentSignal.metadata.price_change_24h > 0 ? '+' : '') + currentSignal.metadata.price_change_24h.toFixed(2) + '%' : '-' }}
                  </span>
                </el-descriptions-item>
              </el-descriptions>
            </el-card>
          </el-col>
        </el-row>

        <!-- 信号触发逻辑 -->
        <el-card shadow="never" header="信号触发逻辑" style="margin-bottom: 20px" v-if="currentSignal.trigger_logic">
          <div style="padding-left: 16px">
            <div v-for="(logic, index) in currentSignal.trigger_logic" :key="index" style="margin-bottom: 8px">
              <el-icon color="#67C23A"><Check /></el-icon>
              <span style="margin-left: 8px; color: #606266">{{ logic }}</span>
            </div>
          </div>
        </el-card>

        <!-- 通知状态 -->
        <el-card shadow="never" header="通知状态" v-if="currentSignal.notification_sent">
          <el-descriptions :column="2" size="small">
            <el-descriptions-item label="通知优先级">
              <el-tag v-if="currentSignal.priority === 'P2'" type="danger">P2 (立即发送)</el-tag>
              <el-tag v-else-if="currentSignal.priority === 'P1'" type="warning">P1 (1分钟内)</el-tag>
              <el-tag v-else-if="currentSignal.priority === 'P0'" type="info">P0 (批量通知)</el-tag>
              <el-tag v-else>未设置</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="发送时间">
              {{ currentSignal.notification_time || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="发送渠道" :span="2">
              <el-space wrap v-if="currentSignal.notification_channels && currentSignal.notification_channels.length > 0">
                <el-tag v-for="channel in currentSignal.notification_channels" :key="channel" size="small" type="success">
                  ✓ {{ getChannelName(channel) }}
                </el-tag>
              </el-space>
              <span v-else>-</span>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>

        <!-- 盈亏信息（如果有） -->
        <el-card shadow="never" header="盈亏信息" v-if="currentSignal.entry_price" style="margin-top: 20px">
          <el-descriptions :column="2" size="small">
            <el-descriptions-item label="入场价格">
              ${{ currentSignal.entry_price.toFixed(8) }}
            </el-descriptions-item>
            <el-descriptions-item label="当前价格">
              ${{ currentSignal.current_rate?.toFixed(8) }}
            </el-descriptions-item>
            <el-descriptions-item label="盈亏比">
              <span v-if="currentSignal.profit_ratio" :style="{ color: currentSignal.profit_ratio > 0 ? '#67C23A' : '#F56C6C', fontWeight: 'bold' }">
                {{ currentSignal.profit_ratio > 0 ? '+' : '' }}{{ (currentSignal.profit_ratio * 100).toFixed(2) }}%
              </span>
              <span v-else>-</span>
            </el-descriptions-item>
            <el-descriptions-item label="盈亏金额">
              <span v-if="currentSignal.profit_abs" :style="{ color: currentSignal.profit_abs > 0 ? '#67C23A' : '#F56C6C', fontWeight: 'bold' }">
                {{ currentSignal.profit_abs > 0 ? '+' : '' }}${{ currentSignal.profit_abs.toFixed(2) }}
              </span>
              <span v-else>-</span>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </div>

      <template #footer>
        <el-button @click="showDetailDialog = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Check } from '@element-plus/icons-vue'
import { signalAPI } from '@/api'

const loading = ref(false)
const signals = ref([])
const statistics = ref({})
const showDetailDialog = ref(false)
const currentSignal = ref(null)

const searchForm = reactive({
  pair: '',
  action: '',
  strength_level: '',
  hours: 24
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

const getStrengthColor = (strength) => {
  if (strength >= 0.8) return '#67C23A'
  if (strength >= 0.6) return '#E6A23C'
  if (strength >= 0.4) return '#909399'
  return '#F56C6C'
}

const fetchData = async () => {
  loading.value = true
  try {
    const params = {
      ...searchForm,
      skip: (pagination.page - 1) * pagination.pageSize,
      limit: pagination.pageSize
    }

    const res = await signalAPI.list(params)
    signals.value = res.signals
    pagination.total = res.total

    // 获取统计信息
    const stats = await signalAPI.statistics({ hours: searchForm.hours })
    statistics.value = stats
  } catch (error) {
    ElMessage.error('获取信号列表失败')
  } finally {
    loading.value = false
  }
}

const resetSearch = () => {
  searchForm.pair = ''
  searchForm.action = ''
  searchForm.strength_level = ''
  searchForm.hours = 24
  pagination.page = 1
  fetchData()
}

const handleView = async (row) => {
  try {
    const detail = await signalAPI.get(row.id)
    currentSignal.value = detail
    showDetailDialog.value = true
  } catch (error) {
    ElMessage.error('获取信号详情失败')
  }
}

// 辅助函数
const formatVolume = (volume) => {
  if (!volume) return '-'
  if (volume >= 1000000) {
    return (volume / 1000000).toFixed(2) + 'M'
  } else if (volume >= 1000) {
    return (volume / 1000).toFixed(2) + 'K'
  }
  return volume.toFixed(2)
}

const getPriceChangeColor = (change) => {
  if (!change) return '#606266'
  return change > 0 ? '#67C23A' : '#F56C6C'
}

const getChannelName = (channel) => {
  const channelMap = {
    'sms': '短信',
    'feishu': '飞书',
    'wechat': '微信',
    'email': '邮件',
    'telegram': 'Telegram'
  }
  return channelMap[channel] || channel
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.signals {
  padding: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.search-form {
  margin-bottom: 16px;
}
</style>
