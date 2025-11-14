/**
 * 实时数据适配器
 * Realtime Data Adapter
 *
 * 统一WebSocket和HTTP轮询的数据获取接口
 * 特性：
 * - WebSocket优先，HTTP轮询降级
 * - 按页面需求智能轮询
 * - 页面可见性优化
 */
import wsClient from './websocket'
import { REALTIME_CONFIG, getPollingStrategy, getPollingInterval } from '@/config/realtime'
import axios from 'axios'

class RealtimeDataAdapter {
  constructor() {
    this.mode = 'websocket'  // 'websocket' | 'polling'
    this.timers = {
      high: null,
      medium: null,
      low: null
    }
    this.currentPage = 'dashboard'
    this.isConnected = false
    this.wsRetryCount = 0
    this.lastSignalId = 0

    // 回调函数 - 改为数组支持多个监听器
    this.callbacks = {
      onData: [],        // 改为数组
      onModeChange: null,
      onError: null
    }

    // 绑定页面可见性事件
    this.setupVisibilityHandler()
  }

  /**
   * 连接（优先WebSocket）
   */
  async connect(token, page = 'dashboard') {
    this.currentPage = page

    if (REALTIME_CONFIG.debug.forcePolling) {
      console.log('[Realtime] Force polling mode enabled')
      this.fallbackToPolling()
      return
    }

    if (!REALTIME_CONFIG.websocket.enabled) {
      this.fallbackToPolling()
      return
    }

    try {
      await this.tryWebSocket(token)
    } catch (error) {
      console.warn('[Realtime] WebSocket failed, fallback to polling:', error)
      this.fallbackToPolling()
    }
  }

