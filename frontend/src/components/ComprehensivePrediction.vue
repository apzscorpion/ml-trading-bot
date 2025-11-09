<template>
  <div class="comprehensive-prediction-panel">
    <div class="panel-header">
      <h3>📊 Trading Analysis</h3>
      <div class="header-actions">
        <div class="tab-selector">
          <button
            :class="['tab-btn', { active: activeTab === 'ta' }]"
            @click="activeTab = 'ta'"
          >
            📈 Technical Analysis
          </button>
          <button
            :class="['tab-btn', { active: activeTab === 'ml' }]"
            @click="activeTab = 'ml'"
          >
            🤖 ML Predictions
          </button>
        </div>
        <button
          class="btn-refresh-prediction"
          @click="
            activeTab === 'ta' ? loadTechnicalAnalysis() : loadPrediction()
          "
          :disabled="isLoading || isTALoading"
        >
          {{ isLoading || isTALoading ? "⏳ Loading..." : "🔄 Refresh" }}
        </button>
      </div>
    </div>

    <!-- Technical Analysis Tab -->
    <div v-show="activeTab === 'ta'" class="ta-tab-content">
      <div v-if="isTALoading" class="loading-state">
        <div class="spinner"></div>
        <p>Loading technical analysis (60-90 days)...</p>
      </div>

      <div v-else-if="taAnalysis" class="ta-content">
        <!-- TA Header -->
        <div class="ta-header">
          <div class="ta-info">
            <h2>{{ taAnalysis.symbol }}</h2>
            <span class="timeframe-badge">{{ taAnalysis.timeframe }}</span>
            <span class="data-badge"
              >{{ taAnalysis.candles_analyzed }} candles ({{
                taAnalysis.data_window_days
              }}
              days)</span
            >
          </div>
          <div class="ta-price">
            <div class="current-price">
              ₹{{ taAnalysis.indicators?.current_price?.toFixed(2) }}
            </div>
            <div
              class="price-change"
              :class="
                taAnalysis.indicators?.price_change_pct >= 0
                  ? 'positive'
                  : 'negative'
              "
            >
              {{ taAnalysis.indicators?.price_change_pct >= 0 ? "+" : ""
              }}{{ taAnalysis.indicators?.price_change_pct?.toFixed(2) }}%
            </div>
          </div>
        </div>

        <!-- TA Recommendation -->
        <div class="ta-recommendation">
          <div
            class="recommendation-card"
            :class="taAnalysis.recommendation?.action?.toLowerCase()"
          >
            <div class="rec-label">Recommendation</div>
            <div class="rec-action">
              {{ taAnalysis.recommendation?.action || "HOLD" }}
            </div>
            <div class="rec-confidence">
              Confidence:
              {{ (taAnalysis.recommendation?.confidence * 100)?.toFixed(0) }}%
            </div>
          </div>
          <div class="recommendation-details">
            <div class="detail-item">
              <span class="label">Bullish Score</span>
              <span class="value"
                >{{
                  (taAnalysis.recommendation?.bullish_score * 100)?.toFixed(0)
                }}%</span
              >
            </div>
            <div class="detail-item">
              <span class="label">Bearish Score</span>
              <span class="value"
                >{{
                  (taAnalysis.recommendation?.bearish_score * 100)?.toFixed(0)
                }}%</span
              >
            </div>
          </div>
        </div>

        <!-- TA Indicators Grid -->
        <div class="ta-indicators-grid">
          <div class="ta-indicator">
            <div class="indicator-title">RSI (14)</div>
            <div
              class="indicator-value"
              :class="getRSIClass(taAnalysis.indicators?.rsi)"
            >
              {{ taAnalysis.indicators?.rsi?.toFixed(2) }}
            </div>
            <div class="indicator-signal">
              {{ taAnalysis.signals?.rsi?.signal }}
            </div>
          </div>
          <div class="ta-indicator">
            <div class="indicator-title">MACD</div>
            <div
              class="indicator-value"
              :class="taAnalysis.signals?.macd?.signal"
            >
              {{ taAnalysis.indicators?.macd?.toFixed(2) }}
            </div>
            <div class="indicator-signal">
              {{ taAnalysis.signals?.macd?.signal }}
            </div>
          </div>
          <div class="ta-indicator">
            <div class="indicator-title">SMA 20/50</div>
            <div class="indicator-value">
              {{ taAnalysis.indicators?.sma_20?.toFixed(2) }} /
              {{ taAnalysis.indicators?.sma_50?.toFixed(2) }}
            </div>
            <div class="indicator-signal">
              {{ taAnalysis.signals?.ma?.signal }}
            </div>
          </div>
          <div class="ta-indicator">
            <div class="indicator-title">Bollinger Bands</div>
            <div class="indicator-value">
              {{ taAnalysis.indicators?.bb_middle?.toFixed(2) }}
            </div>
            <div class="indicator-signal">
              {{ taAnalysis.signals?.bollinger?.signal }}
            </div>
          </div>
          <div class="ta-indicator">
            <div class="indicator-title">ATR</div>
            <div class="indicator-value">
              {{ taAnalysis.indicators?.atr?.toFixed(2) }}
            </div>
            <div class="indicator-signal">Volatility measure</div>
          </div>
          <div class="ta-indicator">
            <div class="indicator-title">Volume</div>
            <div class="indicator-value">
              {{ formatVolume(taAnalysis.indicators?.volume_ratio) }}
            </div>
            <div class="indicator-signal">
              {{ taAnalysis.signals?.volume?.signal }}
            </div>
          </div>
        </div>

        <!-- Support/Resistance Levels -->
        <div class="ta-levels">
          <div class="level-card resistance">
            <div class="level-label">Resistance</div>
            <div class="level-value">
              ₹{{ taAnalysis.recommendation?.resistance_level?.toFixed(2) }}
            </div>
          </div>
          <div class="level-card support">
            <div class="level-label">Support</div>
            <div class="level-value">
              ₹{{ taAnalysis.recommendation?.support_level?.toFixed(2) }}
            </div>
          </div>
          <div class="level-card stop-loss">
            <div class="level-label">Suggested Stop Loss</div>
            <div class="level-value">
              ₹{{ taAnalysis.recommendation?.stop_loss_suggestion?.toFixed(2) }}
            </div>
          </div>
          <div class="level-card take-profit">
            <div class="level-label">Suggested Take Profit</div>
            <div class="level-value">
              ₹{{
                taAnalysis.recommendation?.take_profit_suggestion?.toFixed(2)
              }}
            </div>
          </div>
        </div>

        <div class="ta-footer">
          Pure Technical Analysis - No ML interference | Updated:
          {{ formatTime(taAnalysis.analyzed_at) }}
        </div>
      </div>

      <div v-else-if="taError" class="error-state">
        <p>❌ {{ taError }}</p>
        <button @click="loadTechnicalAnalysis" class="btn-retry">Retry</button>
      </div>
    </div>

    <!-- ML Predictions Tab -->
    <div v-show="activeTab === 'ml'" class="ml-tab-content">
      <div v-if="isLoading" class="loading-state">
        <div class="spinner"></div>
        <p>Analyzing with all ML models...</p>
      </div>

      <div v-else-if="prediction" class="prediction-content">
        <!-- Current Stock Info -->
        <div class="stock-header">
          <div class="stock-main">
            <h2>{{ prediction.symbol }}</h2>
            <span class="timeframe-badge">{{ prediction.timeframe }}</span>
          </div>
          <div class="price-info">
            <div class="current-price">₹{{ prediction.current_price }}</div>
            <div class="prediction-time">
              {{ formatTime(prediction.current_time) }}
            </div>
          </div>
        </div>

        <!-- Targets and Stop Loss -->
        <div class="targets-section">
          <div class="date-header">
            <strong>On {{ formatDate(prediction.current_time) }}</strong>
          </div>

          <div class="targets-grid">
            <div class="target-card target-1">
              <div class="target-label">Target 1</div>
              <div class="target-value">₹{{ prediction.targets.target_1 }}</div>
              <div class="target-meta">
                <span class="reward"
                  >Reward: ₹{{ prediction.targets.reward_1 }}</span
                >
                <span class="rr-ratio"
                  >R:R {{ prediction.targets.risk_reward_ratio_1 }}:1</span
                >
              </div>
            </div>

            <div class="target-card target-2">
              <div class="target-label">Target 2</div>
              <div class="target-value">₹{{ prediction.targets.target_2 }}</div>
              <div class="target-meta">
                <span class="reward"
                  >Reward: ₹{{ prediction.targets.reward_2 }}</span
                >
                <span class="rr-ratio"
                  >R:R {{ prediction.targets.risk_reward_ratio_2 }}:1</span
                >
              </div>
            </div>

            <div class="target-card stop-loss">
              <div class="target-label">Stop Loss</div>
              <div class="target-value">
                ₹{{ prediction.targets.stop_loss }}
              </div>
              <div class="target-meta">
                <span class="risk"
                  >Risk: ₹{{ prediction.targets.risk_amount }}</span
                >
              </div>
            </div>
          </div>
        </div>

        <!-- Pattern Analysis -->
        <div class="patterns-section">
          <h4>📊 Candlestick Patterns</h4>
          <div
            v-if="prediction.candlestick_patterns.detected_patterns.length > 0"
            class="patterns-list"
          >
            <span
              v-for="pattern in prediction.candlestick_patterns
                .detected_patterns"
              :key="pattern"
              class="pattern-badge"
              :class="getPatternType(pattern)"
            >
              {{ formatPatternName(pattern) }}
            </span>
          </div>
          <div v-else class="no-patterns">No significant patterns detected</div>
          <div class="pattern-sentiment">
            <span class="sentiment-label">Sentiment:</span>
            <span
              class="sentiment-value"
              :class="prediction.candlestick_patterns.sentiment"
            >
              {{ prediction.candlestick_patterns.sentiment.toUpperCase() }}
            </span>
            <span class="confidence"
              >({{
                (prediction.candlestick_patterns.confidence * 100).toFixed(0)
              }}%)</span
            >
          </div>
        </div>

        <!-- Indicators Summary -->
        <div class="indicators-section">
          <h4>📈 Technical Indicators</h4>
          <div class="indicators-grid">
            <div class="indicator-item">
              <span class="indicator-label">RSI:</span>
              <span
                class="indicator-value"
                :class="getRSIClass(prediction.indicators.rsi)"
              >
                {{
                  prediction.indicators.rsi
                    ? prediction.indicators.rsi.toFixed(2)
                    : "N/A"
                }}
              </span>
            </div>
            <div class="indicator-item">
              <span class="indicator-label">MACD:</span>
              <span
                class="indicator-value"
                :class="getMACDClass(prediction.indicators.macd_histogram)"
              >
                {{
                  prediction.indicators.macd
                    ? prediction.indicators.macd.toFixed(2)
                    : "N/A"
                }}
              </span>
            </div>
            <div class="indicator-item">
              <span class="indicator-label">Volume:</span>
              <span class="indicator-value">
                {{ formatVolume(prediction.indicators.volume) }}
              </span>
            </div>
            <div class="indicator-item">
              <span class="indicator-label">VWAP:</span>
              <span class="indicator-value">
                ₹{{
                  prediction.indicators.vwap
                    ? prediction.indicators.vwap.toFixed(2)
                    : "N/A"
                }}
              </span>
            </div>
            <div class="indicator-item">
              <span class="indicator-label">SMA 20:</span>
              <span class="indicator-value">
                ₹{{
                  prediction.indicators.sma_20
                    ? prediction.indicators.sma_20.toFixed(2)
                    : "N/A"
                }}
              </span>
            </div>
            <div class="indicator-item">
              <span class="indicator-label">SMA 50:</span>
              <span class="indicator-value">
                ₹{{
                  prediction.indicators.sma_50
                    ? prediction.indicators.sma_50.toFixed(2)
                    : "N/A"
                }}
              </span>
            </div>
            <div class="indicator-item">
              <span class="indicator-label">ATR:</span>
              <span class="indicator-value">
                ₹{{
                  prediction.indicators.atr
                    ? prediction.indicators.atr.toFixed(2)
                    : "N/A"
                }}
              </span>
            </div>
            <div class="indicator-item">
              <span class="indicator-label">BB Upper:</span>
              <span class="indicator-value">
                ₹{{
                  prediction.indicators.bb_upper
                    ? prediction.indicators.bb_upper.toFixed(2)
                    : "N/A"
                }}
              </span>
            </div>
          </div>
        </div>

        <!-- Model Confidence -->
        <div class="confidence-section">
          <h4>🤖 Model Confidence</h4>
          <div class="confidence-bar">
            <div
              class="confidence-fill"
              :style="{
                width: prediction.prediction.overall_confidence * 100 + '%',
              }"
            ></div>
            <span class="confidence-text">
              {{ (prediction.prediction.overall_confidence * 100).toFixed(1) }}%
            </span>
          </div>
          <div class="models-summary">
            {{ prediction.models_used.successful_bots }}/{{
              prediction.models_used.total_bots
            }}
            models successful
          </div>
        </div>

        <!-- Freddy AI Insight -->
        <div class="freddy-section">
          <div class="freddy-header">
            <h4>🤖 Freddy AI Insight</h4>
            <div class="freddy-controls">
              <label class="freddy-cache-toggle">
                <input type="checkbox" v-model="useFreddyCache" />
                <span>Reuse cached response</span>
              </label>
              <button
                class="freddy-reset"
                v-if="freddyPromptInput.trim() !== defaultFreddyPrompt"
                @click="resetFreddyPrompt"
              >
                Reset Prompt
              </button>
            </div>
          </div>

          <p class="freddy-helper">
            Combine live indicators, volume, and last-day news to get an
            actionable plan from Freddy AI.
          </p>

          <div class="freddy-input-row">
            <textarea
              v-model="freddyPromptInput"
              :placeholder="defaultFreddyPrompt"
              rows="3"
            ></textarea>
            <div class="freddy-actions">
              <button
                class="btn-freddy"
                @click="triggerFreddy({ forceFresh: !useFreddyCache })"
                :disabled="isFreddyLoading"
              >
                {{
                  isFreddyLoading ? "⏳ Asking Freddy..." : "🤖 Ask Freddy AI"
                }}
              </button>
              <small class="freddy-meta">
                Uses the latest {{ FREDDY_LOOKBACK_MINUTES }} min context.
              </small>
            </div>
          </div>

          <div v-if="freddyError" class="freddy-error">
            {{ freddyError }}
          </div>

          <div v-else-if="isFreddyLoading" class="freddy-loading">
            <div class="spinner"></div>
            <span>Freddy AI is crunching the latest signals...</span>
          </div>

          <div v-else-if="freddyAnalysis" class="freddy-results">
            <div class="freddy-metrics-grid">
              <div class="freddy-metric-card">
                <span class="metric-label">Recommendation</span>
                <span
                  class="metric-value"
                  :class="['freddy-recommendation', freddyRecommendationClass]"
                >
                  {{ freddyAnalysis.recommendation || "N/A" }}
                </span>
              </div>
              <div class="freddy-metric-card">
                <span class="metric-label">Target</span>
                <span class="metric-value">{{
                  formatCurrencyValue(freddyAnalysis.target_price)
                }}</span>
              </div>
              <div class="freddy-metric-card">
                <span class="metric-label">Stop Loss</span>
                <span class="metric-value">{{
                  formatCurrencyValue(freddyAnalysis.stop_loss)
                }}</span>
              </div>
              <div class="freddy-metric-card">
                <span class="metric-label">Confidence</span>
                <span class="metric-value">{{
                  formatPercentageValue(freddyAnalysis.confidence)
                }}</span>
              </div>
            </div>

            <div v-if="freddyAnalysis.summary" class="freddy-summary">
              {{ freddyAnalysis.summary }}
            </div>

            <div v-if="freddyAnalysis.technical_indicators" class="freddy-tech">
              <div class="tech-item">
                <span>RSI 14</span>
                <strong>{{
                  formatNumberValue(freddyAnalysis.technical_indicators.rsi_14)
                }}</strong>
              </div>
              <div class="tech-item">
                <span>Bias</span>
                <strong>{{
                  freddyAnalysis.technical_indicators.technical_bias || "N/A"
                }}</strong>
              </div>
              <div
                v-if="freddyAnalysis.technical_indicators.moving_averages"
                class="tech-item"
              >
                <span>Moving Averages</span>
                <strong>
                  5:
                  {{
                    formatNumberValue(
                      freddyAnalysis.technical_indicators.moving_averages[
                        "5_day"
                      ]
                    )
                  }}, 50:
                  {{
                    formatNumberValue(
                      freddyAnalysis.technical_indicators.moving_averages[
                        "50_day"
                      ]
                    )
                  }}, 200:
                  {{
                    formatNumberValue(
                      freddyAnalysis.technical_indicators.moving_averages[
                        "200_day"
                      ]
                    )
                  }}
                </strong>
              </div>
            </div>

            <div v-if="hasSupportResistance" class="freddy-support">
              <div
                v-if="freddyAnalysis.support_resistance?.support_levels?.length"
                class="support-block"
              >
                <h5>Support</h5>
                <div class="level-chips">
                  <span
                    v-for="level in freddyAnalysis.support_resistance
                      .support_levels"
                    :key="`sup-${level}`"
                  >
                    {{ formatCurrencyValue(level) }}
                  </span>
                </div>
              </div>
              <div
                v-if="
                  freddyAnalysis.support_resistance?.resistance_levels?.length
                "
                class="support-block"
              >
                <h5>Resistance</h5>
                <div class="level-chips">
                  <span
                    v-for="level in freddyAnalysis.support_resistance
                      .resistance_levels"
                    :key="`res-${level}`"
                  >
                    {{ formatCurrencyValue(level) }}
                  </span>
                </div>
              </div>
            </div>

            <div v-if="freddyNewsEvents.length" class="freddy-news">
              <h5>Latest News (24h)</h5>
              <div class="freddy-news-list">
                <div
                  v-for="event in freddyNewsEvents"
                  :key="event.title"
                  class="freddy-news-item"
                >
                  <div class="news-title">{{ event.title }}</div>
                  <div class="news-meta">
                    <span
                      class="freddy-impact"
                      :class="event.impact || 'neutral'"
                      >{{ event.impact || "neutral" }}</span
                    >
                    <span v-if="event.date" class="news-date">{{
                      formatFreddyTimestamp(event.date)
                    }}</span>
                  </div>
                  <div v-if="event.description" class="news-desc">
                    {{ event.description }}
                  </div>
                </div>
              </div>
            </div>

            <div class="freddy-footer">
              <span v-if="freddyAnalysis.timestamp"
                >Updated
                {{ formatFreddyTimestamp(freddyAnalysis.timestamp) }}</span
              >
              <span v-if="freddyAnalysis.current_price"
                >Current price:
                {{ formatCurrencyValue(freddyAnalysis.current_price) }}</span
              >
            </div>
          </div>

          <div v-else class="freddy-empty">
            Click "Ask Freddy AI" to generate live guidance with the latest
            market data.
          </div>
        </div>
        <!-- End Freddy section -->
      </div>
      <!-- End prediction content -->

      <div v-else-if="error" class="error-state">
        <p>❌ {{ error }}</p>
        <button @click="loadPrediction" class="btn-retry">Retry</button>
      </div>

      <div v-else class="empty-state">
        <p>Click "Refresh Prediction" to generate ML analysis</p>
      </div>
    </div>
    <!-- End ML tab -->
  </div>
  <!-- End panel -->
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { api } from "../services/api";

