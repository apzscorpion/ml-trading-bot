<template>
  <div class="accuracy-panel">
    <div class="accuracy-header">
      <h3>🎯 Prediction Accuracy</h3>
      <span v-if="accuracy" :class="['accuracy-badge', accuracyClass]">
        {{ accuracyStatus }}
      </span>
    </div>

    <div v-if="loading" class="loading">
      <div class="spinner-small"></div>
      <p>Evaluating predictions...</p>
    </div>

    <div v-else-if="accuracy" class="accuracy-content">
      <!-- Real-time Comparison -->
      <div class="comparison-section">
        <div class="comparison-item">
          <span class="label">Predicted Direction:</span>
          <span :class="['value', directionClass(accuracy.predictedDirection)]">
            {{ formatDirection(accuracy.predictedDirection) }}
          </span>
        </div>
        <div class="comparison-item">
          <span class="label">Actual Direction:</span>
          <span :class="['value', directionClass(accuracy.actualDirection)]">
            {{ formatDirection(accuracy.actualDirection) }}
          </span>
        </div>
        <div class="comparison-item">
          <span class="label">Direction Match:</span>
          <span :class="['value', accuracy.directionMatch ? 'correct' : 'incorrect']">
            {{ accuracy.directionMatch ? '✅ Correct' : '❌ Wrong' }}
          </span>
        </div>
      </div>

      <!-- Error Metrics -->
      <div class="metrics-section">
        <div class="metric-box">
          <div class="metric-label">Price Error</div>
          <div class="metric-value">₹{{ Math.abs(accuracy.priceError).toFixed(2) }}</div>
          <div class="metric-subtitle">{{ Math.abs(accuracy.errorPercent).toFixed(2) }}% off</div>
        </div>
        
        <div class="metric-box">
          <div class="metric-label">Confidence</div>
          <div class="metric-value">{{ (accuracy.confidence * 100).toFixed(1) }}%</div>
          <div class="metric-subtitle">{{ getConfidenceLevel(accuracy.confidence) }}</div>
        </div>
        
        <div class="metric-box">
          <div class="metric-label">Reliability</div>
          <div class="metric-value">{{ accuracy.reliability }}</div>
          <div class="metric-subtitle">{{ getReliabilityDesc(accuracy.reliability) }}</div>
        </div>
      </div>

      <!-- Warnings & Recommendations -->
      <div v-if="warnings.length > 0" class="warnings-section">
        <div class="warning-header">⚠️ Warnings</div>
        <div v-for="(warning, idx) in warnings" :key="idx" class="warning-item">
          {{ warning }}
        </div>
      </div>

      <div v-if="recommendations.length > 0" class="recommendations-section">
        <div class="recommendation-header">💡 Recommendations</div>
        <div v-for="(rec, idx) in recommendations" :key="idx" class="recommendation-item">
          {{ rec }}
        </div>
      </div>

      <!-- Historical Accuracy -->
      <div v-if="accuracy.historicalAccuracy" class="historical-section">
        <div class="historical-label">Historical Performance (Last 10 predictions)</div>
        <div class="historical-stats">
          <div class="stat">
            <span>Avg Accuracy:</span>
            <strong>{{ accuracy.historicalAccuracy.toFixed(1) }}%</strong>
          </div>
          <div class="stat">
            <span>Success Rate:</span>
            <strong>{{ accuracy.successRate?.toFixed(1) }}%</strong>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="no-data">
      <p>No prediction to evaluate</p>
      <small>Generate a prediction first</small>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  prediction: {
    type: Object,
    default: null
  },
  latestCandle: {
    type: Object,
    default: null
  },
  symbol: {
    type: String,
    required: true
  },
  timeframe: {
    type: String,
    required: true
  }
})

const loading = ref(false)
const accuracy = ref(null)
const warnings = ref([])
const recommendations = ref([])

