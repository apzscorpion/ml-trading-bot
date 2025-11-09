<template>
  <div class="analysis-panel">
    <h3>📊 Trading Analysis & Recommendation</h3>
    
    <div v-if="loading" class="loading">
      <div class="spinner-small"></div>
      <p>Analyzing predictions...</p>
    </div>
    
    <div v-else-if="analysis" class="analysis-content">
      <!-- Main Recommendation Card -->
      <div class="recommendation-card" :class="recommendationClass">
        <div class="recommendation-header">
          <div class="recommendation-badge" :class="recommendationClass">
            {{ analysis.recommendation.toUpperCase() }}
          </div>
          <div class="signal-strength" :class="signalClass">
            {{ formatSignalStrength(analysis.signal_strength) }}
          </div>
        </div>
        
        <div class="recommendation-body">
          <div class="price-info">
            <div class="price-item">
              <span class="label">Current Price</span>
              <span class="value">₹{{ analysis.current_price?.toFixed(2) || 'N/A' }}</span>
            </div>
            <div class="price-item">
              <span class="label">Predicted Price</span>
              <span class="value">₹{{ analysis.predicted_price?.toFixed(2) || 'N/A' }}</span>
            </div>
            <div class="price-item">
              <span class="label">Expected Change</span>
              <span class="value" :class="changeClass">
                {{ analysis.price_change_pct >= 0 ? '+' : '' }}{{ analysis.price_change_pct?.toFixed(2) }}%
              </span>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Metrics Grid -->
      <div class="metrics-row">
        <div class="metric-box">
          <div class="metric-icon">🎯</div>
          <div class="metric-info">
            <span class="metric-label">Success Rate</span>
            <span class="metric-value" :class="successRateClass">
              {{ analysis.success_rate ? analysis.success_rate.toFixed(1) + '%' : 'N/A' }}
            </span>
          </div>
        </div>
        
        <div class="metric-box">
          <div class="metric-icon">📈</div>
          <div class="metric-info">
            <span class="metric-label">Trend</span>
            <span class="metric-value">{{ formatTrend(analysis.trend) }}</span>
          </div>
        </div>
        
        <div class="metric-box">
          <div class="metric-icon">⚡</div>
          <div class="metric-info">
            <span class="metric-label">Volatility</span>
            <span class="metric-value">{{ analysis.volatility?.toFixed(2) }}%</span>
          </div>
        </div>
        
        <div class="metric-box">
          <div class="metric-icon">⚠️</div>
          <div class="metric-info">
            <span class="metric-label">Risk Level</span>
            <span class="metric-value" :class="riskClass">
              {{ analysis.risk_level?.toUpperCase() }}
            </span>
          </div>
        </div>
      </div>
      
      <!-- Insights -->
      <div v-if="analysis.insights && analysis.insights.length > 0" class="insights-section">
        <h4>💡 Key Insights</h4>
        <ul class="insights-list">
          <li v-for="(insight, idx) in analysis.insights" :key="idx">
            {{ insight }}
          </li>
        </ul>
      </div>
      
      <!-- Additional Info -->
      <div class="info-footer">
        <span class="info-item">
          <strong>Horizon:</strong> {{ analysis.horizon_minutes }} minutes
        </span>
        <span class="info-item">
          <strong>Confidence:</strong> {{ analysis.confidence?.toFixed(1) }}%
        </span>
        <span class="info-item">
          <strong>Updated:</strong> {{ formatTime(analysis.prediction_time) }}
        </span>
      </div>
    </div>
    
    <div v-else class="no-data">
      <p>No analysis available. Generate a prediction first.</p>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed, onMounted } from 'vue'
import { api } from '../services/api'

const props = defineProps({
  symbol: {
    type: String,
    required: true
  },
  timeframe: {
    type: String,
    required: true
  },
  refreshTrigger: {
    type: Number,
    default: 0
  }
})

const analysis = ref(null)
const loading = ref(false)

// Computed classes
const recommendationClass = computed(() => {
  if (!analysis.value) return ''
  return `recommendation-${analysis.value.recommendation}`
})

const signalClass = computed(() => {
  if (!analysis.value) return ''
  const strength = analysis.value.signal_strength
  if (strength === 'very_strong') return 'signal-very-strong'
  if (strength === 'strong') return 'signal-strong'
  if (strength === 'moderate') return 'signal-moderate'
  return 'signal-weak'
})

const changeClass = computed(() => {
  if (!analysis.value) return ''
  return analysis.value.price_change_pct >= 0 ? 'positive' : 'negative'
})

const successRateClass = computed(() => {
  if (!analysis.value?.success_rate) return ''
  const rate = analysis.value.success_rate
  if (rate >= 70) return 'success-high'
  if (rate >= 50) return 'success-medium'
  return 'success-low'
})

const riskClass = computed(() => {
  if (!analysis.value) return ''
  return `risk-${analysis.value.risk_level}`
})

// Debounce timer to prevent rapid-fire requests
let debounceTimer = null

// Methods
const loadAnalysis = async () => {
  // Clear any pending debounce
  if (debounceTimer) {
    clearTimeout(debounceTimer)
    debounceTimer = null
  }
  
  loading.value = true
  try {
    const data = await api.fetchTradingRecommendation(props.symbol, props.timeframe)
    if (data && !data.error) {
      analysis.value = data
    }
  } catch (error) {
    console.error('Error loading analysis:', error)
  } finally {
    loading.value = false
  }
}