  /**
   * 尝试WebSocket连接
   */
  async tryWebSocket(token) {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error('WebSocket connection timeout'))
      }, REALTIME_CONFIG.websocket.connectionTimeout)

      // 构建WebSocket URL
      let wsUrl = import.meta.env.VITE_WS_URL

      if (!wsUrl) {
        // 根据当前页面协议和主机自动构建WebSocket URL
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        const host = window.location.host  // 会通过Vite dev server的代理
        wsUrl = `${protocol}//${host}`

        if (REALTIME_CONFIG.debug.logConnections) {
          console.log('[Realtime] Auto-constructed WebSocket URL:', wsUrl)
        }
      } else {
        if (REALTIME_CONFIG.debug.logConnections) {
          console.log('[Realtime] Using configured WebSocket URL:', wsUrl)
        }
      }

      wsClient.on('open', () => {
        clearTimeout(timeout)
        this.mode = 'websocket'
        this.isConnected = true
        this.wsRetryCount = 0

        if (REALTIME_CONFIG.debug.logConnections) {
          console.log('[Realtime] WebSocket connected')
        }
        this.callbacks.onModeChange?.('websocket')
        resolve()
      })

      wsClient.on('connected', (data) => {
        clearTimeout(timeout)
        if (REALTIME_CONFIG.debug.logConnections) {
          console.log('[Realtime] WebSocket ready, available topics:', data.available_topics)
        }

        // 订阅当前页面需要的主题
        this.subscribeTopics()
        resolve()
      })

      wsClient.on('close', (event) => {
        clearTimeout(timeout)
        this.isConnected = false

        if (event.code !== 1000 && this.wsRetryCount < REALTIME_CONFIG.websocket.retryAttempts) {
          // 非正常关闭，重试
          this.wsRetryCount++
          console.log(`[Realtime] Retry WebSocket (${this.wsRetryCount}/${REALTIME_CONFIG.websocket.retryAttempts})`)

          setTimeout(() => {
            this.tryWebSocket(token).catch(() => {
              if (this.wsRetryCount >= REALTIME_CONFIG.websocket.retryAttempts) {
                this.fallbackToPolling()
              }
            })
          }, REALTIME_CONFIG.websocket.retryDelay)
        } else if (this.wsRetryCount >= REALTIME_CONFIG.websocket.retryAttempts) {
          reject(new Error('Max retry attempts reached'))
        }
      })

      wsClient.on('error', (error) => {
        clearTimeout(timeout)
        console.error('[Realtime] WebSocket error:', error)
        this.callbacks.onError?.(error)
        reject(error)
      })

      wsClient.on('data', (message) => {
        // 调用所有data回调
        this.callbacks.onData.forEach(callback => callback(message))
      })

      // 开始连接 - 传入token和wsUrl
      wsClient.connect(token, wsUrl)
    })
  }

  /**
   * 订阅WebSocket主题
   */
  subscribeTopics() {
    const strategy = getPollingStrategy(this.currentPage)
    const allTopics = [...strategy.high, ...strategy.medium, ...strategy.low]

    allTopics.forEach(topic => {
      wsClient.subscribe(topic)
    })

    if (REALTIME_CONFIG.debug.logConnections) {
      console.log('[Realtime] Subscribed to topics:', allTopics)
    }
  }

  /**
   * 降级到轮询模式
   */
  fallbackToPolling() {
    console.log('[Realtime] Switching to polling mode')

    this.mode = 'polling'
    this.isConnected = false

    // 断开WebSocket
    if (wsClient.isConnected) {
      wsClient.disconnect()
    }

    // 启动轮询
    this.startPolling()

    this.callbacks.onModeChange?.('polling')
  }

  /**
   * 启动轮询
   */
  startPolling(page) {
    if (page) {
      this.currentPage = page
    }

    this.stopPolling()

    const strategy = getPollingStrategy(this.currentPage)

    if (REALTIME_CONFIG.debug.logConnections) {
      console.log('[Realtime] Starting polling for page:', this.currentPage, strategy)
    }

    // 高频轮询
    if (strategy.high.length > 0) {
      this.startFrequencyPolling('high', strategy.high)
    }

    // 中频轮询
    if (strategy.medium.length > 0) {
      this.startFrequencyPolling('medium', strategy.medium)
    }

    // 低频轮询
    if (strategy.low.length > 0) {
      this.startFrequencyPolling('low', strategy.low)
    }

    // 立即执行一次
    if (strategy.high.length > 0) this.fetchBatch(strategy.high)
    if (strategy.medium.length > 0) this.fetchBatch(strategy.medium)
    if (strategy.low.length > 0) this.fetchBatch(strategy.low)
  }

  /**
   * 启动特定频率的轮询
   */
  startFrequencyPolling(frequency, topics) {
    let interval = getPollingInterval(frequency)

    // 页面不可见时降低频率
    if (document.hidden) {
      interval *= REALTIME_CONFIG.polling.backgroundMultiplier
      if (REALTIME_CONFIG.debug.logPolling) {
        console.log(`[Realtime] Background mode, ${frequency} interval: ${interval}ms`)
      }
    }

    this.timers[frequency] = setInterval(() => {
      // 检查页面可见性
      if (document.hidden) {
        if (REALTIME_CONFIG.debug.logPolling) {
          console.log('[Realtime] Page hidden, skipping poll')
        }
        return  // 后台时跳过
      }

      this.fetchBatch(topics)
    }, interval)
  }

  /**
   * 批量获取数据
   */
  async fetchBatch(topics) {
    if (REALTIME_CONFIG.debug.logPolling) {
      console.log('[Realtime] Polling:', topics)
    }

    try {
      const params = {
        topics: topics.join(',')
      }

      // 信号增量查询
      if (topics.includes('signals') && this.lastSignalId > 0) {
        params.last_signal_id = this.lastSignalId
      }

      const response = await axios.get('/api/v1/realtime/batch', { params })

      if (response.data.success) {
        const data = response.data.data

        // 更新最后信号ID
        if (data.signals && data.signals.last_id) {
          this.lastSignalId = data.signals.last_id
        }

        // 触发数据回调
        topics.forEach(topic => {
          if (data[topic]) {
            const message = {
              type: 'data',
              topic: topic,
              data: data[topic],
              timestamp: data[topic].timestamp
            }
            // 调用所有data回调
            this.callbacks.onData.forEach(callback => callback(message))
          }
        })
      }
    } catch (error) {
      console.error('[Realtime] Polling error:', error)
      this.callbacks.onError?.(error)
    }
  }

  /**
   * 停止轮询
   */
  stopPolling() {
    Object.values(this.timers).forEach(timer => {
      if (timer) clearInterval(timer)
    })
    this.timers = { high: null, medium: null, low: null }
  }

  /**
   * 断开连接
   */
  disconnect() {
    if (this.mode === 'websocket') {
      wsClient.disconnect()
    } else {
      this.stopPolling()
    }

    this.isConnected = false
  }

  /**
   * 切换页面
   */
  switchPage(page) {
    if (this.currentPage === page) return

    if (REALTIME_CONFIG.debug.logConnections) {
      console.log('[Realtime] Switching page:', this.currentPage, '->', page)
    }

    this.currentPage = page

    if (this.mode === 'websocket') {
      // WebSocket模式：重新订阅
      // TODO: 取消订阅旧主题，优化资源使用
      this.subscribeTopics()
    } else {
      // 轮询模式：重启轮询
      this.startPolling(page)
    }
  }

  /**
   * 手动重试WebSocket
   */
  async retryWebSocket(token) {
    if (this.mode === 'websocket') {
      console.log('[Realtime] Already in WebSocket mode')
      return
    }

    console.log('[Realtime] Manual retry WebSocket')
    this.stopPolling()
    this.wsRetryCount = 0

    try {
      await this.tryWebSocket(token)
    } catch (error) {
      console.error('[Realtime] Retry failed:', error)
      this.fallbackToPolling()
      throw error
    }
  }

  /**
   * 注册回调
   */
  on(event, callback) {
    if (event === 'data') {
      // data事件支持多个监听器
      if (!this.callbacks.onData.includes(callback)) {
        this.callbacks.onData.push(callback)
      }
    }
    if (event === 'modeChange') this.callbacks.onModeChange = callback
    if (event === 'error') this.callbacks.onError = callback
  }

  /**
   * 移除回调
   */
  off(event, callback) {
    if (event === 'data') {
      const index = this.callbacks.onData.indexOf(callback)
      if (index > -1) {
        this.callbacks.onData.splice(index, 1)
      }
    }
  }

  /**
   * 订阅动态主题（用于特殊需求，如策略日志）
   * @param {string} topic - 主题名称
   */
  subscribe(topic) {
    if (this.mode === 'websocket' && wsClient.isConnected) {
      wsClient.subscribe(topic)
      if (REALTIME_CONFIG.debug.logConnections) {
        console.log(`[Realtime] Subscribed to dynamic topic: ${topic}`)
      }
    } else {
      console.warn(`[Realtime] Cannot subscribe to ${topic}: not in websocket mode`)
    }
  }

  /**
   * 取消订阅主题
   * @param {string} topic - 主题名称
   */
  unsubscribe(topic) {
    if (this.mode === 'websocket' && wsClient.isConnected) {
      wsClient.unsubscribe(topic)
      if (REALTIME_CONFIG.debug.logConnections) {
        console.log(`[Realtime] Unsubscribed from dynamic topic: ${topic}`)
      }
    }
  }

  /**
   * 获取当前状态
   */
  getStatus() {
    return {
      mode: this.mode,
      isConnected: this.isConnected,
      currentPage: this.currentPage,
      wsRetryCount: this.wsRetryCount
    }
  }

  /**
   * 设置页面可见性处理
   */
  setupVisibilityHandler() {
    document.addEventListener('visibilitychange', () => {
      if (this.mode !== 'polling') return

      if (document.hidden) {
        if (REALTIME_CONFIG.debug.logConnections) {
          console.log('[Realtime] Page hidden, will reduce polling frequency on next cycle')
        }
        // 页面隐藏时，下一个轮询周期会自动使用降低的频率
      } else {
        if (REALTIME_CONFIG.debug.logConnections) {
          console.log('[Realtime] Page visible, restoring polling frequency')
        }
        // 页面恢复时，重启轮询以使用正常频率
        this.startPolling()
      }
    })
  }
}

// 全局单例
const realtimeAdapter = new RealtimeDataAdapter()

export default realtimeAdapter
