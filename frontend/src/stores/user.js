import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authAPI } from '@/api'

export const useUserStore = defineStore('user', () => {
  // State
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(null)

  // Getters
  const isAuthenticated = computed(() => !!token.value)

  // Actions
  async function login(username, password) {
    try {
      const res = await authAPI.login(username, password)
      token.value = res.access_token
      user.value = res.user
      localStorage.setItem('token', res.access_token)
      return true
    } catch (error) {
      console.error('Login failed:', error)
      return false
    }
  }

  async function logout() {
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