const props = defineProps({
  symbol: {
    type: String,
    required: true,
  },
  timeframe: {
    type: String,
    default: "5m",
  },
  horizonMinutes: {
    type: Number,
    default: 180,
  },
});

// Tab state
const activeTab = ref("ta"); // 'ta' or 'ml'

// TA state
const taAnalysis = ref(null);
const isTALoading = ref(false);
const taError = ref(null);

// ML state
const prediction = ref(null);
const isLoading = ref(false);
const error = ref(null);

const defaultFreddyPrompt =
  "Give me details of the stock using actual values. Include any impactful news or events from the past day, state whether the bias is bullish, bearish, or hold, and provide precise targets and stop loss.";
const FREDDY_LOOKBACK_MINUTES = 360;

const freddyPromptInput = ref(defaultFreddyPrompt);
const freddyResponse = ref(null);
const isFreddyLoading = ref(false);
const freddyError = ref(null);
const useFreddyCache = ref(false);
const hasAutoTriggeredFreddy = ref(false);

// Load pure technical analysis
const loadTechnicalAnalysis = async () => {
  isTALoading.value = true;
  taError.value = null;

  try {
    const response = await fetch(
      `/api/recommendation/analysis?symbol=${props.symbol}&timeframe=${props.timeframe}&mode=ta_only`
    );
    const data = await response.json();

    if (data.error) {
      taError.value = data.message || "Technical analysis failed";
    } else {
      taAnalysis.value = data;
    }
  } catch (err) {
    taError.value = err.message || "Error loading technical analysis";
    console.error("Error loading TA:", err);
  } finally {
    isTALoading.value = false;
  }
};

