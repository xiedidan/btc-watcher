import { defineStore } from 'pinia'
import { ref } from 'vue'
import { strategyAPI } from '@/api'

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
    fetchOverview
  }
})
