/**
 * WebSocket状态管理
 * WebSocket State Management
 *
 * 使用Pinia管理WebSocket连接状态和数据
 * 支持WebSocket和HTTP轮询双模式
 */
import { defineStore } from 'pinia'
import realtimeAdapter from '@/utils/realtimeDataAdapter'

export const useWebSocketStore = defineStore('websocket', {
  state: () => ({
    // 连接状态
    connectionMode: 'websocket',    // 'websocket' | 'polling'
    isConnected: false,
    reconnectAttempts: 0,
    subscribedTopics: [],

    // 实时数据
    monitoringData: null,      // 系统监控数据
    strategiesData: null,       // 策略状态数据
    signalsData: [],            // 新信号数据
    capacityData: null,         // 容量数据

    // 健康状态
    healthStatus: null,

    // 事件和通知
    events: [],                 // 事件列表
    notifications: [],          // 通知列表

    // 最后更新时间
    lastUpdate: {
      monitoring: null,
      strategies: null,
      signals: null,
      capacity: null
    }
  }),

  getters: {
    /**
     * 是否已连接
     */
    connected: (state) => state.isConnected,

    /**
     * 获取系统健康状态
     */
    systemHealth: (state) => {
      if (!state.healthStatus) return null
      return state.healthStatus.status
    },

    /**
     * 获取运行中的策略数量
     */
    runningStrategiesCount: (state) => {
      if (!state.strategiesData) return 0
      return state.strategiesData.running || 0
    },

    /**
     * 获取最近的信号
     */
    recentSignals: (state) => {
      return state.signalsData.slice(0, 10)
    },

    /**
     * 获取未读通知数量
     */
    unreadNotificationsCount: (state) => {
      return state.notifications.filter(n => !n.read).length
    },

    /**
     * CPU使用率
     */
    cpuUsage: (state) => {
      if (!state.monitoringData?.system?.cpu) return null
      return state.monitoringData.system.cpu.percent
    },

    /**
     * 内存使用率
     */
    memoryUsage: (state) => {
      if (!state.monitoringData?.system?.memory) return null
      return state.monitoringData.system.memory.percent
    },

    /**
     * 磁盘使用率
     */
    diskUsage: (state) => {
      if (!state.monitoringData?.system?.disk) return null
      return state.monitoringData.system.disk.percent
    }
  },

  actions: {
    /**
     * 连接实时数据（WebSocket优先，自动降级到轮询）
     * @param {string} token - JWT token
     * @param {string} page - 页面名称 (dashboard/strategies/signals/monitoring/settings)
     */
    async connect(token, page = 'dashboard') {
      if (this.isConnected) {
        console.warn('[Store] Already connected')
        return
      }

      // 注册适配器回调
      this.setupAdapterCallbacks()

      // 连接适配器（会自动尝试WebSocket，失败则降级到轮询）
      try {
        await realtimeAdapter.connect(token, page)
      } catch (error) {
        console.error('[Store] Failed to connect:', error)
      }
    },

    /**
     * 断开连接
     */
    disconnect() {
      realtimeAdapter.disconnect()
      this.isConnected = false
      this.subscribedTopics = []
      this.connectionMode = 'websocket'
    },

    /**
     * 切换页面（更新订阅策略）
     * @param {string} page - 页面名称
     */
    switchPage(page) {
      realtimeAdapter.switchPage(page)
    },

    /**
     * 手动重试WebSocket连接
     * @param {string} token - JWT token
     */
    async retryWebSocket(token) {
      try {
        await realtimeAdapter.retryWebSocket(token)
      } catch (error) {
        console.error('[Store] Retry WebSocket failed:', error)
        throw error
      }
    },

    /**
     * 设置适配器回调
     */
    setupAdapterCallbacks() {
      // 接收数据
      realtimeAdapter.on('data', (message) => {
        this.handleDataMessage(message)
      })

      // 连接模式变化
      realtimeAdapter.on('modeChange', (mode) => {
        console.log('[Store] Connection mode changed to:', mode)
        this.connectionMode = mode
        this.isConnected = (mode === 'websocket') ? realtimeAdapter.isConnected : true

        // 轮询模式也视为已连接
        if (mode === 'polling') {
          this.isConnected = true
        }
      })

      // 错误处理
      realtimeAdapter.on('error', (error) => {
        console.error('[Store] Adapter error:', error)
      })
    },

    /**
     * 处理数据消息
     * @param {object} message - 消息对象
     */
    handleDataMessage(message) {
      const { topic, data, timestamp } = message

      switch (topic) {
        case 'monitoring':
          // 更新监控数据
          this.monitoringData = data
          this.healthStatus = data.health
          this.lastUpdate.monitoring = timestamp
          break

        case 'strategies':
          // 更新策略数据
          this.strategiesData = data
          this.lastUpdate.strategies = timestamp
          break

        case 'signals':
          // 添加新信号（保留最近50个）
          if (data.signals && data.signals.length > 0) {
            this.signalsData.unshift(...data.signals)
            this.signalsData = this.signalsData.slice(0, 50)
            this.lastUpdate.signals = timestamp
          }
          break

        case 'capacity':
          // 更新容量数据
          this.capacityData = data
          this.lastUpdate.capacity = timestamp
          break

        default:
          // 检查是否是动态主题（如 strategy_*_logs）
          if (topic.startsWith('strategy_') && topic.endsWith('_logs')) {
            // 动态主题由其他store处理（如strategy store），这里忽略
            console.debug(`[Store] Ignoring dynamic topic: ${topic}`)
          } else {
            console.warn('[Store] Unknown data topic:', topic)
          }
      }
    },

    /**
     * 处理事件消息
     * @param {object} message - 消息对象
     */
    handleEventMessage(message) {
      const { event_type, data, timestamp } = message

      // 添加到事件列表
      this.events.unshift({
        type: event_type,
        data,
        timestamp,
        read: false
      })

      // 只保留最近100个事件
      this.events = this.events.slice(0, 100)

      // 根据事件类型执行特定操作
      switch (event_type) {
        case 'strategy_started':
          console.log('[Event] Strategy started:', data)
          break

        case 'strategy_stopped':
          console.log('[Event] Strategy stopped:', data)
          break

        case 'signal_received':
          console.log('[Event] Signal received:', data)
          break

        default:
          console.log('[Event]', event_type, data)
      }
    },

    /**
     * 处理通知消息
     * @param {object} message - 消息对象
     */
    handleNotificationMessage(message) {
      const { data, timestamp } = message

      // 添加到通知列表
      this.notifications.unshift({
        ...data,
        timestamp,
        read: false
      })

      // 只保留最近50个通知
      this.notifications = this.notifications.slice(0, 50)

      // 可以在这里触发浏览器通知
      if (Notification.permission === 'granted') {
        new Notification(data.title || '新通知', {
          body: data.message || '',
          icon: '/logo.png'
        })
      }
    },

    /**
     * 标记通知为已读
     * @param {number} index - 通知索引
     */
    markNotificationAsRead(index) {
      if (this.notifications[index]) {
        this.notifications[index].read = true
      }
    },

    /**
     * 标记所有通知为已读
     */
    markAllNotificationsAsRead() {
      this.notifications.forEach(n => {
        n.read = true
      })
    },

    /**
     * 清除所有通知
     */
    clearNotifications() {
      this.notifications = []
    },

    /**
     * 标记事件为已读
     * @param {number} index - 事件索引
     */
    markEventAsRead(index) {
      if (this.events[index]) {
        this.events[index].read = true
      }
    },

    /**
     * 获取连接状态
     */
    getStatus() {
      return {
        isConnected: this.isConnected,
        connectionMode: this.connectionMode,
        reconnectAttempts: this.reconnectAttempts,
        subscribedTopics: this.subscribedTopics,
        adapterStatus: realtimeAdapter.getStatus()
      }
    }
  }
})
