import { defineNuxtPlugin, useRuntimeConfig } from '#imports'

type Subscription = {
  symbol: string
  timeframe: string
}

type SocketMessage = {
  type: string
  symbol: string
  timeframe: string
  candle?: Record<string, unknown>
  prediction?: Record<string, unknown>
}

class SocketService {
  private socket?: WebSocket
  private heartbeat?: number
  private reconnectTimer?: number
  private readonly config: ReturnType<typeof useRuntimeConfig>['public']
  private readonly listeners = new Map<string, Set<(payload: SocketMessage) => void>>()
  private subscription?: Subscription

  constructor(config: ReturnType<typeof useRuntimeConfig>['public']) {
    this.config = config
  }

  connect() {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      return
    }
    this.socket = new WebSocket(this.config.wsBase)
    this.socket.onopen = () => {
      if (this.subscription) {
        this.send({ action: 'subscribe', ...this.subscription })
      }
      this.heartbeat = window.setInterval(() => this.send({ action: 'ping' }), 25000)
    }
    this.socket.onclose = () => this.scheduleReconnect()
    this.socket.onerror = () => this.scheduleReconnect()
    this.socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as SocketMessage
        this.broadcast(message)
      } catch (error) {
        console.warn('Failed to parse socket message', error)
      }
    }
  }

  subscribe(symbol: string, timeframe: string) {
    this.subscription = { symbol, timeframe }
    this.send({ action: 'subscribe', symbol, timeframe })
  }

  addListener(channel: string, handler: (payload: SocketMessage) => void) {
    if (!this.listeners.has(channel)) {
      this.listeners.set(channel, new Set())
    }
    this.listeners.get(channel)!.add(handler)
  }

  removeListener(channel: string, handler: (payload: SocketMessage) => void) {
    this.listeners.get(channel)?.delete(handler)
  }

  private broadcast(message: SocketMessage) {
    this.listeners.get(message.type)?.forEach((handler) => handler(message))
  }

  private send(payload: Record<string, unknown>) {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(payload))
    }
  }

  private scheduleReconnect() {
    if (this.heartbeat) {
      window.clearInterval(this.heartbeat)
    }
    if (this.reconnectTimer) {
      window.clearTimeout(this.reconnectTimer)
    }
    this.reconnectTimer = window.setTimeout(() => this.connect(), 4000)
  }
}

export default defineNuxtPlugin(() => {
  const config = useRuntimeConfig()
  const service = new SocketService(config.public)
  service.connect()
  return {
    provide: {
      socket: service,
    },
  }
})
