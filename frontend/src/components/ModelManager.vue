<template>
  <div class="model-manager">
    <div class="model-manager-header">
      <h3>🤖 Model Management</h3>
      <div class="training-controls">
        <button
          v-if="!trainingStatus.is_running && !trainingStatus.is_paused"
          @click="startAutoTraining"
          class="btn-training btn-start"
          :disabled="isLoading"
        >
          <span v-if="isLoading">⏳ Starting...</span>
          <span v-else>▶️ Start Auto Training</span>
        </button>
        <button
          v-if="trainingStatus.is_running && !trainingStatus.is_paused"
          @click="stopTraining"
          class="btn-training btn-stop-running"
        >
          ⏹️ Stop Training
        </button>
        <button
          v-if="trainingStatus.is_running && !trainingStatus.is_paused"
          @click="pauseTraining"
          class="btn-training btn-pause"
        >
          ⏸️ Pause
        </button>
        <button
          v-if="trainingStatus.is_paused"
          @click="resumeTraining"
          class="btn-training btn-resume"
        >
          ▶️ Resume
        </button>
        <button
          v-if="trainingStatus.is_paused"
          @click="stopTraining"
          class="btn-training btn-stop"
        >
          ⏹️ Stop
        </button>
        <button
          v-if="trainingStatus.is_running"
          @click="forceStopTraining"
          class="btn-training btn-force-stop"
        >
          🛑 Force Stop
        </button>
      </div>
    </div>

    <!-- Training Status -->
    <div
      v-if="trainingStatus.is_running || trainingStatus.is_paused"
      class="training-status-card"
    >
      <div class="status-indicator" :class="statusClass">
        <span class="status-dot"></span>
        <span class="status-text">{{ statusText }}</span>
      </div>
      <div v-if="trainingStatus.current_training" class="current-training">
        <div>
          Training:
          <strong>{{
            formatBotName(trainingStatus.current_training.bot_name)
          }}</strong>
        </div>
        <div>
          {{ trainingStatus.current_training.symbol }} /
          {{ trainingStatus.current_training.timeframe }}
        </div>
        <div class="started-at">
          Started: {{ formatTime(trainingStatus.current_training.started_at) }}
        </div>
      </div>
      <div class="queue-info">
        <span>Queue: {{ trainingStatus.queue_length }} tasks</span>
        <span>Completed: {{ trainingStatus.completed_count }}</span>
        <span :class="{ 'error-count': trainingStatus.failed_count > 0 }">
          Failed: {{ trainingStatus.failed_count }}
        </span>
      </div>
    </div>

    <!-- Error Notification -->
    <div v-if="lastError" class="error-notification">
      <div class="error-header">
        <span class="error-icon">⚠️</span>
        <span class="error-title">Training Error</span>
        <button @click="lastError = null" class="error-close">✕</button>
      </div>
      <div class="error-message">{{ lastError }}</div>
    </div>

    <!-- Success Notification -->
    <div v-if="lastSuccess" class="success-notification">
      <div class="success-header">
        <span class="success-icon">✅</span>
        <span class="success-title">{{ lastSuccess }}</span>
        <button @click="lastSuccess = null" class="success-close">✕</button>
      </div>
    </div>

    <!-- Training Configuration -->
    <div
      v-if="!trainingStatus.is_running && !trainingStatus.is_paused"
      class="training-config"
    >
      <h4>📋 Training Configuration</h4>

      <div class="config-section">
        <label class="config-label">📊 Select Timeframes:</label>
        <div class="timeframe-selector">
          <label
            v-for="tf in availableTimeframes"
            :key="tf"
            class="timeframe-checkbox"
          >
            <input
              type="checkbox"
              :value="tf"
              v-model="selectedTimeframes"
              @change="saveTimeframeSelection"
            />
            <span>{{ tf }}</span>
          </label>
        </div>
        <small class="config-hint">
          Selected: {{ selectedTimeframes.length }} timeframe(s) • Stocks:
          {{ getWatchlistSymbols().length }} (watchlist + current)
        </small>
      </div>

      <div class="config-section">
        <label class="config-label">📈 Stocks to Train:</label>
        <div class="stocks-list">
          <span
            v-for="symbol in getWatchlistSymbols()"
            :key="symbol"
            class="stock-badge"
          >
            {{ symbol.replace(".NS", "").replace(".BO", "") }}
          </span>
        </div>
        <small class="config-hint">
          Total tasks: {{ getWatchlistSymbols().length }} stocks ×
          {{ selectedTimeframes.length }} timeframes × 4 bots =
          <strong>{{
            getWatchlistSymbols().length * selectedTimeframes.length * 4
          }}</strong>
          tasks
        </small>
      </div>
    </div>

    <!-- Models List -->
    <div class="models-list">
      <div
        v-for="model in modelsList"
        :key="model.id"
        class="model-card"
        :class="getModelStatusClass(model)"
      >
        <div class="model-header">
          <div class="model-info">
            <h4 class="model-name">{{ formatBotName(model.bot_name) }}</h4>
            <div class="model-meta">
              <span class="symbol">{{ model.symbol }}</span>
              <span class="timeframe">{{ model.timeframe }}</span>
            </div>
          </div>
          <div class="model-health-badges">
            <div class="health-badge" :class="getHealthBadgeClass(model)">
              {{ getHealthStatus(model) }}
            </div>
            <div class="model-status-badge" :class="getStatusBadgeClass(model)">
              {{ getStatusBadgeText(model) }}
            </div>
          </div>
        </div>

        <div class="model-details">
          <div class="detail-row">
            <span class="label">Trained:</span>
            <span class="value">{{ formatDate(model.trained_at) }}</span>
            <span class="age" :class="getAgeClass(model)"
              >({{ getAge(model) }})</span
            >
          </div>
          
          <div class="detail-row">
            <span class="label">Health:</span>
            <span class="value">{{ getHealthDescription(model) }}</span>
          </div>

          <div v-if="model.data_points_used" class="detail-row">
            <span class="label">Data Points:</span>
            <span class="value">{{
              model.data_points_used.toLocaleString()
            }}</span>
          </div>

          <div v-if="model.test_rmse" class="detail-row">
            <span class="label">Test RMSE:</span>
            <span class="value">₹{{ model.test_rmse.toFixed(2) }}</span>
          </div>

          <div v-if="model.test_mae" class="detail-row">
            <span class="label">Test MAE:</span>
            <span class="value">₹{{ model.test_mae.toFixed(2) }}</span>
          </div>

          <div v-if="model.model_size_mb" class="detail-row">
            <span class="label">Size:</span>
            <span class="value">{{ model.model_size_mb.toFixed(2) }} MB</span>
          </div>

          <div v-if="model.error_message" class="error-message">
            <span class="error-icon">⚠️</span>
            <span>{{ model.error_message }}</span>
          </div>

          <div v-if="model.training_period" class="detail-row">
            <span class="label">Training Period:</span>
            <span class="value">{{ model.training_period }}</span>
          </div>
        </div>

        <div class="model-actions">
          <button
            @click="clearModel(model)"
            class="btn-clear"
            :disabled="isClearing || isRetraining(model)"
          >
            🗑️ Clear Model
          </button>
          <button
            @click="retrainModel(model)"
            class="btn-retrain"
            :disabled="isRetraining(model) || isClearing"
          >
            <span v-if="isRetraining(model)">
              <span class="spinner"></span> Training...
            </span>
            <span v-else>🔄 Retrain</span>
          </button>
        </div>
      </div>

      <div v-if="modelsList.length === 0" class="no-models">
        <p>No trained models found</p>
        <small>Start auto-training to train models for your stocks</small>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import { api } from "../services/api";

