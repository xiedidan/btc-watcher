import request from './request'

// 认证API
export const authAPI = {
  // 登录
  login: (username, password) => {
    const formData = new FormData()
    formData.append('username', username)
    formData.append('password', password)
    return request.post('/auth/token', formData)
  },

  // 注册
  register: (username, email, password) => {
    return request.post('/auth/register', null, {
      params: { username, email, password }
    })
  },

  // 获取当前用户信息
  getCurrentUser: () => {
    return request.get('/auth/me')
  },

  // 修改密码
  changePassword: (oldPassword, newPassword) => {
    return request.put('/auth/me/password', null, {
      params: { old_password: oldPassword, new_password: newPassword }
    })
  }
}

// 策略API
export const strategyAPI = {
  // 获取策略列表
  list: (params = {}) => {
    return request.get('/strategies/', { params })
  },

  // 获取策略详情
  get: (id) => {
    return request.get(`/strategies/${id}`)
  },

  // 创建策略
  create: (data) => {
    return request.post('/strategies/', data)
  },

  // 启动策略
  start: (id) => {
    return request.post(`/strategies/${id}/start`)
  },

  // 停止策略
  stop: (id) => {
    return request.post(`/strategies/${id}/stop`)
  },

  // 删除策略
  delete: (id) => {
    return request.delete(`/strategies/${id}`)
  },

  // 获取策略概览
  overview: () => {
    return request.get('/strategies/overview')
  }
}

// 信号API
export const signalAPI = {
  // 获取信号列表
  list: (params = {}) => {
    return request.get('/signals/', { params })
  },

  // 获取信号详情
  get: (id) => {
    return request.get(`/signals/${id}`)
  },

  // 获取信号统计
  statistics: (params = {}) => {
    return request.get('/signals/statistics/summary', { params })
  }
}

// 系统API
export const systemAPI = {
  // 获取系统容量
  capacity: () => {
    return request.get('/system/capacity')
  },

  // 获取端口池状态
  portPool: () => {
    return request.get('/system/port-pool')
  },

  // 获取详细容量信息
  capacityDetailed: () => {
    return request.get('/system/capacity/detailed')
  },

  // 获取容量趋势
  capacityTrend: (hours = 24) => {
    return request.get('/system/capacity/utilization-trend', { params: { hours } })
  },

  // 设置容量告警阈值
  setAlertThreshold: (threshold) => {
    return request.post('/system/capacity/alert-threshold', null, {
      params: { threshold_percent: threshold }
    })
  },

  // 获取系统统计
  statistics: () => {
    return request.get('/system/statistics')
  },

  // 健康检查
  health: () => {
    return request.get('/system/health')
  }
}

// 监控API
export const monitoringAPI = {
  // 获取系统监控指标
  system: () => {
    return request.get('/monitoring/system')
  },

  // 获取策略监控指标
  strategies: () => {
    return request.get('/monitoring/strategies')
  },

  // 获取容量趋势
  capacityTrend: (hours = 24) => {
    return request.get('/monitoring/capacity/trend', { params: { hours } })
  },

  // 获取健康摘要
  healthSummary: () => {
    return request.get('/monitoring/health-summary')
  }
}

// 通知API
export const notificationAPI = {
  // 发送通知
  send: (data) => {
    return request.post('/notifications/send', null, { params: data })
  },

  // 测试通知
  test: (channel) => {
    return request.post('/notifications/test', null, { params: { channel } })
  },

  // 获取通知统计
  statistics: (hours = 24) => {
    return request.get('/notifications/statistics', { params: { hours } })
  },

  // 获取通知渠道
  channels: () => {
    return request.get('/notifications/channels')
  }
}
