import { defineStore } from 'pinia'
import { ref } from 'vue'
import { systemAPI, monitoringAPI } from '@/api'

export const useSystemStore = defineStore('system', () => {
  // State
  const capacity = ref({})
  const systemMetrics = ref({})
  const strategyMetrics = ref({})
  const healthStatus = ref({})

  // Actions
  async function fetchCapacity() {
    try {
      const res = await systemAPI.capacity()
      capacity.value = res
      return res
    } catch (error) {
      console.error('Failed to fetch capacity:', error)
      throw error
    }
  }

  async function fetchSystemMetrics() {
    try {
      const res = await monitoringAPI.system()
      systemMetrics.value = res
      return res
    } catch (error) {
      console.error('Failed to fetch system metrics:', error)
      throw error
    }
  }

  async function fetchStrategyMetrics() {
    try {
      const res = await monitoringAPI.strategies()
      strategyMetrics.value = res
      return res
    } catch (error) {
      console.error('Failed to fetch strategy metrics:', error)
      throw error
    }
  }

  async function fetchHealthStatus() {
    try {
      const res = await systemAPI.health()
      healthStatus.value = res
      return res
    } catch (error) {
      console.error('Failed to fetch health status:', error)
      throw error
    }
  }

  async function fetchCapacityTrend(hours = 24) {
    try {
      return await monitoringAPI.capacityTrend(hours)
    } catch (error) {
      console.error('Failed to fetch capacity trend:', error)
      throw error
    }
  }

  return {
    capacity,
    systemMetrics,
    strategyMetrics,
    healthStatus,
    fetchCapacity,
    fetchSystemMetrics,
    fetchStrategyMetrics,
    fetchHealthStatus,
    fetchCapacityTrend
  }
})
