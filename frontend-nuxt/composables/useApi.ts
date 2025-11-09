import { useRuntimeConfig } from '#imports'
import type { TradingSymbol } from '~/types/domain'

export type Candle = {
  start_ts: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export type PredictionResponse = {
  predicted_series: { ts: string; price: number }[]
  overall_confidence: number
  confidence_interval?: { lower: number; upper: number }
  bot_contributions: Record<string, { weight: number; confidence: number; meta: Record<string, unknown> }>
  trend: Record<string, unknown>
}

export const useApi = () => {
  const config = useRuntimeConfig()
  const apiBase = config.public.apiBase

  async function fetchCandles(symbol: TradingSymbol, timeframe: string) {
    const { data } = await useFetch<Candle[]>(`${apiBase}/history/latest`, {
      query: { symbol, timeframe, limit: 500 },
      key: `candles-${symbol}-${timeframe}`,
    })
    return data
  }

  async function triggerPrediction(symbol: TradingSymbol, timeframe: string, horizonMinutes: number) {
    const response = await $fetch<{ result: PredictionResponse }>(`${apiBase}/prediction/trigger`, {
      method: 'POST',
      body: { symbol, timeframe, horizon_minutes: horizonMinutes },
    })
    return response.result
  }

  async function loadLatestPrediction(symbol: TradingSymbol, timeframe: string) {
    return await $fetch<PredictionResponse>(`${apiBase}/prediction/latest`, {
      query: { symbol, timeframe },
    })
  }

  return { fetchCandles, triggerPrediction, loadLatestPrediction }
}
