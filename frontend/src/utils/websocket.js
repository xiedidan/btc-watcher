/**
 * WebSocket客户端管理器
 * WebSocket Client Manager
 *
 * 功能：
 * - WebSocket连接管理
 * - 自动重连
 * - 心跳检测
 * - 消息订阅
 * - 事件处理
 */

class WebSocketClient {
  constructor() {
    this.ws = null
    this.url = null
    this.token = null
    this.isConnected = false
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.reconnectDelay = 3000 // 3秒
    this.heartbeatInterval = null
    this.heartbeatTimeout = 25000 // 25秒（服务器30秒超时）

    // 订阅的主题
    this.subscribedTopics = new Set()

    // 事件监听器
    this.listeners = {
      open: [],
      close: [],
      error: [],
      message: [],
      connected: [],
      data: [],
      event: [],
      notification: [],
      ping: []
    }
  }

  /**
   * 连接WebSocket
   * @param {string} token - JWT token
   * @param {string} baseUrl - WebSocket服务器地址
   */
  connect(token, baseUrl = 'ws://localhost:8000') {
    if (this.isConnected) {
      console.warn('WebSocket already connected')
      return
    }

    this.token = token
    this.url = `${baseUrl}/api/v1/ws?token=${token}`

    try {
      this.ws = new WebSocket(this.url)

      // 连接打开
      this.ws.onopen = (event) => {
        console.log('WebSocket connected')
        this.isConnected = true
        this.reconnectAttempts = 0
        this.startHeartbeat()
        this.emit('open', event)
      }

      // 接收消息
      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          this.handleMessage(message)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }

      // 连接关闭
      this.ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason)
        this.isConnected = false
        this.stopHeartbeat()
        this.emit('close', event)

        // 如果不是正常关闭，尝试重连
        if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnect()
        }
      }

      // 连接错误
      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        this.emit('error', error)
      }

    } catch (error) {
      console.error('Failed to create WebSocket:', error)
      this.emit('error', error)
    }
  }

  /**
   * 断开连接
   */
  disconnect() {
    if (this.ws) {
      this.stopHeartbeat()
      this.ws.close(1000, 'Client disconnect')
      this.ws = null
      this.isConnected = false
      this.subscribedTopics.clear()
    }
  }

  /**
   * 重新连接
   */
  reconnect() {
    this.reconnectAttempts++
    console.log(`Attempting to reconnect... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`)

    setTimeout(() => {
      if (!this.isConnected && this.token) {
        this.connect(this.token, this.url.split('/api')[0])
      }
    }, this.reconnectDelay * this.reconnectAttempts)
  }

  /**
   * 发送消息
   * @param {object} message - 消息对象
   */
  send(message) {
    if (!this.isConnected || !this.ws) {
      console.warn('WebSocket not connected')
      return false
    }

    try {
      this.ws.send(JSON.stringify(message))
      return true
    } catch (error) {
      console.error('Failed to send WebSocket message:', error)
      return false
    }
  }

  /**
   * 订阅主题
   * @param {string} topic - 主题名称 (monitoring, strategies, signals, logs, capacity)
   */
  subscribe(topic) {
    if (this.subscribedTopics.has(topic)) {
      console.warn(`Already subscribed to ${topic}`)
      return
    }

    const success = this.send({
      type: 'subscribe',
      topic: topic
    })

    if (success) {
      this.subscribedTopics.add(topic)
      console.log(`Subscribed to ${topic}`)
    }
  }

  /**
   * 取消订阅主题
   * @param {string} topic - 主题名称
   */
  unsubscribe(topic) {
    if (!this.subscribedTopics.has(topic)) {
      console.warn(`Not subscribed to ${topic}`)
      return
    }

    const success = this.send({
      type: 'unsubscribe',
      topic: topic
    })

    if (success) {
      this.subscribedTopics.delete(topic)
      console.log(`Unsubscribed from ${topic}`)
    }
  }

  /**
   * 处理接收到的消息
   * @param {object} message - 消息对象
   */
  handleMessage(message) {
    const { type } = message

    // 触发通用消息事件
    this.emit('message', message)

    // 根据消息类型触发特定事件
    switch (type) {
      case 'connected':
        console.log('Connected to WebSocket server:', message)
        this.emit('connected', message)

        // 重新订阅之前的主题
        this.subscribedTopics.forEach(topic => {
          this.send({ type: 'subscribe', topic })
        })
        break

      case 'subscribed':
        console.log(`Subscribed to ${message.topic}`)
        break

      case 'unsubscribed':
        console.log(`Unsubscribed from ${message.topic}`)
        break

      case 'data':
        // 数据推送
        this.emit('data', message)
        break

      case 'event':
        // 事件推送
        this.emit('event', message)
        break

      case 'notification':
        // 通知推送
        this.emit('notification', message)
        break

      case 'ping':
        // 服务器ping，响应pong
        this.sendPong()
        this.emit('ping', message)
        break

      case 'error':
        console.error('WebSocket error message:', message)
        break

      default:
        console.warn('Unknown message type:', type, message)
    }
  }

  /**
   * 发送pong响应
   */
  sendPong() {
    this.send({
      type: 'pong',
      timestamp: new Date().toISOString()
    })
  }

  /**
   * 启动心跳
   */
  startHeartbeat() {
    this.stopHeartbeat()

    this.heartbeatInterval = setInterval(() => {
      if (this.isConnected) {
        this.sendPong()
      }
    }, this.heartbeatTimeout)
  }

  /**
   * 停止心跳
   */
  stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval)
      this.heartbeatInterval = null
    }
  }

  /**
   * 添加事件监听器
   * @param {string} event - 事件名称
   * @param {function} callback - 回调函数
   */
  on(event, callback) {
    if (!this.listeners[event]) {
      this.listeners[event] = []
    }
    this.listeners[event].push(callback)
  }

  /**
   * 移除事件监听器
   * @param {string} event - 事件名称
   * @param {function} callback - 回调函数
   */
  off(event, callback) {
    if (!this.listeners[event]) {
      return
    }

    const index = this.listeners[event].indexOf(callback)
    if (index > -1) {
      this.listeners[event].splice(index, 1)
    }
  }

  /**
   * 触发事件
   * @param {string} event - 事件名称
   * @param {any} data - 事件数据
   */
  emit(event, data) {
    if (!this.listeners[event]) {
      return
    }

    this.listeners[event].forEach(callback => {
      try {
        callback(data)
      } catch (error) {
        console.error(`Error in ${event} listener:`, error)
      }
    })
  }

  /**
   * 获取连接状态
   */
  getStatus() {
    return {
      isConnected: this.isConnected,
      reconnectAttempts: this.reconnectAttempts,
      subscribedTopics: Array.from(this.subscribedTopics),
      readyState: this.ws ? this.ws.readyState : null
    }
  }
}

// 创建全局单例
const wsClient = new WebSocketClient()

export default wsClient
