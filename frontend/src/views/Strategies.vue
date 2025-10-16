<template>
  <div class="strategies">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>策略管理</span>
          <el-space>
            <el-button size="small" @click="$router.push('/drafts')">
              <el-icon><Document /></el-icon>
              草稿管理
            </el-button>
            <el-button type="primary" @click="handleOpenCreateDialog">
              <el-icon><Plus /></el-icon>
              创建策略
            </el-button>
          </el-space>
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

        <el-table-column label="健康分数" width="150">
          <template #default="{ row }">
            <div style="display: flex; align-items: center; gap: 8px">
              <el-progress
                :percentage="calculateHealthScore(row)"
                :color="getHealthColor(calculateHealthScore(row))"
                :stroke-width="12"
                :show-text="false"
                style="flex: 1"
              />
              <span style="font-size: 12px; min-width: 28px">{{ calculateHealthScore(row) }}分</span>
            </div>
          </template>
        </el-table-column>

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
      <!-- 草稿管理 -->
      <el-alert
        v-if="draftKey"
        title="正在编辑草稿"
        type="info"
        :closable="false"
        style="margin-bottom: 16px"
      >
        <template #default>
          <div style="display: flex; justify-content: space-between; align-items: center">
            <span style="font-size: 12px">草稿会每30秒自动保存</span>
            <div>
              <el-button size="small" @click="saveDraft">立即保存草稿</el-button>
              <el-button size="small" type="danger" @click="handleClearDraft">清除草稿</el-button>
            </div>
          </div>
        </template>
      </el-alert>

      <el-form
        ref="createFormRef"
        :model="createForm"
        :rules="createRules"
        label-width="120px"
      >
        <el-form-item label="策略名称" prop="name">
          <el-input v-model="createForm.name" placeholder="请输入策略名称" />
        </el-form-item>

        <!-- 策略文件上传 -->
        <el-divider content-position="left">策略代码</el-divider>

        <el-form-item label="策略文件" prop="strategy_file">
          <div style="width: 100%">
            <el-upload
              ref="uploadRef"
              :action="uploadAction"
              :headers="uploadHeaders"
              :on-success="handleUploadSuccess"
              :on-error="handleUploadError"
              :before-upload="beforeUpload"
              :file-list="uploadedFiles"
              :limit="1"
              accept=".py"
              :auto-upload="true"
            >
              <el-button type="primary" size="small">
                <el-icon><Upload /></el-icon>
                上传策略文件 (.py)
              </el-button>
            </el-upload>
            <div style="margin-top: 8px; font-size: 12px; color: #909399">
              支持上传Python策略文件，系统将自动扫描策略类
            </div>
          </div>
        </el-form-item>

        <el-form-item label="策略类" prop="strategy_class">
          <el-select
            v-model="createForm.strategy_class"
            placeholder="请先上传策略文件"
            :disabled="availableStrategyClasses.length === 0"
            style="width: 100%"
          >
            <el-option
              v-for="cls in availableStrategyClasses"
              :key="cls.name"
              :label="cls.name"
              :value="cls.name"
            >
              <div style="display: flex; justify-content: space-between">
                <span>{{ cls.name }}</span>
                <span style="color: #8492a6; font-size: 12px">{{ cls.description || '无描述' }}</span>
              </div>
            </el-option>
          </el-select>
          <div v-if="strategyFileInfo" style="margin-top: 8px; font-size: 12px; color: #67C23A">
            ✓ 已加载: {{ strategyFileInfo.filename }} ({{ availableStrategyClasses.length }} 个策略类)
          </div>
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

        <el-divider content-position="left">信号强度阈值配置</el-divider>

        <el-form-item label="强烈信号阈值" label-width="140px">
          <el-row :gutter="10" style="width: 100%">
            <el-col :span="12">
              <el-input-number
                v-model="createForm.signal_thresholds.strong"
                :min="0"
                :max="1"
                :step="0.01"
                :precision="2"
                style="width: 100%"
              />
            </el-col>
            <el-col :span="12">
              <el-tag type="danger" size="small">🔴 P2立即通知</el-tag>
            </el-col>
          </el-row>
          <div style="margin-top: 4px; font-size: 12px; color: #909399">
            信号强度 ≥ {{ createForm.signal_thresholds.strong }} 时发送P2级通知
          </div>
        </el-form-item>

        <el-form-item label="中等信号阈值" label-width="140px">
          <el-row :gutter="10" style="width: 100%">
            <el-col :span="12">
              <el-input-number
                v-model="createForm.signal_thresholds.medium"
                :min="0"
                :max="1"
                :step="0.01"
                :precision="2"
                style="width: 100%"
              />
            </el-col>
            <el-col :span="12">
              <el-tag type="warning" size="small">🟠 P1通知</el-tag>
            </el-col>
          </el-row>
          <div style="margin-top: 4px; font-size: 12px; color: #909399">
            信号强度 ≥ {{ createForm.signal_thresholds.medium }} 时发送P1级通知
          </div>
        </el-form-item>

        <el-form-item label="弱信号阈值" label-width="140px">
          <el-row :gutter="10" style="width: 100%">
            <el-col :span="12">
              <el-input-number
                v-model="createForm.signal_thresholds.weak"
                :min="0"
                :max="1"
                :step="0.01"
                :precision="2"
                style="width: 100%"
              />
            </el-col>
            <el-col :span="12">
              <el-tag type="info" size="small">🟡 P0批量通知</el-tag>
            </el-col>
          </el-row>
          <div style="margin-top: 4px; font-size: 12px; color: #909399">
            信号强度 ≥ {{ createForm.signal_thresholds.weak }} 时发送P0级通知
          </div>
        </el-form-item>

        <el-form-item label="阈值预览" label-width="140px">
          <div style="width: 100%">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px">
              <span style="font-size: 12px; width: 30px">0.0</span>
              <div style="flex: 1; height: 20px; background: linear-gradient(to right, #909399 0%, #909399 {{ createForm.signal_thresholds.weak * 100 }}%, #E6A23C {{ createForm.signal_thresholds.weak * 100 }}%, #E6A23C {{ createForm.signal_thresholds.medium * 100 }}%, #F56C6C {{ createForm.signal_thresholds.medium * 100 }}%, #F56C6C {{ createForm.signal_thresholds.strong * 100 }}%, #67C23A {{ createForm.signal_thresholds.strong * 100 }}%, #67C23A 100%); border-radius: 4px; position: relative">
                <div style="position: absolute; left: {{ createForm.signal_thresholds.weak * 100 }}%; top: -24px; transform: translateX(-50%); font-size: 10px; color: #E6A23C">{{ createForm.signal_thresholds.weak }}</div>
                <div style="position: absolute; left: {{ createForm.signal_thresholds.medium * 100 }}%; top: -24px; transform: translateX(-50%); font-size: 10px; color: #F56C6C">{{ createForm.signal_thresholds.medium }}</div>
                <div style="position: absolute; left: {{ createForm.signal_thresholds.strong * 100 }}%; top: -24px; transform: translateX(-50%); font-size: 10px; color: #67C23A">{{ createForm.signal_thresholds.strong }}</div>
              </div>
              <span style="font-size: 12px; width: 30px">1.0</span>
            </div>
            <div style="display: flex; gap: 16px; font-size: 12px; color: #606266; margin-top: 16px">
              <span>⚪ 忽略 (< {{ createForm.signal_thresholds.weak }})</span>
              <span>🟡 弱 ({{ createForm.signal_thresholds.weak }} - {{ createForm.signal_thresholds.medium }})</span>
              <span>🟠 中 ({{ createForm.signal_thresholds.medium }} - {{ createForm.signal_thresholds.strong }})</span>
              <span>🔴 强 (≥ {{ createForm.signal_thresholds.strong }})</span>
            </div>
          </div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleCreate">
          创建
        </el-button>
      </template>
    </el-dialog>

    <!-- 策略详情对话框 -->
    <el-dialog
      v-model="showDetailDialog"
      title="策略详情"
      width="800px"
      destroy-on-close
    >
      <div v-if="currentStrategy">
        <!-- 基础信息和运行状态 -->
        <el-row :gutter="16" style="margin-bottom: 20px">
          <el-col :span="12">
            <el-card shadow="never" header="基础信息">
              <el-descriptions :column="1" size="small">
                <el-descriptions-item label="策略ID">{{ currentStrategy.id }}</el-descriptions-item>
                <el-descriptions-item label="策略名称">{{ currentStrategy.name }}</el-descriptions-item>
                <el-descriptions-item label="策略类型">信号监控策略</el-descriptions-item>
                <el-descriptions-item label="版本">{{ currentStrategy.version }}</el-descriptions-item>
                <el-descriptions-item label="创建时间">
                  {{ formatDateTime(currentStrategy.created_at) }}
                </el-descriptions-item>
                <el-descriptions-item label="最后修改">
                  {{ formatDateTime(currentStrategy.updated_at) }}
                </el-descriptions-item>
              </el-descriptions>
            </el-card>
          </el-col>

          <el-col :span="12">
            <el-card shadow="never" header="运行状态">
              <el-descriptions :column="1" size="small">
                <el-descriptions-item label="状态">
                  <el-tag v-if="currentStrategy.status === 'running'" type="success">运行中</el-tag>
                  <el-tag v-else-if="currentStrategy.status === 'stopped'" type="info">已停止</el-tag>
                  <el-tag v-else type="danger">错误</el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="健康分数">
                  <div style="display: flex; align-items: center; gap: 8px">
                    <el-progress
                      :percentage="calculateHealthScore(currentStrategy)"
                      :color="getHealthColor(calculateHealthScore(currentStrategy))"
                      :stroke-width="16"
                      :show-text="false"
                      style="flex: 1; max-width: 120px"
                    />
                    <span>{{ calculateHealthScore(currentStrategy) }}/100</span>
                  </div>
                </el-descriptions-item>
                <el-descriptions-item label="运行时长" v-if="currentStrategy.status === 'running'">
                  {{ calculateUptime(currentStrategy.started_at) }}
                </el-descriptions-item>
                <el-descriptions-item label="启动时间" v-if="currentStrategy.started_at">
                  {{ formatDateTime(currentStrategy.started_at) }}
                </el-descriptions-item>
                <el-descriptions-item label="停止时间" v-if="currentStrategy.stopped_at">
                  {{ formatDateTime(currentStrategy.stopped_at) }}
                </el-descriptions-item>
                <el-descriptions-item label="PID" v-if="currentStrategy.process_id">
                  {{ currentStrategy.process_id }}
                </el-descriptions-item>
                <el-descriptions-item label="端口" v-if="currentStrategy.port">
                  {{ currentStrategy.port }}
                </el-descriptions-item>
              </el-descriptions>
            </el-card>
          </el-col>
        </el-row>

        <!-- 配置信息 -->
        <el-card shadow="never" header="配置信息" style="margin-bottom: 20px">
          <el-descriptions :column="2" size="small">
            <el-descriptions-item label="策略类">
              {{ currentStrategy.strategy_class }}
            </el-descriptions-item>
            <el-descriptions-item label="交易所">
              {{ currentStrategy.exchange }}
            </el-descriptions-item>
            <el-descriptions-item label="时间周期">
              {{ currentStrategy.timeframe }}
            </el-descriptions-item>
            <el-descriptions-item label="模拟交易">
              <el-tag :type="currentStrategy.dry_run ? 'success' : 'warning'">
                {{ currentStrategy.dry_run ? '是' : '否' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="交易对" :span="2">
              <el-space wrap>
                <el-tag v-for="pair in currentStrategy.pair_whitelist" :key="pair" size="small">
                  {{ pair }}
                </el-tag>
              </el-space>
            </el-descriptions-item>
            <el-descriptions-item label="最大持仓数">
              {{ currentStrategy.max_open_trades }}
            </el-descriptions-item>
            <el-descriptions-item label="钱包金额" v-if="currentStrategy.dry_run">
              {{ currentStrategy.dry_run_wallet }} USDT
            </el-descriptions-item>
          </el-descriptions>

          <el-divider content-position="left">信号强度阈值</el-divider>
          <el-descriptions :column="3" size="small" v-if="currentStrategy.signal_thresholds">
            <el-descriptions-item label="强信号">
              ≥ {{ currentStrategy.signal_thresholds.strong || 0.8 }}
            </el-descriptions-item>
            <el-descriptions-item label="中等信号">
              ≥ {{ currentStrategy.signal_thresholds.medium || 0.6 }}
            </el-descriptions-item>
            <el-descriptions-item label="弱信号">
              ≥ {{ currentStrategy.signal_thresholds.weak || 0.4 }}
            </el-descriptions-item>
          </el-descriptions>

          <div v-if="currentStrategy.description" style="margin-top: 16px">
            <el-divider content-position="left">策略描述</el-divider>
            <p style="color: #606266; line-height: 1.6">{{ currentStrategy.description }}</p>
          </div>
        </el-card>

        <!-- 操作按钮 -->
        <div style="display: flex; justify-content: flex-end; gap: 8px">
          <el-button @click="showDetailDialog = false">关闭</el-button>
          <el-button
            v-if="currentStrategy.status === 'stopped'"
            type="success"
            @click="handleStartFromDetail"
          >
            启动策略
          </el-button>
          <el-button
            v-else-if="currentStrategy.status === 'running'"
            type="warning"
            @click="handleStopFromDetail"
          >
            停止策略
          </el-button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Upload, Document } from '@element-plus/icons-vue'
import { useStrategyStore } from '@/stores/strategy'
import { useUserStore } from '@/stores/user'

const strategyStore = useStrategyStore()
const userStore = useUserStore()

const loading = ref(false)
const submitting = ref(false)
const strategies = ref([])
const selectedStrategies = ref([])
const showCreateDialog = ref(false)
const showDetailDialog = ref(false)
const createFormRef = ref(null)
const uploadRef = ref(null)
const currentStrategy = ref(null)
let autoSaveTimer = null
let draftKey = null

// 文件上传相关状态
const uploadedFiles = ref([])
const availableStrategyClasses = ref([])
const strategyFileInfo = ref(null)

// 上传配置
const uploadAction = computed(() => {
  return `${import.meta.env.VITE_API_URL}/api/v1/strategies/upload`
})

const uploadHeaders = computed(() => {
  return {
    'Authorization': `Bearer ${userStore.token}`
  }
})

const searchForm = reactive({
  status: ''
})

const createForm = reactive({
  name: '',
  strategy_class: '',
  strategy_file: null,
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
  strategy_class: [{ required: true, message: '请选择策略类', trigger: 'change' }],
  exchange: [{ required: true, message: '请选择交易所', trigger: 'change' }],
  timeframe: [{ required: true, message: '请选择时间周期', trigger: 'change' }],
  pair_whitelist: [{ required: true, message: '请选择交易对', trigger: 'change' }]
}

// 文件上传处理函数
const beforeUpload = (file) => {
  const isPython = file.name.endsWith('.py')
  const isLt10M = file.size / 1024 / 1024 < 10

  if (!isPython) {
    ElMessage.error('只能上传 Python 文件（.py）')
    return false
  }

  if (!isLt10M) {
    ElMessage.error('文件大小不能超过 10MB')
    return false
  }

  return true
}

const handleUploadSuccess = (response, file, fileList) => {
  if (response.success) {
    ElMessage.success('策略文件上传成功')

    // 保存文件信息
    strategyFileInfo.value = {
      filename: file.name,
      file_id: response.file_id,
      file_path: response.file_path
    }

    // 更新已上传文件列表
    uploadedFiles.value = fileList

    // 更新可用策略类列表
    availableStrategyClasses.value = response.strategy_classes || []

    // 保存文件ID到表单
    createForm.strategy_file = response.file_id

    // 如果只有一个策略类，自动选中
    if (availableStrategyClasses.value.length === 1) {
      createForm.strategy_class = availableStrategyClasses.value[0].name
      ElMessage.info('已自动选择唯一的策略类')
    }
  } else {
    ElMessage.error(response.message || '文件上传失败')
  }
}

const handleUploadError = (error, file) => {
  console.error('Upload error:', error)
  ElMessage.error('文件上传失败，请重试')
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

const handleView = async (row) => {
  try {
    const detail = await strategyStore.fetchStrategy(row.id)
    currentStrategy.value = detail
    showDetailDialog.value = true
  } catch (error) {
    ElMessage.error('获取策略详情失败')
  }
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

const handleOpenCreateDialog = () => {
  // 重置表单
  createForm.name = ''
  createForm.strategy_class = ''
  createForm.strategy_file = null

  // 重置文件上传相关状态
  uploadedFiles.value = []
  availableStrategyClasses.value = []
  strategyFileInfo.value = null

  showCreateDialog.value = true
}

const handleCreate = async () => {
  const valid = await createFormRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    await strategyStore.createStrategy(createForm)
    ElMessage.success('策略创建成功')
    // 清除草稿
    clearDraft()
    showCreateDialog.value = false
    fetchData()
  } catch (error) {
    ElMessage.error('策略创建失败')
  } finally {
    submitting.value = false
  }
}

// 辅助函数
const formatDateTime = (dateString) => {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

const calculateUptime = (startedAt) => {
  if (!startedAt) return '-'
  const start = new Date(startedAt)
  const now = new Date()
  const diff = now - start

  const hours = Math.floor(diff / (1000 * 60 * 60))
  const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))

  if (hours > 0) {
    return `${hours}小时${minutes}分钟`
  } else {
    return `${minutes}分钟`
  }
}

// 计算健康分数（简化版本）
const calculateHealthScore = (strategy) => {
  if (strategy.status === 'stopped') {
    return 0
  } else if (strategy.status === 'error') {
    return 15
  } else if (strategy.status === 'running') {
    // 运行中基础分数90分
    let score = 90

    // 有端口信息加5分
    if (strategy.port) {
      score += 5
    }

    // 有进程ID加5分
    if (strategy.process_id) {
      score += 5
    }

    return Math.min(100, score)
  }

  return 50
}

// 获取健康分数颜色
const getHealthColor = (score) => {
  if (score >= 80) return '#67C23A'  // 绿色
  if (score >= 60) return '#E6A23C'  // 橙色
  if (score >= 30) return '#F56C6C'  // 红色
  return '#909399'  // 灰色
}

const handleStartFromDetail = async () => {
  try {
    await handleStart(currentStrategy.value)
    // 重新获取详情
    const detail = await strategyStore.fetchStrategy(currentStrategy.value.id)
    currentStrategy.value = detail
  } catch (error) {
    // 错误已在handleStart中处理
  }
}

const handleStopFromDetail = async () => {
  try {
    await handleStop(currentStrategy.value)
    // 重新获取详情
    const detail = await strategyStore.fetchStrategy(currentStrategy.value.id)
    currentStrategy.value = detail
  } catch (error) {
    // 错误已在handleStop中处理
  }
}

// 草稿管理功能
const saveDraft = () => {
  try {
    const draft = {
      ...createForm,
      draftId: draftKey || Date.now().toString(),
      savedAt: new Date().toISOString(),
      status: 'draft'
    }

    if (!draftKey) {
      draftKey = draft.draftId
    }

    localStorage.setItem(`strategy_draft_${draft.draftId}`, JSON.stringify(draft))

    // 保存草稿列表索引
    const drafts = JSON.parse(localStorage.getItem('strategy_drafts') || '[]')
    if (!drafts.includes(draft.draftId)) {
      drafts.push(draft.draftId)
      localStorage.setItem('strategy_drafts', JSON.stringify(drafts))
    }

    console.log('Draft saved:', draft.draftId)
  } catch (error) {
    console.error('Failed to save draft:', error)
  }
}

const loadDraft = (draftId) => {
  try {
    const draft = localStorage.getItem(`strategy_draft_${draftId}`)
    if (draft) {
      const draftData = JSON.parse(draft)
      Object.assign(createForm, {
        name: draftData.name,
        strategy_class: draftData.strategy_class,
        exchange: draftData.exchange,
        timeframe: draftData.timeframe,
        pair_whitelist: draftData.pair_whitelist,
        pair_blacklist: draftData.pair_blacklist,
        dry_run: draftData.dry_run,
        dry_run_wallet: draftData.dry_run_wallet,
        stake_amount: draftData.stake_amount,
        max_open_trades: draftData.max_open_trades,
        signal_thresholds: draftData.signal_thresholds
      })
      draftKey = draftId
      ElMessage.success('草稿已加载')
    }
  } catch (error) {
    console.error('Failed to load draft:', error)
    ElMessage.error('加载草稿失败')
  }
}

const clearDraft = () => {
  if (draftKey) {
    try {
      localStorage.removeItem(`strategy_draft_${draftKey}`)

      // 从草稿列表中移除
      const drafts = JSON.parse(localStorage.getItem('strategy_drafts') || '[]')
      const index = drafts.indexOf(draftKey)
      if (index > -1) {
        drafts.splice(index, 1)
        localStorage.setItem('strategy_drafts', JSON.stringify(drafts))
      }

      draftKey = null
      console.log('Draft cleared')
    } catch (error) {
      console.error('Failed to clear draft:', error)
    }
  }
}

const handleClearDraft = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要清除草稿吗？此操作不可撤销。',
      '确认清除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    clearDraft()
    ElMessage.success('草稿已清除')
  } catch (error) {
    // 用户取消
  }
}

const startAutoSave = () => {
  // 每30秒自动保存一次
  autoSaveTimer = setInterval(() => {
    if (showCreateDialog.value && createForm.name) {
      saveDraft()
    }
  }, 30000)
}

const stopAutoSave = () => {
  if (autoSaveTimer) {
    clearInterval(autoSaveTimer)
    autoSaveTimer = null
  }
}

// 监听对话框关闭，停止自动保存
watch(showCreateDialog, (newVal) => {
  if (newVal) {
    startAutoSave()
  } else {
    stopAutoSave()
  }
})

onMounted(() => {
  fetchData()
})

onUnmounted(() => {
  stopAutoSave()
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