// Compute accuracy status
const accuracyStatus = computed(() => {
  if (!accuracy.value) return 'N/A'
  const error = Math.abs(accuracy.value.errorPercent)
  if (error < 1) return 'Excellent'
  if (error < 3) return 'Good'
  if (error < 5) return 'Fair'
  return 'Poor'
})

const accuracyClass = computed(() => {
  const status = accuracyStatus.value
  if (status === 'Excellent') return 'excellent'
  if (status === 'Good') return 'good'
  if (status === 'Fair') return 'fair'
  return 'poor'
})

const directionClass = (direction) => {
  if (direction === 'up') return 'bullish'
  if (direction === 'down') return 'bearish'
  return 'neutral'
}

const formatDirection = (direction) => {
  if (direction === 'up') return '📈 Bullish'
  if (direction === 'down') return '📉 Bearish'
  return '➡️ Sideways'
}

const getConfidenceLevel = (confidence) => {
  if (confidence >= 0.8) return 'Very High'
  if (confidence >= 0.6) return 'High'
  if (confidence >= 0.4) return 'Moderate'
  return 'Low'
}

const getReliabilityDesc = (reliability) => {
  if (reliability === 'high') return 'Trust this'
  if (reliability === 'medium') return 'Use caution'
  return 'Don\'t rely on this'
}

// Evaluate prediction accuracy
const evaluatePrediction = () => {
  if (!props.prediction || !props.latestCandle) {
    accuracy.value = null
    return
  }

  loading.value = true
  warnings.value = []
  recommendations.value = []

  try {
    const predictedSeries = props.prediction.predicted_series || []
    if (predictedSeries.length === 0) {
      accuracy.value = null
      return
    }

    // Get first predicted price (what it predicted for near future)
    const firstPrediction = predictedSeries[0]
    const lastPrediction = predictedSeries[predictedSeries.length - 1]
    const currentPrice = props.latestCandle.close

    // Calculate prediction direction
    const predictedChange = lastPrediction.price - firstPrediction.price
    const predictedDirection = predictedChange > 0 ? 'up' : predictedChange < 0 ? 'down' : 'sideways'

    // Calculate actual direction (compare to first prediction)
    const actualChange = currentPrice - firstPrediction.price
    const actualDirection = actualChange > 0 ? 'up' : actualChange < 0 ? 'down' : 'sideways'

    // Direction match
    const directionMatch = predictedDirection === actualDirection

    // Price error
    const priceError = currentPrice - firstPrediction.price
    const errorPercent = (priceError / firstPrediction.price) * 100

    // Confidence from prediction
    const confidence = props.prediction.confidence || props.prediction.overall_confidence || 0.5

    // Determine reliability
    let reliability = 'low'
    const absError = Math.abs(errorPercent)
    
    if (absError < 2 && directionMatch && confidence > 0.6) {
      reliability = 'high'
    } else if (absError < 5 && confidence > 0.4) {
      reliability = 'medium'
    }

    // Generate warnings
    if (absError > 5) {
      warnings.value.push(`High prediction error: ${absError.toFixed(2)}% deviation from actual`)
    }
    if (!directionMatch) {
      warnings.value.push('Predicted direction is WRONG - prediction suggests opposite trend')
    }
    if (confidence < 0.5) {
      warnings.value.push('Low confidence prediction - results may be unreliable')
    }

    // Generate recommendations
    if (absError > 5 || !directionMatch) {
      recommendations.value.push('Consider retraining the model with recent data')
      recommendations.value.push('Try using different prediction models (Technical Analysis vs ML)')
    }
    if (confidence < 0.5) {
      recommendations.value.push('Generate a new prediction for better confidence')
    }
    if (reliability === 'low') {
      recommendations.value.push('Do NOT trade based on this prediction - accuracy is poor')
    }

    accuracy.value = {
      predictedDirection,
      actualDirection,
      directionMatch,
      priceError,
      errorPercent,
      confidence,
      reliability,
      predictedPrice: firstPrediction.price,
      actualPrice: currentPrice,
      historicalAccuracy: null, // Could fetch from API
      successRate: null
    }

  } catch (error) {
    console.error('Error evaluating prediction:', error)
    accuracy.value = null
  } finally {
    loading.value = false
  }
}