const loadPrediction = async () => {
  isLoading.value = true;
  error.value = null;
  resetFreddyState(false);

  try {
    const data = await api.fetchComprehensivePrediction(
      props.symbol,
      props.timeframe,
      props.horizonMinutes
    );

    if (data) {
      prediction.value = data;
      // Don't auto-trigger Freddy - let user manually request it
      // This prevents 502 errors when Freddy AI is not configured
    } else {
      error.value = "Failed to load prediction";
    }
  } catch (err) {
    error.value = err.message || "Error loading prediction";
    console.error("Error loading comprehensive prediction:", err);
  } finally {
    isLoading.value = false;
  }
};

const formatDate = (dateStr) => {
  if (!dateStr) return "";
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
};

const formatTime = (dateStr) => {
  if (!dateStr) return "";
  const date = new Date(dateStr);
  return date.toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Asia/Kolkata",
  });
};

const formatPatternName = (pattern) => {
  return pattern
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
};

const getPatternType = (pattern) => {
  const bullish = ["hammer", "bullish_engulfing", "bullish_harami"];
  const bearish = [
    "hanging_man",
    "shooting_star",
    "bearish_engulfing",
    "bearish_harami",
  ];

  if (bullish.includes(pattern)) return "bullish";
  if (bearish.includes(pattern)) return "bearish";
  return "neutral";
};

