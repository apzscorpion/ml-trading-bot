// API service for making HTTP requests to the backend
import axios from 'axios'

// Use relative path so it works in all environments
const API_BASE = '/api'

export const api = {
  /**
   * Fetch historical candles
   */
  async fetchHistory(symbol, timeframe, limit = 500, to_ts = null, from_ts = null, bypass_cache = false) {
    const params = {
      symbol,
      timeframe,
      limit
    }
    if (to_ts) params.to_ts = to_ts
    if (from_ts) params.from_ts = from_ts
    if (bypass_cache) params.bypass_cache = true

    try {
      const response = await axios.get(`${API_BASE}/history`, { params })
      return response.data
    } catch (error) {
      console.error('Error fetching history:', error)
      throw error
    }
  },

  /**
   * Fetch prediction
   */
  async fetchPrediction(symbol, timeframe = '5m', horizonMinutes = 180) {
    try {
      const response = await axios.get(`${API_BASE}/prediction`, {
        params: {
          symbol,
          timeframe,
          horizon_minutes: horizonMinutes
        }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching prediction:', error)
      throw error
    }
  },

  /**
   * Trigger prediction
   */
  async triggerPrediction(symbol, timeframe = '5m', horizonMinutes = 180) {
    try {
      const response = await axios.post(`${API_BASE}/prediction/trigger`, {
        symbol,
        timeframe,
        horizon_minutes: horizonMinutes
      })
      return response.data
    } catch (error) {
      console.error('Error triggering prediction:', error)
      throw error
    }
  },

  /**
   * Fetch recommendation
   */
  async fetchRecommendation(symbol, timeframe = '5m') {
    try {
      const response = await axios.get(`${API_BASE}/recommendation`, {
        params: { symbol, timeframe }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching recommendation:', error)
      throw error
    }
  },

  /**
   * Fetch market indices (Nifty50 and Sensex)
   */
  async fetchMarketIndices() {
    try {
      const response = await axios.get(`${API_BASE}/market/indices`)
      return response.data
    } catch (error) {
      console.error('Error fetching market indices:', error)
      throw error
    }
  },

  /**
   * Fetch market status
   */
  async fetchMarketStatus() {
    try {
      const response = await axios.get(`${API_BASE}/market/status`)
      return response.data
    } catch (error) {
      console.error('Error fetching market status:', error)
      throw error
    }
  },

  /**
   * Train a specific bot
   */
  async trainBot(symbol, timeframe, botName, epochs = 50, batchSize = 32) {
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
      throw error
    }
  },

  /**
   * Get bot status
   */
  async getBotStatus(botName) {
    try {
      const response = await axios.get(`${API_BASE}/models/status/${botName}`)
      return response.data
    } catch (error) {
      console.error('Error fetching bot status:', error)
      throw error
    }
  },

  /**
   * Retrain all bots
   */
  async retrainAllBots(symbol, timeframe) {
    try {
      const response = await axios.post(`${API_BASE}/models/retrain-all`, {
        symbol,
        timeframe
      })
      return response.data
    } catch (error) {
      console.error('Error retraining all bots:', error)
      throw error
    }
  },

  /**
   * Clear bot models
   */
  async clearBotModels(botName) {
    try {
      const response = await axios.delete(`${API_BASE}/models/${botName}`)
      return response.data
    } catch (error) {
      console.error('Error clearing bot models:', error)
      throw error
    }
  },

  /**
   * Get technical analysis
   */
  async getTechnicalAnalysis(symbol, timeframe = '5m') {
    try {
      const response = await axios.get(`${API_BASE}/recommendation/analysis`, {
        params: { symbol, timeframe, mode: 'ta_only' }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching technical analysis:', error)
      throw error
    }
  },

  /**
   * Get comprehensive intraday prediction
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
        // Extract error detail from backend response, or use default message
        const errorDetail = error.response?.data?.detail || 
          'Freddy AI is not configured. Set FREDDY_API_KEY, FREDDY_ORGANIZATION_ID, and FREDDY_ASSISTANT_ID in .env to enable.'
        
        return {
          error: 'freddy_disabled',
          message: errorDetail,
          analysis: null
        }
      }
      
      throw error
    }
  },

  /**
   * Trigger AI-powered training for a symbol (NEW!)
   */
  async triggerAITraining(symbol, timeframe = '5m', options = {}) {
    try {
      const payload = {
        symbol,
        timeframe,
        lookback_days: options.lookbackDays || 30,
        sample_points: options.samplePoints || 100,
        bot_names: options.botNames || ['lstm_bot', 'transformer_bot', 'ensemble_bot'],
        use_for_training: options.useForTraining !== false
      }

      const response = await axios.post(`${API_BASE}/ai-training/generate-dataset`, payload)
      return response.data
    } catch (error) {
      console.error('Error triggering AI training:', error)
      throw error
    }
  },

  /**
   * Trigger AI training for currently active symbol (quick training)
   */
  async triggerAITrainingForActiveSymbol(symbol, timeframe = '5m') {
    try {
      const response = await axios.post(`${API_BASE}/ai-training/trigger-for-active-symbol`, null, {
        params: { symbol, timeframe }
      })
      return response.data
    } catch (error) {
      console.error('Error triggering AI training for active symbol:', error)
      throw error
    }
  },

  /**
   * Get training status (for regular bot training)
   */
  async getTrainingStatus() {
    try {
      const response = await axios.get(`${API_BASE}/training/status`)
      return response.data
    } catch (error) {
      console.error('Error fetching training status:', error)
      throw error
    }
  },

  /**
   * Get AI training status
   */
  async getAITrainingStatus() {
    try {
      const response = await axios.get(`${API_BASE}/ai-training/status`)
      return response.data
    } catch (error) {
      console.error('Error fetching AI training status:', error)
      throw error
    }
  },

  /**
   * Get models report
   */
  async getModelsReport(limit = 1000) {
    try {
      const response = await axios.get(`${API_BASE}/models/report`, {
        params: { limit }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching models report:', error)
      throw error
    }
  },

  /**
   * Fetch latest prediction for a symbol
   */
  /**
   * Fetch prediction history
   */
  async fetchPredictionHistory(symbol, timeframe = '5m', limit = 50, predictionType = null) {
    try {
      const params = {
        symbol,
        timeframe,
        limit
      }
      if (predictionType) {
        params.prediction_type = predictionType
      }
      const response = await axios.get(`${API_BASE}/prediction/history/all`, { params })
      return response.data
    } catch (error) {
      console.error('Error fetching prediction history:', error)
      throw error
    }
  },

  /**
   * Fetch prediction history grouped by type
   */
  async fetchPredictionHistoryByType(symbol, timeframe = '5m', limitPerType = 10) {
    try {
      const response = await axios.get(`${API_BASE}/prediction/history/by-type`, {
        params: {
          symbol,
          timeframe,
          limit_per_type: limitPerType
        }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching prediction history by type:', error)
      throw error
    }
  },

  async fetchLatestPrediction(symbol, timeframe = '5m') {
    try {
      const response = await axios.get(`${API_BASE}/prediction/latest`, {
        params: { symbol, timeframe }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching latest prediction:', error)
      throw error
    }
  },

  /**
   * Fetch metrics summary
   */
  async fetchMetricsSummary(symbol, timeframe = '5m') {
    try {
      const response = await axios.get(`${API_BASE}/evaluation/metrics/summary`, {
        params: { symbol, timeframe }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching metrics summary:', error)
      throw error
    }
  },

  /**
   * Fetch latest candle for a symbol
   */
  async fetchLatestCandle(symbol, timeframe = '5m') {
    try {
      const response = await axios.get(`${API_BASE}/history/latest`, {
        params: { symbol, timeframe }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching latest candle:', error)
      throw error
    }
  },

  /**
   * Fetch trading recommendation
   */
  async fetchTradingRecommendation(symbol, timeframe = '5m', mode = 'combined') {
    try {
      const response = await axios.get(`${API_BASE}/recommendation/analysis`, {
        params: { symbol, timeframe, mode }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching trading recommendation:', error)
      throw error
    }
  },

  /**
   * Start auto training for multiple symbol/timeframe/bot combinations
   */
  async startAutoTraining(symbols, timeframes, bots) {
    try {
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

  /**
   * Pause training
   */
  async pauseTraining() {
    try {
      const response = await axios.post(`${API_BASE}/training/pause`)
      return response.data
    } catch (error) {
      console.error('Error pausing training:', error)
      throw error
    }
  },

  /**
   * Resume training
   */
  async resumeTraining() {
    try {
      const response = await axios.post(`${API_BASE}/training/resume`)
      return response.data
    } catch (error) {
      console.error('Error resuming training:', error)
      throw error
    }
  },

  /**
   * Stop training (stops after current task)
   */
  async stopTraining() {
    try {
      const response = await axios.post(`${API_BASE}/training/stop`)
      return response.data
    } catch (error) {
      console.error('Error stopping training:', error)
      throw error
    }
  },

  /**
   * Force stop training (immediately)
   */
  async forceStopTraining() {
    try {
      const response = await axios.post(`${API_BASE}/training/force-stop`)
      return response.data
    } catch (error) {
      console.error('Error force stopping training:', error)
      throw error
    }
  },

  /**
   * Clear a specific model
   */
  async clearModel(symbol, timeframe, botName) {
    try {
      const response = await axios.delete(`${API_BASE}/models/clear/${symbol}/${timeframe}/${botName}`)
      return response.data
    } catch (error) {
      console.error('Error clearing model:', error)
      throw error
    }
  },

  /**
   * Clear all models for a symbol across all timeframes
   */
  async clearAllModelsForSymbol(symbol) {
    try {
      const response = await axios.delete(`${API_BASE}/models/clear-all/${symbol}`)
      return response.data
    } catch (error) {
      console.error('Error clearing all models for symbol:', error)
      throw error
    }
  },

  /**
   * Clear all models for a symbol and timeframe
   */
  async clearModelsForTimeframe(symbol, timeframe) {
    try {
      const response = await axios.delete(`${API_BASE}/models/clear-all/${symbol}/${timeframe}`)
      return response.data
    } catch (error) {
      console.error('Error clearing models for timeframe:', error)
      throw error
    }
  },

  /**
   * Clear cache (both Redis and in-memory)
   */
  async clearCache() {
    try {
      const response = await axios.post(`${API_BASE}/debug/clear-cache`)
      return response.data
    } catch (error) {
      console.error('Error clearing cache:', error)
      throw error
    }
  }
}
