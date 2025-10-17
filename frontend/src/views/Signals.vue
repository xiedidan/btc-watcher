<template>
  <div class="signals">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ t('signal.title') }}</span>
          <el-space>
            <el-tag>{{ t('signal.todaySignals') }}: {{ statistics.total_signals || 0 }}</el-tag>
            <el-tag type="success">{{ t('signal.strongSignals') }}: {{ statistics.strong_signals || 0 }}</el-tag>
          </el-space>
        </div>
      </template>

      <!-- 筛选条件 -->
      <el-form :inline="true" class="search-form">
        <el-form-item :label="t('signal.pair')">
          <el-input v-model="searchForm.pair" placeholder="BTC/USDT" clearable style="width: 150px" />
        </el-form-item>

        <el-form-item :label="t('signal.action')">
          <el-select v-model="searchForm.action" :placeholder="t('signal.all')" clearable style="width: 120px">
            <el-option :label="t('signal.all')" value="" />
            <el-option :label="t('signal.buy')" value="buy" />
            <el-option :label="t('signal.sell')" value="sell" />
          </el-select>
        </el-form-item>

        <el-form-item :label="t('signal.strength')">
          <el-select v-model="searchForm.strength_level" :placeholder="t('signal.all')" clearable style="width: 120px">
            <el-option :label="t('signal.all')" value="" />
            <el-option :label="t('signal.strong')" value="strong" />
            <el-option :label="t('signal.medium')" value="medium" />
            <el-option :label="t('signal.weak')" value="weak" />
          </el-select>
        </el-form-item>

        <el-form-item :label="t('signal.timeRange')">
          <el-select v-model="searchForm.hours" :placeholder="t('signal.hours24')" style="width: 120px">
            <el-option :label="t('signal.hour1')" :value="1" />
            <el-option :label="t('signal.hours6')" :value="6" />
            <el-option :label="t('signal.hours24')" :value="24" />
            <el-option :label="t('signal.days7')" :value="168" />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="fetchData">{{ t('signal.query') }}</el-button>
          <el-button @click="resetSearch">{{ t('signal.reset') }}</el-button>
        </el-form-item>
      </el-form>

      <!-- 信号列表 -->
      <el-table
        :data="signals"
        v-loading="loading"
        style="width: 100%"
      >
        <el-table-column prop="id" label="ID" width="80" />

        <el-table-column prop="pair" :label="t('signal.pair')" width="120" />

        <el-table-column :label="t('signal.action')" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.action === 'buy'" type="success">{{ t('signal.buy') }}</el-tag>
            <el-tag v-else-if="row.action === 'sell'" type="danger">{{ t('signal.sell') }}</el-tag>
            <el-tag v-else type="info">{{ t('signal.hold') }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column :label="t('signal.signalStrength')" width="150">
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

        <el-table-column :label="t('signal.strengthLevel')" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.strength_level === 'strong'" type="success">{{ t('signal.strong') }}</el-tag>
            <el-tag v-else-if="row.strength_level === 'medium'" type="warning">{{ t('signal.medium') }}</el-tag>
            <el-tag v-else-if="row.strength_level === 'weak'" type="info">{{ t('signal.weak') }}</el-tag>
            <el-tag v-else type="info">{{ t('signal.ignore') }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="current_rate" :label="t('signal.currentPrice')" width="120">
          <template #default="{ row }">
            ${{ row.current_rate?.toFixed(8) }}
          </template>
        </el-table-column>

        <el-table-column :label="t('signal.profit')" width="100">
          <template #default="{ row }">
            <span v-if="row.profit_ratio" :style="{ color: row.profit_ratio > 0 ? '#67C23A' : '#F56C6C' }">
              {{ (row.profit_ratio * 100).toFixed(2) }}%
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>

        <el-table-column prop="created_at" :label="t('signal.time')" width="180" />

        <el-table-column :label="t('common.detail')" width="120" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="handleView(row)">
              {{ t('signal.detail') }}
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
      :title="t('signal.signalDetail')"
      width="800px"
      destroy-on-close
    >
      <div v-if="currentSignal">
        <!-- 基础信息和技术指标 -->
        <el-row :gutter="16" style="margin-bottom: 20px">
          <el-col :span="12">
            <el-card shadow="never" :header="t('signal.basicInfo')">
              <el-descriptions :column="1" size="small">
                <el-descriptions-item :label="t('signal.pair')">{{ currentSignal.pair }}</el-descriptions-item>
                <el-descriptions-item :label="t('signal.signalType')">
                  <el-tag v-if="currentSignal.action === 'buy'" type="success">{{ t('signal.buy') }} 🟢</el-tag>
                  <el-tag v-else-if="currentSignal.action === 'sell'" type="danger">{{ t('signal.sell') }} 🔴</el-tag>
                  <el-tag v-else type="info">{{ t('signal.hold') }}</el-tag>
                </el-descriptions-item>
                <el-descriptions-item :label="t('signal.signalStrength')">
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
                <el-descriptions-item :label="t('signal.strengthLevel')">
                  <el-tag v-if="currentSignal.strength_level === 'strong'" type="success">{{ t('signal.strongSignalLevel') }}</el-tag>
                  <el-tag v-else-if="currentSignal.strength_level === 'medium'" type="warning">{{ t('signal.mediumSignalLevel') }}</el-tag>
                  <el-tag v-else-if="currentSignal.strength_level === 'weak'" type="info">{{ t('signal.weakSignalLevel') }}</el-tag>
                  <el-tag v-else>{{ t('signal.ignore') }}</el-tag>
                </el-descriptions-item>
                <el-descriptions-item :label="t('signal.triggerTime')">
                  {{ currentSignal.created_at }}
                </el-descriptions-item>
                <el-descriptions-item :label="t('signal.currentPrice')">
                  ${{ currentSignal.current_rate?.toFixed(8) }}
                </el-descriptions-item>
                <el-descriptions-item :label="t('signal.strategyId')">
                  {{ currentSignal.strategy_id }}
                </el-descriptions-item>
              </el-descriptions>
            </el-card>
          </el-col>

          <el-col :span="12">
            <el-card shadow="never" :header="t('signal.technicalIndicators')">
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
                <el-descriptions-item :label="t('signal.volume24h')">
                  {{ currentSignal.metadata?.volume_24h ? formatVolume(currentSignal.metadata.volume_24h) : '-' }}
                </el-descriptions-item>
                <el-descriptions-item :label="t('signal.priceChange24h')">
                  <span :style="{ color: getPriceChangeColor(currentSignal.metadata?.price_change_24h) }">
                    {{ currentSignal.metadata?.price_change_24h ? (currentSignal.metadata.price_change_24h > 0 ? '+' : '') + currentSignal.metadata.price_change_24h.toFixed(2) + '%' : '-' }}
                  </span>
                </el-descriptions-item>
              </el-descriptions>
            </el-card>
          </el-col>
        </el-row>

        <!-- 信号触发逻辑 -->
        <el-card shadow="never" :header="t('signal.triggerLogic')" style="margin-bottom: 20px" v-if="currentSignal.trigger_logic">
          <div style="padding-left: 16px">
            <div v-for="(logic, index) in currentSignal.trigger_logic" :key="index" style="margin-bottom: 8px">
              <el-icon color="#67C23A"><Check /></el-icon>
              <span style="margin-left: 8px; color: #606266">{{ logic }}</span>
            </div>
          </div>
        </el-card>

        <!-- 通知状态 -->
        <el-card shadow="never" :header="t('signal.notificationStatus')" v-if="currentSignal.notification_sent">
          <el-descriptions :column="2" size="small">
            <el-descriptions-item :label="t('signal.notificationPriority')">
              <el-tag v-if="currentSignal.priority === 'P2'" type="danger">{{ t('signal.p2Immediate') }}</el-tag>
              <el-tag v-else-if="currentSignal.priority === 'P1'" type="warning">{{ t('signal.p1Within1Min') }}</el-tag>
              <el-tag v-else-if="currentSignal.priority === 'P0'" type="info">{{ t('signal.p0Batch') }}</el-tag>
              <el-tag v-else>{{ t('signal.notSet') }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item :label="t('signal.sendTime')">
              {{ currentSignal.notification_time || '-' }}
            </el-descriptions-item>
            <el-descriptions-item :label="t('signal.sendChannels')" :span="2">
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
        <el-card shadow="never" :header="t('signal.profitInfo')" v-if="currentSignal.entry_price" style="margin-top: 20px">
          <el-descriptions :column="2" size="small">
            <el-descriptions-item :label="t('signal.entryPrice')">
              ${{ currentSignal.entry_price.toFixed(8) }}
            </el-descriptions-item>
            <el-descriptions-item :label="t('signal.currentPrice')">
              ${{ currentSignal.current_rate?.toFixed(8) }}
            </el-descriptions-item>
            <el-descriptions-item :label="t('signal.profitRatio')">
              <span v-if="currentSignal.profit_ratio" :style="{ color: currentSignal.profit_ratio > 0 ? '#67C23A' : '#F56C6C', fontWeight: 'bold' }">
                {{ currentSignal.profit_ratio > 0 ? '+' : '' }}{{ (currentSignal.profit_ratio * 100).toFixed(2) }}%
              </span>
              <span v-else>-</span>
            </el-descriptions-item>
            <el-descriptions-item :label="t('signal.profitAmount')">
              <span v-if="currentSignal.profit_abs" :style="{ color: currentSignal.profit_abs > 0 ? '#67C23A' : '#F56C6C', fontWeight: 'bold' }">
                {{ currentSignal.profit_abs > 0 ? '+' : '' }}${{ currentSignal.profit_abs.toFixed(2) }}
              </span>
              <span v-else>-</span>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </div>

      <template #footer>
        <el-button @click="showDetailDialog = false">{{ t('common.close') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Check } from '@element-plus/icons-vue'
import { signalAPI } from '@/api'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

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
    ElMessage.error(t('signal.fetchListFailed'))
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
    ElMessage.error(t('signal.fetchDetailFailed'))
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
    'sms': t('settings.smsChannel'),
    'feishu': t('settings.feishuChannel'),
    'wechat': t('settings.wechatChannel'),
    'email': t('settings.emailChannel'),
    'telegram': t('settings.telegramChannel')
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
