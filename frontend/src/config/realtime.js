/**
 * 实时数据配置
 * Realtime data configuration
 *
 * 定义WebSocket和轮询模式的配置参数
 */

// 轮询策略：按页面定义需要的数据和频率
export const POLLING_STRATEGIES = {
  // Dashboard页面：全部数据
  dashboard: {
    high: ['monitoring', 'strategies'],     // 5秒
    medium: ['signals'],                     // 10秒
    low: ['capacity']                        // 30秒
  },

  // 策略页面：只需策略数据
  strategies: {
    high: ['strategies'],                    // 5秒
    medium: [],
    low: []
  },

  // 信号页面：策略+信号
  signals: {
    high: ['strategies'],                    // 5秒
    medium: ['signals'],                     // 10秒
    low: []
  },

  // 监控页面：监控+策略+容量
  monitoring: {
    high: ['monitoring', 'strategies'],      // 5秒
    medium: [],
    low: ['capacity']                        // 30秒
  },

  // 设置页面：只需容量
  settings: {
    high: [],
    medium: [],
    low: ['capacity']                        // 30秒
  }
}

export const REALTIME_CONFIG = {
  // WebSocket配置
  websocket: {
    enabled: true,              // 是否启用WebSocket
    retryAttempts: 3,           // 最大重试次数
    retryDelay: 3000,           // 重试延迟（毫秒）
    heartbeatInterval: 25000,   // 心跳间隔（服务器30秒超时）
    connectionTimeout: 10000    // 连接超时
  },

  // 轮询配置
  polling: {
    enabled: true,              // 是否启用轮询降级
    fallbackDelay: 10000,       // 降级等待时间（10秒后触发降级）

    // 轮询间隔（毫秒）
    intervals: {
      high: 5000,      // 高频：5秒
      medium: 10000,   // 中频：10秒
      low: 30000       // 低频：30秒
    },

    // 页面不可见时的优化
    backgroundMultiplier: 2,  // 后台时间隔翻倍（降低服务器负载）
  },

  // 调试选项
  debug: {
    forcePolling: false,        // 强制使用轮询模式（测试用）
    logConnections: true,       // 记录连接日志
    logPolling: false           // 记录轮询日志（调试时启用）
  }
}

/**
 * 根据页面名称获取轮询策略
 * @param {string} pageName - 页面名称
 * @returns {object} 轮询策略对象
 */
export function getPollingStrategy(pageName) {
  return POLLING_STRATEGIES[pageName] || POLLING_STRATEGIES.dashboard
}

/**
 * 获取主题的轮询间隔
 * @param {string} frequency - 频率级别 ('high' | 'medium' | 'low')
 * @returns {number} 轮询间隔（毫秒）
 */
export function getPollingInterval(frequency) {
  return REALTIME_CONFIG.polling.intervals[frequency] || 5000
}
