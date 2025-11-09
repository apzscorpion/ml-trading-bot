<template>
  <div class="app">
    <header class="header">
      <h1>📈 ML Trading Bot</h1>
      <div class="header-right">
        <NotificationCenter ref="notificationCenter" />
        <div class="connection-status" :class="{ connected: isConnected }">
          <span class="status-dot"></span>
          {{ isConnected ? "Connected" : "Disconnected" }}
        </div>
      </div>
    </header>

    <!-- Training Progress Component -->
    <TrainingProgress ref="trainingProgressRef" />

    <main class="main-content">
      <!-- Stock Info Display -->
      <div v-if="stockInfo" class="stock-info-banner">
        <div class="stock-info-main">
          <div class="stock-title-row">
            <h2 class="stock-symbol">{{ stockInfo.symbol }}</h2>
            <span class="stock-exchange-badge">{{ stockInfo.exchange }}</span>
            <span v-if="latestPrice" class="stock-current-price"
              >₹{{ latestPrice.toFixed(2) }}</span
            >
          </div>
          <span class="stock-name">{{ stockInfo.name }}</span>
        </div>
        <div class="stock-info-details">
          <span class="stock-timeframe">{{ selectedTimeframe }}</span>
          <span class="stock-yahoo-symbol" title="Yahoo Finance Symbol"
            >📊 {{ selectedSymbol }}</span
          >
        </div>
      </div>

      <!-- Controls Panel -->
      <div class="controls-panel">
        <div class="control-group control-group-wide">
          <label>Search Stock</label>
          <StockSearch @select="onStockSelect" />
        </div>

        <div class="control-group">
          <label>Timeframe</label>
          <div class="button-group">
            <button
              v-for="tf in timeframes"
              :key="tf"
              :class="{ active: selectedTimeframe === tf }"
              @click="selectTimeframe(tf)"
            >
              {{ tf }}
            </button>
          </div>
        </div>

        <div class="control-group">
          <label>Prediction Horizon: {{ horizonMinutes }} min</label>
          <input
            type="range"
            v-model="horizonMinutes"
            min="30"
            max="360"
            step="30"
            class="slider"
          />
        </div>

        <div class="control-group">
          <button
            class="btn-refresh"
            @click="refreshData"
            :disabled="isLoading"
          >
            🔄 Refresh Data
          </button>
        </div>
      </div>

      <!-- Prediction Models Panel -->
      <div class="models-panel">
        <h3>🤖 Prediction Models</h3>
        <div class="models-grid">
          <div class="model-group">
            <h4>Technical Indicators</h4>
            <button
              class="btn-model"
              @click="
                triggerPredictionWithBots(['rsi_bot', 'macd_bot', 'ma_bot'])
              "
              :disabled="isLoading"
            >
              📊 Technical Analysis
            </button>
          </div>

          <div class="model-group">
            <h4>Machine Learning</h4>
            <button
              class="btn-model btn-ml"
              @click="triggerPredictionWithBots(['ml_bot', 'ensemble_bot'])"
              :disabled="isLoading"
            >
              🧠 ML Models
            </button>
          </div>

          <div class="model-group">
            <h4>Deep Learning</h4>
            <button
              class="btn-model btn-dl"
              @click="
                triggerPredictionWithBots(['lstm_bot', 'transformer_bot'])
              "
              :disabled="isLoading"
            >
              🔥 LSTM + Transformer
            </button>
          </div>

          <div class="model-group">
            <h4>All Models</h4>
            <button
              class="btn-model btn-all"
              @click="triggerPrediction()"
              :disabled="isLoading"
            >
              🚀 Full Ensemble
            </button>
          </div>

          <div class="model-group">
            <h4>Train Models</h4>
            <button
              class="btn-model btn-train"
              @click="trainDeepLearningModels"
              :disabled="isTraining || isRetrainingAll"
            >
              {{ isTraining ? "⏳ Training..." : "🎓 Train DL Models" }}
            </button>
          </div>

          <div class="model-group">
            <h4>Retrain All</h4>
            <button
              class="btn-model btn-retrain"
              @click="retrainAllModels"
              :disabled="isTraining || isRetrainingAll"
              title="Retrain all ML models (LSTM, Transformer, Ensemble, ML) for current symbol across all timeframes"
            >
              {{
                isRetrainingAll ? "⏳ Retraining..." : "🔄 Retrain All Models"
              }}
            </button>
          </div>

          <div class="model-group">
            <h4>Clear Models</h4>
            <button
              class="btn-model btn-clear"
              @click="clearAllModels"
              :disabled="isClearingAll"
              title="Clear all trained models for current symbol (useful before retraining)"
            >
              {{ isClearingAll ? "⏳ Clearing..." : "🗑️ Clear All Models" }}
            </button>
          </div>
        </div>
      </div>

      <!-- Chart -->
      <ChartComponent
        ref="chartRef"
        :candles="candles"
        :predictions="predictions"
        :historical-predictions="historicalPredictions"
        :loading="isLoading || isLoadingSymbol"
        @loadMoreHistory="loadMoreHistory"
        @loadNewerHistory="loadNewerHistory"
      />

      <!-- Symbol Loading Overlay -->
      <div v-if="isLoadingSymbol" class="symbol-loading-overlay">
        <div class="loading-content">
          <div class="spinner-large"></div>
          <p>Loading {{ stockInfo?.symbol || selectedSymbol }}...</p>
          <small>Fetching chart data and predictions</small>
        </div>
      </div>

      <!-- Metrics Panel -->
      <div class="metrics-panel">
        <div class="metrics-grid">
          <div class="metric-card">
            <div class="metric-label">Overall Confidence</div>
            <div class="metric-value">
              {{
                latestPrediction?.overall_confidence
                  ? (latestPrediction.overall_confidence * 100).toFixed(1) + "%"
                  : "N/A"
              }}
            </div>
          </div>

          <div class="metric-card">
            <div class="metric-label">Prediction Points</div>
            <div class="metric-value">{{ predictions.length || 0 }}</div>
          </div>

          <div class="metric-card">
            <div class="metric-label">Last Updated</div>
            <div class="metric-value metric-small">
              {{ lastUpdateTime || "Never" }}
            </div>
          </div>

          <div class="metric-card">
            <div class="metric-label">Avg Directional Accuracy</div>
            <div class="metric-value">
              {{
                metricsSummary?.avg_directional_accuracy
                  ? metricsSummary.avg_directional_accuracy.toFixed(1) + "%"
                  : "N/A"
              }}
            </div>
          </div>
        </div>

        <!-- Bot Contributions -->
        <div v-if="latestPrediction?.bot_contributions" class="bot-panel">
          <h3>🤖 Bot Contributions</h3>
          <div class="bot-grid">
            <div
              v-for="(bot, name) in latestPrediction.bot_contributions"
              :key="name"
              class="bot-card"
            >
              <div class="bot-name">{{ formatBotName(name) }}</div>
              <div class="bot-stats">
                <span>Weight: {{ (bot.weight * 100).toFixed(0) }}%</span>
                <span
                  >Confidence: {{ (bot.confidence * 100).toFixed(0) }}%</span
                >
              </div>
              <div class="bot-progress">
                <div
                  class="progress-bar"
                  :style="{ width: bot.confidence * 100 + '%' }"
                ></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Prediction Analysis -->
      <PredictionAnalysis
        :symbol="selectedSymbol"
        :timeframe="selectedTimeframe"
        :refresh-trigger="analysisRefreshTrigger"
      />

      <!-- Prediction Accuracy Monitor -->
      <PredictionAccuracy
        :prediction="latestPrediction"
        :latest-candle="candles[candles.length - 1]"
        :symbol="selectedSymbol"
        :timeframe="selectedTimeframe"
      />

      <!-- Comprehensive Intraday Prediction -->
      <ComprehensivePrediction
        :symbol="selectedSymbol"
        :timeframe="selectedTimeframe"
        :horizon-minutes="horizonMinutes"
      />

      <!-- Watchlist Sidebar -->
      <div class="watchlist-sidebar">
        <Watchlist
          ref="watchlistRef"
          :current-symbol="selectedSymbol"
          @select="onStockSelect"
        />
      </div>

      <!-- Model Manager -->
      <ModelManager ref="modelManagerRef" />
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, computed, watch } from "vue";
import ChartComponent from "./components/ChartComponent.vue";
import PredictionAnalysis from "./components/PredictionAnalysis.vue";
import PredictionAccuracy from "./components/PredictionAccuracy.vue";
import StockSearch from "./components/StockSearch.vue";
import Watchlist from "./components/Watchlist.vue";
import ModelManager from "./components/ModelManager.vue";
import NotificationCenter from "./components/NotificationCenter.vue";
import TrainingProgress from "./components/TrainingProgress.vue";
import ComprehensivePrediction from "./components/ComprehensivePrediction.vue";
import { api } from "./services/api";
import { socketService } from "./services/socket";
import { refreshService } from "./services/refreshService";