const modelsList = ref([]);
const trainingStatus = ref({
  is_running: false,
  is_paused: false,
  current_training: null,
  queue_length: 0,
  completed_count: 0,
  failed_count: 0,
});

const isLoading = ref(false);
const isClearing = ref(false);
const isTraining = ref(false);
const retrainingModelId = ref(null); // Track which model is currently being retrained
const lastError = ref(null);
const lastSuccess = ref(null);
let statusInterval = null;

// Available timeframes for training
const availableTimeframes = [
  "1m",
  "5m",
  "15m",
  "1h",
  "4h",
  "1d",
  "5d",
  "1wk",
  "1mo",
  "3mo",
];

// Selected timeframes (persisted to localStorage)
const selectedTimeframes = ref([]);

// Load selected timeframes from localStorage
const loadTimeframeSelection = () => {
  const saved = localStorage.getItem("autoTrainingTimeframes");
  if (saved) {
    try {
      selectedTimeframes.value = JSON.parse(saved);
    } catch (e) {
      console.error("Failed to load timeframe selection:", e);
      // Default selection
      selectedTimeframes.value = ["5m", "15m", "1h", "1d"];
    }
  } else {
    // Default selection
    selectedTimeframes.value = ["5m", "15m", "1h", "1d"];
    saveTimeframeSelection();
  }
};

// Save selected timeframes to localStorage
const saveTimeframeSelection = () => {
  localStorage.setItem(
    "autoTrainingTimeframes",
    JSON.stringify(selectedTimeframes.value)
  );
};

