<template>
  <div class="proxies">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ t('proxy.title') }}</span>
          <el-button type="primary" @click="handleCreate">
            <el-icon><Plus /></el-icon>
            {{ t('proxy.create') }}
          </el-button>
        </div>
      </template>

      <!-- 代理列表 -->
      <el-table
        :data="proxies"
        v-loading="loading"
        style="width: 100%"
      >
        <el-table-column prop="priority" :label="t('proxy.priority')" width="80" sortable>
          <template #default="{ row }">
            <div style="display: flex; align-items: center; gap: 4px">
              <span>{{ row.priority }}</span>
              <el-button-group size="small">
                <el-button
                  :icon="ArrowUp"
                  size="small"
                  @click="handleMovePriority(row, 'up')"
                  :disabled="row.priority === 1"
                />
                <el-button
                  :icon="ArrowDown"
                  size="small"
                  @click="handleMovePriority(row, 'down')"
                  :disabled="row.priority === proxies.length"
                />
              </el-button-group>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="name" :label="t('proxy.name')" min-width="150" />

        <el-table-column :label="t('proxy.type')" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ row.type.toUpperCase() }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column :label="t('proxy.address')" min-width="250">
          <template #default="{ row }">
            <span>{{ row.host }}:{{ row.port }}</span>
            <span v-if="row.username" style="margin-left: 8px; color: #909399; font-size: 12px">
              ({{ row.username }})
            </span>
          </template>
        </el-table-column>

        <el-table-column :label="t('proxy.healthStatus')" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.status === 'healthy'" type="success">{{ t('proxy.healthy') }} ✓</el-tag>
            <el-tag v-else-if="row.status === 'unhealthy'" type="danger">{{ t('proxy.unhealthy') }} ✗</el-tag>
            <el-tag v-else type="info">{{ t('proxy.unknown') }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column :label="t('proxy.performanceMetrics')" width="200">
          <template #default="{ row }">
            <div v-if="row.performance_metrics" style="font-size: 12px">
              <div>{{ t('proxy.successRate') }}: {{ row.performance_metrics.success_rate?.toFixed(1) }}%</div>
              <div style="margin-top: 2px">
                {{ t('proxy.latency') }}: {{ row.performance_metrics.avg_latency_ms }}ms
              </div>
            </div>
            <span v-else style="color: #909399">-</span>
          </template>
        </el-table-column>

        <el-table-column :label="t('proxy.requestStats')" width="150">
          <template #default="{ row }">
            <div v-if="row.performance_metrics" style="font-size: 12px">
              <div>{{ t('proxy.totalRequests') }}: {{ row.performance_metrics.total_requests || 0 }}</div>
              <div style="margin-top: 2px; color: #F56C6C">
                {{ t('proxy.failedRequests') }}: {{ row.performance_metrics.failed_requests || 0 }}
              </div>
            </div>
            <span v-else style="color: #909399">-</span>
          </template>
        </el-table-column>

        <el-table-column :label="t('proxy.lastCheck')" width="150">
          <template #default="{ row }">
            <span v-if="row.performance_metrics?.last_success_time" style="font-size: 12px">
              {{ formatRelativeTime(row.performance_metrics.last_success_time) }}
            </span>
            <span v-else style="color: #909399">{{ t('proxy.notChecked') }}</span>
          </template>
        </el-table-column>

        <el-table-column :label="t('proxy.status')" width="100">
          <template #default="{ row }">
            <el-switch
              v-model="row.enabled"
              @change="handleToggleEnabled(row)"
            />
          </template>
        </el-table-column>

        <el-table-column :label="t('common.edit')" width="240" fixed="right">
          <template #default="{ row }">
            <el-button
              type="primary"
              size="small"
              @click="handleTest(row)"
              :loading="testingProxyId === row.id"
            >
              {{ t('proxy.test') }}
            </el-button>
            <el-button
              type="warning"
              size="small"
              @click="handleEdit(row)"
            >
              {{ t('common.edit') }}
            </el-button>
            <el-button
              type="danger"
              size="small"
              @click="handleDelete(row)"
            >
              {{ t('common.delete') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 健康检查配置 -->
    <el-card style="margin-top: 12px">
      <template #header>
        <div class="card-header">
          <span>{{ t('proxy.healthCheckConfig') }}</span>
          <el-button size="small" @click="saveHealthCheckConfig">
            {{ t('proxy.saveConfig') }}
          </el-button>
        </div>
      </template>

      <el-form :model="healthCheckConfig" label-width="140px">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item :label="t('proxy.checkInterval')">
              <el-input-number
                v-model="healthCheckConfig.interval_seconds"
                :min="60"
                :max="3600"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>

          <el-col :span="8">
            <el-form-item :label="t('proxy.timeoutSeconds')">
              <el-input-number
                v-model="healthCheckConfig.timeout_seconds"
                :min="5"
                :max="60"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>

          <el-col :span="8">
            <el-form-item :label="t('proxy.retryCount')">
              <el-input-number
                v-model="healthCheckConfig.retry_count"
                :min="1"
                :max="5"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item :label="t('proxy.testUrl')">
          <el-input
            v-model="healthCheckConfig.test_url"
            placeholder="https://api.binance.com/api/v3/ping"
          />
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 创建/编辑代理对话框 -->
    <el-dialog
      v-model="showProxyDialog"
      :title="dialogMode === 'create' ? t('proxy.create') : t('proxy.edit')"
      width="600px"
    >
      <el-form
        ref="proxyFormRef"
        :model="proxyForm"
        :rules="proxyRules"
        label-width="120px"
      >
        <el-form-item :label="t('proxy.proxyName')" prop="name">
          <el-input v-model="proxyForm.name" :placeholder="t('proxy.namePlaceholder')" />
        </el-form-item>

        <el-form-item :label="t('proxy.proxyType')" prop="type">
          <el-select v-model="proxyForm.type" style="width: 100%">
            <el-option label="SOCKS5" value="socks5" />
            <el-option label="HTTP" value="http" />
            <el-option label="HTTPS" value="https" />
          </el-select>
        </el-form-item>

        <el-row :gutter="10">
          <el-col :span="16">
            <el-form-item :label="t('proxy.hostAddress')" prop="host">
              <el-input v-model="proxyForm.host" :placeholder="t('proxy.hostPlaceholder')" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item :label="t('proxy.port')" prop="port">
              <el-input-number
                v-model="proxyForm.port"
                :min="1"
                :max="65535"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">{{ t('proxy.authInfo') }}</el-divider>

        <el-form-item :label="t('proxy.username')">
          <el-input v-model="proxyForm.username" :placeholder="t('proxy.noAuthPlaceholder')" />
        </el-form-item>

        <el-form-item :label="t('proxy.password')">
          <el-input
            v-model="proxyForm.password"
            type="password"
            show-password
            :placeholder="t('proxy.noAuthPlaceholder')"
          />
        </el-form-item>

        <el-form-item :label="t('proxy.enable')">
          <el-switch v-model="proxyForm.enabled" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showProxyDialog = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="handleSave" :loading="submitting">
          {{ dialogMode === 'create' ? t('common.create') : t('common.save') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, ArrowUp, ArrowDown } from '@element-plus/icons-vue'
import { proxyAPI } from '@/api'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const loading = ref(false)
const submitting = ref(false)
const proxies = ref([])
const showProxyDialog = ref(false)
const dialogMode = ref('create')
const proxyFormRef = ref(null)
const testingProxyId = ref(null)

// 健康检查配置
const healthCheckConfig = reactive({
  interval_seconds: 3600,
  timeout_seconds: 10,
  retry_count: 3,
  test_url: 'https://api.binance.com/api/v3/ping'
})

// 代理表单
const proxyForm = reactive({
  id: null,
  name: '',
  type: 'socks5',
  host: '',
  port: 1080,
  username: '',
  password: '',
  enabled: true,
  priority: null
})

// 表单验证规则
const proxyRules = {
  name: [{ required: true, message: t('proxy.nameRequired'), trigger: 'blur' }],
  type: [{ required: true, message: t('proxy.typeRequired'), trigger: 'change' }],
  host: [{ required: true, message: t('proxy.hostRequired'), trigger: 'blur' }],
  port: [
    { required: true, message: t('proxy.portRequired'), trigger: 'blur' },
    { type: 'number', min: 1, max: 65535, message: t('proxy.portRange'), trigger: 'blur' }
  ]
}

// 加载代理列表
const fetchProxies = async () => {
  loading.value = true
  try {
    const res = await proxyAPI.list()
    proxies.value = res.proxies.sort((a, b) => a.priority - b.priority)
  } catch (error) {
    console.error('Failed to fetch proxies:', error)
    ElMessage.error(t('proxy.fetchListFailed'))
  } finally {
    loading.value = false
  }
}

// 添加代理
const handleCreate = () => {
  dialogMode.value = 'create'
  resetProxyForm()
  showProxyDialog.value = true
}

// 编辑代理
const handleEdit = (proxy) => {
  dialogMode.value = 'edit'
  Object.assign(proxyForm, {
    id: proxy.id,
    name: proxy.name,
    type: proxy.type,
    host: proxy.host,
    port: proxy.port,
    username: proxy.username || '',
    password: proxy.password || '',
    enabled: proxy.enabled,
    priority: proxy.priority
  })
  showProxyDialog.value = true
}

// 保存代理
const handleSave = async () => {
  const valid = await proxyFormRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    if (dialogMode.value === 'create') {
      await proxyAPI.create(proxyForm)
      ElMessage.success(t('proxy.proxyCreated'))
    } else {
      await proxyAPI.update(proxyForm.id, proxyForm)
      ElMessage.success(t('proxy.proxyUpdated'))
    }
    showProxyDialog.value = false
    fetchProxies()
  } catch (error) {
    console.error('Failed to save proxy:', error)
    ElMessage.error(dialogMode.value === 'create' ? t('proxy.createFailed') : t('proxy.updateFailed'))
  } finally {
    submitting.value = false
  }
}

// 删除代理
const handleDelete = async (proxy) => {
  try {
    await ElMessageBox.confirm(
      t('proxy.deleteConfirm', { name: proxy.name }),
      t('proxy.confirmDelete'),
      {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        type: 'warning'
      }
    )

    await proxyAPI.delete(proxy.id)
    ElMessage.success(t('proxy.proxyDeleted'))
    fetchProxies()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to delete proxy:', error)
      ElMessage.error(t('proxy.deleteFailed'))
    }
  }
}

// 测试代理
const handleTest = async (proxy) => {
  testingProxyId.value = proxy.id
  try {
    const res = await proxyAPI.test(proxy.id)
    if (res.success) {
      ElMessage.success(t('proxy.testSuccess', { latency: res.latency_ms }))
    } else {
      ElMessage.error(t('proxy.testFailed', { error: res.error }))
    }
  } catch (error) {
    console.error('Failed to test proxy:', error)
    ElMessage.error(t('proxy.testFailedGeneric'))
  } finally {
    testingProxyId.value = null
  }
}

// 切换启用状态
const handleToggleEnabled = async (proxy) => {
  try {
    await proxyAPI.update(proxy.id, { enabled: proxy.enabled })
    ElMessage.success(proxy.enabled ? t('proxy.proxyEnabled') : t('proxy.proxyDisabled'))
  } catch (error) {
    console.error('Failed to toggle proxy:', error)
    ElMessage.error(t('proxy.operationFailed'))
    proxy.enabled = !proxy.enabled // 回滚状态
  }
}

// 调整优先级
const handleMovePriority = async (proxy, direction) => {
  try {
    const currentIndex = proxies.value.findIndex(p => p.id === proxy.id)
    if (
      (direction === 'up' && currentIndex === 0) ||
      (direction === 'down' && currentIndex === proxies.value.length - 1)
    ) {
      return
    }

    const targetIndex = direction === 'up' ? currentIndex - 1 : currentIndex + 1
    const targetProxy = proxies.value[targetIndex]

    // 交换优先级
    await proxyAPI.swapPriority(proxy.id, targetProxy.id)

    ElMessage.success(t('proxy.priorityAdjusted'))
    fetchProxies()
  } catch (error) {
    console.error('Failed to move priority:', error)
    ElMessage.error(t('proxy.adjustPriorityFailed'))
  }
}

// 保存健康检查配置
const saveHealthCheckConfig = async () => {
  try {
    await proxyAPI.updateHealthCheckConfig(healthCheckConfig)
    ElMessage.success(t('proxy.healthCheckSaved'))
  } catch (error) {
    console.error('Failed to save health check config:', error)
    ElMessage.error(t('proxy.saveHealthCheckFailed'))
  }
}

// 加载健康检查配置
const loadHealthCheckConfig = async () => {
  try {
    const res = await proxyAPI.getHealthCheckConfig()
    Object.assign(healthCheckConfig, res)
  } catch (error) {
    console.error('Failed to load health check config:', error)
  }
}

// 重置表单
const resetProxyForm = () => {
  proxyForm.id = null
  proxyForm.name = ''
  proxyForm.type = 'socks5'
  proxyForm.host = ''
  proxyForm.port = 1080
  proxyForm.username = ''
  proxyForm.password = ''
  proxyForm.enabled = true
  proxyForm.priority = null
}

// 格式化相对时间
const formatRelativeTime = (timestamp) => {
  const now = new Date()
  const time = new Date(timestamp)
  const diff = (now - time) / 1000 // 秒

  if (diff < 60) {
    return t('proxy.justNow')
  } else if (diff < 3600) {
    return t('proxy.minutesAgo', { n: Math.floor(diff / 60) })
  } else if (diff < 86400) {
    return t('proxy.hoursAgo', { n: Math.floor(diff / 3600) })
  } else {
    return t('proxy.daysAgo', { n: Math.floor(diff / 86400) })
  }
}

onMounted(() => {
  fetchProxies()
  loadHealthCheckConfig()
})
</script>

<style scoped>
.proxies {
  padding: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
