<template>
  <div class="chart-wrapper">
    <div ref="chartContainer" class="chart"></div>
    <div class="overlay" v-if="confidenceInterval">
      <span>Uncertainty band: ₹{{ confidenceInterval.lower.toFixed(2) }} → ₹{{ confidenceInterval.upper.toFixed(2) }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { createChart, ColorType, type IChartApi, type ISeriesApi } from 'lightweight-charts'
import type { Candle, PredictionResponse } from '~/composables/useApi'
import type { IndicatorPreset } from '~/types/domain'

const props = defineProps<{
  candles: Candle[]
  prediction?: PredictionResponse
  indicatorPreset: IndicatorPreset
}>()

const chartContainer = ref<HTMLDivElement | null>(null)
let chart: IChartApi | undefined
let candleSeries: ISeriesApi<'Candlestick'> | undefined
let predictionSeries: ISeriesApi<'Line'> | undefined
let smaSeries: ISeriesApi<'Line'> | undefined
let emaSeries: ISeriesApi<'Line'> | undefined
let rsiSeries: ISeriesApi<'Histogram'> | undefined

const confidenceInterval = computed(() => props.prediction?.confidence_interval)

onMounted(() => {
  if (!chartContainer.value) { return }
  chart = createChart(chartContainer.value, {
    layout: { background: { type: ColorType.Solid, color: '#0f172a' }, textColor: '#cbd5f5' },
    grid: {
      horzLines: { color: 'rgba(148, 163, 184, 0.1)' },
      vertLines: { color: 'rgba(148, 163, 184, 0.1)' },
    },
    rightPriceScale: { borderColor: '#334155' },
    timeScale: { borderColor: '#334155', timeVisible: true, secondsVisible: false },
    crosshair: { mode: 1 },
  })
  candleSeries = chart.addCandlestickSeries({
    upColor: '#22c55e',
    downColor: '#ef4444',
    wickUpColor: '#22c55e',
    wickDownColor: '#ef4444',
    borderUpColor: '#22c55e',
    borderDownColor: '#ef4444',
  })
  predictionSeries = chart.addLineSeries({
    color: '#f97316',
    lineWidth: 2,
    lineType: 2,
  })
  emaSeries = chart.addLineSeries({ color: '#6366f1', lineWidth: 1, priceLineVisible: false })
  smaSeries = chart.addLineSeries({ color: '#38bdf8', lineWidth: 1, priceLineVisible: false })
  rsiSeries = chart.addHistogramSeries({ color: 'rgba(250, 204, 21, 0.4)', priceFormat: { type: 'percent' } })
  renderChart()
})

onBeforeUnmount(() => {
  chart?.remove()
})

watch(() => [props.candles, props.prediction, props.indicatorPreset], () => renderChart(), { deep: true })

function renderChart() {
  if (!chart || !candleSeries) { return }
  if (props.candles.length === 0) { return }

  const candleData = props.candles.map((c) => ({
    time: (new Date(c.start_ts).getTime() / 1000) as unknown as number,
    open: c.open,
    high: c.high,
    low: c.low,
    close: c.close,
  }))
  candleSeries.setData(candleData)

  if (props.prediction?.predicted_series && props.prediction.predicted_series.length) {
    const predictionData = props.prediction.predicted_series.map((p) => ({
      time: (new Date(p.ts).getTime() / 1000) as unknown as number,
      value: p.price,
    }))
    predictionSeries?.setData(predictionData)
  }

  renderIndicators()
  chart.timeScale().fitContent()
}

function renderIndicators() {
  if (!props.indicatorPreset || !emaSeries || !smaSeries || !rsiSeries) { return }
  const closes = props.candles.map((c) => c.close)
  const indicatorSet = new Set(props.indicatorPreset.indicators)

  if (indicatorSet.has('ema')) {
    const emaValues = exponentialMovingAverage(closes, 21).map((value, idx) => ({
      time: (new Date(props.candles[idx].start_ts).getTime() / 1000) as unknown as number,
      value,
    }))
    emaSeries.setData(emaValues)
  } else {
    emaSeries.setData([])
  }

  if (indicatorSet.has('sma')) {
    const smaValues = simpleMovingAverage(closes, 50).map((value, idx) => ({
      time: (new Date(props.candles[idx].start_ts).getTime() / 1000) as unknown as number,
      value,
    }))
    smaSeries.setData(smaValues)
  } else {
    smaSeries.setData([])
  }

  if (indicatorSet.has('rsi')) {
    const rsiValues = relativeStrengthIndex(closes, 14).map((value, idx) => ({
      time: (new Date(props.candles[idx].start_ts).getTime() / 1000) as unknown as number,
      value,
      color: value > 70 ? 'rgba(239, 68, 68, 0.6)' : value < 30 ? 'rgba(34, 197, 94, 0.6)' : 'rgba(250, 204, 21, 0.4)',
    }))
    rsiSeries.setData(rsiValues)
  } else {
    rsiSeries.setData([])
  }
}

function simpleMovingAverage(values: number[], window: number): number[] {
  const result: number[] = []
  for (let i = 0; i < values.length; i++) {
    if (i < window) {
      result.push(values[i])
      continue
    }
    const slice = values.slice(i - window, i)
    result.push(slice.reduce((a, b) => a + b, 0) / window)
  }
  return result
}

function exponentialMovingAverage(values: number[], window: number): number[] {
  const k = 2 / (window + 1)
  const ema: number[] = []
  values.forEach((value, idx) => {
    if (idx === 0) {
      ema.push(value)
    } else {
      ema.push(value * k + ema[idx - 1] * (1 - k))
    }
  })
  return ema
}

function relativeStrengthIndex(values: number[], window: number): number[] {
  const gains: number[] = []
  const losses: number[] = []
  for (let i = 1; i < values.length; i++) {
    const change = values[i] - values[i - 1]
    gains.push(Math.max(0, change))
    losses.push(Math.max(0, -change))
  }
  const avgGain = simpleMovingAverage(gains, window)
  const avgLoss = simpleMovingAverage(losses, window)
  return avgGain.map((gain, idx) => {
    const loss = avgLoss[idx] || 1
    const rs = loss === 0 ? 100 : gain / loss
    return 100 - 100 / (1 + rs)
  })
}
</script>

<style scoped>
.chart-wrapper {
  position: relative;
  width: 100%;
  background: rgba(15, 23, 42, 0.8);
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.15);
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.45);
  overflow: hidden;
}

.chart {
  height: 540px;
}

.overlay {
  position: absolute;
  left: 16px;
  bottom: 16px;
  background: rgba(15, 23, 42, 0.85);
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 12px;
  color: #e2e8f0;
  border: 1px solid rgba(148, 163, 184, 0.25);
}
</style>
