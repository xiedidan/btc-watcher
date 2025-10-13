<template>
  <div class="strategies">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>策略管理</span>
          <el-button type="primary" @click="showCreateDialog = true">
            <el-icon><Plus /></el-icon>
            创建策略
          </el-button>
        </div>
      </template>

      <!-- 搜索栏 -->
      <el-form :inline="true" class="search-form">
        <el-form-item label="状态">
          <el-select v-model="searchForm.status" placeholder="全部" clearable @change="fetchData">
            <el-option label="全部" value="" />
            <el-option label="运行中" value="running" />
            <el-option label="已停止" value="stopped" />
            <el-option label="错误" value="error" />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="fetchData">查询</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>

      <!-- 策略表格 -->
      <el-table
        :data="strategies"
        v-loading="loading"
        style="width: 100%"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="策略名称" min-width="180" />
        <el-table-column prop="strategy_class" label="策略类" width="150" />
        <el-table-column prop="exchange" label="交易所" width="120" />
        <el-table-column prop="port" label="端口" width="100" />

        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.status === 'running'" type="success">运行中</el-tag>
            <el-tag v-else-if="row.status === 'stopped'" type="info">已停止</el-tag>
            <el-tag v-else type="danger">错误</el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="created_at" label="创建时间" width="180" />

        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'stopped'"
              type="success"
              size="small"
              @click="handleStart(row)"
            >
              启动
            </el-button>
            <el-button
              v-else
              type="warning"
              size="small"
              @click="handleStop(row)"
            >
              停止
            </el-button>
            <el-button
              type="primary"
              size="small"
              @click="handleView(row)"
            >
              查看
            </el-button>
            <el-button
              type="danger"
              size="small"
              @click="handleDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 创建策略对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      title="创建策略"
      width="600px"
    >
      <el-form
        ref="createFormRef"
        :model="createForm"
        :rules="createRules"
        label-width="120px"
      >
        <el-form-item label="策略名称" prop="name">
          <el-input v-model="createForm.name" placeholder="请输入策略名称" />
        </el-form-item>

        <el-form-item label="策略类" prop="strategy_class">
          <el-input v-model="createForm.strategy_class" placeholder="例如: SampleStrategy" />
        </el-form-item>

        <el-form-item label="交易所" prop="exchange">
          <el-select v-model="createForm.exchange" placeholder="请选择交易所">
            <el-option label="Binance" value="binance" />
            <el-option label="OKX" value="okx" />
            <el-option label="Huobi" value="huobi" />
          </el-select>
        </el-form-item>

        <el-form-item label="时间周期" prop="timeframe">
          <el-select v-model="createForm.timeframe" placeholder="请选择时间周期">
            <el-option label="1分钟" value="1m" />
            <el-option label="5分钟" value="5m" />
            <el-option label="15分钟" value="15m" />
            <el-option label="1小时" value="1h" />
            <el-option label="4小时" value="4h" />
            <el-option label="1天" value="1d" />
          </el-select>
        </el-form-item>

        <el-form-item label="交易对" prop="pair_whitelist">
          <el-select
            v-model="createForm.pair_whitelist"
            multiple
            filterable
            allow-create
            placeholder="请输入交易对"
          >
            <el-option label="BTC/USDT" value="BTC/USDT" />
            <el-option label="ETH/USDT" value="ETH/USDT" />
            <el-option label="BNB/USDT" value="BNB/USDT" />
          </el-select>
        </el-form-item>

        <el-form-item label="模拟交易">
          <el-switch v-model="createForm.dry_run" />
        </el-form-item>

        <el-form-item label="信号阈值">
          <el-row :gutter="10">
            <el-col :span="8">
              <el-input v-model.number="createForm.signal_thresholds.strong" placeholder="强">
                <template #prepend>强</template>
              </el-input>
            </el-col>
            <el-col :span="8">
              <el-input v-model.number="createForm.signal_thresholds.medium" placeholder="中">
                <template #prepend>中</template>
              </el-input>
            </el-col>
            <el-col :span="8">
              <el-input v-model.number="createForm.signal_thresholds.weak" placeholder="弱">
                <template #prepend>弱</template>
              </el-input>
            </el-col>
          </el-row>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleCreate">
          创建
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useStrategyStore } from '@/stores/strategy'

const strategyStore = useStrategyStore()

const loading = ref(false)
const submitting = ref(false)
const strategies = ref([])
const selectedStrategies = ref([])
const showCreateDialog = ref(false)
const createFormRef = ref(null)

const searchForm = reactive({
  status: ''
})

const createForm = reactive({
  name: '',
  strategy_class: '',
  exchange: 'binance',
  timeframe: '1h',
  pair_whitelist: ['BTC/USDT'],
  pair_blacklist: [],
  dry_run: true,
  dry_run_wallet: 1000,
  stake_amount: null,
  max_open_trades: 3,
  signal_thresholds: {
    strong: 0.8,
    medium: 0.6,
    weak: 0.4
  }
})

const createRules = {
  name: [{ required: true, message: '请输入策略名称', trigger: 'blur' }],
  strategy_class: [{ required: true, message: '请输入策略类', trigger: 'blur' }],
  exchange: [{ required: true, message: '请选择交易所', trigger: 'change' }],
  timeframe: [{ required: true, message: '请选择时间周期', trigger: 'change' }],
  pair_whitelist: [{ required: true, message: '请选择交易对', trigger: 'change' }]
}

const fetchData = async () => {
  loading.value = true
  try {
    const res = await strategyStore.fetchStrategies(searchForm)
    strategies.value = res.strategies
  } catch (error) {
    ElMessage.error('获取策略列表失败')
  } finally {
    loading.value = false
  }
}

const resetSearch = () => {
  searchForm.status = ''
  fetchData()
}

const handleSelectionChange = (selection) => {
  selectedStrategies.value = selection
}

const handleStart = async (row) => {
  try {
    await strategyStore.startStrategy(row.id)
    ElMessage.success('策略启动成功')
    fetchData()
  } catch (error) {
    ElMessage.error('策略启动失败')
  }
}

const handleStop = async (row) => {
  try {
    await strategyStore.stopStrategy(row.id)
    ElMessage.success('策略停止成功')
    fetchData()
  } catch (error) {
    ElMessage.error('策略停止失败')
  }
}

const handleView = (row) => {
  // TODO: 打开策略详情对话框
  ElMessage.info('查看策略详情（待实现）')
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除策略 "${row.name}" 吗？`,
      '警告',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await strategyStore.deleteStrategy(row.id)
    ElMessage.success('策略删除成功')
    fetchData()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('策略删除失败')
    }
  }
}

const handleCreate = async () => {
  const valid = await createFormRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    await strategyStore.createStrategy(createForm)
    ElMessage.success('策略创建成功')
    showCreateDialog.value = false
    fetchData()
  } catch (error) {
    ElMessage.error('策略创建失败')
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.strategies {
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