// Debounced version for watch
const loadAnalysisDebounced = () => {
  if (debounceTimer) {
    clearTimeout(debounceTimer)
  }
  // Wait 300ms after last change before loading
  debounceTimer = setTimeout(() => {
    loadAnalysis()
  }, 300)
}

const formatSignalStrength = (strength) => {
  if (!strength) return 'N/A'
  return strength.replace('_', ' ').toUpperCase()
}

const formatTrend = (trend) => {
  if (!trend) return 'N/A'
  return trend.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())
}

const formatTime = (isoString) => {
  if (!isoString) return 'N/A'
  return new Date(isoString).toLocaleString()
}

// Watch for changes with debouncing (but load immediately on mount)
watch([() => props.symbol, () => props.timeframe, () => props.refreshTrigger], loadAnalysisDebounced, { immediate: false })
// Load immediately on mount (but wait a bit for other critical data to load first)
onMounted(() => {
  setTimeout(() => loadAnalysis(), 500) // Delay to let history/prediction load first
})
</script>

<style scoped>
.analysis-panel {
  background: #18181b;
  padding: 24px;
  border-radius: 8px;
  border: 1px solid #2b2b2e;
}

.analysis-panel h3 {
  margin: 0 0 20px 0;
  font-size: 18px;
  color: #efeff1;
}

.loading {
  display: flex;
  align-items: center;
  gap: 12px;
  color: #999;
  padding: 20px 0;
}

.spinner-small {
  width: 20px;
  height: 20px;
  border: 2px solid #2b2b2e;
  border-top-color: #2962FF;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.analysis-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.recommendation-card {
  background: #1a1a1d;
  border-radius: 8px;
  padding: 20px;
  border: 2px solid;
}

.recommendation-card.recommendation-buy {
  border-color: #26a69a;
  background: linear-gradient(135deg, rgba(38, 166, 154, 0.1), rgba(38, 166, 154, 0.05));
}

.recommendation-card.recommendation-sell {
  border-color: #ef5350;
  background: linear-gradient(135deg, rgba(239, 83, 80, 0.1), rgba(239, 83, 80, 0.05));
}

.recommendation-card.recommendation-hold {
  border-color: #ffa726;
  background: linear-gradient(135deg, rgba(255, 167, 38, 0.1), rgba(255, 167, 38, 0.05));
}

.recommendation-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.recommendation-badge {
  font-size: 24px;
  font-weight: 700;
  padding: 8px 20px;
  border-radius: 6px;
}

.recommendation-badge.recommendation-buy {
  background: #26a69a;
  color: white;
}

.recommendation-badge.recommendation-sell {
  background: #ef5350;
  color: white;
}

.recommendation-badge.recommendation-hold {
  background: #ffa726;
  color: white;
}

.signal-strength {
  font-size: 12px;
  font-weight: 600;
  padding: 6px 12px;
  border-radius: 4px;
  text-transform: uppercase;
}

.signal-very-strong {
  background: #26a69a;
  color: white;
}

.signal-strong {
  background: #66bb6a;
  color: white;
}

.signal-moderate {
  background: #ffa726;
  color: white;
}

.signal-weak {
  background: #888;
  color: white;
}

.recommendation-body {
  margin-top: 16px;
}

.price-info {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 16px;
}

.price-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.price-item .label {
  font-size: 12px;
  color: #999;
}

.price-item .value {
  font-size: 20px;
  font-weight: 600;
  color: #efeff1;
}

.price-item .value.positive {
  color: #26a69a;
}

.price-item .value.negative {
  color: #ef5350;
}

.metrics-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}

.metric-box {
  background: #1a1a1d;
  padding: 16px;
  border-radius: 6px;
  border: 1px solid #2b2b2e;
  display: flex;
  align-items: center;
  gap: 12px;
}

.metric-icon {
  font-size: 28px;
}

.metric-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.metric-label {
  font-size: 12px;
  color: #999;
}

.metric-value {
  font-size: 18px;
  font-weight: 600;
  color: #efeff1;
}

.metric-value.success-high {
  color: #26a69a;
}

.metric-value.success-medium {
  color: #ffa726;
}

.metric-value.success-low {
  color: #ef5350;
}

.metric-value.risk-high {
  color: #ef5350;
}

.metric-value.risk-medium {
  color: #ffa726;
}

.metric-value.risk-low {
  color: #26a69a;
}

.insights-section {
  background: #1a1a1d;
  padding: 16px;
  border-radius: 6px;
  border: 1px solid #2b2b2e;
}

.insights-section h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: #efeff1;
}

.insights-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.insights-list li {
  padding-left: 20px;
  position: relative;
  color: #d1d4dc;
  font-size: 14px;
}

.insights-list li::before {
  content: '▸';
  position: absolute;
  left: 0;
  color: #2962FF;
}

.info-footer {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  padding-top: 16px;
  border-top: 1px solid #2b2b2e;
  font-size: 13px;
  color: #999;
}

.info-item strong {
  color: #d1d4dc;
}

.no-data {
  text-align: center;
  padding: 40px 20px;
  color: #999;
}
</style>

