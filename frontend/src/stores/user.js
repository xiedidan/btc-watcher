import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authAPI } from '@/api'
import { useWebSocketStore } from './websocket'

export const useUserStore = defineStore('user', () => {
  // State
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(null)

  // Getters
  const isAuthenticated = computed(() => !!token.value)

  // Actions
  async function login(username, password) {
    try {
      console.log('[UserStore] Starting login for:', username)
      const res = await authAPI.login(username, password)
      console.log('[UserStore] Login API response:', res)

      if (!res || !res.access_token) {
        console.error('[UserStore] Invalid response - missing access_token:', res)
        return false
      }

      token.value = res.access_token
      user.value = res.user
      localStorage.setItem('token', res.access_token)
      console.log('[UserStore] Login successful, token saved')

      // TODO: WebSocket连接暂时禁用，Alpha测试后再启用
      // 登录成功后连接WebSocket
      // const wsStore = useWebSocketStore()
      // wsStore.connect(res.access_token)

      // 订阅所有主题
      // setTimeout(() => {
      //   wsStore.subscribe('monitoring')
      //   wsStore.subscribe('strategies')
      //   wsStore.subscribe('signals')
      //   wsStore.subscribe('capacity')
      // }, 1000)

      return true
    } catch (error) {
      console.error('[UserStore] Login failed:', error)
      console.error('[UserStore] Error details:', error.response || error.message)
      return false
    }
  }

  async function logout() {
    // TODO: WebSocket连接暂时禁用，Alpha测试后再启用
    // 登出前断开WebSocket
    // const wsStore = useWebSocketStore()
    // wsStore.disconnect()

    token.value = ''
    user.value = null
    localStorage.removeItem('token')
  }

  async function checkAuth() {
    if (!token.value) return false

    try {
      const userData = await authAPI.getCurrentUser()
      user.value = userData
      return true
    } catch (error) {
      console.error('Auth check failed:', error)
      await logout()
      return false
    }
  }

  async function register(username, email, password) {
    try {
      await authAPI.register(username, email, password)
      return true
    } catch (error) {
      console.error('Registration failed:', error)
      return false
    }
  }

  return {
    token,
    user,
    isAuthenticated,
    login,
    logout,
    checkAuth,
    register
  }
})