const getRSIClass = (rsi) => {
  if (!rsi) return "";
  if (rsi > 70) return "overbought";
  if (rsi < 30) return "oversold";
  return "neutral";
};

const getMACDClass = (histogram) => {
  if (!histogram) return "";
  if (histogram > 0) return "bullish";
  return "bearish";
};

const formatVolume = (volume) => {
  if (!volume) return "N/A";
  if (volume >= 1000000) return (volume / 1000000).toFixed(2) + "M";
  if (volume >= 1000) return (volume / 1000).toFixed(2) + "K";
  return volume.toString();
};

const formatCurrencyValue = (value) => {
  const num = Number(value);
  if (!Number.isFinite(num)) {
    return "N/A";
  }
  return `₹${num.toFixed(2)}`;
};

const formatNumberValue = (value, decimals = 2) => {
  const num = Number(value);
  if (!Number.isFinite(num)) {
    return "N/A";
  }
  return num.toFixed(decimals);
};

const formatPercentageValue = (value) => {
  if (value === null || value === undefined) {
    return "N/A";
  }
  const num = Number(value);
  if (!Number.isFinite(num)) {
    return "N/A";
  }
  const normalized = Math.abs(num) <= 1 ? num * 100 : num;
  return `${normalized.toFixed(1)}%`;
};

