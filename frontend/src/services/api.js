/**
 * API service for REST endpoints
 */
import axios from 'axios'

const API_BASE = '/api'

export const api = {
  /**
   * Fetch historical candles
   */
  async fetchHistory(symbol, timeframe, limit = 500, to_ts = null, from_ts = null, bypass_cache = false) {
    try {
      const params = { symbol, timeframe, limit }
      if (to_ts) params.to_ts = to_ts
      if (from_ts) params.from_ts = from_ts
      if (bypass_cache) params.bypass_cache = true  // Add bypass_cache parameter
      
      console.log('🌐 API Call: fetchHistory', params)
      
      const response = await axios.get(`${API_BASE}/history`, {
        params
      })
      
      console.log('✅ API Response: fetchHistory', { 
        count: response.data?.length || 0,
        symbol,
        timeframe,
        hasData: !!response.data
      })
      
      return response.data
    } catch (error) {
      console.error('❌ Error fetching history:', error)
      return []
    }
  },

  /**
   * Get latest candle for a symbol (for watchlist prices)
   */
  async fetchLatestCandle(symbol, timeframe = '5m') {
    try {
      const response = await axios.get(`${API_BASE}/history/latest`, {
        params: { symbol, timeframe }
      })
      return response.data
    } catch (error) {
      console.error(`Error fetching latest candle for ${symbol}:`, error)
      return null
    }
  },

  /**
   * Get latest prediction
   */
  async fetchLatestPrediction(symbol, timeframe) {
    try {
      const response = await axios.get(`${API_BASE}/prediction/latest`, {
        params: { symbol, timeframe }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching prediction:', error)
      return null
    }
  },

  /**
   * Trigger new prediction
   */
  async triggerPrediction(symbol, timeframe, horizonMinutes = 180, selectedBots = null) {
    try {
      const payload = {
        symbol,
        timeframe,
        horizon_minutes: horizonMinutes
      }
      if (selectedBots) {
        payload.selected_bots = selectedBots
      }
      const response = await axios.post(`${API_BASE}/prediction/trigger`, payload)
      return response.data
    } catch (error) {
      console.error('Error triggering prediction:', error)
      return null
    }
  },

  /**
   * Get prediction history
   */
  async fetchPredictionHistory(symbol, timeframe, limit = 50) {
    try {
      const response = await axios.get(`${API_BASE}/prediction/history/all`, {
        params: { symbol, timeframe, limit }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching prediction history:', error)
      return []
    }
  },

  /**
   * Get bot performance metrics
   */
  async fetchBotPerformance(symbol = null, days = 7) {
    try {
      const params = { days }
      if (symbol) params.symbol = symbol
      
      const response = await axios.get(`${API_BASE}/evaluation/bot-performance`, { params })
      return response.data
    } catch (error) {
      console.error('Error fetching bot performance:', error)
      return null
    }
  },

  /**
   * Get available symbols
   */
  async fetchSymbols() {
    try {
      const response = await axios.get(`${API_BASE}/history/symbols`)
      return response.data.symbols || []
    } catch (error) {
      console.error('Error fetching symbols:', error)
      return []
    }
  },

  /**
   * Get metrics summary
   */
  async fetchMetricsSummary(symbol, timeframe) {
    try {
      const response = await axios.get(`${API_BASE}/evaluation/metrics/summary`, {
        params: { symbol, timeframe }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching metrics:', error)
      return null
    }
  },

  /**
   * Get available bots
   */
  async fetchAvailableBots() {
    try {
      const response = await axios.get(`${API_BASE}/prediction/bots/available`)
      return response.data
    } catch (error) {
      console.error('Error fetching available bots:', error)
      return null
    }
  },

  /**
   * Train a bot (returns immediately with training_id, progress via WebSocket)
   */
  async trainBot(symbol, timeframe, botName, epochs = 50, batchSize = 200) {
    try {
      const response = await axios.post(`${API_BASE}/prediction/train`, {
        symbol,
        timeframe,
        bot_name: botName,
        epochs,
        batch_size: batchSize
      })
      return response.data
    } catch (error) {
      console.error('Error training bot:', error)
      // Add notification if notification center is available
      if (window.notificationCenter) {
        const errorDetails = {
          message: error.message,
          status: error.response?.status,
          statusText: error.response?.statusText,
          data: error.response?.data,
          config: {
            url: error.config?.url,
            method: error.config?.method,
            data: error.config?.data
          }
        }
        window.notificationCenter.addError(
          `Training failed for ${botName}: ${error.response?.data?.detail || error.message}`,
          errorDetails,
          `POST ${API_BASE}/prediction/train (${botName})`
        )
      }
      // Return error response data if available, otherwise null
      if (error.response?.data) {
        return { ...error.response.data, error: true }
      }
      return null
    }
  },

  /**
   * Get trading recommendation analysis
   */
  async fetchTradingRecommendation(symbol, timeframe) {
    try {
      const response = await axios.get(`${API_BASE}/recommendation/analysis`, {
        params: { symbol, timeframe }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching trading recommendation:', error)
      return null
    }
  },

  /**
   * Clear data cache to force fresh data fetch
   */
  async clearCache() {
    try {
      const response = await axios.post(`${API_BASE}/debug/clear-cache`)
      return response.data
    } catch (error) {
      console.error('Error clearing cache:', error)
      return null
    }
  },

  /**
   * Get debug info about latest data
   */
  async getDebugInfo(symbol, timeframe) {
    try {
      const response = await axios.get(`${API_BASE}/debug/latest-data`, {
        params: { symbol, timeframe }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching debug info:', error)
      return null
    }
  },

  /**
   * Model Management APIs
   */
  async getModelsReport() {
    try {
      const response = await axios.get(`${API_BASE}/models/report`, {
        timeout: 30000 // 30 second timeout - increased for large datasets
      })
      return response.data
    } catch (error) {
      console.error('Error fetching models report:', error)
      return null
    }
  },

  async getTrainingStatus() {
    try {
      const response = await axios.get(`${API_BASE}/training/status`, {
        timeout: 15000 // 15 second timeout - increased for reliability
      })
      return response.data
    } catch (error) {
      console.error('Error fetching training status:', error)
      return {
        is_running: false,
        is_paused: false,
        current_training: null,
        queue_length: 0,
        completed_count: 0,
        failed_count: 0
      }
    }
  },

  async startAutoTraining(symbols, timeframes, bots) {
    try {
      // Note: This endpoint returns immediately after queuing the background training tasks.
      // The actual training happens asynchronously in the background.
      // No timeout - endpoint returns immediately after queuing
      const response = await axios.post(`${API_BASE}/training/start-auto`, {
        symbols,
        timeframes,
        bots
      })
      return response.data
    } catch (error) {
      console.error('Error starting auto training:', error)
      throw error
    }
  },

  async pauseTraining() {
    try {
      const response = await axios.post(`${API_BASE}/training/pause`)
      return response.data
    } catch (error) {
      console.error('Error pausing training:', error)
      throw error
    }
  },

  async resumeTraining() {
    try {
      const response = await axios.post(`${API_BASE}/training/resume`)
      return response.data
    } catch (error) {
      console.error('Error resuming training:', error)
      throw error
    }
  },

  async clearModelsForTimeframe(symbol, timeframe) {
    try {
      const response = await axios.delete(`${API_BASE}/models/clear-all/${symbol}/${timeframe}`)
      return response.data
    } catch (error) {
      console.error('Error clearing models for timeframe:', error)
      throw error
    }
  },

  async stopTraining() {
    try {
      const response = await axios.post(`${API_BASE}/training/stop`)
      return response.data
    } catch (error) {
      console.error('Error stopping training:', error)
      throw error
    }
  },

  async forceStopTraining() {
    try {
      const response = await axios.post(`${API_BASE}/training/force-stop`)
      return response.data
    } catch (error) {
      console.error('Error force stopping training:', error)
      throw error
    }
  },

  async clearModel(symbol, timeframe, botName) {
    try {
      const response = await axios.delete(
        `${API_BASE}/models/clear/${symbol}/${timeframe}/${botName}`
      )
      return response.data
    } catch (error) {
      console.error('Error clearing model:', error)
      throw error
    }
  },

  async clearAllModelsForSymbol(symbol) {
    try {
      console.log(`🗑️ API: Clearing all models for ${symbol}`)
      const response = await axios.delete(
        `${API_BASE}/models/clear-all/${symbol}`,
        {
          timeout: 30000 // 30 second timeout
        }
      )
      console.log(`✅ API: Clear models response:`, response.data)
      return response.data
    } catch (error) {
      console.error('❌ API Error clearing all models for symbol:', {
        symbol,
        message: error.message,
        response: error.response?.data,
        status: error.response?.status,
        statusText: error.response?.statusText,
        url: error.config?.url
      })
      throw error
    }
  },

  /**
   * Get comprehensive intraday prediction using all models, indicators, and patterns
   */
  async fetchComprehensivePrediction(symbol, timeframe = '5m', horizonMinutes = 180) {
    try {
      const response = await axios.get(`${API_BASE}/intraday/comprehensive-prediction`, {
        params: { symbol, timeframe, horizon_minutes: horizonMinutes }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching comprehensive prediction:', error)
      return null
    }
  },

  /**
   * Run Freddy AI analysis with custom prompt and real-time context
   */
  async runFreddyAnalysis({
    symbol,
    timeframe = '5m',
    prompt,
    useCache = false,
    lookbackMinutes = 360
  }) {
    try {
      if (!symbol) {
        throw new Error('Symbol is required for Freddy analysis')
      }

      const payload = {
        symbol,
        timeframe,
        use_cache: useCache,
        lookback_minutes: lookbackMinutes
      }

      if (prompt && prompt.trim().length > 0) {
        payload.prompt = prompt.trim()
      }

      const response = await axios.post(`${API_BASE}/freddy/analysis`, payload)
      return response.data
    } catch (error) {
      console.error('Error running Freddy analysis:', error)
      
      // Check if Freddy AI is disabled (503) or not configured (502)
      if (error.response?.status === 503 || error.response?.status === 502) {
        return {
          error: 'freddy_disabled',
          message: 'Freddy AI is not configured. Set FREDDY_API_KEY, FREDDY_ORGANIZATION_ID, and FREDDY_ASSISTANT_ID in .env to enable.',
          analysis: null
        }
      }
      
      throw error
    }
  }
}

