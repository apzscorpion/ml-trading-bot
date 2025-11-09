/**
 * WebSocket service for real-time updates
 */
export class SocketService {
  constructor() {
    this.ws = null
    this.listeners = {
      'candle:update': [],
      'prediction:update': [],
      'training:progress': [],
      'subscribed': [],
      'connected': [],
      'disconnected': []
    }
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.reconnectDelay = 2000
  }

  /**
   * Connect to WebSocket server
   */
  connect(url = null) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected')
      return
    }

    // Use proxy in development, direct connection in production
    if (!url) {
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsHost = window.location.host
      url = `${wsProtocol}//${wsHost}/ws`
    }

    console.log('Connecting to WebSocket...', url)
    this.ws = new WebSocket(url)

    this.ws.onopen = () => {
      console.log('WebSocket connected')
      this.reconnectAttempts = 0
      this._emit('connected')
    }

    this.ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data)
        this._handleMessage(message)
      } catch (error) {
        console.error('Error parsing WebSocket message:', error)
      }
    }

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    this.ws.onclose = () => {
      console.log('WebSocket disconnected')
      this._emit('disconnected')
      this._reconnect()
    }
  }

  /**
   * Disconnect WebSocket
   */
  disconnect() {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  /**
   * Subscribe to symbol updates
   */
  subscribe(symbol, timeframe) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.error('WebSocket not connected')
      return
    }

    const message = {
      action: 'subscribe',
      symbol,
      timeframe
    }

    this.ws.send(JSON.stringify(message))
    console.log(`Subscribed to ${symbol} ${timeframe}`)
  }

  /**
   * Unsubscribe from updates
   * @param {string} symbol - Optional symbol to unsubscribe from (for logging)
   * @param {string} timeframe - Optional timeframe to unsubscribe from (for logging)
   */
  unsubscribe(symbol = null, timeframe = null) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      return
    }

    const message = { action: 'unsubscribe' }
    this.ws.send(JSON.stringify(message))
    
    if (symbol && timeframe) {
      console.log(`Unsubscribed from ${symbol} ${timeframe}`)
    } else {
      console.log('Unsubscribed from all updates')
    }
  }

  /**
   * Register event listener
   */
  on(event, callback) {
    if (!this.listeners[event]) {
      this.listeners[event] = []
    }
    this.listeners[event].push(callback)
  }

  /**
   * Remove event listener
   */
  off(event, callback) {
    if (!this.listeners[event]) return
    
    this.listeners[event] = this.listeners[event].filter(cb => cb !== callback)
  }

  /**
   * Handle incoming message
   */
  _handleMessage(message) {
    const type = message.type

    if (type === 'candle:update') {
      this._emit('candle:update', message)
    } else if (type === 'prediction:update') {
      this._emit('prediction:update', message)
    } else if (type === 'training:progress') {
      this._emit('training:progress', message)
    } else if (type === 'subscribed') {
      this._emit('subscribed', message)
    }
  }

  /**
   * Emit event to listeners
   */
  _emit(event, data = null) {
    if (!this.listeners[event]) return

    this.listeners[event].forEach(callback => {
      try {
        callback(data)
      } catch (error) {
        console.error(`Error in ${event} listener:`, error)
      }
    })
  }

  /**
   * Attempt to reconnect
   */
  _reconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached')
      return
    }

    this.reconnectAttempts++
    console.log(`Reconnecting... Attempt ${this.reconnectAttempts}`)

    setTimeout(() => {
      this.connect()
    }, this.reconnectDelay * this.reconnectAttempts)
  }
}

// Singleton instance
export const socketService = new SocketService()