const formatFreddyTimestamp = (isoString) => {
  if (!isoString) return "";
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) {
    return isoString;
  }
  return date.toLocaleString("en-IN", {
    timeZone: "Asia/Kolkata",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
};

const freddyAnalysis = computed(() => freddyResponse.value?.analysis || null);

const hasSupportResistance = computed(() => {
  const sr = freddyAnalysis.value?.support_resistance;
  if (!sr) return false;
  const hasSupport =
    Array.isArray(sr.support_levels) && sr.support_levels.length > 0;
  const hasResistance =
    Array.isArray(sr.resistance_levels) && sr.resistance_levels.length > 0;
  return hasSupport || hasResistance;
});

const freddyNewsEvents = computed(() => {
  const news = freddyAnalysis.value?.news_events;
  if (!Array.isArray(news)) {
    return [];
  }
  return news;
});

const freddyRecommendationClass = computed(() => {
  const recommendation = freddyAnalysis.value?.recommendation;
  if (!recommendation) return "";
  const normalized = recommendation.toLowerCase();
  if (normalized.includes("buy")) return "bullish";
  if (normalized.includes("sell")) return "bearish";
  return "neutral";
});

const resetFreddyState = (resetPrompt = false) => {
  freddyResponse.value = null;
  freddyError.value = null;
  isFreddyLoading.value = false;
  hasAutoTriggeredFreddy.value = false;
  if (resetPrompt) {
    freddyPromptInput.value = defaultFreddyPrompt;
    useFreddyCache.value = false;
  }
};

const resetFreddyPrompt = () => {
  freddyPromptInput.value = defaultFreddyPrompt;
};

const triggerFreddy = async ({ forceFresh = false } = {}) => {
  if (!props.symbol) {
    freddyError.value = "Select a symbol to run Freddy AI analysis.";
    return;
  }

  isFreddyLoading.value = true;
  freddyError.value = null;

  const finalPrompt =
    (freddyPromptInput.value || "").trim() || defaultFreddyPrompt;
  freddyPromptInput.value = finalPrompt;

  try {
    const data = await api.runFreddyAnalysis({
      symbol: props.symbol,
      timeframe: props.timeframe,
      prompt: finalPrompt,
      useCache: !forceFresh && useFreddyCache.value,
      lookbackMinutes: FREDDY_LOOKBACK_MINUTES,
    });

    if (!data) {
      freddyError.value = "Freddy AI did not return any analysis.";
      freddyResponse.value = null;
      return;
    }

    // Check if Freddy AI is disabled
    if (data.error === "freddy_disabled") {
      freddyError.value =
        data.message ||
        "Freddy AI is not configured. Please set API keys in .env to enable this feature.";
      freddyResponse.value = null;
      return;
    }

    if (!data.analysis) {
      freddyError.value =
        data.detail ||
        data.message ||
        "Freddy AI response was missing analysis.";
      freddyResponse.value = null;
      return;
    }

    freddyResponse.value = data;
    hasAutoTriggeredFreddy.value = true;
  } catch (err) {
    console.error("Error fetching Freddy AI insight:", err);
    freddyError.value =
      err.response?.data?.detail ||
      err.message ||
      "Failed to fetch Freddy AI insight.";
    freddyResponse.value = null;
  } finally {
    isFreddyLoading.value = false;
  }
};

// Auto-load when symbol or timeframe changes
watch(
  [() => props.symbol, () => props.timeframe],
  () => {
    if (props.symbol) {
      resetFreddyState(true);
      // Load TA by default (it's independent of ML)
      if (activeTab.value === "ta") {
        loadTechnicalAnalysis();
      } else {
        loadPrediction();
      }
    }
  },
  { immediate: true }
);

// Auto-load when switching tabs
watch(activeTab, (newTab) => {
  if (newTab === "ta" && !taAnalysis.value) {
    loadTechnicalAnalysis();
  } else if (newTab === "ml" && !prediction.value) {
    loadPrediction();
  }
});
</script>

<style scoped>
.comprehensive-prediction-panel {
  background: #18181b;
  border-radius: 8px;
  border: 1px solid #2b2b2e;
  padding: 24px;
  margin-top: 24px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  gap: 16px;
  flex-wrap: wrap;
}

.panel-header h3 {
  margin: 0;
  font-size: 20px;
  color: #efeff1;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.tab-selector {
  display: flex;
  gap: 8px;
  background: #1a1a1d;
  padding: 4px;
  border-radius: 6px;
  border: 1px solid #2b2b2e;
}

.tab-btn {
  padding: 8px 16px;
  background: transparent;
  border: none;
  border-radius: 4px;
  color: #999;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.tab-btn:hover {
  color: #efeff1;
  background: #2b2b2e;
}

.tab-btn.active {
  background: #2962ff;
  color: white;
}

.btn-refresh-prediction {
  padding: 10px 20px;
  background: linear-gradient(135deg, #2962ff, #1e4fd9);
  border: none;
  border-radius: 6px;
  color: white;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-refresh-prediction:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(41, 98, 255, 0.5);
}

.btn-refresh-prediction:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.loading-state {
  text-align: center;
  padding: 40px;
  color: #999;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #2b2b2e;
  border-top-color: #2962ff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 16px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.stock-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid #2b2b2e;
}

.stock-main {
  display: flex;
  align-items: center;
  gap: 12px;
}

.stock-main h2 {
  margin: 0;
  font-size: 28px;
  color: #efeff1;
  font-family: "SF Mono", "Monaco", "Cascadia Code", monospace;
}

.timeframe-badge {
  padding: 4px 10px;
  background: #2b2b2e;
  color: #efeff1;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}

.price-info {
  text-align: right;
}

.current-price {
  font-size: 32px;
  font-weight: 700;
  color: #26a69a;
  font-family: "SF Mono", "Monaco", "Cascadia Code", monospace;
}

.prediction-time {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

.targets-section {
  margin-bottom: 24px;
}

.date-header {
  font-size: 16px;
  color: #efeff1;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid #2b2b2e;
}

.targets-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.target-card {
  background: #1a1a1d;
  padding: 20px;
  border-radius: 8px;
  border: 2px solid #2b2b2e;
  text-align: center;
}

.target-card.target-1 {
  border-color: #26a69a;
}

.target-card.target-2 {
  border-color: #2962ff;
}

.target-card.stop-loss {
  border-color: #ff6b6b;
}

.target-label {
  font-size: 12px;
  color: #999;
  text-transform: uppercase;
  margin-bottom: 8px;
  font-weight: 600;
}

.target-value {
  font-size: 28px;
  font-weight: 700;
  color: #efeff1;
  margin-bottom: 12px;
  font-family: "SF Mono", "Monaco", "Cascadia Code", monospace;
}

.target-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
}

.reward {
  color: #26a69a;
}

.risk {
  color: #ff6b6b;
}

.rr-ratio {
  color: #999;
}

.patterns-section,
.indicators-section,
.confidence-section {
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid #2b2b2e;
}

.patterns-section h4,
.indicators-section h4,
.confidence-section h4 {
  margin: 0 0 16px 0;
  font-size: 16px;
  color: #efeff1;
}

.patterns-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.pattern-badge {
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}

.pattern-badge.bullish {
  background: rgba(38, 166, 154, 0.2);
  color: #26a69a;
  border: 1px solid rgba(38, 166, 154, 0.3);
}

.pattern-badge.bearish {
  background: rgba(255, 107, 107, 0.2);
  color: #ff6b6b;
  border: 1px solid rgba(255, 107, 107, 0.3);
}

.pattern-badge.neutral {
  background: rgba(149, 165, 166, 0.2);
  color: #95a5a6;
  border: 1px solid rgba(149, 165, 166, 0.3);
}

.no-patterns {
  color: #999;
  font-size: 14px;
  margin-bottom: 12px;
}

.pattern-sentiment {
  display: flex;
  align-items: center;
  gap: 8px;
}

.sentiment-label {
  color: #999;
  font-size: 14px;
}

.sentiment-value {
  font-weight: 600;
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 14px;
}

.sentiment-value.bullish {
  background: rgba(38, 166, 154, 0.2);
  color: #26a69a;
}

.sentiment-value.bearish {
  background: rgba(255, 107, 107, 0.2);
  color: #ff6b6b;
}

.sentiment-value.neutral {
  background: rgba(149, 165, 166, 0.2);
  color: #95a5a6;
}

.confidence {
  color: #999;
  font-size: 12px;
}

.indicators-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}

.indicator-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 12px;
  background: #1a1a1d;
  border-radius: 4px;
  border: 1px solid #2b2b2e;
}

.indicator-label {
  color: #999;
  font-size: 13px;
}

.indicator-value {
  font-weight: 600;
  font-size: 13px;
  color: #efeff1;
}

.indicator-value.overbought {
  color: #ff6b6b;
}

.indicator-value.oversold {
  color: #26a69a;
}

.indicator-value.bullish {
  color: #26a69a;
}

.indicator-value.bearish {
  color: #ff6b6b;
}

.confidence-bar {
  position: relative;
  height: 32px;
  background: #1a1a1d;
  border-radius: 4px;
  border: 1px solid #2b2b2e;
  overflow: hidden;
  margin-bottom: 12px;
}

.confidence-fill {
  height: 100%;
  background: linear-gradient(90deg, #2962ff, #26a69a);
  transition: width 0.3s;
}

.confidence-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-weight: 600;
  color: #efeff1;
  font-size: 14px;
}

.models-summary {
  color: #999;
  font-size: 13px;
}

.error-state {
  text-align: center;
  padding: 40px;
  color: #ff6b6b;
}

.btn-retry {
  padding: 8px 16px;
  background: #2962ff;
  border: none;
  border-radius: 4px;
  color: white;
  cursor: pointer;
  margin-top: 12px;
}

.empty-state {
  text-align: center;
  padding: 40px;
  color: #999;
}

.freddy-section {
  margin-bottom: 24px;
  padding: 20px;
  background: #1a1a1d;
  border-radius: 8px;
  border: 1px solid #2b2b2e;
}

.freddy-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.freddy-header h4 {
  margin: 0;
  font-size: 16px;
  color: #efeff1;
}

.freddy-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.freddy-cache-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #999;
}

