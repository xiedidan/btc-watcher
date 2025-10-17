<template>
  <div class="drafts">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ t('drafts.title') }}</span>
          <el-space>
            <el-button type="warning" size="small" @click="handleBatchDelete">
              {{ t('drafts.batchDelete') }}
            </el-button>
            <el-button type="danger" size="small" @click="handleClearExpired">
              {{ t('drafts.clearExpired') }}
            </el-button>
            <el-button size="small" @click="showSettingsDialog = true">
              <el-icon><Setting /></el-icon>
              {{ t('drafts.settings') }}
            </el-button>
          </el-space>
        </div>
      </template>

      <!-- 统计信息 -->
      <el-alert
        :title="t('drafts.statistics', { total: drafts.length, editing: editingCount, expired: expiredCount })"
        type="info"
        :closable="false"
        style="margin-bottom: 16px"
      />

      <!-- 草稿列表 -->
      <el-table
        :data="drafts"
        v-loading="loading"
        style="width: 100%"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />

        <el-table-column prop="name" :label="t('drafts.table.name')" min-width="200">
          <template #default="{ row }">
            <div>
              <span>{{ row.name || t('drafts.unnamed') }}</span>
              <el-tag v-if="row.version" size="small" style="margin-left: 8px">
                {{ row.version }}
              </el-tag>
            </div>
          </template>
        </el-table-column>

        <el-table-column :label="t('drafts.table.status')" width="120">
          <template #default="{ row }">
            <el-tag v-if="isExpired(row)" type="danger">{{ t('drafts.status.expired') }}</el-tag>
            <el-tag v-else-if="isEditing(row)" type="warning">{{ t('drafts.status.editing') }}</el-tag>
            <el-tag v-else type="info">{{ t('drafts.status.saved') }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="savedAt" :label="t('drafts.table.lastModified')" width="180">
          <template #default="{ row }">
            {{ formatRelativeTime(row.savedAt) }}
          </template>
        </el-table-column>

        <el-table-column :label="t('drafts.table.configSummary')" min-width="250">
          <template #default="{ row }">
            <div style="font-size: 12px; color: #606266">
              <div>{{ t('drafts.configSummary.exchange') }}: {{ row.exchange }} | {{ t('drafts.configSummary.timeframe') }}: {{ row.timeframe }}</div>
              <div style="margin-top: 4px">
                {{ t('drafts.configSummary.pairs') }}: {{ (row.pair_whitelist || []).join(', ') || t('drafts.configSummary.notSet') }}
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column :label="t('drafts.table.expiryTime')" width="150">
          <template #default="{ row }">
            <span :style="{ color: getExpiryColor(row) }">
              {{ formatExpiryTime(row) }}
            </span>
          </template>
        </el-table-column>

        <el-table-column :label="t('drafts.table.actions')" width="280" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="!isExpired(row)"
              type="primary"
              size="small"
              @click="handleEdit(row)"
            >
              {{ t('drafts.actions.continueEdit') }}
            </el-button>
            <el-button
              v-if="!isExpired(row)"
              type="success"
              size="small"
              @click="handlePublish(row)"
            >
              {{ t('drafts.actions.publish') }}
            </el-button>
            <el-button
              v-if="isExpired(row)"
              type="warning"
              size="small"
              @click="handleCopy(row)"
            >
              {{ t('drafts.actions.copyAsNew') }}
            </el-button>
            <el-button
              type="danger"
              size="small"
              @click="handleDelete(row)"
            >
              {{ t('drafts.actions.delete') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @current-change="loadDrafts"
        @size-change="loadDrafts"
        style="margin-top: 20px; justify-content: center"
      />
    </el-card>

    <!-- 草稿设置对话框 -->
    <el-dialog
      v-model="showSettingsDialog"
      :title="t('drafts.settingsDialog.title')"
      width="600px"
    >
      <el-form :model="settings" label-width="160px">
        <el-form-item :label="t('drafts.settingsDialog.autoSave')">
          <el-switch v-model="settings.autoSave" />
          <div class="form-item-tip">
            {{ t('drafts.settingsDialog.autoSaveTip') }}
          </div>
        </el-form-item>

        <el-form-item :label="t('drafts.settingsDialog.saveInterval')">
          <el-input-number
            v-model="settings.saveInterval"
            :min="10"
            :max="300"
            :step="10"
          />
          <div class="form-item-tip">
            {{ t('drafts.settingsDialog.saveIntervalTip') }}
          </div>
        </el-form-item>

        <el-form-item :label="t('drafts.settingsDialog.retentionDays')">
          <el-input-number
            v-model="settings.retentionDays"
            :min="1"
            :max="30"
          />
          <div class="form-item-tip">
            {{ t('drafts.settingsDialog.retentionDaysTip') }}
          </div>
        </el-form-item>

        <el-form-item :label="t('drafts.settingsDialog.expiryAction')">
          <el-radio-group v-model="settings.expiryAction">
            <el-radio label="mark">{{ t('drafts.settingsDialog.expiryActionMark') }}</el-radio>
            <el-radio label="delete">{{ t('drafts.settingsDialog.expiryActionDelete') }}</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item :label="t('drafts.settingsDialog.versionFormat')">
          <el-input
            v-model="settings.versionFormat"
            :placeholder="t('drafts.settingsDialog.versionFormatPlaceholder')"
            disabled
          />
          <div class="form-item-tip">
            {{ t('drafts.settingsDialog.versionFormatTip') }}
          </div>
        </el-form-item>

        <el-form-item :label="t('drafts.settingsDialog.publishVersionStrategy')">
          <el-radio-group v-model="settings.publishVersionStrategy">
            <el-radio label="auto">{{ t('drafts.settingsDialog.publishVersionAuto') }}</el-radio>
            <el-radio label="manual">{{ t('drafts.settingsDialog.publishVersionManual') }}</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showSettingsDialog = false">{{ t('drafts.settingsDialog.cancel') }}</el-button>
        <el-button type="primary" @click="saveSettings">{{ t('drafts.settingsDialog.save') }}</el-button>
        <el-button type="warning" @click="resetSettings">{{ t('drafts.settingsDialog.reset') }}</el-button>
      </template>
    </el-dialog>

    <!-- 发布策略对话框 -->
    <el-dialog
      v-model="showPublishDialog"
      :title="t('drafts.publishDialog.title')"
      width="500px"
    >
      <el-form :model="publishForm" label-width="120px">
        <el-form-item :label="t('drafts.publishDialog.name')">
          <el-input v-model="publishForm.name" disabled />
        </el-form-item>

        <el-form-item :label="t('drafts.publishDialog.version')">
          <el-input
            v-if="settings.publishVersionStrategy === 'manual'"
            v-model="publishForm.version"
            :placeholder="t('drafts.publishDialog.versionPlaceholder')"
          />
          <el-input
            v-else
            :value="t('drafts.publishDialog.versionAuto')"
            disabled
          />
        </el-form-item>

        <el-form-item :label="t('drafts.publishDialog.versionNote')">
          <el-input
            v-model="publishForm.versionNote"
            type="textarea"
            :rows="3"
            :placeholder="t('drafts.publishDialog.versionNotePlaceholder')"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showPublishDialog = false">{{ t('drafts.publishDialog.cancel') }}</el-button>
        <el-button type="primary" @click="confirmPublish">{{ t('drafts.publishDialog.confirm') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Setting } from '@element-plus/icons-vue'

const router = useRouter()
const { t } = useI18n()

const loading = ref(false)
const drafts = ref([])
const selectedDrafts = ref([])
const showSettingsDialog = ref(false)
const showPublishDialog = ref(false)

const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

// 草稿设置（默认值）
const defaultSettings = {
  autoSave: true,
  saveInterval: 30,
  retentionDays: 7,
  expiryAction: 'mark',
  versionFormat: 'v0.{counter}-draft',
  publishVersionStrategy: 'auto'
}

const settings = reactive({ ...defaultSettings })

// 发布表单
const publishForm = reactive({
  draftId: null,
  name: '',
  version: 'v1.0',
  versionNote: ''
})

// 计算属性
const editingCount = computed(() => {
  return drafts.value.filter(d => isEditing(d)).length
})

const expiredCount = computed(() => {
  return drafts.value.filter(d => isExpired(d)).length
})

// 加载草稿列表
const loadDrafts = () => {
  try {
    // 从localStorage加载所有草稿
    const draftIds = JSON.parse(localStorage.getItem('strategy_drafts') || '[]')
    const allDrafts = []

    draftIds.forEach(id => {
      const draftData = localStorage.getItem(`strategy_draft_${id}`)
      if (draftData) {
        try {
          const draft = JSON.parse(draftData)
          allDrafts.push(draft)
        } catch (e) {
          console.error(`Failed to parse draft ${id}:`, e)
        }
      }
    })

    // 按修改时间倒序排序
    allDrafts.sort((a, b) => new Date(b.savedAt) - new Date(a.savedAt))

    // 分页
    pagination.total = allDrafts.length
    const start = (pagination.page - 1) * pagination.pageSize
    const end = start + pagination.pageSize
    drafts.value = allDrafts.slice(start, end)
  } catch (error) {
    console.error('Failed to load drafts:', error)
    ElMessage.error(t('drafts.messages.loadFailed'))
  }
}

// 判断是否正在编辑（最近5分钟保存的）
const isEditing = (draft) => {
  const savedTime = new Date(draft.savedAt)
  const now = new Date()
  const diff = (now - savedTime) / 1000 / 60 // 分钟
  return diff < 5
}

// 判断是否过期
const isExpired = (draft) => {
  const savedTime = new Date(draft.savedAt)
  const now = new Date()
  const diff = (now - savedTime) / 1000 / 60 / 60 / 24 // 天数
  return diff > settings.retentionDays
}

// 格式化相对时间
const formatRelativeTime = (timestamp) => {
  const now = new Date()
  const time = new Date(timestamp)
  const diff = (now - time) / 1000 // 秒

  if (diff < 60) {
    return t('drafts.time.justNow')
  } else if (diff < 3600) {
    return t('drafts.time.minutesAgo', { n: Math.floor(diff / 60) })
  } else if (diff < 86400) {
    return t('drafts.time.hoursAgo', { n: Math.floor(diff / 3600) })
  } else {
    return t('drafts.time.daysAgo', { n: Math.floor(diff / 86400) })
  }
}

// 格式化过期时间
const formatExpiryTime = (draft) => {
  const savedTime = new Date(draft.savedAt)
  const expiryTime = new Date(savedTime)
  expiryTime.setDate(expiryTime.getDate() + settings.retentionDays)

  if (isExpired(draft)) {
    return t('drafts.time.expired')
  }

  const now = new Date()
  const diff = (expiryTime - now) / 1000 / 60 / 60 / 24 // 天数

  if (diff < 1) {
    return t('drafts.time.expiresInHours', { n: Math.floor(diff * 24) })
  } else {
    return t('drafts.time.expiresInDays', { n: Math.floor(diff) })
  }
}

// 获取过期时间颜色
const getExpiryColor = (draft) => {
  if (isExpired(draft)) return '#F56C6C'

  const savedTime = new Date(draft.savedAt)
  const now = new Date()
  const diff = (now - savedTime) / 1000 / 60 / 60 / 24 // 天数

  if (diff > settings.retentionDays * 0.8) return '#F56C6C' // 红色
  if (diff > settings.retentionDays * 0.5) return '#E6A23C' // 橙色
  return '#67C23A' // 绿色
}

// 继续编辑
const handleEdit = (draft) => {
  // 跳转到策略管理页面并加载草稿
  router.push({
    path: '/strategies',
    query: { loadDraft: draft.draftId }
  })
}

// 发布策略
const handlePublish = (draft) => {
  publishForm.draftId = draft.draftId
  publishForm.name = draft.name
  publishForm.version = 'v1.0'
  publishForm.versionNote = ''
  showPublishDialog.value = true
}

// 确认发布
const confirmPublish = async () => {
  try {
    // TODO: 调用API发布策略
    // const draft = JSON.parse(localStorage.getItem(`strategy_draft_${publishForm.draftId}`))
    // await strategyStore.createStrategy({
    //   ...draft,
    //   version: publishForm.version,
    //   version_note: publishForm.versionNote
    // })

    // 删除草稿
    localStorage.removeItem(`strategy_draft_${publishForm.draftId}`)
    const draftIds = JSON.parse(localStorage.getItem('strategy_drafts') || '[]')
    const index = draftIds.indexOf(publishForm.draftId)
    if (index > -1) {
      draftIds.splice(index, 1)
      localStorage.setItem('strategy_drafts', JSON.stringify(draftIds))
    }

    ElMessage.success(t('drafts.messages.publishSuccess'))
    showPublishDialog.value = false
    loadDrafts()

    // 跳转到策略列表
    router.push('/strategies')
  } catch (error) {
    console.error('Failed to publish strategy:', error)
    ElMessage.error(t('drafts.messages.publishFailed'))
  }
}

// 复制为新策略
const handleCopy = (draft) => {
  try {
    // 创建新草稿
    const newDraft = {
      ...draft,
      draftId: Date.now().toString(),
      savedAt: new Date().toISOString(),
      name: `${draft.name} ${t('drafts.copy')}`
    }

    // 保存新草稿
    localStorage.setItem(`strategy_draft_${newDraft.draftId}`, JSON.stringify(newDraft))

    // 更新草稿列表索引
    const draftIds = JSON.parse(localStorage.getItem('strategy_drafts') || '[]')
    draftIds.push(newDraft.draftId)
    localStorage.setItem('strategy_drafts', JSON.stringify(draftIds))

    ElMessage.success(t('drafts.messages.copySuccess'))
    loadDrafts()
  } catch (error) {
    console.error('Failed to copy draft:', error)
    ElMessage.error(t('drafts.messages.copyFailed'))
  }
}

// 删除草稿
const handleDelete = async (draft) => {
  try {
    await ElMessageBox.confirm(
      t('drafts.confirmations.deleteMessage', { name: draft.name || t('drafts.unnamed') }),
      t('drafts.confirmations.deleteTitle'),
      {
        confirmButtonText: t('drafts.confirmations.confirm'),
        cancelButtonText: t('drafts.confirmations.cancel'),
        type: 'warning'
      }
    )

    // 删除草稿
    localStorage.removeItem(`strategy_draft_${draft.draftId}`)

    // 从草稿列表中移除
    const draftIds = JSON.parse(localStorage.getItem('strategy_drafts') || '[]')
    const index = draftIds.indexOf(draft.draftId)
    if (index > -1) {
      draftIds.splice(index, 1)
      localStorage.setItem('strategy_drafts', JSON.stringify(draftIds))
    }

    ElMessage.success(t('drafts.messages.deleteSuccess'))
    loadDrafts()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to delete draft:', error)
      ElMessage.error(t('drafts.messages.deleteFailed'))
    }
  }
}

// 批量删除
const handleBatchDelete = async () => {
  if (selectedDrafts.value.length === 0) {
    ElMessage.warning(t('drafts.messages.selectDrafts'))
    return
  }

  try {
    await ElMessageBox.confirm(
      t('drafts.confirmations.batchDeleteMessage', { count: selectedDrafts.value.length }),
      t('drafts.confirmations.batchDeleteTitle'),
      {
        confirmButtonText: t('drafts.confirmations.confirm'),
        cancelButtonText: t('drafts.confirmations.cancel'),
        type: 'warning'
      }
    )

    // 批量删除
    const draftIds = JSON.parse(localStorage.getItem('strategy_drafts') || '[]')

    selectedDrafts.value.forEach(draft => {
      localStorage.removeItem(`strategy_draft_${draft.draftId}`)
      const index = draftIds.indexOf(draft.draftId)
      if (index > -1) {
        draftIds.splice(index, 1)
      }
    })

    localStorage.setItem('strategy_drafts', JSON.stringify(draftIds))

    ElMessage.success(t('drafts.messages.batchDeleteSuccess', { count: selectedDrafts.value.length }))
    selectedDrafts.value = []
    loadDrafts()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to batch delete:', error)
      ElMessage.error(t('drafts.messages.batchDeleteFailed'))
    }
  }
}

// 清理过期草稿
const handleClearExpired = async () => {
  const expiredDrafts = drafts.value.filter(d => isExpired(d))

  if (expiredDrafts.length === 0) {
    ElMessage.info(t('drafts.messages.noExpired'))
    return
  }

  try {
    await ElMessageBox.confirm(
      t('drafts.confirmations.clearExpiredMessage', { count: expiredDrafts.length }),
      t('drafts.confirmations.clearExpiredTitle'),
      {
        confirmButtonText: t('drafts.confirmations.confirm'),
        cancelButtonText: t('drafts.confirmations.cancel'),
        type: 'warning'
      }
    )

    // 清理过期草稿
    const draftIds = JSON.parse(localStorage.getItem('strategy_drafts') || '[]')

    expiredDrafts.forEach(draft => {
      localStorage.removeItem(`strategy_draft_${draft.draftId}`)
      const index = draftIds.indexOf(draft.draftId)
      if (index > -1) {
        draftIds.splice(index, 1)
      }
    })

    localStorage.setItem('strategy_drafts', JSON.stringify(draftIds))

    ElMessage.success(t('drafts.messages.clearSuccess', { count: expiredDrafts.length }))
    loadDrafts()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to clear expired drafts:', error)
      ElMessage.error(t('drafts.messages.clearFailed'))
    }
  }
}

// 选择变化
const handleSelectionChange = (selection) => {
  selectedDrafts.value = selection
}

// 保存设置
const saveSettings = () => {
  try {
    localStorage.setItem('draft_settings', JSON.stringify(settings))
    ElMessage.success(t('drafts.messages.settingsSaved'))
    showSettingsDialog.value = false
  } catch (error) {
    console.error('Failed to save settings:', error)
    ElMessage.error(t('drafts.messages.settingsSaveFailed'))
  }
}

// 重置设置
const resetSettings = () => {
  Object.assign(settings, defaultSettings)
  ElMessage.success(t('drafts.messages.settingsReset'))
}

// 加载设置
const loadSettings = () => {
  try {
    const saved = localStorage.getItem('draft_settings')
    if (saved) {
      Object.assign(settings, JSON.parse(saved))
    }
  } catch (error) {
    console.error('Failed to load settings:', error)
  }
}

onMounted(() => {
  loadSettings()
  loadDrafts()
})
</script>

<style scoped>
.drafts {
  padding: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.form-item-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
</style>