// Get stocks from watchlist + current selected stock
const getWatchlistSymbols = () => {
  // Get watchlist from localStorage
  const watchlistStr = localStorage.getItem("watchlist");
  const symbols = new Set();

  // Add current selected symbol (from parent component or localStorage)
  const currentSymbol = localStorage.getItem("selectedSymbol") || "TCS.NS";
  if (currentSymbol) {
    symbols.add(currentSymbol);
  }

  // Add watchlist stocks
  if (watchlistStr) {
    try {
      const watchlist = JSON.parse(watchlistStr);
      watchlist.forEach((stock) => {
        if (stock.symbol) {
          symbols.add(stock.symbol);
        }
      });
    } catch (e) {
      console.error("Failed to parse watchlist:", e);
    }
  }

  return Array.from(symbols).sort();
};
let previousFailedCount = 0;
let isLoadingModels = false;
let isLoadingStatus = false;

const loadModels = async () => {
  // Prevent concurrent requests
  if (isLoadingModels) {
    return;
  }
  isLoadingModels = true;
  try {
    const response = await api.getModelsReport();
    if (response && response.models) {
      modelsList.value = response.models;
    }
  } catch (error) {
    console.error("Error loading models:", error);
  } finally {
    isLoadingModels = false;
  }
};

const loadTrainingStatus = async () => {
  // Prevent concurrent requests
  if (isLoadingStatus) {
    return;
  }
  isLoadingStatus = true;
  try {
    const status = await api.getTrainingStatus();
    if (status) {
      // Check if new failures occurred
      if (status.failed_count > previousFailedCount) {
        const newFailures = status.failed_count - previousFailedCount;
        console.error(`❌ ${newFailures} new training failure(s) detected!`);
        showError(
          `Training failed for ${newFailures} model(s). Check notifications for details.`,
          {
            failed_count: status.failed_count,
            previous_failed_count: previousFailedCount,
          },
          "GET /api/training/status"
        );
      }
      previousFailedCount = status.failed_count;

      const wasRunning = trainingStatus.value.is_running;
      trainingStatus.value = status;

      // Log status changes
      if (status.is_running && status.current_training) {
        console.log(
          `🔄 Training: ${formatBotName(
            status.current_training.bot_name
          )} for ${status.current_training.symbol}/${
            status.current_training.timeframe
          }`
        );
      }

      // Adjust polling based on training state
      adjustPollingInterval(status.is_running, wasRunning);
    }
  } catch (error) {
    console.error("❌ Error loading training status:", error);
    showError(
      "Failed to load training status: " + (error.message || "Unknown error"),
      {
        error: error.message,
        stack: error.stack,
        response: error.response?.data,
      },
      "GET /api/training/status"
    );
  } finally {
    isLoadingStatus = false;
  }
};

const adjustPollingInterval = (isRunning, wasRunning) => {
  if (isRunning) {
    // Always restart polling when training is running
    if (statusInterval) {
      clearInterval(statusInterval);
      statusInterval = null;
    }
    console.log("🔄 Training active - polling every 3 seconds");
    statusInterval = setInterval(() => {
      loadTrainingStatus();
      loadModels();
    }, 3000);
  } else if (wasRunning) {
    // Training just stopped - stop polling
    if (statusInterval) {
      clearInterval(statusInterval);
      statusInterval = null;
      console.log("⏸️ Training idle - stopping polling");
    }
  }
};

const showError = (message, details = null, apiCall = null) => {
  console.error("🚨 Training Error:", message);
  if (window.notificationCenter) {
    window.notificationCenter.addError(
      message,
      details,
      apiCall || "Training Error"
    );
  } else {
    // Fallback to local notification if notification center not available
    lastError.value = message;
    setTimeout(() => {
      lastError.value = null;
    }, 10000);
  }
};

const showSuccess = (message, details = null, apiCall = null) => {
  console.log("✅ Success:", message);
  if (window.notificationCenter) {
    window.notificationCenter.addSuccess(
      message,
      details,
      apiCall || "Training Success"
    );
  } else {
    // Fallback to local notification if notification center not available
    lastSuccess.value = message;
    setTimeout(() => {
      lastSuccess.value = null;
    }, 5000);
  }
};