.freddy-cache-toggle input {
  accent-color: #2962ff;
}

.freddy-reset {
  padding: 6px 12px;
  background: transparent;
  border: 1px solid #3a3a3e;
  border-radius: 4px;
  color: #999;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.freddy-reset:hover {
  color: #efeff1;
  border-color: #efeff1;
}

.freddy-helper {
  margin: 0 0 12px 0;
  font-size: 13px;
  color: #999;
}

.freddy-input-row {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.freddy-input-row textarea {
  flex: 1 1 420px;
  min-height: 96px;
  background: #18181b;
  border: 1px solid #2b2b2e;
  border-radius: 6px;
  color: #efeff1;
  padding: 12px;
  resize: vertical;
  font-size: 13px;
  line-height: 1.5;
}

.freddy-input-row textarea:focus {
  border-color: #2962ff;
  outline: none;
}

.freddy-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 200px;
}

.btn-freddy {
  padding: 10px 16px;
  background: linear-gradient(135deg, #00bcd4, #2962ff);
  border: none;
  border-radius: 6px;
  color: white;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 2px 8px rgba(41, 98, 255, 0.35);
}

.btn-freddy:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(0, 188, 212, 0.35);
}

.btn-freddy:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.freddy-meta {
  font-size: 11px;
  color: #777;
}

