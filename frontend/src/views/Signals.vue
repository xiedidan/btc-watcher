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
      width="600px"
    >
      <el-descriptions :column="2" border v-if="currentSignal">
        <el-descriptions-item label="ID">{{ currentSignal.id }}</el-descriptions-item>
        <el-descriptions-item label="策略ID">{{ currentSignal.strategy_id }}</el-descriptions-item>
        <el-descriptions-item label="交易对">{{ currentSignal.pair }}</el-descriptions-item>
        <el-descriptions-item label="动作">
          <el-tag v-if="currentSignal.action === 'buy'" type="success">买入</el-tag>
          <el-tag v-else-if="currentSignal.action === 'sell'" type="danger">卖出</el-tag>
          <el-tag v-else type="info">持有</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="信号强度">
          {{ (currentSignal.signal_strength * 100).toFixed(2) }}%
        </el-descriptions-item>
        <el-descriptions-item label="强度等级">
          <el-tag v-if="currentSignal.strength_level === 'strong'" type="success">强</el-tag>
          <el-tag v-else-if="currentSignal.strength_level === 'medium'" type="warning">中</el-tag>
          <el-tag v-else type="info">弱</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="当前价格">
          ${{ currentSignal.current_rate?.toFixed(8) }}
        </el-descriptions-item>
        <el-descriptions-item label="入场价格">
          {{ currentSignal.entry_price ? '$' + currentSignal.entry_price.toFixed(8) : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="盈亏比">
          <span v-if="currentSignal.profit_ratio" :style="{ color: currentSignal.profit_ratio > 0 ? '#67C23A' : '#F56C6C' }">
            {{ (currentSignal.profit_ratio * 100).toFixed(2) }}%
          </span>
          <span v-else>-</span>
        </el-descriptions-item>
        <el-descriptions-item label="盈亏金额">
          {{ currentSignal.profit_abs ? '$' + currentSignal.profit_abs.toFixed(2) : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="创建时间" :span="2">
          {{ currentSignal.created_at }}
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
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