const startAutoTraining = async () => {
  console.log("🚀 Start Auto Training clicked");
  isLoading.value = true;
  lastError.value = null;

  try {
    // Validate selections
    if (selectedTimeframes.value.length === 0) {
      showError(
        "Please select at least one timeframe for training",
        null,
        "Training Configuration"
      );
      isLoading.value = false;
      return;
    }

    const symbols = getWatchlistSymbols();
    if (symbols.length === 0) {
      showError(
        "No stocks found. Please add stocks to watchlist or select a stock.",
        null,
        "Training Configuration"
      );
      isLoading.value = false;
      return;
    }

    const timeframes = selectedTimeframes.value;
    const bots = ["lstm_bot", "transformer_bot", "ml_bot", "ensemble_bot"];

    const totalTasks = symbols.length * timeframes.length * bots.length;

    console.log("📤 Sending training request:", { symbols, timeframes, bots });
    console.log(`📊 Total tasks: ${totalTasks}`);
    console.log(`📈 Stocks: ${symbols.join(", ")}`);
    console.log(`⏰ Timeframes: ${timeframes.join(", ")}`);

    const result = await api.startAutoTraining(symbols, timeframes, bots);
    console.log("✅ Training started successfully:", result);
    console.log(`📋 Queue size: ${result.queue_size || 0} tasks`);

    // Show success notification
    showSuccess(
      `Training started! ${result.queue_size || 0} tasks queued (${
        symbols.length
      } stocks × ${timeframes.length} timeframes × 4 bots).`,
      result,
      "POST /api/training/start-auto"
    );

    // Reload status and adjust polling (will switch to frequent polling)
    await loadTrainingStatus();

    // Force start polling if training is running
    if (trainingStatus.value.is_running) {
      if (statusInterval) {
        clearInterval(statusInterval);
      }
      console.log("🔄 Training active - starting polling every 3 seconds");
      statusInterval = setInterval(() => {
        loadTrainingStatus();
        loadModels();
      }, 3000);
    }
  } catch (error) {
    console.error("❌ Error starting auto training:", error);
    console.error("Error details:", {
      message: error.message,
      response: error.response?.data,
      status: error.response?.status,
    });

    const errorMsg =
      error.response?.data?.detail || error.message || "Unknown error";
    showError(
      `Failed to start auto training: ${errorMsg}`,
      {
        error: error.message,
        response: error.response?.data,
        stack: error.stack,
      },
      "POST /api/training/start-auto"
    );
  } finally {
    isLoading.value = false;
  }
};

const pauseTraining = async () => {
  try {
    console.log("⏸️ Pausing training...");
    const result = await api.pauseTraining();
    console.log("✅ Training paused");
    showSuccess("Training paused", result, "POST /api/training/pause");
    // Status will still show as running (just paused), so polling continues
    await loadTrainingStatus();
  } catch (error) {
    console.error("❌ Error pausing training:", error);
    showError(
      "Failed to pause training: " + (error.message || "Unknown error"),
      { error: error.message, response: error.response?.data },
      "POST /api/training/pause"
    );
  }
};

const resumeTraining = async () => {
  try {
    console.log("▶️ Resuming training...");
    const result = await api.resumeTraining();
    console.log("✅ Training resumed");
    showSuccess("Training resumed", result, "POST /api/training/resume");
    await loadTrainingStatus();
  } catch (error) {
    console.error("❌ Error resuming training:", error);
    showError(
      "Failed to resume training: " + (error.message || "Unknown error"),
      { error: error.message, response: error.response?.data },
      "POST /api/training/resume"
    );
  }
};

const stopTraining = async () => {
  if (!confirm("Stop training? Current task will finish.")) return;
  try {
    console.log("⏹️ Stopping training...");
    const result = await api.stopTraining();
    console.log("✅ Training stopped");
    showSuccess("Training stopped", result, "POST /api/training/stop");
    // This will switch polling to idle mode (less frequent)
    await loadTrainingStatus();
  } catch (error) {
    console.error("❌ Error stopping training:", error);
    showError(
      "Failed to stop training: " + (error.message || "Unknown error"),
      { error: error.message, response: error.response?.data },
      "POST /api/training/stop"
    );
  }
};

const forceStopTraining = async () => {
  if (!confirm("Force stop training? This may interrupt current task.")) return;
  try {
    console.log("🛑 Force stopping training...");
    const result = await api.forceStopTraining();
    console.log("✅ Training force stopped");
    showSuccess(
      "Training force stopped",
      result,
      "POST /api/training/force-stop"
    );
    // This will switch polling to idle mode (less frequent)
    await loadTrainingStatus();
  } catch (error) {
    console.error("❌ Error force stopping training:", error);
    showError(
      "Failed to force stop training: " + (error.message || "Unknown error"),
      { error: error.message, response: error.response?.data },
      "POST /api/training/force-stop"
    );
  }
};

