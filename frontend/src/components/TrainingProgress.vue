<template>
  <div class="training-progress-container">
    <div
      v-for="training in activeTrainings"
      :key="training.training_id"
      class="training-progress-card"
      :class="{
        'status-running': training.status === 'running',
        'status-completed': training.status === 'completed',
        'status-failed': training.status === 'failed',
        'status-queued': training.status === 'queued'
      }"
    >
      <div class="training-header">
        <div class="training-title">
          <span class="training-icon">
            <span v-if="training.status === 'running'">⏳</span>
            <span v-else-if="training.status === 'completed'">✅</span>
            <span v-else-if="training.status === 'failed'">❌</span>
            <span v-else>⏸️</span>
          </span>
          <span class="training-bot-name">{{ formatBotName(training.bot_name) }}</span>
        </div>
        <button
          v-if="training.status === 'completed' || training.status === 'failed'"
          @click="removeTraining(training.training_id)"
          class="btn-close"
        >
          ✕
        </button>
      </div>
      
      <div class="training-info">
        <div class="training-symbol">{{ training.symbol }} / {{ training.timeframe }}</div>
        <div v-if="training.message" class="training-message">{{ training.message }}</div>
      </div>
      
      <div v-if="training.status === 'running' || training.status === 'queued'" class="training-progress-bar-container">
        <div class="training-progress-bar">
          <div
            class="training-progress-fill"
            :style="{ width: training.progress_percent + '%' }"
          ></div>
        </div>
        <div class="training-progress-text">
          <span v-if="training.total_batches > 0">
            Batch {{ training.batch }}/{{ training.total_batches }}
          </span>
          <span class="training-percent">{{ Math.round(training.progress_percent) }}%</span>
        </div>
      </div>
      
      <div v-if="training.status === 'completed'" class="training-success">
        Training completed successfully!
      </div>
      
      <div v-if="training.status === 'failed'" class="training-error">
        {{ training.message || 'Training failed' }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'

const activeTrainings = ref([])

const formatBotName = (name) => {
  return name.replace('_bot', '').toUpperCase()
}

const addOrUpdateTraining = (progressData) => {
  const existingIndex = activeTrainings.value.findIndex(
    t => t.training_id === progressData.training_id
  )
  
  if (existingIndex >= 0) {
    // Update existing training
    activeTrainings.value[existingIndex] = {
      ...activeTrainings.value[existingIndex],
      ...progressData
    }
  } else {
    // Add new training
    activeTrainings.value.push({
      training_id: progressData.training_id,
      bot_name: progressData.bot_name,
      symbol: progressData.symbol,
      timeframe: progressData.timeframe,
      batch: progressData.batch || 0,
      total_batches: progressData.total_batches || 1,
      progress_percent: progressData.progress_percent || 0,
      status: progressData.status || 'queued',
      message: progressData.message || ''
    })
  }
  
  // Auto-remove completed trainings after 5 seconds
  if (progressData.status === 'completed') {
    setTimeout(() => {
      removeTraining(progressData.training_id)
    }, 5000)
  }
  
  // Auto-remove failed trainings after 10 seconds
  if (progressData.status === 'failed') {
    setTimeout(() => {
      removeTraining(progressData.training_id)
    }, 10000)
  }
}

const removeTraining = (trainingId) => {
  const index = activeTrainings.value.findIndex(t => t.training_id === trainingId)
  if (index >= 0) {
    activeTrainings.value.splice(index, 1)
  }
}

// Expose methods for parent component
defineExpose({
  addOrUpdateTraining,
  removeTraining,
  activeTrainings
})

// Listen for training progress events from socket service
onMounted(() => {
  // Register handler for training progress events
  if (window.socketService) {
    window.socketService.on('training:progress', (message) => {
      addOrUpdateTraining(message)
    })
  }
})

onBeforeUnmount(() => {
  // Cleanup if needed
  if (window.socketService) {
    window.socketService.off('training:progress', addOrUpdateTraining)
  }
})
</script>

<style scoped>
.training-progress-container {
  position: fixed;
  top: 80px;
  right: 16px;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 400px;
  pointer-events: none;
}

.training-progress-card {
  background: #1a1a1d;
  border: 1px solid #2b2b2e;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
  pointer-events: auto;
  min-width: 320px;
}

.training-progress-card.status-running {
  border-left: 3px solid #2962FF;
}

.training-progress-card.status-completed {
  border-left: 3px solid #26a69a;
}

.training-progress-card.status-failed {
  border-left: 3px solid #ef5350;
}

.training-progress-card.status-queued {
  border-left: 3px solid #888;
}

.training-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.training-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.training-icon {
  font-size: 18px;
}

.training-bot-name {
  font-size: 14px;
  font-weight: 600;
  color: #efeff1;
}

.btn-close {
  background: transparent;
  border: none;
  color: #888;
  cursor: pointer;
  padding: 4px;
  font-size: 16px;
  line-height: 1;
  opacity: 0.6;
  transition: opacity 0.2s;
}

.btn-close:hover {
  opacity: 1;
  color: #ef5350;
}

.training-info {
  margin-bottom: 12px;
}

.training-symbol {
  font-size: 12px;
  color: #999;
  margin-bottom: 4px;
}

.training-message {
  font-size: 12px;
  color: #d1d4dc;
}

.training-progress-bar-container {
  margin-top: 8px;
}

.training-progress-bar {
  height: 6px;
  background: #2b2b2e;
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 6px;
}

.training-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #2962FF, #26a69a);
  transition: width 0.3s ease;
  border-radius: 3px;
}

.training-progress-text {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: #999;
}

.training-percent {
  font-weight: 600;
  color: #2962FF;
}

.training-success {
  color: #26a69a;
  font-size: 12px;
  font-weight: 500;
  margin-top: 8px;
}

.training-error {
  color: #ef5350;
  font-size: 12px;
  margin-top: 8px;
}
</style>

