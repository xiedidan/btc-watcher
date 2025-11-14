import { defineStore } from 'pinia'
import { ref } from 'vue'
import { strategyAPI } from '@/api'
import realtimeAdapter from '@/utils/realtimeDataAdapter'

export const useStrategyStore = defineStore('strategy', () => {
  // State
  const strategies = ref([])
  const currentStrategy = ref(null)
  const loading = ref(false)

  // Actions
  async function fetchStrategies(params = {}) {
    loading.value = true
    try {
      const res = await strategyAPI.list(params)
      strategies.value = res.strategies
      return res
    } catch (error) {
      console.error('Failed to fetch strategies:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  async function fetchStrategy(id) {
    loading.value = true
    try {
      const res = await strategyAPI.get(id)
      currentStrategy.value = res
      return res
    } catch (error) {
      console.error('Failed to fetch strategy:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  async function createStrategy(data) {
    loading.value = true
    try {
      const res = await strategyAPI.create(data)
      await fetchStrategies()
      return res
    } catch (error) {
      console.error('Failed to create strategy:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  async function startStrategy(id) {
    try {
      const res = await strategyAPI.start(id)
      await fetchStrategies()
      return res
    } catch (error) {
      console.error('Failed to start strategy:', error)
      throw error
    }
  }

  async function stopStrategy(id) {
    try {
      const res = await strategyAPI.stop(id)
      await fetchStrategies()
      return res
    } catch (error) {
      console.error('Failed to stop strategy:', error)
      throw error
    }
  }

  async function deleteStrategy(id) {
    try {
      const res = await strategyAPI.delete(id)
      await fetchStrategies()
      return res
    } catch (error) {
      console.error('Failed to delete strategy:', error)
      throw error
    }
  }

  async function fetchOverview() {
    try {
      return await strategyAPI.overview()
    } catch (error) {
      console.error('Failed to fetch overview:', error)
      throw error
    }
  }

  /**
   * 订阅WebSocket主题并注册回调
   * @param {string} topic - 主题名称
   * @param {function} callback - 消息回调函数
   * @returns {function} 取消订阅的函数
   */
  function subscribeToTopic(topic, callback) {
    // 订阅主题（使用realtimeAdapter的动态订阅功能）
    realtimeAdapter.subscribe(topic)

    // 注册数据监听器
    const dataHandler = (message) => {
      // 只处理匹配的主题
      if (message.topic === topic) {
        callback(message)
      }
    }

    // 监听data事件（支持多个监听器）
    realtimeAdapter.on('data', dataHandler)

    // 返回取消订阅函数
    return () => {
      realtimeAdapter.unsubscribe(topic)
      realtimeAdapter.off('data', dataHandler)
    }
  }

  return {
    strategies,
    currentStrategy,
    loading,
    fetchStrategies,
    fetchStrategy,
    createStrategy,
    startStrategy,
    stopStrategy,
    deleteStrategy,
    fetchOverview,
    subscribeToTopic
  }
})
