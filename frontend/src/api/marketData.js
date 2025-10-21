/**
 * Market Data API Client
 * Provides methods for accessing cryptocurrency market data and indicators
 */
import request from './request'

// Market Data API
export const marketDataAPI = {
  /**
   * Get K-line (OHLCV) data
   * @param {Object} params - Query parameters
   * @param {string} params.symbol - Trading pair symbol (e.g., BTC/USDT)
   * @param {string} params.timeframe - Timeframe (1m, 5m, 15m, 1h, 4h, 1d)
   * @param {string} [params.exchange='binance'] - Exchange name
   * @param {number} [params.limit=200] - Number of candles to fetch
   * @param {boolean} [params.force_refresh=false] - Force refresh from API
   * @returns {Promise} K-line data response
   */
  getKlines: (params) => {
    return request.get('/market/klines', { params })
  },

  /**
   * Get technical indicator data
   * @param {string} indicatorType - Indicator type (MA, MACD, RSI, BOLL, VOL)
   * @param {Object} params - Query parameters
   * @param {string} params.symbol - Trading pair symbol
   * @param {string} params.timeframe - Timeframe
   * @param {string} [params.exchange='binance'] - Exchange name
   * @param {boolean} [params.force_refresh=false] - Force recalculate
   * @returns {Promise} Indicator data response
   */
  getIndicator: (indicatorType, params) => {
    return request.get(`/market/indicators/${indicatorType}`, { params })
  },

  /**
   * Get all technical indicators for a symbol
   * @param {Object} params - Query parameters
   * @param {string} params.symbol - Trading pair symbol
   * @param {string} params.timeframe - Timeframe
   * @param {string} [params.exchange='binance'] - Exchange name
   * @param {boolean} [params.force_refresh=false] - Force recalculate
   * @returns {Promise} All indicators response
   */
  getAllIndicators: (params) => {
    return request.get('/market/indicators', { params })
  },

  /**
   * Get list of supported exchanges
   * @returns {Promise} List of exchange names
   */
  getSupportedExchanges: () => {
    return request.get('/market/exchanges')
  },

  /**
   * Get list of supported timeframes
   * @returns {Promise} List of timeframe strings
   */
  getSupportedTimeframes: () => {
    return request.get('/market/timeframes')
  },

  // Scheduler operations
  /**
   * Start market data scheduler
   * @returns {Promise} Scheduler status
   */
  startScheduler: () => {
    return request.post('/market/scheduler/start')
  },

  /**
   * Stop market data scheduler
   * @returns {Promise} Success message
   */
  stopScheduler: () => {
    return request.post('/market/scheduler/stop')
  },

  /**
   * Get scheduler status
   * @returns {Promise} Scheduler status and job information
   */
  getSchedulerStatus: () => {
    return request.get('/market/scheduler/status')
  },

  /**
   * Trigger manual market data update
   * @param {Object} [params] - Optional parameters
   * @param {string} [params.symbol] - Specific symbol to update
   * @param {string} [params.timeframe] - Specific timeframe to update
   * @returns {Promise} Update confirmation
   */
  triggerManualUpdate: (params = {}) => {
    return request.post('/market/scheduler/trigger', null, { params })
  }
}

// System Configuration API
export const systemConfigAPI = {
  /**
   * Get full system configuration
   * @returns {Promise} System configuration
   */
  getConfig: () => {
    return request.get('/system/config')
  },

  /**
   * Get market data configuration
   * @returns {Promise} Market data configuration
   */
  getMarketDataConfig: () => {
    return request.get('/system/config/market-data')
  },

  /**
   * Update market data configuration
   * @param {Object} config - Configuration updates
   * @returns {Promise} Updated configuration
   */
  updateMarketDataConfig: (config) => {
    return request.put('/system/config/market-data', config)
  },

  /**
   * Reset market data configuration to defaults
   * @returns {Promise} Reset confirmation with default config
   */
  resetMarketDataConfig: () => {
    return request.post('/system/config/market-data/reset')
  },

  /**
   * Get default market data configuration
   * @returns {Promise} Default configuration values
   */
  getDefaultMarketDataConfig: () => {
    return request.get('/system/config/defaults/market-data')
  }
}

// Health Check API
export const healthCheckAPI = {
  /**
   * Market data service health check
   * @returns {Promise} Health status of all market data components
   */
  marketData: () => {
    return request.get('/health/market-data')
  },

  /**
   * Exchange connectivity health check
   * @returns {Promise} Health status of all exchanges
   */
  exchanges: () => {
    return request.get('/health/exchanges')
  },

  /**
   * Cache system health check
   * @returns {Promise} Redis cache health and statistics
   */
  cache: () => {
    return request.get('/health/cache')
  },

  /**
   * Database health check
   * @returns {Promise} PostgreSQL database health and statistics
   */
  database: () => {
    return request.get('/health/database')
  }
}

export default {
  marketDataAPI,
  systemConfigAPI,
  healthCheckAPI
}
