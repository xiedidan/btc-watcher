<template>
  <div class="strategies">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ t('strategy.title') }}</span>
          <el-space>
            <el-button size="small" @click="$router.push('/drafts')">
              <el-icon><Document /></el-icon>
              {{ t('strategy.drafts') }}
            </el-button>
            <el-button type="primary" @click="handleOpenCreateDialog">
              <el-icon><Plus /></el-icon>
              {{ t('strategy.create') }}
            </el-button>
          </el-space>
        </div>
      </template>

      <!-- 搜索栏 -->
      <el-form :inline="true" class="search-form">
        <el-form-item :label="t('strategy.status')">
          <el-select v-model="searchForm.status" :placeholder="t('strategy.all')" clearable @change="fetchData" style="width: 150px">
            <el-option :label="t('strategy.all')" value="" />
            <el-option :label="t('strategy.running')" value="running" />
            <el-option :label="t('strategy.stopped')" value="stopped" />
            <el-option label="正在启动" value="starting" />
            <el-option label="正在停止" value="stopping" />
            <el-option :label="t('strategy.error')" value="error" />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="fetchData">{{ t('strategy.query') }}</el-button>
          <el-button @click="resetSearch">{{ t('strategy.reset') }}</el-button>
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
        <el-table-column prop="name" :label="t('strategy.name')" min-width="180" />
        <el-table-column prop="strategy_class" :label="t('strategy.strategyClass')" width="150" />
        <el-table-column prop="exchange" :label="t('strategy.exchange')" width="120" />
        <el-table-column prop="port" :label="t('strategy.port')" width="100" />

        <el-table-column :label="t('strategy.healthScore')" width="150">
          <template #default="{ row }">
            <div style="display: flex; align-items: center; gap: 8px">
              <el-progress
                :percentage="calculateHealthScore(row)"
                :color="getHealthColor(calculateHealthScore(row))"
                :stroke-width="12"
                :show-text="false"
                style="flex: 1"
              />
              <span style="font-size: 12px; min-width: 28px">{{ calculateHealthScore(row) }}{{ t('strategy.score') }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column :label="t('strategy.status')" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.status === 'running'" type="success">{{ t('strategy.running') }}</el-tag>
            <el-tag v-else-if="row.status === 'stopped'" type="info">{{ t('strategy.stopped') }}</el-tag>
            <el-tag v-else-if="row.status === 'starting'" type="warning" :icon="Loading">正在启动</el-tag>
            <el-tag v-else-if="row.status === 'stopping'" type="warning" :icon="Loading">正在停止</el-tag>
            <el-tag v-else type="danger">{{ t('strategy.error') }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="created_at" :label="t('strategy.createdAt')" width="180" />

        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'stopped'"
              type="success"
              size="small"
              @click="handleStart(row)"
            >
              {{ t('strategy.start') }}
            </el-button>
            <el-button
              v-else-if="row.status === 'running'"
              type="warning"
              size="small"
              @click="handleStop(row)"
            >
              {{ t('strategy.stop') }}
            </el-button>
            <el-button
              v-else-if="row.status === 'error'"
              type="success"
              size="small"
              @click="handleStart(row)"
            >
              {{ t('strategy.restart') }}
            </el-button>
            <el-button
              v-if="row.status === 'error'"
              type="danger"
              size="small"
              @click="handleStop(row)"
            >
              {{ t('strategy.forceStop') }}
            </el-button>
            <el-button
              v-else-if="row.status === 'starting'"
              type="warning"
              size="small"
              disabled
              loading
            >
              正在启动
            </el-button>
            <el-button
              v-else-if="row.status === 'stopping'"
              type="warning"
              size="small"
              disabled
              loading
            >
              正在停止
            </el-button>
            <el-button
              type="primary"
              size="small"
              @click="handleView(row)"
            >
              {{ t('common.detail') }}
            </el-button>
            <el-button
              type="danger"
              size="small"
              @click="handleDelete(row)"
              :disabled="row.status === 'starting' || row.status === 'stopping'"
            >
              {{ t('common.delete') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 创建策略对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      :title="t('strategy.create')"
      width="600px"
    >
      <!-- 草稿管理 -->
      <el-alert
        v-if="draftKey"
        :title="t('strategy.draftEditing')"
        type="info"
        :closable="false"
        style="margin-bottom: 16px"
      >
        <template #default>
          <div style="display: flex; justify-content: space-between; align-items: center">
            <span style="font-size: 12px">{{ t('strategy.autoSaveTip') }}</span>
            <div>
              <el-button size="small" @click="saveDraft">{{ t('strategy.saveNow') }}</el-button>
              <el-button size="small" type="danger" @click="handleClearDraft">{{ t('strategy.clearDraft') }}</el-button>
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
        <el-form-item :label="t('strategy.name')" prop="name">
          <el-input v-model="createForm.name" :placeholder="t('strategy.enterName')" />
        </el-form-item>

        <!-- 策略文件上传 -->
        <el-divider content-position="left">{{ t('strategy.strategyCode') }}</el-divider>

        <el-form-item :label="t('strategy.strategyFile')">
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
                {{ t('strategy.uploadStrategy') }}
              </el-button>
            </el-upload>
            <div style="margin-top: 8px; font-size: 12px; color: #909399">
              {{ t('strategy.uploadTip') }}
            </div>
          </div>
        </el-form-item>

        <el-form-item :label="t('strategy.strategyClass')" prop="strategy_class">
          <el-select
            v-model="createForm.strategy_class"
            :placeholder="t('strategy.selectFile')"
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
                <span style="color: #8492a6; font-size: 12px">{{ cls.description || t('strategy.noDescription') }}</span>
              </div>
            </el-option>
          </el-select>
          <div v-if="strategyFileInfo" style="margin-top: 8px; font-size: 12px; color: #67C23A">
            ✓ {{ t('strategy.loaded') }}: {{ strategyFileInfo.filename }} ({{ availableStrategyClasses.length }} {{ t('strategy.classesFound') }})
          </div>
        </el-form-item>

        <el-form-item :label="t('strategy.exchange')" prop="exchange">
          <el-select v-model="createForm.exchange" :placeholder="t('strategy.selectExchange')">
            <el-option label="Binance" value="binance" />
            <el-option label="OKX" value="okx" />
            <el-option label="Huobi" value="huobi" />
          </el-select>
        </el-form-item>

        <el-form-item :label="t('strategy.timeframe')" prop="timeframe">
          <el-select v-model="createForm.timeframe" :placeholder="t('strategy.selectTimeframe')">
            <el-option label="1分钟" value="1m" />
            <el-option label="5分钟" value="5m" />
            <el-option label="15分钟" value="15m" />
            <el-option label="1小时" value="1h" />
            <el-option label="4小时" value="4h" />
            <el-option label="1天" value="1d" />
          </el-select>
        </el-form-item>

        <el-form-item :label="t('strategy.tradingPairs')" prop="pair_whitelist">
          <el-select
            v-model="createForm.pair_whitelist"
            multiple
            filterable
            allow-create
            default-first-option
            :reserve-keyword="false"
            :placeholder="t('strategy.enterPairs')"
            style="width: 100%"
          >
            <el-option label="BTC/USDT" value="BTC/USDT" />
            <el-option label="ETH/USDT" value="ETH/USDT" />
            <el-option label="BNB/USDT" value="BNB/USDT" />
            <el-option label="SOL/USDT" value="SOL/USDT" />
            <el-option label="ADA/USDT" value="ADA/USDT" />
            <el-option label="DOGE/USDT" value="DOGE/USDT" />
            <el-option label="XRP/USDT" value="XRP/USDT" />
            <el-option label="DOT/USDT" value="DOT/USDT" />
            <el-option label="MATIC/USDT" value="MATIC/USDT" />
            <el-option label="AVAX/USDT" value="AVAX/USDT" />
          </el-select>
          <div style="margin-top: 4px; font-size: 12px; color: #909399">
            支持自定义输入，例如：输入 "SOL/USDT" 后按回车添加
          </div>
        </el-form-item>

        <el-form-item :label="t('strategy.dryRun')">
          <el-switch v-model="createForm.dry_run" />
        </el-form-item>

        <el-divider content-position="left">{{ t('strategy.thresholds') }}</el-divider>

        <el-form-item :label="t('strategy.strongThreshold')" label-width="140px">
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
              <el-tag type="danger" size="small">🔴 {{ t('strategy.p2Immediate') }}</el-tag>
            </el-col>
          </el-row>
          <div style="margin-top: 4px; font-size: 12px; color: #909399">
            {{ t('strategy.strongThresholdTip', { threshold: createForm.signal_thresholds.strong }) }}
          </div>
        </el-form-item>

        <el-form-item :label="t('strategy.mediumThreshold')" label-width="140px">
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
              <el-tag type="warning" size="small">🟠 {{ t('strategy.p1Notify') }}</el-tag>
            </el-col>
          </el-row>
          <div style="margin-top: 4px; font-size: 12px; color: #909399">
            {{ t('strategy.mediumThresholdTip', { threshold: createForm.signal_thresholds.medium }) }}
          </div>
        </el-form-item>

        <el-form-item :label="t('strategy.weakThreshold')" label-width="140px">
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
              <el-tag type="info" size="small">🟡 {{ t('strategy.p0Batch') }}</el-tag>
            </el-col>
          </el-row>
          <div style="margin-top: 4px; font-size: 12px; color: #909399">
            {{ t('strategy.weakThresholdTip', { threshold: createForm.signal_thresholds.weak }) }}
          </div>
        </el-form-item>

        <el-form-item :label="t('strategy.thresholdPreview')" label-width="140px">
          <div style="width: 100%">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px">
              <span style="font-size: 12px; width: 30px">0.0</span>
              <div :style="{
                flex: 1,
                height: '20px',
                background: `linear-gradient(to right, #909399 0%, #909399 ${createForm.signal_thresholds.weak * 100}%, #E6A23C ${createForm.signal_thresholds.weak * 100}%, #E6A23C ${createForm.signal_thresholds.medium * 100}%, #F56C6C ${createForm.signal_thresholds.medium * 100}%, #F56C6C ${createForm.signal_thresholds.strong * 100}%, #67C23A ${createForm.signal_thresholds.strong * 100}%, #67C23A 100%)`,
                borderRadius: '4px',
                position: 'relative'
              }">
                <div :style="{
                  position: 'absolute',
                  left: `${createForm.signal_thresholds.weak * 100}%`,
                  top: '-24px',
                  transform: 'translateX(-50%)',
                  fontSize: '10px',
                  color: '#E6A23C'
                }">{{ createForm.signal_thresholds.weak }}</div>
                <div :style="{
                  position: 'absolute',
                  left: `${createForm.signal_thresholds.medium * 100}%`,
                  top: '-24px',
                  transform: 'translateX(-50%)',
                  fontSize: '10px',
                  color: '#F56C6C'
                }">{{ createForm.signal_thresholds.medium }}</div>
                <div :style="{
                  position: 'absolute',
                  left: `${createForm.signal_thresholds.strong * 100}%`,
                  top: '-24px',
                  transform: 'translateX(-50%)',
                  fontSize: '10px',
                  color: '#67C23A'
                }">{{ createForm.signal_thresholds.strong }}</div>
              </div>
              <span style="font-size: 12px; width: 30px">1.0</span>
            </div>
            <div style="display: flex; gap: 16px; font-size: 12px; color: #606266; margin-top: 16px">
              <span>⚪ {{ t('strategy.ignore') }} (< {{ createForm.signal_thresholds.weak }})</span>
              <span>🟡 {{ t('strategy.weak') }} ({{ createForm.signal_thresholds.weak }} - {{ createForm.signal_thresholds.medium }})</span>
              <span>🟠 {{ t('strategy.medium') }} ({{ createForm.signal_thresholds.medium }} - {{ createForm.signal_thresholds.strong }})</span>
              <span>🔴 {{ t('strategy.strong') }} (≥ {{ createForm.signal_thresholds.strong }})</span>
            </div>
          </div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showCreateDialog = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="submitting" @click="handleCreate">
          {{ t('common.create') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 策略详情对话框 -->
    <el-dialog
      v-model="showDetailDialog"
      :title="t('strategy.detail')"
      width="800px"
      destroy-on-close
    >
      <div v-if="currentStrategy">
        <!-- 基础信息和运行状态 -->
        <el-row :gutter="16" style="margin-bottom: 20px">
          <el-col :span="12">
            <el-card shadow="never" :header="t('strategy.basicInfo')">
              <el-descriptions :column="1" size="small">
                <el-descriptions-item :label="t('strategy.strategyId')">{{ currentStrategy.id }}</el-descriptions-item>
                <el-descriptions-item :label="t('strategy.name')">{{ currentStrategy.name }}</el-descriptions-item>
                <el-descriptions-item :label="t('strategy.strategyType')">{{ t('strategy.signalMonitoring') }}</el-descriptions-item>
                <el-descriptions-item :label="t('strategy.version')">{{ currentStrategy.version }}</el-descriptions-item>
                <el-descriptions-item :label="t('strategy.createdAt')">
                  {{ formatDateTime(currentStrategy.created_at) }}
                </el-descriptions-item>
                <el-descriptions-item :label="t('strategy.lastModified')">
                  {{ formatDateTime(currentStrategy.updated_at) }}
                </el-descriptions-item>
              </el-descriptions>
            </el-card>
          </el-col>

          <el-col :span="12">
            <el-card shadow="never" :header="t('strategy.runningStatus')">
              <el-descriptions :column="1" size="small">
                <el-descriptions-item :label="t('strategy.status')">
                  <el-tag v-if="currentStrategy.status === 'running'" type="success">{{ t('strategy.running') }}</el-tag>
                  <el-tag v-else-if="currentStrategy.status === 'stopped'" type="info">{{ t('strategy.stopped') }}</el-tag>
                  <el-tag v-else-if="currentStrategy.status === 'starting'" type="warning" :icon="Loading">正在启动</el-tag>
                  <el-tag v-else-if="currentStrategy.status === 'stopping'" type="warning" :icon="Loading">正在停止</el-tag>
                  <el-tag v-else type="danger">{{ t('strategy.error') }}</el-tag>
                </el-descriptions-item>
                <el-descriptions-item :label="t('strategy.healthScore')">
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
                <el-descriptions-item :label="t('strategy.uptime')" v-if="currentStrategy.status === 'running'">
                  {{ calculateUptime(currentStrategy.started_at) }}
                </el-descriptions-item>
                <el-descriptions-item :label="t('strategy.startedAt')" v-if="currentStrategy.started_at">
                  {{ formatDateTime(currentStrategy.started_at) }}
                </el-descriptions-item>
                <el-descriptions-item :label="t('strategy.stoppedAt')" v-if="currentStrategy.stopped_at">
                  {{ formatDateTime(currentStrategy.stopped_at) }}
                </el-descriptions-item>
                <el-descriptions-item :label="t('strategy.pid')" v-if="currentStrategy.process_id">
                  {{ currentStrategy.process_id }}
                </el-descriptions-item>
                <el-descriptions-item :label="t('strategy.port')" v-if="currentStrategy.port">
                  {{ currentStrategy.port }}
                </el-descriptions-item>
              </el-descriptions>
            </el-card>
          </el-col>
        </el-row>

        <!-- 配置信息 -->
        <el-card shadow="never" :header="t('strategy.configInfo')" style="margin-bottom: 20px">
          <el-descriptions :column="2" size="small">
            <el-descriptions-item :label="t('strategy.strategyClass')">
              {{ currentStrategy.strategy_class }}
            </el-descriptions-item>
            <el-descriptions-item :label="t('strategy.exchange')">
              {{ currentStrategy.exchange }}
            </el-descriptions-item>
            <el-descriptions-item :label="t('strategy.timeframe')">
              {{ currentStrategy.timeframe }}
            </el-descriptions-item>
            <el-descriptions-item :label="t('strategy.dryRun')">
              <el-tag :type="currentStrategy.dry_run ? 'success' : 'warning'">
                {{ currentStrategy.dry_run ? t('common.yes') : t('common.no') }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item :label="t('strategy.tradingPairs')" :span="2">
              <el-space wrap>
                <el-tag v-for="pair in currentStrategy.pair_whitelist" :key="pair" size="small">
                  {{ pair }}
                </el-tag>
              </el-space>
            </el-descriptions-item>
            <el-descriptions-item :label="t('strategy.maxTrades')">
              {{ currentStrategy.max_open_trades }}
            </el-descriptions-item>
            <el-descriptions-item :label="t('strategy.wallet')" v-if="currentStrategy.dry_run">
              {{ currentStrategy.dry_run_wallet }} USDT
            </el-descriptions-item>
          </el-descriptions>

          <el-divider content-position="left">{{ t('strategy.thresholds') }}</el-divider>
          <el-descriptions :column="3" size="small" v-if="currentStrategy.signal_thresholds">
            <el-descriptions-item :label="t('strategy.strong')">
              ≥ {{ currentStrategy.signal_thresholds.strong || 0.8 }}
            </el-descriptions-item>
            <el-descriptions-item :label="t('strategy.medium')">
              ≥ {{ currentStrategy.signal_thresholds.medium || 0.6 }}
            </el-descriptions-item>
            <el-descriptions-item :label="t('strategy.weak')">
              ≥ {{ currentStrategy.signal_thresholds.weak || 0.4 }}
            </el-descriptions-item>
          </el-descriptions>

          <div v-if="currentStrategy.description" style="margin-top: 16px">
            <el-divider content-position="left">{{ t('strategy.description') }}</el-divider>
            <p style="color: #606266; line-height: 1.6">{{ currentStrategy.description }}</p>
          </div>
        </el-card>

        <!-- 实时日志展示 -->
        <el-card shadow="never" style="margin-bottom: 20px">
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center">
              <span>运行日志</span>
              <el-space>
                <el-select v-model="logFilter" size="small" style="width: 120px">
                  <el-option label="全部" value="ALL" />
                  <el-option label="INFO" value="INFO" />
                  <el-option label="WARNING" value="WARNING" />
                  <el-option label="ERROR" value="ERROR" />
                </el-select>
                <el-checkbox v-model="autoScroll" size="small">自动滚动</el-checkbox>
                <el-button size="small" @click="clearLogs">清空</el-button>
                <el-button size="small" @click="refreshLogs">刷新</el-button>
              </el-space>
            </div>
          </template>

          <div ref="logContainer" class="log-container">
            <div v-if="filteredLogs.length === 0" class="log-empty">
              <el-empty description="暂无日志数据" :image-size="80" />
            </div>
            <div v-else>
              <div
                v-for="(log, index) in filteredLogs"
                :key="index"
                class="log-entry"
                :class="`log-level-${log.level?.toLowerCase() || 'info'}`"
              >
                <span class="log-timestamp">{{ log.timestamp }}</span>
                <span class="log-level" :class="`level-${log.level?.toLowerCase() || 'info'}`">
                  {{ log.level || 'INFO' }}
                </span>
                <span class="log-logger">{{ log.logger || 'freqtrade' }}</span>
                <span class="log-message">{{ log.message }}</span>
              </div>
            </div>
          </div>
        </el-card>

        <!-- 操作按钮 -->
        <div style="display: flex; justify-content: flex-end; gap: 8px">
          <el-button @click="showDetailDialog = false">{{ t('common.close') }}</el-button>
          <el-button
            v-if="currentStrategy.status === 'stopped'"
            type="success"
            @click="handleStartFromDetail"
          >
            {{ t('strategy.start') }}
          </el-button>
          <el-button
            v-else-if="currentStrategy.status === 'running'"
            type="warning"
            @click="handleStopFromDetail"
          >
            {{ t('strategy.stop') }}
          </el-button>
          <el-button
            v-else-if="currentStrategy.status === 'error'"
            type="success"
            @click="handleStartFromDetail"
          >
            {{ t('strategy.restart') }}
          </el-button>
          <el-button
            v-if="currentStrategy.status === 'error'"
            type="danger"
            @click="handleStopFromDetail"
          >
            {{ t('strategy.forceStop') }}
          </el-button>
          <el-button
            v-else-if="currentStrategy.status === 'starting'"
            type="warning"
            disabled
            loading
          >
            正在启动
          </el-button>
          <el-button
            v-else-if="currentStrategy.status === 'stopping'"
            type="warning"
            disabled
            loading
          >
            正在停止
          </el-button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Upload, Document, Loading } from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'
import { useStrategyStore } from '@/stores/strategy'
import { useUserStore } from '@/stores/user'

const { t } = useI18n()
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
const strategyLogs = ref([])  // 策略日志
const logFilter = ref('ALL')  // 日志级别过滤
const autoScroll = ref(true)  // 自动滚动
const logContainer = ref(null)  // 日志容器引用
let autoSaveTimer = null
let draftKey = null
let detailRefreshTimer = null  // 详情页自动刷新定时器
let statusPollingTimers = {}  // 状态轮询定时器 (strategy_id -> timer)
let wsUnsubscribeLogs = null  // WebSocket日志订阅取消函数

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

// 过滤后的日志
const filteredLogs = computed(() => {
  if (logFilter.value === 'ALL') {
    return strategyLogs.value
  }
  return strategyLogs.value.filter(log => log.level === logFilter.value)
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
  name: [{ required: true, message: t('strategy.enterName'), trigger: 'blur' }],
  strategy_class: [{ required: true, message: t('strategy.selectClass'), trigger: 'change' }],
  exchange: [{ required: true, message: t('strategy.enterExchange'), trigger: 'change' }],
  timeframe: [{ required: true, message: t('strategy.enterTimeframe'), trigger: 'change' }],
  pair_whitelist: [{
    required: true,
    type: 'array',
    min: 1,
    message: t('strategy.enterPairs'),
    trigger: 'change'
  }]
}

// 文件上传处理函数
const beforeUpload = (file) => {
  const isPython = file.name.endsWith('.py')
  const isLt10M = file.size / 1024 / 1024 < 10

  if (!isPython) {
    ElMessage.error(t('strategy.onlyPython'))
    return false
  }

  if (!isLt10M) {
    ElMessage.error(t('strategy.fileTooLarge'))
    return false
  }

  return true
}

const handleUploadSuccess = (response, file, fileList) => {
  if (response.success) {
    // 显示后端返回的详细消息（包含找到的策略类数量）
    ElMessage.success(response.message || t('strategy.uploadSuccess'))

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
      ElMessage.info(t('strategy.autoSelected'))
    }
  } else {
    ElMessage.error(response.message || t('strategy.uploadFailed'))
  }
}

const handleUploadError = (error, file) => {
  console.error('Upload error:', error)
  let errorMessage = t('strategy.uploadFailed')

  // 尝试解析错误消息
  try {
    if (error.message) {
      errorMessage = error.message
    } else if (typeof error === 'string') {
      errorMessage = error
    }
  } catch (e) {
    console.error('Failed to parse error:', e)
  }

  ElMessage.error(errorMessage)

  // 清除已上传文件列表
  uploadedFiles.value = []
  availableStrategyClasses.value = []
  strategyFileInfo.value = null
  createForm.strategy_file = null
  createForm.strategy_class = ''
}

const fetchData = async () => {
  loading.value = true
  try {
    const res = await strategyStore.fetchStrategies(searchForm)
    strategies.value = res.strategies
  } catch (error) {
    ElMessage.error(t('strategy.fetchFailed'))
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

// 状态轮询：等待策略达到目标状态
const startStatusPolling = (strategyId, targetStatus) => {
  // 清理之前的定时器
  if (statusPollingTimers[strategyId]) {
    clearInterval(statusPollingTimers[strategyId])
  }

  let pollCount = 0
  const maxPolls = 60 // 最多轮询60次 (2秒*60 = 120秒)

  statusPollingTimers[strategyId] = setInterval(async () => {
    pollCount++

    try {
      const detail = await strategyStore.fetchStrategy(strategyId)

      // 检查是否达到目标状态
      if (detail.status === targetStatus) {
        // 清理定时器
        clearInterval(statusPollingTimers[strategyId])
        delete statusPollingTimers[strategyId]

        // 刷新列表
        await fetchData()

        // 显示成功消息
        if (targetStatus === 'running') {
          ElMessage.success('策略启动成功')
        } else if (targetStatus === 'stopped') {
          ElMessage.success('策略停止成功')
        }
      } else if (detail.status === 'stopped' && targetStatus === 'running') {
        // 启动失败
        clearInterval(statusPollingTimers[strategyId])
        delete statusPollingTimers[strategyId]
        await fetchData()
        ElMessage.error('策略启动失败')
      } else if (detail.status === 'running' && targetStatus === 'stopped') {
        // 停止失败
        clearInterval(statusPollingTimers[strategyId])
        delete statusPollingTimers[strategyId]
        await fetchData()
        ElMessage.error('策略停止失败')
      } else if (pollCount >= maxPolls) {
        // 超时
        clearInterval(statusPollingTimers[strategyId])
        delete statusPollingTimers[strategyId]
        await fetchData()
        ElMessage.warning('操作超时，请检查策略状态')
      }
    } catch (error) {
      console.error('Status polling error:', error)
      // 继续轮询，不中断
    }
  }, 2000) // 每2秒轮询一次
}

const handleStart = async (row) => {
  try {
    // 先更新本地状态为starting
    const index = strategies.value.findIndex(s => s.id === row.id)
    if (index !== -1) {
      strategies.value[index].status = 'starting'
    }

    await strategyStore.startStrategy(row.id)

    // 立即刷新获取最新状态
    await fetchData()

    // 启动轮询检测状态变化
    startStatusPolling(row.id, 'running')
  } catch (error) {
    ElMessage.error(t('strategy.startFailed'))
    // 失败时恢复原状态
    await fetchData()
  }
}

const handleStop = async (row) => {
  try {
    // 先更新本地状态为stopping
    const index = strategies.value.findIndex(s => s.id === row.id)
    if (index !== -1) {
      strategies.value[index].status = 'stopping'
    }

    await strategyStore.stopStrategy(row.id)

    // 立即刷新获取最新状态
    await fetchData()

    // 启动轮询检测状态变化
    startStatusPolling(row.id, 'stopped')
  } catch (error) {
    ElMessage.error(t('strategy.stopFailed'))
    // 失败时恢复原状态
    await fetchData()
  }
}

const handleView = async (row) => {
  try {
    const detail = await strategyStore.fetchStrategy(row.id)
    currentStrategy.value = detail
    showDetailDialog.value = true

    // 加载历史日志
    await loadStrategyLogs(row.id)

    // 订阅WebSocket实时日志
    subscribeToStrategyLogs(row.id)

    // 如果是正在启动或停止状态，启动自动刷新
    startDetailRefresh()
  } catch (error) {
    ElMessage.error(t('strategy.detailFailed'))
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(
      t('strategy.deleteConfirm', { name: row.name }),
      t('strategy.warning'),
      {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        type: 'warning'
      }
    )

    await strategyStore.deleteStrategy(row.id)
    ElMessage.success(t('strategy.deleteSuccess'))
    fetchData()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('strategy.deleteFailed'))
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
  try {
    // 验证表单
    const valid = await createFormRef.value.validate().catch((err) => {
      console.error('Form validation failed:', err)
      return false
    })

    if (!valid) {
      ElMessage.warning('请填写完整的表单信息')
      return
    }

    // 检查是否上传了策略文件
    if (!createForm.strategy_file) {
      ElMessage.warning('请先上传策略文件')
      return
    }

    // 检查是否选择了策略类
    if (!createForm.strategy_class) {
      ElMessage.warning('请选择策略类')
      return
    }

    submitting.value = true

    await strategyStore.createStrategy(createForm)
    ElMessage.success(t('strategy.createSuccess'))

    // 清除草稿
    clearDraft()

    // 关闭对话框
    showCreateDialog.value = false

    // 刷新列表
    await fetchData()
  } catch (error) {
    console.error('Failed to create strategy:', error)
    ElMessage.error(error.message || t('strategy.createFailed'))
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
    return `${hours}${t('strategy.hours')}${minutes}${t('strategy.minutes')}`
  } else {
    return `${minutes}${t('strategy.minutes')}`
  }
}

// 计算健康分数（简化版本）
const calculateHealthScore = (strategy) => {
  if (strategy.status === 'stopped') {
    return 0
  } else if (strategy.status === 'error') {
    return 15
  } else if (strategy.status === 'starting') {
    return 50  // 正在启动中
  } else if (strategy.status === 'stopping') {
    return 40  // 正在停止中
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
    // 先更新本地状态为starting
    if (currentStrategy.value) {
      currentStrategy.value.status = 'starting'
      // 立即启动自动刷新
      startDetailRefresh()
    }

    await handleStart(currentStrategy.value)

    // 重新获取详情
    const detail = await strategyStore.fetchStrategy(currentStrategy.value.id)
    currentStrategy.value = detail
  } catch (error) {
    // 错误已在handleStart中处理
    // 重新获取详情以恢复状态
    try {
      const detail = await strategyStore.fetchStrategy(currentStrategy.value.id)
      currentStrategy.value = detail
    } catch (e) {
      // 忽略
    }
  }
}

const handleStopFromDetail = async () => {
  try {
    // 先更新本地状态为stopping
    if (currentStrategy.value) {
      currentStrategy.value.status = 'stopping'
      // 立即启动自动刷新
      startDetailRefresh()
    }

    await handleStop(currentStrategy.value)

    // 重新获取详情
    const detail = await strategyStore.fetchStrategy(currentStrategy.value.id)
    currentStrategy.value = detail
  } catch (error) {
    // 错误已在handleStop中处理
    // 重新获取详情以恢复状态
    try {
      const detail = await strategyStore.fetchStrategy(currentStrategy.value.id)
      currentStrategy.value = detail
    } catch (e) {
      // 忽略
    }
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
      ElMessage.success(t('strategy.draftLoaded'))
    }
  } catch (error) {
    console.error('Failed to load draft:', error)
    ElMessage.error(t('strategy.draftLoadFailed'))
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
      t('strategy.confirmClearDraft'),
      t('strategy.confirmClear'),
      {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        type: 'warning'
      }
    )
    clearDraft()
    ElMessage.success(t('strategy.draftCleared'))
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

// 详情页自动刷新相关函数
const refreshStrategyDetail = async () => {
  if (!currentStrategy.value || !showDetailDialog.value) {
    return
  }

  try {
    const detail = await strategyStore.fetchStrategy(currentStrategy.value.id)
    currentStrategy.value = detail

    // 如果状态已经稳定（不是starting或stopping），停止刷新
    if (detail.status !== 'starting' && detail.status !== 'stopping') {
      stopDetailRefresh()
      // 同时刷新列表
      await fetchData()
    }
  } catch (error) {
    console.error('Failed to refresh strategy detail:', error)
  }
}

const startDetailRefresh = () => {
  // 先停止之前的定时器
  stopDetailRefresh()

  // 如果状态是starting或stopping，启动定时刷新
  if (currentStrategy.value &&
      (currentStrategy.value.status === 'starting' || currentStrategy.value.status === 'stopping')) {
    // 每2秒刷新一次
    detailRefreshTimer = setInterval(refreshStrategyDetail, 2000)
  }
}

const stopDetailRefresh = () => {
  if (detailRefreshTimer) {
    clearInterval(detailRefreshTimer)
    detailRefreshTimer = null
  }
}

// ===== 日志相关方法 =====

// 加载策略历史日志
const loadStrategyLogs = async (strategyId) => {
  try {
    const response = await fetch(
      `${import.meta.env.VITE_API_URL}/api/v1/strategies/${strategyId}/logs?lines=100`,
      {
        headers: {
          'Authorization': `Bearer ${userStore.token}`
        }
      }
    )
    const data = await response.json()
    strategyLogs.value = data.logs || []

    // 滚动到底部
    setTimeout(() => scrollLogsToBottom(), 100)
  } catch (error) {
    console.error('Failed to load strategy logs:', error)
    strategyLogs.value = []
  }
}

// 订阅WebSocket实时日志（支持动态主题订阅）
const subscribeToStrategyLogs = (strategyId) => {
  // 取消之前的订阅
  if (wsUnsubscribeLogs) {
    wsUnsubscribeLogs()
    wsUnsubscribeLogs = null
  }

  // 订阅策略特定日志主题（动态主题）
  const topic = `strategy_${strategyId}_logs`
  wsUnsubscribeLogs = strategyStore.subscribeToTopic(topic, (message) => {
    if (message.data && message.data.log) {
      // 添加新日志到列表
      strategyLogs.value.push(message.data.log)

      // 限制日志数量，保留最新的500条
      if (strategyLogs.value.length > 500) {
        strategyLogs.value = strategyLogs.value.slice(-500)
      }

      // 自动滚动到底部
      if (autoScroll.value) {
        setTimeout(() => scrollLogsToBottom(), 50)
      }
    }
  })
}

// 取消订阅日志
const unsubscribeFromLogs = () => {
  if (wsUnsubscribeLogs) {
    wsUnsubscribeLogs()
    wsUnsubscribeLogs = null
  }
}

// 滚动日志到底部
const scrollLogsToBottom = () => {
  if (logContainer.value) {
    logContainer.value.scrollTop = logContainer.value.scrollHeight
  }
}

// 清空日志
const clearLogs = () => {
  strategyLogs.value = []
}

// 刷新日志
const refreshLogs = async () => {
  if (currentStrategy.value) {
    await loadStrategyLogs(currentStrategy.value.id)
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

// 监听详情对话框关闭，停止详情刷新
watch(showDetailDialog, (newVal) => {
  if (!newVal) {
    stopDetailRefresh()
    unsubscribeFromLogs()  // 取消日志订阅
    clearLogs()  // 清空日志
  }
})

// 监听当前策略状态变化，启动或停止刷新
watch(() => currentStrategy.value?.status, (newStatus) => {
  if (newStatus === 'starting' || newStatus === 'stopping') {
    startDetailRefresh()
  }
})

onMounted(() => {
  fetchData()
})

onUnmounted(() => {
  stopAutoSave()
  stopDetailRefresh()
  // 清理所有状态轮询定时器
  Object.keys(statusPollingTimers).forEach(strategyId => {
    if (statusPollingTimers[strategyId]) {
      clearInterval(statusPollingTimers[strategyId])
    }
  })
  statusPollingTimers = {}
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

/* 日志容器样式 */
.log-container {
  height: 400px;
  overflow-y: auto;
  background-color: #1e1e1e;
  border-radius: 4px;
  padding: 12px;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.5;
}

.log-empty {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.log-entry {
  display: flex;
  gap: 12px;
  padding: 4px 0;
  border-bottom: 1px solid #2d2d2d;
}

.log-entry:last-child {
  border-bottom: none;
}

.log-timestamp {
  color: #858585;
  white-space: nowrap;
  flex-shrink: 0;
}

.log-level {
  font-weight: bold;
  width: 60px;
  text-align: center;
  flex-shrink: 0;
  border-radius: 3px;
  padding: 0 6px;
}

.log-level.level-info {
  color: #4fc3f7;
  background-color: rgba(79, 195, 247, 0.1);
}

.log-level.level-warning {
  color: #ffa726;
  background-color: rgba(255, 167, 38, 0.1);
}

.log-level.level-error,
.log-level.level-critical {
  color: #ef5350;
  background-color: rgba(239, 83, 80, 0.1);
}

.log-level.level-debug {
  color: #9575cd;
  background-color: rgba(149, 117, 205, 0.1);
}

.log-logger {
  color: #66bb6a;
  max-width: 200px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex-shrink: 0;
}

.log-message {
  color: #d4d4d4;
  flex: 1;
  word-break: break-word;
}

/* 自定义滚动条 */
.log-container::-webkit-scrollbar {
  width: 8px;
}

.log-container::-webkit-scrollbar-track {
  background: #2d2d2d;
  border-radius: 4px;
}

.log-container::-webkit-scrollbar-thumb {
  background: #555;
  border-radius: 4px;
}

.log-container::-webkit-scrollbar-thumb:hover {
  background: #666;
}
</style>