.freddy-error {
  margin-top: 12px;
  padding: 12px;
  border-radius: 6px;
  border: 1px solid rgba(255, 107, 107, 0.3);
  background: rgba(255, 107, 107, 0.12);
  color: #ff6b6b;
  font-size: 13px;
}

.freddy-loading {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  color: #999;
  font-size: 13px;
}

.freddy-results {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 12px;
}

.freddy-metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
}

.freddy-metric-card {
  background: #18181b;
  border: 1px solid #2b2b2e;
  border-radius: 6px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.freddy-metric-card .metric-label {
  font-size: 12px;
  color: #999;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.freddy-metric-card .metric-value {
  font-size: 18px;
  font-weight: 600;
  color: #efeff1;
}

.freddy-recommendation.bullish {
  color: #26a69a;
}

.freddy-recommendation.bearish {
  color: #ff6b6b;
}

.freddy-recommendation.neutral {
  color: #f5c26b;
}

.freddy-summary {
  background: #18181b;
  border: 1px solid #2b2b2e;
  border-radius: 6px;
  padding: 14px;
  color: #d1d1d4;
  font-size: 14px;
  line-height: 1.5;
}

.freddy-tech {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.tech-item {
  background: #18181b;
  border: 1px solid #2b2b2e;
  border-radius: 6px;
  padding: 12px;
  min-width: 150px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
  color: #efeff1;
}

.freddy-support {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.support-block {
  flex: 1 1 200px;
  background: #18181b;
  border: 1px solid #2b2b2e;
  border-radius: 6px;
  padding: 12px;
}

.support-block h5 {
  margin: 0 0 8px 0;
  font-size: 13px;
  color: #efeff1;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.level-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.level-chips span {
  padding: 6px 10px;
  background: #2b2b2e;
  border-radius: 4px;
  color: #efeff1;
  font-size: 12px;
}

.freddy-news {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.freddy-news h5 {
  margin: 0;
  font-size: 14px;
  color: #efeff1;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.freddy-news-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.freddy-news-item {
  background: #18181b;
  border: 1px solid #2b2b2e;
  border-radius: 6px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.news-title {
  font-size: 14px;
  font-weight: 600;
  color: #efeff1;
}

.news-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: #999;
  text-transform: capitalize;
}

.freddy-impact {
  font-weight: 600;
}

.freddy-impact.positive {
  color: #26a69a;
}

.freddy-impact.negative {
  color: #ff6b6b;
}

.freddy-impact.neutral {
  color: #f5c26b;
}

.news-desc {
  font-size: 13px;
  color: #d1d1d4;
  line-height: 1.45;
}

.news-date {
  font-size: 12px;
  color: #777;
}

.freddy-footer {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 12px;
  color: #777;
}

.freddy-empty {
  font-size: 13px;
  color: #777;
  padding: 12px 0;
}

@media (max-width: 768px) {
  .targets-grid {
    grid-template-columns: 1fr;
  }

  .stock-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .price-info {
    text-align: left;
  }

  .freddy-input-row {
    flex-direction: column;
  }

  .freddy-actions {
    width: 100%;
  }

  .btn-freddy {
    width: 100%;
  }
}

/* TA-specific styles */
.ta-tab-content,
.ml-tab-content {
  margin-top: 16px;
}

.ta-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid #2b2b2e;
}

.ta-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.data-badge {
  padding: 4px 10px;
  background: #26a69a;
  color: white;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
}

.ta-price {
  text-align: right;
}

.price-change {
  font-size: 14px;
  font-weight: 600;
  margin-top: 4px;
}

.price-change.positive {
  color: #26a69a;
}

.price-change.negative {
  color: #ff6b6b;
}

.ta-recommendation {
  display: grid;
  grid-template-columns: 2fr 3fr;
  gap: 16px;
  margin-bottom: 24px;
}

.recommendation-card {
  padding: 20px;
  border-radius: 8px;
  text-align: center;
  border: 2px solid;
}

.recommendation-card.buy,
.recommendation-card.strong.buy {
  background: rgba(38, 166, 154, 0.1);
  border-color: #26a69a;
}

.recommendation-card.sell,
.recommendation-card.strong.sell {
  background: rgba(255, 107, 107, 0.1);
  border-color: #ff6b6b;
}

.recommendation-card.hold {
  background: rgba(245, 194, 107, 0.1);
  border-color: #f5c26b;
}

.rec-label {
  font-size: 12px;
  color: #999;
  text-transform: uppercase;
  margin-bottom: 8px;
}

.rec-action {
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 8px;
  color: #efeff1;
}

.rec-confidence {
  font-size: 14px;
  color: #999;
}

.recommendation-details {
  display: flex;
  flex-direction: column;
  gap: 12px;
  justify-content: center;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  padding: 12px;
  background: #1a1a1d;
  border-radius: 6px;
  border: 1px solid #2b2b2e;
}

.detail-item .label {
  color: #999;
  font-size: 13px;
}

.detail-item .value {
  color: #efeff1;
  font-weight: 600;
  font-size: 14px;
}

.ta-indicators-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.ta-indicator {
  background: #1a1a1d;
  border: 1px solid #2b2b2e;
  border-radius: 6px;
  padding: 16px;
  text-align: center;
}

.indicator-title {
  font-size: 12px;
  color: #999;
  text-transform: uppercase;
  margin-bottom: 8px;
}

.indicator-value {
  font-size: 20px;
  font-weight: 700;
  color: #efeff1;
  margin-bottom: 6px;
}

.indicator-signal {
  font-size: 11px;
  color: #999;
  text-transform: capitalize;
}

.ta-levels {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.level-card {
  padding: 16px;
  border-radius: 6px;
  border: 2px solid;
  text-align: center;
}

.level-card.resistance {
  border-color: #ff6b6b;
  background: rgba(255, 107, 107, 0.05);
}

.level-card.support {
  border-color: #26a69a;
  background: rgba(38, 166, 154, 0.05);
}

.level-card.stop-loss {
  border-color: #ff6b6b;
  background: rgba(255, 107, 107, 0.08);
}

.level-card.take-profit {
  border-color: #26a69a;
  background: rgba(38, 166, 154, 0.08);
}

.level-label {
  font-size: 11px;
  color: #999;
  text-transform: uppercase;
  margin-bottom: 6px;
}

.level-value {
  font-size: 20px;
  font-weight: 700;
  color: #efeff1;
}

.ta-footer {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #2b2b2e;
  font-size: 12px;
  color: #26a69a;
  text-align: center;
}
</style>