const clearModel = async (model) => {
  if (
    !confirm(
      `Clear model ${model.bot_name} for ${model.symbol}/${model.timeframe}?`
    )
  )
    return;

  isClearing.value = true;
  try {
    await api.clearModel(model.symbol, model.timeframe, model.bot_name);
    await loadModels();
  } catch (error) {
    console.error("Error clearing model:", error);
    if (window.notificationCenter) {
      window.notificationCenter.addError(
        `Failed to clear model: ${error.message}`,
        {
          error: error.message,
          response: error.response?.data,
          symbol: model.symbol,
          timeframe: model.timeframe,
          botName: model.bot_name,
        },
        `DELETE /api/models/clear/${model.symbol}/${model.timeframe}/${model.bot_name}`
      );
    } else {
      alert("Failed to clear model: " + error.message);
    }
  } finally {
    isClearing.value = false;
  }
};

const isRetraining = (model) => {
  return retrainingModelId.value === model.id;
};

const retrainModel = async (model) => {
  if (isRetraining(model)) return; // Prevent double-click

  retrainingModelId.value = model.id;

  try {
    console.log(
      `🔄 Retraining ${formatBotName(model.bot_name)} for ${model.symbol}/${
        model.timeframe
      }...`
    );

    // Show notification that training started
    if (window.notificationCenter) {
      window.notificationCenter.addInfo(
        `Training ${formatBotName(model.bot_name)}...`,
        {
          symbol: model.symbol,
          timeframe: model.timeframe,
          botName: model.bot_name,
        },
        `POST /api/prediction/train (${model.bot_name})`
      );
    }

    const result = await api.trainBot(
      model.symbol,
      model.timeframe,
      model.bot_name,
      30
    );

    console.log("✅ Retraining completed:", result);

    // Show success notification
    if (window.notificationCenter) {
      window.notificationCenter.addSuccess(
        `${formatBotName(model.bot_name)} retrained successfully!`,
        {
          symbol: model.symbol,
          timeframe: model.timeframe,
          botName: model.bot_name,
          result: result,
          modelId: result.model_id,
          duration: result.duration,
        },
        `POST /api/prediction/train (${model.bot_name})`
      );
    } else {
      showSuccess(`Model retrained successfully!`);
    }

    // Refresh model list to show updated timestamp
    await loadModels();
  } catch (error) {
    console.error("❌ Error retraining model:", error);
    const errorMsg =
      error.response?.data?.detail || error.message || "Unknown error";

    if (window.notificationCenter) {
      window.notificationCenter.addError(
        `Failed to retrain ${formatBotName(model.bot_name)}: ${errorMsg}`,
        {
          error: error.message,
          response: error.response?.data,
          symbol: model.symbol,
          timeframe: model.timeframe,
          botName: model.bot_name,
        },
        `POST /api/prediction/train (${model.bot_name})`
      );
    } else {
      showError(`Failed to retrain model: ${errorMsg}`);
    }
  } finally {
    retrainingModelId.value = null;
  }
};

const formatBotName = (name) => {
  const names = {
    lstm_bot: "LSTM",
    transformer_bot: "Transformer",
    ml_bot: "ML Models",
    ensemble_bot: "Ensemble",
    rsi_bot: "RSI",
    macd_bot: "MACD",
    ma_bot: "Moving Average",
  };
  return names[name] || name;
};

