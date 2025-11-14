<template>
  <div class="connection-status">
    <!-- 连接状态指示器 -->
    <div class="status-indicator" :class="statusClass">
      <div class="status-dot"></div>
      <span class="status-text">{{ statusText }}</span>
    </div>

    <!-- 连接模式信息 -->
    <el-tooltip :content="tooltipContent" placement="bottom">
      <el-tag
        :type="connectionMode === 'websocket' ? 'success' : 'warning'"
        size="small"
        effect="plain"
      >
        {{ connectionModeText }}
      </el-tag>
    </el-tooltip>

    <!-- 重试按钮（仅轮询模式显示） -->
    <el-button
      v-if="connectionMode === 'polling'"
      type="primary"
      size="small"
      :loading="retrying"
      @click="handleRetry"
      class="retry-button"
    >
      {{ $t('connection.retryWebSocket') }}
    </el-button>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useWebSocketStore } from '@/stores/websocket'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const wsStore = useWebSocketStore()
const userStore = useUserStore()
const retrying = ref(false)

// 连接状态
const isConnected = computed(() => wsStore.isConnected)
const connectionMode = computed(() => wsStore.connectionMode)

// 状态样式类
const statusClass = computed(() => {
  if (!isConnected.value) return 'status-disconnected'
  return connectionMode.value === 'websocket' ? 'status-websocket' : 'status-polling'
})

// 状态文本
const statusText = computed(() => {
  if (!isConnected.value) return t('connection.disconnected')
  return t('connection.connected')
})

// 连接模式文本
const connectionModeText = computed(() => {
  return connectionMode.value === 'websocket'
    ? 'WebSocket'
    : t('connection.polling')
})

// 提示内容
const tooltipContent = computed(() => {
  if (connectionMode.value === 'websocket') {
    return t('connection.usingWebSocket')
  }
  return t('connection.usingPolling')
})

// 手动重试WebSocket
const handleRetry = async () => {
  if (retrying.value) return

  retrying.value = true
  try {
    await wsStore.retryWebSocket(userStore.token)
    ElMessage.success(t('connection.retrySuccess'))
  } catch (error) {
    ElMessage.warning(t('connection.retryFailed'))
    console.error('[ConnectionStatus] Retry failed:', error)
  } finally {
    retrying.value = false
  }
}
</script>

<style scoped>
.connection-status {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background: var(--el-bg-color);
  border-radius: 8px;
  border: 1px solid var(--el-border-color-light);
  transition: background-color 0.3s, border-color 0.3s;
}

/* 暗色主题适配 */
html.dark .connection-status {
  background: var(--card-bg);
  border-color: var(--border-color);
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  animation: pulse 2s ease-in-out infinite;
}

.status-websocket .status-dot {
  background: var(--el-color-success);
}

.status-polling .status-dot {
  background: var(--el-color-warning);
  animation: pulse-warning 2s ease-in-out infinite;
}

.status-disconnected .status-dot {
  background: var(--el-color-danger);
  animation: none;
}

.status-text {
  font-size: 13px;
  color: var(--el-text-color-regular);
  font-weight: 500;
  transition: color 0.3s;
}

/* 暗色主题文字颜色 */
html.dark .status-text {
  color: var(--text-primary);
}

.retry-button {
  margin-left: 4px;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

@keyframes pulse-warning {
  0%, 100% {
    opacity: 1;
    box-shadow: 0 0 0 0 rgba(230, 162, 60, 0.7);
  }
  50% {
    opacity: 0.7;
    box-shadow: 0 0 0 4px rgba(230, 162, 60, 0);
  }
}

/* 暗色主题下的脉冲动画颜色调整 */
html.dark @keyframes pulse-warning {
  0%, 100% {
    opacity: 1;
    box-shadow: 0 0 0 0 rgba(230, 162, 60, 0.5);
  }
  50% {
    opacity: 0.7;
    box-shadow: 0 0 0 4px rgba(230, 162, 60, 0);
  }
}
</style>