// Watch for changes
watch([() => props.prediction, () => props.latestCandle], evaluatePrediction, { immediate: true, deep: true })
</script>

<style scoped>
.accuracy-panel {
  background: #18181b;
  border-radius: 8px;
  border: 1px solid #2b2b2e;
  padding: 20px;
}

.accuracy-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.accuracy-header h3 {
  margin: 0;
  font-size: 18px;
  color: #efeff1;
}

.accuracy-badge {
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
}

.accuracy-badge.excellent {
  background: rgba(38, 166, 154, 0.2);
  color: #26a69a;
}

.accuracy-badge.good {
  background: rgba(102, 187, 106, 0.2);
  color: #66bb6a;
}

.accuracy-badge.fair {
  background: rgba(255, 167, 38, 0.2);
  color: #ffa726;
}

.accuracy-badge.poor {
  background: rgba(239, 83, 80, 0.2);
  color: #ef5350;
}

.loading {
  text-align: center;
  padding: 40px;
  color: #999;
}

.spinner-small {
  width: 32px;
  height: 32px;
  border: 3px solid #2b2b2e;
  border-top-color: #2962FF;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 12px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.accuracy-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.comparison-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  background: #1a1a1d;
  border-radius: 6px;
}

.comparison-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.comparison-item .label {
  font-size: 14px;
  color: #999;
}

.comparison-item .value {
  font-size: 14px;
  font-weight: 600;
}

.value.bullish {
  color: #26a69a;
}

.value.bearish {
  color: #ef5350;
}

.value.neutral {
  color: #999;
}

.value.correct {
  color: #26a69a;
}

.value.incorrect {
  color: #ef5350;
}

.metrics-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
}

.metric-box {
  background: #1a1a1d;
  padding: 16px;
  border-radius: 6px;
  text-align: center;
}

.metric-label {
  font-size: 12px;
  color: #999;
  margin-bottom: 8px;
}

.metric-value {
  font-size: 24px;
  font-weight: 700;
  color: #efeff1;
  margin-bottom: 4px;
}

.metric-subtitle {
  font-size: 11px;
  color: #666;
}

.warnings-section,
.recommendations-section {
  padding: 16px;
  border-radius: 6px;
}

.warnings-section {
  background: rgba(239, 83, 80, 0.1);
  border: 1px solid rgba(239, 83, 80, 0.3);
}

.recommendations-section {
  background: rgba(41, 98, 255, 0.1);
  border: 1px solid rgba(41, 98, 255, 0.3);
}

.warning-header,
.recommendation-header {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 12px;
}

.warning-header {
  color: #ef5350;
}

.recommendation-header {
  color: #2962FF;
}

.warning-item,
.recommendation-item {
  font-size: 13px;
  padding: 8px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.warning-item {
  color: #ff9999;
}

.recommendation-item {
  color: #99bbff;
}

.warning-item:last-child,
.recommendation-item:last-child {
  border-bottom: none;
}

.historical-section {
  padding: 16px;
  background: #1a1a1d;
  border-radius: 6px;
}

.historical-label {
  font-size: 13px;
  color: #999;
  margin-bottom: 12px;
}

.historical-stats {
  display: flex;
  gap: 24px;
}

.stat {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat span {
  font-size: 12px;
  color: #999;
}

.stat strong {
  font-size: 18px;
  color: #efeff1;
}

.no-data {
  text-align: center;
  padding: 40px;
  color: #999;
}

.no-data p {
  margin: 0 0 8px 0;
  font-size: 16px;
}

.no-data small {
  font-size: 13px;
  color: #666;
}
</style>