const formatDate = (dateStr) => {
  if (!dateStr) return "N/A";
  const date = new Date(dateStr);
  return date.toLocaleString("en-IN", {
    timeZone: "Asia/Kolkata",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

const formatTime = (dateStr) => {
  if (!dateStr) return "N/A";
  const date = new Date(dateStr);
  return date.toLocaleTimeString("en-IN", {
    timeZone: "Asia/Kolkata",
    hour: "2-digit",
    minute: "2-digit",
  });
};

const getAge = (model) => {
  if (!model.trained_at) return "N/A";
  const ageHours =
    (Date.now() - new Date(model.trained_at).getTime()) / (1000 * 60 * 60);
  if (ageHours < 1) return `${Math.round(ageHours * 60)}m ago`;
  if (ageHours < 24) return `${Math.round(ageHours)}h ago`;
  return `${Math.round(ageHours / 24)}d ago`;
};

const getAgeClass = (model) => {
  if (!model.trained_at) return "";
  const ageHours =
    (Date.now() - new Date(model.trained_at).getTime()) / (1000 * 60 * 60);
  if (ageHours > 24) return "stale";
  if (ageHours > 12) return "old";
  return "fresh";
};

const getHealthStatus = (model) => {
  // Green: Healthy (trained <24h ago, no errors, valid metrics)
  // Yellow: Stale (trained >48h ago)
  // Red: Failed (last training crashed or validation failed)
  
  if (!model || !model.trained_at) return 'Unknown';
  
  const ageHours = (Date.now() - new Date(model.trained_at).getTime()) / (1000 * 60 * 60);
  
  if (model.status === 'failed') {
    return 'Failed';
  }
  
  // Check if model was just trained (within last 5 minutes) - consider it fresh
  if (ageHours < 0.083) { // 5 minutes
    return 'Healthy';
  }
  
  if (ageHours > 48) {
    return 'Stale';
  }
  
  if (ageHours < 24 && (model.status === 'active' || model.status === 'completed') && model.test_rmse !== undefined) {
    return 'Healthy';
  }
  
  return 'OK';
};

const getHealthBadgeClass = (model) => {
  const status = getHealthStatus(model);
  if (status === 'Healthy') return 'health-green';
  if (status === 'Stale') return 'health-yellow';
  if (status === 'Failed') return 'health-red';
  return 'health-gray';
};

const getHealthDescription = (model) => {
  if (!model || !model.trained_at) return 'No training data';
  
  const ageHours = (Date.now() - new Date(model.trained_at).getTime()) / (1000 * 60 * 60);
  
  if (model.status === 'failed') {
    return 'Last training failed - retrain recommended';
  }
  
  // Check if model was just trained (within last 5 minutes)
  if (ageHours < 0.083) { // 5 minutes
    const rmse = model.test_rmse != null && typeof model.test_rmse === 'number' 
      ? model.test_rmse.toFixed(2) 
      : 'N/A';
    return `Just trained, RMSE: ₹${rmse}`;
  }
  
  if (ageHours > 48) {
    return 'Model is stale (>48h) - retrain recommended';
  }
  
  if (ageHours < 24 && (model.status === 'active' || model.status === 'completed')) {
    if (model.test_rmse != null && typeof model.test_rmse === 'number') {
      return `Fresh model, RMSE: ₹${model.test_rmse.toFixed(2)}`;
    }
    return 'Fresh model';
  }
  
  return 'Model OK';
};

const getModelStatusClass = (model) => {
  if (model.status === "failed") return "status-failed";
  if (model.status === "archived") return "status-archived";
  const ageHours = model.trained_at
    ? (Date.now() - new Date(model.trained_at).getTime()) / (1000 * 60 * 60)
    : 999;
  if (ageHours > 24) return "status-stale";
  return "status-active";
};

const getStatusBadgeClass = (model) => {
  if (model.status === "failed") return "badge-failed";
  if (model.status === "archived") return "badge-archived";
  const ageHours = model.trained_at
    ? (Date.now() - new Date(model.trained_at).getTime()) / (1000 * 60 * 60)
    : 999;
  if (ageHours > 24) return "badge-stale";
  return "badge-active";
};

const getStatusBadgeText = (model) => {
  if (model.status === "failed") return "❌ Failed";
  if (model.status === "archived") return "🗄️ Archived";
  const ageHours = model.trained_at
    ? (Date.now() - new Date(model.trained_at).getTime()) / (1000 * 60 * 60)
    : 999;
  if (ageHours > 24) return "⚠️ Stale";
  return "✅ Active";
};

const statusClass = computed(() => {
  if (trainingStatus.value.is_paused) return "status-paused";
  if (trainingStatus.value.is_running) return "status-running";
  return "status-idle";
});

const statusText = computed(() => {
  if (trainingStatus.value.is_paused) return "Paused";
  if (trainingStatus.value.is_running) return "Running";
  return "Idle";
});

onMounted(async () => {
  // Load timeframe selection from localStorage
  loadTimeframeSelection();

  // Load initial data once
  await loadModels();
  await loadTrainingStatus();

  // Only start polling if training is actively running
  // If idle, don't poll - data is already loaded and won't change
  const initialStatus = trainingStatus.value;
  if (initialStatus && initialStatus.is_running) {
    // Training is active - poll frequently to get updates
    console.log("🔄 Training active - starting polling every 3 seconds");
    statusInterval = setInterval(() => {
      loadTrainingStatus();
      loadModels();
    }, 3000); // Every 3 seconds when training
  } else {
    // Training is idle - don't poll, data is already loaded
    console.log("✅ Training idle - data loaded, no polling needed");
  }
});

onBeforeUnmount(() => {
  if (statusInterval) {
    clearInterval(statusInterval);
  }
});

// Expose methods for parent component to call
defineExpose({
  loadModels,
  loadTrainingStatus,
});
</script>

<style scoped>
.model-manager {
  background: #1a1a1d;
  border-radius: 8px;
  padding: 20px;
  margin-top: 20px;
}

.model-manager-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.model-manager-header h3 {
  margin: 0;
  color: #efeff1;
}

.training-controls {
  display: flex;
  gap: 8px;
}

.btn-training {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-start {
  background: #26a69a;
  color: white;
}

.btn-start:hover:not(:disabled) {
  background: #2bb5a8;
}

.btn-pause {
  background: #ffa726;
  color: white;
}

.btn-pause:hover {
  background: #ffb74d;
}

.btn-resume {
  background: #42a5f5;
  color: white;
}

.btn-resume:hover {
  background: #64b5f6;
}

.btn-stop {
  background: #ef5350;
  color: white;
}

.btn-stop:hover {
  background: #e57373;
}

.btn-stop-running {
  background: #ef5350;
  color: white;
  font-weight: 700;
  font-size: 14px;
  padding: 10px 20px;
}

.btn-stop-running:hover {
  background: #e57373;
}

.btn-force-stop {
  background: #d32f2f;
  color: white;
}

.btn-force-stop:hover {
  background: #f44336;
}

.training-status-card {
  background: #2b2b2e;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 20px;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.status-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

.status-running .status-dot {
  background: #26a69a;
}

.status-paused .status-dot {
  background: #ffa726;
}

.status-idle .status-dot {
  background: #666;
  animation: none;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.status-text {
  font-weight: 600;
  color: #efeff1;
}

.current-training {
  margin-bottom: 12px;
  padding: 12px;
  background: #1a1a1d;
  border-radius: 6px;
  color: #efeff1;
  font-size: 14px;
}

.current-training div {
  margin-bottom: 4px;
}

.started-at {
  font-size: 12px;
  color: #999;
}

.queue-info {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: #999;
}

.queue-info .error-count {
  color: #ef5350;
  font-weight: 600;
}

.training-config {
  background: #2b2b2e;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
  border: 1px solid #3a3a3e;
}

.training-config h4 {
  margin: 0 0 16px 0;
  color: #efeff1;
  font-size: 16px;
  font-weight: 600;
}

.config-section {
  margin-bottom: 20px;
}

.config-section:last-child {
  margin-bottom: 0;
}

.config-label {
  display: block;
  margin-bottom: 12px;
  color: #d1d4dc;
  font-size: 14px;
  font-weight: 500;
}

.timeframe-selector {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 8px;
}

.timeframe-checkbox {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: #1a1a1d;
  border: 1px solid #3a3a3e;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  user-select: none;
}

.timeframe-checkbox:hover {
  background: #2b2b2e;
  border-color: #4a4a4e;
}

.timeframe-checkbox input[type="checkbox"] {
  margin: 0;
  cursor: pointer;
  width: 16px;
  height: 16px;
  accent-color: #26a69a;
}

.timeframe-checkbox input[type="checkbox"]:checked + span {
  color: #26a69a;
  font-weight: 600;
}

.timeframe-checkbox span {
  color: #d1d4dc;
  font-size: 13px;
  font-weight: 500;
}

.config-hint {
  display: block;
  color: #999;
  font-size: 12px;
  margin-top: 8px;
}

.config-hint strong {
  color: #26a69a;
  font-weight: 600;
}

.stocks-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}

.stock-badge {
  padding: 6px 12px;
  background: #1a1a1d;
  border: 1px solid #3a3a3e;
  border-radius: 6px;
  color: #d1d4dc;
  font-size: 12px;
  font-weight: 500;
  font-family: "SF Mono", "Monaco", "Cascadia Code", monospace;
}

.models-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 16px;
}

.model-card {
  background: #2b2b2e;
  border-radius: 8px;
  padding: 16px;
  border: 2px solid transparent;
  transition: all 0.2s;
}

.model-card.status-active {
  border-color: #26a69a;
}

.model-card.status-stale {
  border-color: #ffa726;
}

.model-card.status-failed {
  border-color: #ef5350;
}

.model-card.status-archived {
  border-color: #666;
  opacity: 0.6;
}

.model-header {
  display: flex;
  justify-content: space-between;
  align-items: start;
  margin-bottom: 12px;
}

.model-info {
  flex: 1;
}

.model-health-badges {
  display: flex;
  gap: 8px;
  flex-direction: column;
  align-items: flex-end;
}

.health-badge {
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.health-badge.health-green {
  background: rgba(38, 166, 154, 0.2);
  color: #26a69a;
  border: 1px solid rgba(38, 166, 154, 0.4);
}

.health-badge.health-yellow {
  background: rgba(255, 167, 38, 0.2);
  color: #ffa726;
  border: 1px solid rgba(255, 167, 38, 0.4);
}

.health-badge.health-red {
  background: rgba(239, 83, 80, 0.2);
  color: #ef5350;
  border: 1px solid rgba(239, 83, 80, 0.4);
}

.health-badge.health-gray {
  background: rgba(149, 165, 166, 0.2);
  color: #95a5a6;
  border: 1px solid rgba(149, 165, 166, 0.3);
}

.model-name {
  margin: 0 0 8px 0;
  color: #efeff1;
  font-size: 16px;
}

.model-meta {
  display: flex;
  gap: 8px;
}

.symbol,
.timeframe {
  padding: 2px 8px;
  background: #1a1a1d;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}

.symbol {
  color: #2962ff;
}

.timeframe {
  color: #999;
}

.model-status-badge {
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}

.badge-active {
  background: rgba(38, 166, 154, 0.2);
  color: #26a69a;
}

.badge-stale {
  background: rgba(255, 167, 38, 0.2);
  color: #ffa726;
}

.badge-failed {
  background: rgba(239, 83, 80, 0.2);
  color: #ef5350;
}

.badge-archived {
  background: rgba(102, 102, 102, 0.2);
  color: #999;
}

.model-details {
  margin-bottom: 12px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 6px;
  font-size: 13px;
}

.label {
  color: #999;
}

.value {
  color: #efeff1;
  font-weight: 600;
}

.age {
  font-size: 11px;
}

.age.fresh {
  color: #26a69a;
}

.age.old {
  color: #ffa726;
}

.age.stale {
  color: #ef5350;
}

.error-message {
  margin-top: 8px;
  padding: 8px;
  background: rgba(239, 83, 80, 0.1);
  border-left: 3px solid #ef5350;
  border-radius: 4px;
  font-size: 12px;
  color: #ef5350;
  display: flex;
  align-items: center;
  gap: 8px;
}

.model-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #1a1a1d;
}

.btn-clear,
.btn-retrain {
  flex: 1;
  padding: 8px 12px;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-clear {
  background: rgba(239, 83, 80, 0.2);
  color: #ef5350;
}

.btn-clear:hover:not(:disabled) {
  background: rgba(239, 83, 80, 0.3);
}

.btn-retrain {
  background: rgba(41, 98, 255, 0.2);
  color: #2962ff;
}

.btn-retrain:hover:not(:disabled) {
  background: rgba(41, 98, 255, 0.3);
}

.btn-retrain:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.spinner {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 2px solid rgba(41, 98, 255, 0.3);
  border-radius: 50%;
  border-top-color: #2962ff;
  animation: spin 0.8s linear infinite;
  margin-right: 6px;
  vertical-align: middle;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.no-models {
  grid-column: 1 / -1;
  text-align: center;
  padding: 40px;
  color: #999;
}

.no-models p {
  margin: 0 0 8px 0;
  font-size: 16px;
  color: #efeff1;
}

/* Notification Styles */
.error-notification {
  margin-bottom: 16px;
  padding: 16px;
  background: rgba(239, 83, 80, 0.15);
  border: 2px solid #ef5350;
  border-radius: 8px;
  animation: slideIn 0.3s ease-out;
}

.error-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.error-icon {
  font-size: 20px;
}

.error-title {
  flex: 1;
  font-weight: 700;
  color: #ef5350;
  font-size: 14px;
}

.error-close {
  background: transparent;
  border: none;
  color: #ef5350;
  font-size: 18px;
  cursor: pointer;
  padding: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: background 0.2s;
}

.error-close:hover {
  background: rgba(239, 83, 80, 0.2);
}

.error-message {
  color: #efeff1;
  font-size: 13px;
  line-height: 1.5;
  padding-left: 32px;
}

.success-notification {
  margin-bottom: 16px;
  padding: 12px 16px;
  background: rgba(38, 166, 154, 0.15);
  border: 2px solid #26a69a;
  border-radius: 8px;
  animation: slideIn 0.3s ease-out;
}

.success-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.success-icon {
  font-size: 18px;
}

.success-title {
  flex: 1;
  font-weight: 600;
  color: #26a69a;
  font-size: 14px;
}

.success-close {
  background: transparent;
  border: none;
  color: #26a69a;
  font-size: 16px;
  cursor: pointer;
  padding: 0;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: background 0.2s;
}

.success-close:hover {
  background: rgba(38, 166, 154, 0.2);
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
