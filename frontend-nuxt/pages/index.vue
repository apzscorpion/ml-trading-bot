<template>
  <div class="page">
    <header>
      <div>
        <h1>Realtime Market Intelligence</h1>
        <p>Regime-aware AI forecasts tuned for the Indian equity market.</p>
      </div>
      <div class="controls">
        <select v-model="selectedSymbol">
          <option v-for="symbol in symbols" :key="symbol" :value="symbol">{{ symbol }}</option>
        </select>
        <select v-model="selectedTimeframe">
          <option v-for="tf in timeframes" :key="tf" :value="tf">{{ tf }}</option>
        </select>
        <select v-model="selectedPreset">
          <option v-for="preset in indicatorPresets" :key="preset.id" :value="preset.id">{{ preset.label }}</option>
        </select>
        <button @click="refresh" :disabled="isLoading">Refresh</button>
      </div>
    </header>

    <section class="grid">
      <div class="chart-panel">
        <TradingChart
          :candles="candles"
          :prediction="prediction"
          :indicator-preset="activePreset"
        />
      </div>
      <aside class="insights">
        <div class="insight-card">
          <h2>Forecast</h2>
          <div class="metric">
            <span>Confidence</span>
            <strong>{{ (((prediction?.overall_confidence ?? 0) * 100)).toFixed(1) }}%</strong>
          </div>
          <div v-if="prediction?.trend" class="trend">
            <span>Regime</span>
            <strong>{{ prediction.trend.regime?.toString() ?? 'unknown' }}</strong>
          </div>
          <div v-if="prediction?.confidence_interval" class="interval">
            <span>Band</span>
            <strong>₹{{ prediction.confidence_interval.lower.toFixed(2) }} → ₹{{ prediction.confidence_interval.upper.toFixed(2) }}</strong>
          </div>
        </div>
        <div class="insight-card">
          <h2>Bot Contributions</h2>
          <div v-for="(bot, name) in prediction?.bot_contributions" :key="name" class="bot-row">
            <span>{{ formatBot(name) }}</span>
            <div class="progress">
              <div class="bar" :style="{ width: (bot.weight * 100).toFixed(0) + '%' }"></div>
            </div>
            <small>{{ (bot.confidence * 100).toFixed(1) }}%</small>
          </div>
        </div>
        <button class="primary" @click="trigger" :disabled="isLoading">Generate Fresh Forecast</button>
      </aside>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import TradingChart from '~/components/TradingChart.vue'
import { useApi } from '~/composables/useApi'
import { DEFAULT_SYMBOLS, INDICATOR_PRESETS, type IndicatorPreset } from '~/types/domain'

const symbols = DEFAULT_SYMBOLS
const timeframes = ['1m', '5m', '15m', '1h', '1d']
const indicatorPresets = INDICATOR_PRESETS

const selectedSymbol = ref(symbols[0])
const selectedTimeframe = ref('5m')
const selectedPreset = ref(indicatorPresets[0].id)
const candles = ref([])
const prediction = ref()
const isLoading = ref(false)

const activePreset = computed<IndicatorPreset>(() => indicatorPresets.find((preset) => preset.id === selectedPreset.value) || indicatorPresets[0])

const { fetchCandles, loadLatestPrediction, triggerPrediction } = useApi()
const { $socket } = useNuxtApp()

const formatBot = (bot: string) => bot.replace('_bot', '').toUpperCase()

onMounted(async () => {
  await refresh()
  $socket.addListener('candle:update', handleCandleUpdate)
  $socket.addListener('prediction:update', handlePredictionUpdate)
  $socket.subscribe(selectedSymbol.value, selectedTimeframe.value)
})

onBeforeUnmount(() => {
  $socket.removeListener('candle:update', handleCandleUpdate)
  $socket.removeListener('prediction:update', handlePredictionUpdate)
})

async function refresh() {
  isLoading.value = true
  try {
    const candleData = await fetchCandles(selectedSymbol.value, selectedTimeframe.value)
    if (candleData.value) {
      candles.value = candleData.value
    }
    prediction.value = await loadLatestPrediction(selectedSymbol.value, selectedTimeframe.value)
  } finally {
    isLoading.value = false
  }
}

async function trigger() {
  isLoading.value = true
  try {
    prediction.value = await triggerPrediction(selectedSymbol.value, selectedTimeframe.value, 180)
  } finally {
    isLoading.value = false
  }
}

function handleCandleUpdate(message: any) {
  if (message.symbol !== selectedSymbol.value || message.timeframe !== selectedTimeframe.value) { return }
  if (message.candle) {
    const next = [...candles.value]
    next.push(message.candle)
    candles.value = next.slice(-800)
  }
}

function handlePredictionUpdate(message: any) {
  if (message.symbol !== selectedSymbol.value || message.timeframe !== selectedTimeframe.value) { return }
  prediction.value = message
}

watch([selectedSymbol, selectedTimeframe], async () => {
  $socket.subscribe(selectedSymbol.value, selectedTimeframe.value)
  await refresh()
})

</script>

<style scoped>
.page {
  padding: 32px;
  display: flex;
  flex-direction: column;
  gap: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 24px;
}

header h1 {
  margin: 0;
  font-size: 28px;
}

.controls {
  display: flex;
  gap: 12px;
  align-items: center;
}

.controls select,
.controls button {
  background: rgba(30, 58, 138, 0.3);
  border: 1px solid rgba(147, 197, 253, 0.2);
  color: #e2e8f0;
  border-radius: 8px;
  padding: 8px 12px;
}

.grid {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 24px;
}

.chart-panel {
  width: 100%;
}

.insights {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.insight-card {
  background: rgba(15, 23, 42, 0.65);
  border: 1px solid rgba(148, 163, 184, 0.15);
  border-radius: 16px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.metric {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.trend,
.interval {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
}

.bot-row {
  display: grid;
  grid-template-columns: 1fr 1fr auto;
  gap: 8px;
  align-items: center;
  font-size: 13px;
}

.progress {
  background: rgba(148, 163, 184, 0.2);
  border-radius: 999px;
  height: 6px;
  overflow: hidden;
}

.bar {
  height: 100%;
  background: linear-gradient(90deg, #2563eb, #22c55e);
}

.primary {
  background: linear-gradient(120deg, #2563eb, #7c3aed);
  color: white;
  padding: 12px;
  border: none;
  border-radius: 12px;
  font-weight: 600;
}
</style>