// State
const chartRef = ref(null);
const notificationCenter = ref(null);
const modelManagerRef = ref(null);
const trainingProgressRef = ref(null);
const watchlistRef = ref(null);
const selectedSymbol = ref(localStorage.getItem("selectedSymbol") || "TCS.NS");
const selectedTimeframe = ref(
  localStorage.getItem("selectedTimeframe") || "5m"
);
const horizonMinutes = ref(
  parseInt(localStorage.getItem("horizonMinutes") || "180")
);
const isConnected = ref(false);
const isLoading = ref(false);
const isTraining = ref(false);
const isRetrainingAll = ref(false);
const isClearingAll = ref(false);
const isLoadingSymbol = ref(false);

const candles = ref([]);
const predictions = ref([]);
const historicalPredictions = ref([]);
const latestPrediction = ref(null);
const metricsSummary = ref(null);

const stockInfo = ref(null);

const availableSymbols = ref([
  "TCS.NS",
  "RELIANCE.NS",
  "HDFCBANK.NS",
  "INFY.NS",
  "ICICIBANK.NS",
  "HINDUNILVR.NS",
  "ITC.NS",
  "SBIN.NS",
  "BHARTIARTL.NS",
  "KOTAKBANK.NS",
]);

const timeframes = [
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

const lastUpdateTime = ref("");
const analysisRefreshTrigger = ref(0);

// Stock info mapping
const stocksData = {
  "TCS.NS": { name: "Tata Consultancy Services Ltd", exchange: "NSE" },
  "RELIANCE.NS": { name: "Reliance Industries Ltd", exchange: "NSE" },
  "HDFCBANK.NS": { name: "HDFC Bank Ltd", exchange: "NSE" },
  "INFY.NS": { name: "Infosys Ltd", exchange: "NSE" },
  "ICICIBANK.NS": { name: "ICICI Bank Ltd", exchange: "NSE" },
  "HINDUNILVR.NS": { name: "Hindustan Unilever Ltd", exchange: "NSE" },
  "ITC.NS": { name: "ITC Ltd", exchange: "NSE" },
  "SBIN.NS": { name: "State Bank of India", exchange: "NSE" },
  "BHARTIARTL.NS": { name: "Bharti Airtel Ltd", exchange: "NSE" },
  "KOTAKBANK.NS": { name: "Kotak Mahindra Bank Ltd", exchange: "NSE" },
};

// Computed
const formatBotName = (name) => {
  return name.replace("_bot", "").toUpperCase();
};

// Methods
const loadHistory = async (forceRefresh = false) => {
  isLoading.value = true;
  try {
    console.log(
      `📥 Fetching history: ${selectedSymbol.value} ${selectedTimeframe.value}${
        forceRefresh ? " (FORCE REFRESH)" : " (incremental)"
      }`
    );

    // SIMPLIFIED APPROACH: On refresh, ALWAYS replace data completely
    // Only do incremental updates when NOT forcing refresh AND we have data
    let to_ts = null;
    let shouldReplace = forceRefresh || candles.value.length === 0;

    if (!shouldReplace && candles.value.length > 0) {
      // Incremental update: get only newer candles
      const latestCandle = candles.value[candles.value.length - 1];
      to_ts = latestCandle.start_ts;
      console.log(`📊 Incremental update: fetching data after ${to_ts}`);
    } else {
      console.log(`🔄 Full refresh: fetching complete dataset`);
    }

    // CRITICAL: Always bypass cache on force refresh to get fresh data
    const data = await api.fetchHistory(
      selectedSymbol.value,
      selectedTimeframe.value,
      10000, // Large limit to get comprehensive data
      to_ts, // null for full refresh, timestamp for incremental
      null, // from_ts not used for normal flow
      shouldReplace // bypass_cache = true when replacing data
    );

    if (!data || !Array.isArray(data)) {
      console.warn("⚠️ No data returned from API");
      if (shouldReplace) {
        candles.value = [];
      }
      return;
    }

    console.log(`📦 Received ${data.length} raw candles from API`);

    // CRITICAL: Validate and normalize ALL candles
    const now = new Date();
    const oneHourFromNow = new Date(now.getTime() + 60 * 60 * 1000);

    const validCandles = data
      .filter((c) => {
        // Must have required fields
        if (!c || !c.start_ts) return false;

        // Parse and validate timestamp
        const candleDate = new Date(c.start_ts);
        if (isNaN(candleDate.getTime())) {
          console.warn(`⚠️ Invalid timestamp: ${c.start_ts}`);
          return false;
        }

        // Filter future dates (1hr buffer for timezone)
        if (candleDate > oneHourFromNow) {
          console.warn(`⚠️ Future date: ${c.start_ts}`);
          return false;
        }

        // Filter weekends (backend should do this, but double-check)
        const dayOfWeek = candleDate.getDay();
        if (dayOfWeek === 0 || dayOfWeek === 6) {
          return false;
        }

        // Validate OHLC integrity
        const { open, high, low, close } = c;
        if (
          typeof open !== "number" ||
          typeof high !== "number" ||
          typeof low !== "number" ||
          typeof close !== "number" ||
          isNaN(open) ||
          isNaN(high) ||
          isNaN(low) ||
          isNaN(close) ||
          high < low ||
          close < low ||
          close > high ||
          open < low ||
          open > high
        ) {
          console.warn(`⚠️ Invalid OHLC:`, { open, high, low, close });
          return false;
        }

        return true;
      })
      .map((c) => ({
        ...c,
        // Normalize timestamp format
        start_ts: new Date(c.start_ts).toISOString(),
        // Ensure numeric values
        open: Number(c.open),
        high: Number(c.high),
        low: Number(c.low),
        close: Number(c.close),
        volume: Number(c.volume || 0),
      }))
      .sort((a, b) => {
        // Sort chronologically (oldest first)
        return new Date(a.start_ts).getTime() - new Date(b.start_ts).getTime();
      });

    // Deduplicate by timestamp
    const uniqueCandles = Array.from(
      new Map(validCandles.map((c) => [c.start_ts, c])).values()
    );

    if (uniqueCandles.length === 0) {
      console.log(`ℹ️ No valid candles after filtering`);
      if (shouldReplace) {
        candles.value = [];
      }
      return;
    }

    console.log(
      `✅ Validated ${uniqueCandles.length} candles (filtered ${
        data.length - uniqueCandles.length
      })`
    );
    console.log(
      `📅 Range: ${uniqueCandles[0].start_ts} → ${
        uniqueCandles[uniqueCandles.length - 1].start_ts
      }`
    );

    // SIMPLIFIED: Replace or merge
    if (shouldReplace) {
      // Full replace: just set the data
      candles.value = uniqueCandles;
      console.log(`🔄 Replaced with ${uniqueCandles.length} candles`);
    } else {
      // Incremental: merge only truly new candles
      const existingTimestamps = new Set(candles.value.map((c) => c.start_ts));
      const newCandles = uniqueCandles.filter(
        (c) => !existingTimestamps.has(c.start_ts)
      );

      if (newCandles.length > 0) {
        // Append and re-sort
        candles.value = [...candles.value, ...newCandles].sort(
          (a, b) =>
            new Date(a.start_ts).getTime() - new Date(b.start_ts).getTime()
        );
        console.log(
          `➕ Added ${newCandles.length} new candles (total: ${candles.value.length})`
        );
      } else {
        console.log(`ℹ️ No new candles (already up-to-date)`);
      }
    }
  } catch (error) {
    console.error("❌ Error loading history:", error);
    if (forceRefresh || candles.value.length === 0) {
      candles.value = [];
    }
    throw error;
  } finally {
    isLoading.value = false;
  }
};

const loadMoreHistory = async ({ from_ts }) => {
  try {
    const fromDate = new Date(from_ts);
    console.log(
      "📜 Loading older history before:",
      fromDate.toISOString(),
      `(${fromDate.toLocaleString("en-IN", { timeZone: "Asia/Kolkata" })})`
    );

    // Always fetch fresh data (no cache) when scrolling
    const data = await api.fetchHistory(
      selectedSymbol.value,
      selectedTimeframe.value,
      500,
      null, // to_ts
      from_ts // from_ts (load data BEFORE this timestamp)
    );

    if (data && data.length > 0) {
      // Ensure data is sorted by start_ts ascending
      const sortedData = [...data].sort((a, b) => {
        const dateA = new Date(a.start_ts).getTime();
        const dateB = new Date(b.start_ts).getTime();
        return dateA - dateB;
      });

      // Remove duplicates by timestamp (using string comparison)
      const existingTimestamps = new Set(
        candles.value.map((c) => String(c.start_ts))
      );
      const newCandles = sortedData.filter(
        (c) => !existingTimestamps.has(String(c.start_ts))
      );

      if (newCandles.length > 0) {
        // Merge and sort to ensure proper ordering (oldest first)
        const merged = [...newCandles, ...candles.value];
        candles.value = merged.sort((a, b) => {
          const dateA = new Date(a.start_ts).getTime();
          const dateB = new Date(b.start_ts).getTime();
          return dateA - dateB;
        });

        // Deduplicate after merge
        candles.value = Array.from(
          new Map(candles.value.map((c) => [String(c.start_ts), c])).values()
        ).sort((a, b) => {
          const dateA = new Date(a.start_ts).getTime();
          const dateB = new Date(b.start_ts).getTime();
          return dateA - dateB;
        });

        const oldestNew = new Date(newCandles[0].start_ts);
        const newestNew = new Date(newCandles[newCandles.length - 1].start_ts);

        console.log(`✅ Loaded ${newCandles.length} older candles:`, {
          oldest: oldestNew.toLocaleString("en-IN", {
            timeZone: "Asia/Kolkata",
          }),
          newest: newestNew.toLocaleString("en-IN", {
            timeZone: "Asia/Kolkata",
          }),
          totalCandles: candles.value.length,
          dateRange:
            candles.value.length > 0
              ? {
                  first: candles.value[0].start_ts,
                  last: candles.value[candles.value.length - 1].start_ts,
                }
              : null,
        });
      } else {
        console.log(
          "ℹ️ No new older data found (already loaded or reached beginning)"
        );
      }
    } else {
      console.log(
        "ℹ️ No older data available - reached the beginning of historical data"
      );
    }
  } catch (error) {
    console.error("❌ Error loading more history:", error);
  }
};

const loadNewerHistory = async ({ to_ts }) => {
  try {
    const toDate = new Date(to_ts);
    console.log(
      "📜 Loading newer history after:",
      toDate.toISOString(),
      `(${toDate.toLocaleString("en-IN", { timeZone: "Asia/Kolkata" })})`
    );

    // Always fetch fresh data (no cache) when scrolling forward
    // Use to_ts to fetch data AFTER this timestamp
    const data = await api.fetchHistory(
      selectedSymbol.value,
      selectedTimeframe.value,
      500,
      to_ts, // to_ts (load data AFTER this timestamp)
      null // from_ts
    );

    if (data && data.length > 0) {
      // Ensure data is sorted by start_ts ascending
      const sortedData = [...data].sort((a, b) => {
        const dateA = new Date(a.start_ts).getTime();
        const dateB = new Date(b.start_ts).getTime();
        return dateA - dateB;
      });

      // Remove duplicates by timestamp (using string comparison)
      const existingTimestamps = new Set(
        candles.value.map((c) => String(c.start_ts))
      );
      const newCandles = sortedData.filter(
        (c) => !existingTimestamps.has(String(c.start_ts))
      );

      if (newCandles.length > 0) {
        // Merge and sort to ensure proper ordering (oldest first)
        const merged = [...candles.value, ...newCandles];
        candles.value = merged.sort((a, b) => {
          const dateA = new Date(a.start_ts).getTime();
          const dateB = new Date(b.start_ts).getTime();
          return dateA - dateB;
        });

        // Deduplicate after merge
        candles.value = Array.from(
          new Map(candles.value.map((c) => [String(c.start_ts), c])).values()
        ).sort((a, b) => {
          const dateA = new Date(a.start_ts).getTime();
          const dateB = new Date(b.start_ts).getTime();
          return dateA - dateB;
        });

        const oldestNew = new Date(newCandles[0].start_ts);
        const newestNew = new Date(newCandles[newCandles.length - 1].start_ts);

        console.log(`✅ Loaded ${newCandles.length} newer candles:`, {
          oldest: oldestNew.toLocaleString("en-IN", {
            timeZone: "Asia/Kolkata",
          }),
          newest: newestNew.toLocaleString("en-IN", {
            timeZone: "Asia/Kolkata",
          }),
          totalCandles: candles.value.length,
          dateRange:
            candles.value.length > 0
              ? {
                  first: candles.value[0].start_ts,
                  last: candles.value[candles.value.length - 1].start_ts,
                }
              : null,
        });
      } else {
        console.log(
          "ℹ️ No new newer data found (already loaded or reached end)"
        );
      }
    } else {
      console.log("ℹ️ No newer data available - already at latest data");
    }
  } catch (error) {
    console.error("❌ Error loading newer history:", error);
  }
};

const loadLatestPrediction = async () => {
  try {
    const data = await api.fetchLatestPrediction(
      selectedSymbol.value,
      selectedTimeframe.value
    );
    if (data && !data.error && data.predicted_series) {
      // Validate that prediction matches current symbol
      if (
        data.symbol === selectedSymbol.value &&
        data.timeframe === selectedTimeframe.value
      ) {
        latestPrediction.value = data;
        predictions.value = data.predicted_series;
        lastUpdateTime.value = new Date(data.produced_at).toLocaleTimeString();
        console.log(
          "Loaded prediction for:",
          data.symbol,
          data.timeframe,
          "Points:",
          data.predicted_series.length
        );
      } else {
        console.warn(
          "Prediction mismatch! Expected:",
          selectedSymbol.value,
          selectedTimeframe.value,
          "Got:",
          data.symbol,
          data.timeframe
        );
        // Clear mismatched predictions
        predictions.value = [];
        latestPrediction.value = null;
      }
    } else {
      // No prediction available, clear display
      predictions.value = [];
      latestPrediction.value = null;
    }
  } catch (error) {
    console.error("Error loading prediction:", error);
    predictions.value = [];
    latestPrediction.value = null;
  }
};

const loadMetricsSummary = async () => {
  try {
    const data = await api.fetchMetricsSummary(
      selectedSymbol.value,
      selectedTimeframe.value
    );
    if (data && !data.message) {
      metricsSummary.value = data;
    }
  } catch (error) {
    console.error("Error loading metrics:", error);
  }
};

const triggerPrediction = async (selectedBots = null) => {
  isLoading.value = true;
  try {
    const result = await api.triggerPrediction(
      selectedSymbol.value,
      selectedTimeframe.value,
      horizonMinutes.value,
      selectedBots
    );

    if (result && result.result) {
      latestPrediction.value = result.result;
      predictions.value = result.result.predicted_series;
      lastUpdateTime.value = new Date().toLocaleTimeString();
      analysisRefreshTrigger.value++;
    }
  } catch (error) {
    console.error("Error triggering prediction:", error);
  } finally {
    isLoading.value = false;
  }
};

const triggerPredictionWithBots = async (bots) => {
  await triggerPrediction(bots);
};

const clearAllModels = async () => {
  if (
    !confirm(
      `Are you sure you want to clear ALL trained models for ${selectedSymbol.value}?\n\nThis will delete all model files and training records for this symbol across all timeframes.`
    )
  ) {
    return;
  }

  isClearingAll.value = true;

  try {
    console.log("🗑️ Clearing all models for:", selectedSymbol.value);

    if (notificationCenter.value) {
      notificationCenter.value.addInfo(
        `Clearing all models for ${selectedSymbol.value}...`,
        { symbol: selectedSymbol.value },
        "Clear All Models"
      );
    }

    const result = await api.clearAllModelsForSymbol(selectedSymbol.value);

    if (!result) {
      throw new Error("No response from server");
    }

    console.log("✅ Clear all models completed:", result);

    const successMessage = `Cleared ${result.cleared_count || 0} models for ${
      selectedSymbol.value
    }${
      result.timeframes_cleared
        ? ` (${result.timeframes_cleared.length} timeframes)`
        : ""
    }`;

    if (notificationCenter.value) {
      notificationCenter.value.addSuccess(
        successMessage,
        result,
        "Clear All Models"
      );
    } else {
      alert(successMessage);
    }

    // Refresh model list after a delay
    setTimeout(() => {
      if (modelManagerRef.value) {
        modelManagerRef.value.loadModels();
      }
    }, 1000);
  } catch (error) {
    console.error("❌ Error clearing all models:", error);

    const errorMessage = `Failed to clear models: ${
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      "Unknown error"
    }`;

    console.error("Error details:", {
      message: error.message,
      response: error.response?.data,
      status: error.response?.status,
      statusText: error.response?.statusText,
    });

    if (notificationCenter.value) {
      notificationCenter.value.addError(
        errorMessage,
        {
          error: error.message,
          stack: error.stack,
          response: error.response?.data,
          status: error.response?.status,
        },
        "Clear All Models Error"
      );
    } else {
      alert(`Error: ${errorMessage}`);
    }
  } finally {
    isClearingAll.value = false;
  }
};

const retrainAllModels = async () => {
  isRetrainingAll.value = true;

  try {
    // Get all ML bots and timeframes for comprehensive retraining
    const symbols = [selectedSymbol.value];
    const timeframes = ["5m", "15m", "1h", "1d"]; // Common timeframes
    const bots = ["lstm_bot", "transformer_bot", "ml_bot", "ensemble_bot"]; // All trainable bots

    console.log("🔄 Starting retrain all models:", {
      symbols,
      timeframes,
      bots,
    });

    notificationCenter.value?.addInfo(
      `Starting retraining for ${symbols.length} symbol(s) × ${
        timeframes.length
      } timeframe(s) × ${bots.length} bot(s) = ${
        symbols.length * timeframes.length * bots.length
      } tasks`,
      { symbols, timeframes, bots },
      "Retrain All Models"
    );

    const result = await api.startAutoTraining(symbols, timeframes, bots);

    console.log("✅ Retrain all started:", result);

    notificationCenter.value?.addSuccess(
      `Retraining started! ${
        result.queue_size || 0
      } tasks queued. Training will happen in the background.`,
      result,
      "Retrain All Models"
    );

    // Refresh model list after a delay
    setTimeout(() => {
      if (modelManagerRef.value) {
        modelManagerRef.value.loadModels();
      }
    }, 2000);
  } catch (error) {
    console.error("❌ Error retraining all models:", error);
    notificationCenter.value?.addError(
      `Failed to start retraining: ${error.message || "Unknown error"}`,
      {
        error: error.message,
        stack: error.stack,
        response: error.response?.data,
      },
      "Retrain All Models Error"
    );
  } finally {
    isRetrainingAll.value = false;
  }
};

const trainDeepLearningModels = async () => {
  isTraining.value = true;
  const trainingIds = [];

  try {
    // Train LSTM (non-blocking, returns immediately)
    console.log("Starting LSTM training...");
    try {
      const lstmResult = await api.trainBot(
        selectedSymbol.value,
        selectedTimeframe.value,
        "lstm_bot",
        30,
        200 // batch_size
      );
      console.log("LSTM training started:", lstmResult);
      if (lstmResult && lstmResult.training_id) {
        trainingIds.push({ bot: "LSTM", id: lstmResult.training_id });
        notificationCenter.value?.addInfo(
          `LSTM training started (ID: ${lstmResult.training_id}). Progress will be shown in the progress panel.`,
          lstmResult,
          "POST /api/prediction/train (lstm_bot)"
        );
      } else if (lstmResult && lstmResult.status === "not_trainable") {
        notificationCenter.value?.addWarning(
          `LSTM bot: ${lstmResult.message || "Cannot be trained"}`,
          lstmResult,
          "POST /api/prediction/train (lstm_bot)"
        );
      } else {
        notificationCenter.value?.addError(
          `LSTM training failed to start: ${
            lstmResult?.message || "Unknown error"
          }`,
          lstmResult,
          "POST /api/prediction/train (lstm_bot)"
        );
      }
    } catch (error) {
      console.error("LSTM training error:", error);
      notificationCenter.value?.addError(
        `LSTM training failed: ${error.message || "Unknown error"}`,
        {
          error: error.message,
          stack: error.stack,
          response: error.response?.data,
        },
        "POST /api/prediction/train (lstm_bot)"
      );
    }

    // Train Transformer (non-blocking)
    console.log("Starting Transformer training...");
    try {
      const transformerResult = await api.trainBot(
        selectedSymbol.value,
        selectedTimeframe.value,
        "transformer_bot",
        20,
        200 // batch_size
      );
      console.log("Transformer training started:", transformerResult);
      if (transformerResult && transformerResult.training_id) {
        trainingIds.push({
          bot: "Transformer",
          id: transformerResult.training_id,
        });
        notificationCenter.value?.addInfo(
          `Transformer training started (ID: ${transformerResult.training_id}). Progress will be shown in the progress panel.`,
          transformerResult,
          "POST /api/prediction/train (transformer_bot)"
        );
      } else if (
        transformerResult &&
        transformerResult.status === "not_trainable"
      ) {
        notificationCenter.value?.addWarning(
          `Transformer bot: ${
            transformerResult.message || "Cannot be trained"
          }`,
          transformerResult,
          "POST /api/prediction/train (transformer_bot)"
        );
      } else {
        notificationCenter.value?.addError(
          `Transformer training failed to start: ${
            transformerResult?.message || "Unknown error"
          }`,
          transformerResult,
          "POST /api/prediction/train (transformer_bot)"
        );
      }
    } catch (error) {
      console.error("Transformer training error:", error);
      notificationCenter.value?.addError(
        `Transformer training failed: ${error.message || "Unknown error"}`,
        {
          error: error.message,
          stack: error.stack,
          response: error.response?.data,
        },
        "POST /api/prediction/train (transformer_bot)"
      );
    }

    // Train Ensemble (non-blocking)
    console.log("Starting Ensemble training...");
    try {
      const ensembleResult = await api.trainBot(
        selectedSymbol.value,
        selectedTimeframe.value,
        "ensemble_bot",
        1,
        200 // batch_size
      );
      console.log("Ensemble training started:", ensembleResult);
      if (ensembleResult && ensembleResult.training_id) {
        trainingIds.push({ bot: "Ensemble", id: ensembleResult.training_id });
        notificationCenter.value?.addInfo(
          `Ensemble training started (ID: ${ensembleResult.training_id}). Progress will be shown in the progress panel.`,
          ensembleResult,
          "POST /api/prediction/train (ensemble_bot)"
        );
      } else if (ensembleResult && ensembleResult.status === "not_trainable") {
        notificationCenter.value?.addWarning(
          `Ensemble bot: ${ensembleResult.message || "Cannot be trained"}`,
          ensembleResult,
          "POST /api/prediction/train (ensemble_bot)"
        );
      } else {
        notificationCenter.value?.addError(
          `Ensemble training failed to start: ${
            ensembleResult?.message || "Unknown error"
          }`,
          ensembleResult,
          "POST /api/prediction/train (ensemble_bot)"
        );
      }
    } catch (error) {
      console.error("Ensemble training error:", error);
      notificationCenter.value?.addError(
        `Ensemble training failed: ${error.message || "Unknown error"}`,
        {
          error: error.message,
          stack: error.stack,
          response: error.response?.data,
        },
        "POST /api/prediction/train (ensemble_bot)"
      );
    }

    if (trainingIds.length > 0) {
      notificationCenter.value?.addSuccess(
        `Started training for ${trainingIds.length} model(s). Progress will be shown in the progress panel.`,
        { trainingIds },
        "Training Started"
      );
    }

    // Refresh model list after a delay (to allow training to complete)
    setTimeout(() => {
      if (modelManagerRef.value) {
        modelManagerRef.value.loadModels();
      }
    }, 5000);
  } catch (error) {
    console.error("Error starting training:", error);
    notificationCenter.value?.addError(
      `Training failed: ${error.message || "Unknown error"}`,
      {
        error: error.message,
        stack: error.stack,
        response: error.response?.data,
      },
      "Training Error"
    );
  } finally {
    isTraining.value = false;
  }
};

const selectTimeframe = async (tf) => {
  if (selectedTimeframe.value === tf) return; // Already selected

  console.log("🔄 Changing timeframe from", selectedTimeframe.value, "to", tf);

  isLoadingSymbol.value = true;

  const oldTimeframe = selectedTimeframe.value;
  selectedTimeframe.value = tf;
  localStorage.setItem("selectedTimeframe", tf);

  // Unsubscribe from old timeframe WebSocket first
  socketService.unsubscribe();

  // Clear ALL data when changing timeframe
  candles.value = [];
  predictions.value = [];
  historicalPredictions.value = [];
  latestPrediction.value = null;

  // Clear models for old timeframe to force retraining
  try {
    await api.clearModelsForTimeframe(selectedSymbol.value, oldTimeframe);
    console.log(
      `🗑️ Cleared models for ${selectedSymbol.value}/${oldTimeframe}`
    );
  } catch (error) {
    console.warn("Could not clear models for old timeframe:", error);
  }

  try {
    // Reload data sequentially to avoid overwhelming backend
    // History is most critical - load it first
    console.log(`📊 Loading ${tf} candles for ${selectedSymbol.value}...`);
    await loadHistory(true); // forceRefresh = true for timeframe change

    // Then load prediction and metrics in parallel (less critical)
    await Promise.all([loadLatestPrediction(), loadMetricsSummary()]);

    // Subscribe to new timeframe WebSocket
    socketService.subscribe(selectedSymbol.value, selectedTimeframe.value);

    // Fetch latest candles after timeframe change
    setTimeout(() => {
      fetchLatestCandles();
    }, 500);

    console.log(`✅ Timeframe changed successfully to ${tf}`);
    console.log(
      `📈 Loaded ${candles.value.length} candles for ${tf} timeframe`
    );
  } catch (error) {
    console.error("❌ Error changing timeframe:", error);
    notificationCenter.value?.addError(
      `Failed to load ${tf} data: ${error.message || "Unknown error"}`,
      { error, timeframe: tf },
      "Timeframe Change Error"
    );
  } finally {
    isLoadingSymbol.value = false;
  }
};

const onStockSelect = async (symbol) => {
  if (symbol === selectedSymbol.value) return; // Already selected

  console.log("Changing symbol from", selectedSymbol.value, "to", symbol);

  isLoadingSymbol.value = true;

  selectedSymbol.value = symbol;
  localStorage.setItem("selectedSymbol", symbol);
  updateStockInfo(symbol);

  // Clear all predictions when changing symbol
  predictions.value = [];
  historicalPredictions.value = [];
  latestPrediction.value = null;
  candles.value = [];
  metricsSummary.value = null;

  await onSymbolChange();

  isLoadingSymbol.value = false;
};

const updateStockInfo = (symbol) => {
  const info = stocksData[symbol];
  if (info) {
    stockInfo.value = {
      symbol: symbol.replace(".NS", "").replace(".BO", ""),
      name: info.name,
      exchange: info.exchange,
    };
  } else {
    // Extract exchange from symbol
    const exchange = symbol.includes(".NS")
      ? "NSE"
      : symbol.includes(".BO")
      ? "BSE"
      : "Unknown";
    stockInfo.value = {
      symbol: symbol.replace(".NS", "").replace(".BO", ""),
      name: symbol,
      exchange: exchange,
    };
  }
};

const onSymbolChange = async () => {
  // Unsubscribe from old symbol
  socketService.unsubscribe();

  // IMPORTANT: Clear old predictions immediately
  predictions.value = [];
  historicalPredictions.value = [];
  latestPrediction.value = null;

  // Load data sequentially to avoid overwhelming the backend
  // 1. History first (most important for chart) - force refresh when changing symbol
  await loadHistory(true); // forceRefresh = true for symbol change

  // 2. Then prediction and metrics in parallel (less critical)
  await Promise.all([loadLatestPrediction(), loadMetricsSummary()]);

  // Subscribe to new symbol
  socketService.subscribe(selectedSymbol.value, selectedTimeframe.value);

  // Fetch latest candles after a short delay to ensure we have current data
  setTimeout(() => {
    fetchLatestCandles();
  }, 500);
};

const refreshData = async () => {
  isLoading.value = true;
  try {
    console.log("🔄 Refreshing ALL data (bypass cache)...");

    // Clear backend cache first to ensure fresh data
    try {
      await api.clearCache();
      console.log("✅ Backend cache cleared");
    } catch (error) {
      console.warn("⚠️ Could not clear backend cache:", error);
    }

    // Force refresh all data from source (bypass cache, replace existing)
    await loadHistory(true); // forceRefresh = true

    console.log(
      `📊 Loaded ${candles.value.length} candles for ${selectedSymbol.value}/${selectedTimeframe.value}`
    );

    if (candles.value.length > 0) {
      console.log(
        `📅 Data range: ${candles.value[0].start_ts} → ${
          candles.value[candles.value.length - 1].start_ts
        }`
      );
    }

    // Fetch the absolute latest candle to ensure we have current data
    await fetchLatestCandles();

    // Reload predictions and metrics
    await Promise.all([loadLatestPrediction(), loadMetricsSummary()]);

    console.log("✅ Data refresh complete");
  } catch (error) {
    console.error("❌ Error refreshing data:", error);
  } finally {
    isLoading.value = false;
  }
};

const fetchLatestCandles = async () => {
  try {
    console.log("🔄 Fetching latest candles to ensure we have current data...");

    // Fetch latest candle from API
    const latestCandle = await api.fetchLatestCandle(
      selectedSymbol.value,
      selectedTimeframe.value
    );

    if (latestCandle && latestCandle.close) {
      console.log("✅ Latest candle fetched:", {
        time: latestCandle.time || latestCandle.start_ts,
        close: latestCandle.close,
        open: latestCandle.open,
        high: latestCandle.high,
        low: latestCandle.low,
      });

      // Check if this candle already exists in our array
      const candleTime = latestCandle.start_ts || latestCandle.time;
      const existingIndex = candles.value.findIndex(
        (c) => c.start_ts === candleTime || c.start_ts === latestCandle.start_ts
      );

      if (existingIndex >= 0) {
        // Update existing candle
        candles.value[existingIndex] = {
          ...latestCandle,
          start_ts: candleTime || latestCandle.start_ts,
          isLive: true,
        };
        console.log("📊 Updated existing candle at index:", existingIndex);
      } else {
        // Add new candle if it's newer than the last one
        if (candles.value.length > 0) {
          const lastCandleTime = new Date(
            candles.value[candles.value.length - 1].start_ts
          ).getTime();
          const newCandleTime = new Date(candleTime).getTime();

          if (newCandleTime > lastCandleTime) {
            candles.value.push({
              ...latestCandle,
              start_ts: candleTime || latestCandle.start_ts,
              isLive: true,
            });
            console.log("✅ Added new latest candle");
          } else {
            console.log("ℹ️ Latest candle is not newer than existing data");
          }
        } else {
          // No candles yet, add it
          candles.value.push({
            ...latestCandle,
            start_ts: candleTime || latestCandle.start_ts,
            isLive: true,
          });
          console.log("✅ Added latest candle (no existing candles)");
        }
      }

      // Ensure candles are sorted
      candles.value.sort((a, b) => {
        const dateA = new Date(a.start_ts).getTime();
        const dateB = new Date(b.start_ts).getTime();
        return dateA - dateB;
      });

      // Update chart with the latest candle
      if (chartRef.value && latestCandle) {
        chartRef.value.updateCandle({
          ...latestCandle,
          start_ts: candleTime || latestCandle.start_ts,
        });
      }
    } else {
      console.warn("⚠️ No latest candle data received");
    }
  } catch (error) {
    console.error("❌ Error fetching latest candles:", error);
  }
};

// WebSocket handlers - Live candle updates
const handleCandleUpdate = (message) => {
  // Update watchlist price if this symbol is in watchlist
  if (watchlistRef.value && message.candle && message.candle.close) {
    const watchlistStr = localStorage.getItem("watchlist");
    if (watchlistStr) {
      try {
        const watchlist = JSON.parse(watchlistStr);
        const stock = watchlist.find((s) => s.symbol === message.symbol);
        if (stock) {
          // Update watchlist price via WebSocket update
          const previousPrice = stock.price || message.candle.close;
          const change = message.candle.close - previousPrice;
          const changePercent =
            previousPrice && previousPrice !== message.candle.close
              ? (change / previousPrice) * 100
              : 0;

          watchlistRef.value.updatePrices({
            symbol: message.symbol,
            price: message.candle.close,
            change: change,
            changePercent: changePercent,
          });
        }
      } catch (e) {
        // Ignore parse errors
      }
    }
  }

  if (
    message.symbol === selectedSymbol.value &&
    message.timeframe === selectedTimeframe.value
  ) {
    const newCandle = message.candle;

    console.log("📊 Live candle update received:", {
      symbol: message.symbol,
      timeframe: message.timeframe,
      time: newCandle.start_ts,
      close: newCandle.close,
    });

    // Check if candle already exists (live update) or is new (completed candle)
    const existingIndex = candles.value.findIndex(
      (c) => c.start_ts === newCandle.start_ts
    );

    if (existingIndex >= 0) {
      // Update existing candle (LIVE UPDATE - candle is still forming)
      // Merge to preserve any additional properties
      candles.value[existingIndex] = {
        ...candles.value[existingIndex],
        ...newCandle,
        isLive: true,
      };

      // Update chart with live candle
      if (chartRef.value) {
        chartRef.value.updateCandle(candles.value[existingIndex]);
      }
    } else {
      // New candle (previous one completed or completely new)
      // Mark previous candle as complete if it exists
      if (candles.value.length > 0) {
        const lastIndex = candles.value.length - 1;
        const lastCandle = candles.value[lastIndex];
        // Only mark as complete if it was live and the new candle is newer
        if (
          lastCandle.isLive &&
          new Date(newCandle.start_ts) > new Date(lastCandle.start_ts)
        ) {
          candles.value[lastIndex] = { ...lastCandle, isLive: false };
        }
      }

      // Add new live candle - insert in correct position to maintain sorted order
      const insertIndex = candles.value.findIndex(
        (c) => new Date(c.start_ts) > new Date(newCandle.start_ts)
      );

      if (insertIndex === -1) {
        // New candle is the latest, append to end
        candles.value.push({ ...newCandle, isLive: true });
      } else {
        // Insert at correct position
        candles.value.splice(insertIndex, 0, { ...newCandle, isLive: true });
      }

      // Keep reasonable number of candles
      if (candles.value.length > 2000) {
        candles.value.shift();
      }

      // Update chart with the new candle
      if (chartRef.value) {
        chartRef.value.updateCandle(newCandle);
      }
    }
  }
};

const handlePredictionUpdate = (message) => {
  // STRICT validation: Only show prediction if it matches current symbol AND timeframe
  if (
    message.symbol === selectedSymbol.value &&
    message.timeframe === selectedTimeframe.value
  ) {
    console.log(
      "Prediction update received for:",
      message.symbol,
      message.timeframe
    );
    latestPrediction.value = message;
    predictions.value = message.predicted_series;
    lastUpdateTime.value = new Date().toLocaleTimeString();
    analysisRefreshTrigger.value++;

    // Update chart
    if (chartRef.value) {
      chartRef.value.updatePrediction(message.predicted_series);
    }
  } else {
    console.log(
      "Ignoring prediction update for different symbol/timeframe:",
      message.symbol,
      message.timeframe,
      "Current:",
      selectedSymbol.value,
      selectedTimeframe.value
    );
  }
};

// Watch for horizon changes and persist
watch(horizonMinutes, (newVal) => {
  localStorage.setItem("horizonMinutes", newVal.toString());
});

// Watchlist price fetching
let watchlistPriceInterval = null;

const fetchWatchlistPrices = async () => {
  if (!watchlistRef.value) return;

  try {
    // Get watchlist from localStorage
    const watchlistStr = localStorage.getItem("watchlist");
    if (!watchlistStr) return;

    const watchlist = JSON.parse(watchlistStr);
    if (!Array.isArray(watchlist) || watchlist.length === 0) return;

    // Fetch prices for all watchlist stocks
    const pricePromises = watchlist.map(async (stock) => {
      try {
        // Use '1d' timeframe for watchlist to get latest close price
        const latestCandle = await api.fetchLatestCandle(stock.symbol, "1d");
        if (latestCandle && latestCandle.close && !latestCandle.error) {
          // Get previous price from the stock object or use current price (no change)
          const previousPrice = stock.price || latestCandle.close;
          const change = latestCandle.close - previousPrice;
          const changePercent =
            previousPrice && previousPrice !== latestCandle.close
              ? (change / previousPrice) * 100
              : 0;

          return {
            symbol: stock.symbol,
            price: latestCandle.close,
            change: change,
            changePercent: changePercent,
          };
        }
      } catch (error) {
        console.error(`Error fetching price for ${stock.symbol}:`, error);
      }
      return null;
    });

    const priceResults = await Promise.all(pricePromises);

    // Update watchlist component with prices
    priceResults.forEach((priceData) => {
      if (priceData && watchlistRef.value) {
        watchlistRef.value.updatePrices(priceData);
      }
    });
  } catch (error) {
    console.error("Error fetching watchlist prices:", error);
  }
};

// Lifecycle
onMounted(async () => {
  // Initialize stock info
  updateStockInfo(selectedSymbol.value);

  // Load initial data sequentially to avoid overwhelming backend
  // 1. History first (most critical for chart rendering) - force refresh on initial load
  await loadHistory(true); // forceRefresh = true for initial load

  // 2. Then prediction and metrics in parallel
  await Promise.all([loadLatestPrediction(), loadMetricsSummary()]);

  // 3. Fetch latest candles to ensure we have the most current data
  setTimeout(() => {
    fetchLatestCandles();
  }, 1000);

  // Note: PredictionAnalysis will load after a short delay (500ms) to avoid simultaneous requests

  // Connect WebSocket
  socketService.on("connected", () => {
    isConnected.value = true;
    socketService.subscribe(selectedSymbol.value, selectedTimeframe.value);
    // Fetch latest candles when WebSocket connects to ensure we have current data
    setTimeout(() => {
      fetchLatestCandles();
    }, 1000);
  });

  socketService.on("disconnected", () => {
    isConnected.value = false;
  });

  socketService.on("candle:update", handleCandleUpdate);
  socketService.on("prediction:update", handlePredictionUpdate);

  // Handle training progress events
  socketService.on("training:progress", (message) => {
    if (trainingProgressRef.value) {
      trainingProgressRef.value.addOrUpdateTraining(message);
    }
  });

  // Make socketService available globally for TrainingProgress component
  window.socketService = socketService;

  socketService.connect();

  // Start automatic refresh service
  refreshService.start({
    refreshHistory: async () => {
      // Only refresh if showing recent data (last 24 hours)
      if (refreshService.isShowingRecentData(candles.value)) {
        console.log("🔄 Auto-refreshing history...");
        await loadHistory(false); // Don't force refresh, just get new data
      }
    },
    refreshPrediction: async () => {
      if (refreshService.isShowingRecentData(candles.value)) {
        console.log("🔄 Auto-refreshing prediction...");
        await loadLatestPrediction();
      }
    },
    refreshMetrics: async () => {
      if (refreshService.isShowingRecentData(candles.value)) {
        console.log("🔄 Auto-refreshing metrics...");
        await loadMetricsSummary();
      }
    },
  });

  // Fetch watchlist prices immediately and then every 30 seconds
  await fetchWatchlistPrices();
  watchlistPriceInterval = setInterval(fetchWatchlistPrices, 30000); // Update every 30 seconds
});

onBeforeUnmount(() => {
  socketService.disconnect();
  refreshService.stop();
  if (watchlistPriceInterval) {
    clearInterval(watchlistPriceInterval);
  }
});
</script>

<style scoped>
.app {
  min-height: 100vh;
  background: #0e0e10;
}

.header {
  background: #18181b;
  padding: 20px 32px;
  border-bottom: 1px solid #2b2b2e;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header h1 {
  font-size: 24px;
  font-weight: 600;
  color: #efeff1;
  margin: 0;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stock-info-banner {
  background: linear-gradient(135deg, #1a1a1d, #2b2b2e);
  padding: 20px 24px;
  border-radius: 8px;
  border: 1px solid #2b2b2e;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stock-info-main {
  display: flex;
  align-items: center;
  gap: 12px;
}

.stock-symbol {
  font-size: 32px;
  font-weight: 700;
  color: #efeff1;
  margin: 0;
  font-family: "SF Mono", "Monaco", "Cascadia Code", monospace;
}

.stock-exchange-badge {
  font-size: 12px;
  padding: 4px 10px;
  background: #2962ff;
  color: white;
  border-radius: 4px;
  font-weight: 600;
}

.stock-info-details {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stock-name {
  font-size: 16px;
  color: #999;
  font-weight: 500;
}

.stock-timeframe {
  font-size: 13px;
  padding: 4px 10px;
  background: #2b2b2e;
  color: #efeff1;
  border-radius: 4px;
  font-weight: 600;
  font-family: "SF Mono", "Monaco", "Cascadia Code", monospace;
}

.stock-yahoo-symbol {
  padding: 4px 12px;
  background: rgba(41, 98, 255, 0.15);
  border: 1px solid rgba(41, 98, 255, 0.3);
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  color: #2962ff;
  font-family: "SF Mono", "Monaco", "Cascadia Code", monospace;
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 6px;
  background: #1a1a1d;
  font-size: 14px;
  color: #888;
}

.connection-status.connected {
  color: #26a69a;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #888;
}

.connection-status.connected .status-dot {
  background: #26a69a;
  animation: pulse 2s infinite;
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

.main-content {
  max-width: 1800px;
  margin: 0 auto;
  padding: 32px;
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: 24px;
  align-items: start;
}

.main-content > *:not(.watchlist-sidebar) {
  grid-column: 1;
}

.watchlist-sidebar {
  grid-column: 2;
  grid-row: 1 / -1;
  position: sticky;
  top: 32px;
}

.controls-panel {
  display: flex;
  gap: 24px;
  align-items: flex-end;
  background: #18181b;
  padding: 20px;
  border-radius: 8px;
  flex-wrap: wrap;
}

.control-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 150px;
}

.control-group-wide {
  min-width: 300px;
  flex: 1;
  max-width: 500px;
}

.control-group label {
  font-size: 13px;
  color: #999;
  font-weight: 500;
}

.control-group select,
.control-group input {
  padding: 10px 14px;
  background: #1a1a1d;
  border: 1px solid #2b2b2e;
  border-radius: 6px;
  color: #efeff1;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
}

.control-group select:focus,
.control-group input:focus {
  border-color: #2962ff;
}

.button-group {
  display: flex;
  gap: 8px;
}

.button-group button {
  padding: 10px 16px;
  background: #1a1a1d;
  border: 1px solid #2b2b2e;
  border-radius: 6px;
  color: #efeff1;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.button-group button:hover {
  background: #2b2b2e;
  border-color: #3a3a3e;
}

.button-group button.active {
  background: #2962ff;
  border-color: #2962ff;
  color: white;
}

.slider {
  width: 200px;
}

.btn-primary {
  padding: 12px 24px;
  background: #2962ff;
  border: none;
  border-radius: 6px;
  color: white;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary:hover:not(:disabled) {
  background: #1e4fd9;
  transform: translateY(-1px);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.metrics-panel {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.metric-card {
  background: #18181b;
  padding: 20px;
  border-radius: 8px;
  border: 1px solid #2b2b2e;
}

.metric-label {
  font-size: 13px;
  color: #999;
  margin-bottom: 8px;
}

.metric-value {
  font-size: 28px;
  font-weight: 700;
  color: #efeff1;
}

.metric-small {
  font-size: 16px;
}

.bot-panel {
  background: #18181b;
  padding: 24px;
  border-radius: 8px;
  border: 1px solid #2b2b2e;
}

.bot-panel h3 {
  margin: 0 0 16px 0;
  font-size: 18px;
  color: #efeff1;
}

.bot-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 16px;
}

.bot-card {
  background: #1a1a1d;
  padding: 16px;
  border-radius: 6px;
  border: 1px solid #2b2b2e;
}

.bot-name {
  font-size: 14px;
  font-weight: 600;
  color: #efeff1;
  margin-bottom: 8px;
}

.bot-stats {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #999;
  margin-bottom: 8px;
}

.bot-progress {
  height: 4px;
  background: #2b2b2e;
  border-radius: 2px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: linear-gradient(90deg, #2962ff, #26a69a);
  transition: width 0.3s;
}

.models-panel {
  background: #18181b;
  padding: 24px;
  border-radius: 8px;
  border: 1px solid #2b2b2e;
}

.models-panel h3 {
  margin: 0 0 20px 0;
  font-size: 18px;
  color: #efeff1;
}

.models-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.model-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.model-group h4 {
  margin: 0;
  font-size: 13px;
  color: #999;
  font-weight: 500;
}

.btn-model {
  padding: 14px 20px;
  background: linear-gradient(135deg, #2962ff, #1e4fd9);
  border: none;
  border-radius: 8px;
  color: white;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 2px 8px rgba(41, 98, 255, 0.3);
}

.btn-model:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(41, 98, 255, 0.5);
}

.btn-model:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.btn-model.btn-ml {
  background: linear-gradient(135deg, #26a69a, #1e8e84);
  box-shadow: 0 2px 8px rgba(38, 166, 154, 0.3);
}

.btn-model.btn-ml:hover:not(:disabled) {
  box-shadow: 0 4px 12px rgba(38, 166, 154, 0.5);
}

.btn-model.btn-dl {
  background: linear-gradient(135deg, #ff6b6b, #ee5253);
  box-shadow: 0 2px 8px rgba(255, 107, 107, 0.3);
}

.btn-model.btn-dl:hover:not(:disabled) {
  box-shadow: 0 4px 12px rgba(255, 107, 107, 0.5);
}

.btn-model.btn-all {
  background: linear-gradient(135deg, #6c5ce7, #a29bfe);
  box-shadow: 0 2px 8px rgba(108, 92, 231, 0.3);
}

.btn-model.btn-all:hover:not(:disabled) {
  box-shadow: 0 4px 12px rgba(108, 92, 231, 0.5);
}

.btn-model.btn-train {
  background: linear-gradient(135deg, #feca57, #ff9ff3);
  color: #18181b;
  box-shadow: 0 2px 8px rgba(254, 202, 87, 0.3);
}

.btn-model.btn-train:hover:not(:disabled) {
  box-shadow: 0 4px 12px rgba(254, 202, 87, 0.5);
}

.btn-model.btn-retrain {
  background: linear-gradient(135deg, #ff6b6b, #ff5252);
  color: white;
  box-shadow: 0 2px 8px rgba(255, 107, 107, 0.3);
  font-weight: 600;
}

.btn-model.btn-retrain:hover:not(:disabled) {
  box-shadow: 0 4px 12px rgba(255, 107, 107, 0.5);
}

.btn-model.btn-clear {
  background: linear-gradient(135deg, #95a5a6, #7f8c8d);
  color: white;
  box-shadow: 0 2px 8px rgba(149, 165, 166, 0.3);
  font-weight: 600;
}

.btn-model.btn-clear:hover:not(:disabled) {
  box-shadow: 0 4px 12px rgba(149, 165, 166, 0.5);
}

.btn-refresh {
  padding: 10px 16px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  border: none;
  border-radius: 6px;
  color: white;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
}

.btn-refresh:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.5);
}

.btn-refresh:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.symbol-loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(14, 14, 16, 0.95);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  backdrop-filter: blur(4px);
}

.loading-content {
  text-align: center;
  color: #efeff1;
}

.spinner-large {
  width: 64px;
  height: 64px;
  border: 4px solid #2b2b2e;
  border-top-color: #2962ff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}

.loading-content p {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 8px 0;
}

.loading-content small {
  font-size: 14px;
  color: #999;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
