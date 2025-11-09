/**
 * Refresh Service - Coordinates automatic data refresh
 * Manages refresh intervals and pauses during user interactions
 */

class RefreshService {
  constructor() {
    this.refreshInterval = null
    this.refreshIntervalMs = 60 * 1000 // 60 seconds
    this.isPaused = false
    this.lastRefreshTime = null
    this.callbacks = {
      refreshHistory: null,
      refreshPrediction: null,
      refreshMetrics: null
    }
  }

  /**
   * Start automatic refresh
   * @param {Object} callbacks - Object with refreshHistory, refreshPrediction, refreshMetrics functions
   */
  start(callbacks) {
    if (this.refreshInterval) {
      this.stop()
    }

    this.callbacks = { ...this.callbacks, ...callbacks }
    this.lastRefreshTime = Date.now()

    // Refresh immediately
    this.performRefresh()

    // Set up interval
    this.refreshInterval = setInterval(() => {
      if (!this.isPaused) {
        this.performRefresh()
      }
    }, this.refreshIntervalMs)

    console.log('🔄 Refresh service started (60s interval)')
  }

  /**
   * Stop automatic refresh
   */
  stop() {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval)
      this.refreshInterval = null
      console.log('⏸️ Refresh service stopped')
    }
  }

  /**
   * Pause refresh (e.g., when user is panning/zooming)
   */
  pause() {
    this.isPaused = true
    console.log('⏸️ Refresh service paused')
  }

  /**
   * Resume refresh
   */
  resume() {
    this.isPaused = false
    // If it's been a while since last refresh, refresh immediately
    const timeSinceLastRefresh = Date.now() - (this.lastRefreshTime || 0)
    if (timeSinceLastRefresh > this.refreshIntervalMs) {
      this.performRefresh()
    }
    console.log('▶️ Refresh service resumed')
  }

  /**
   * Perform refresh (called by interval or manually)
   */
  async performRefresh() {
    if (this.isPaused) {
      return
    }

    try {
      console.log('🔄 Performing automatic refresh...')
      
      // Execute callbacks
      if (this.callbacks.refreshHistory) {
        await this.callbacks.refreshHistory()
      }
      
      if (this.callbacks.refreshPrediction) {
        await this.callbacks.refreshPrediction()
      }
      
      if (this.callbacks.refreshMetrics) {
        await this.callbacks.refreshMetrics()
      }

      this.lastRefreshTime = Date.now()
      console.log('✅ Automatic refresh completed')
    } catch (error) {
      console.error('❌ Error during automatic refresh:', error)
    }
  }

  /**
   * Check if chart is showing recent data (last 24 hours)
   * @param {Array} candles - Array of candle objects
   * @returns {boolean}
   */
  isShowingRecentData(candles) {
    if (!candles || candles.length === 0) {
      return false
    }

    const newestCandle = candles[candles.length - 1]
    const newestTimestamp = new Date(newestCandle.start_ts).getTime()
    const now = Date.now()
    const twentyFourHoursMs = 24 * 60 * 60 * 1000

    return (now - newestTimestamp) < twentyFourHoursMs
  }

  /**
   * Get time since last refresh
   * @returns {number} Milliseconds since last refresh
   */
  getTimeSinceLastRefresh() {
    if (!this.lastRefreshTime) {
      return null
    }
    return Date.now() - this.lastRefreshTime
  }
}

// Export singleton instance
export const refreshService = new RefreshService()

