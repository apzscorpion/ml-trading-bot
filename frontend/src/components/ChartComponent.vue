<template>
  <div class="chart-wrapper">
    <div ref="chartContainer" class="chart-container"></div>

    <!-- Custom Tooltip -->
    <div ref="tooltip" class="chart-tooltip" v-show="tooltipData.visible">
      <div class="tooltip-header">
        <span class="tooltip-time">{{ tooltipData.time }}</span>
      </div>

      <!-- Candle Data -->
      <div v-if="tooltipData.candle" class="tooltip-section">
        <div class="tooltip-label">Price (OHLC)</div>
        <div class="tooltip-grid">
          <div class="tooltip-item">
            <span class="label">Open:</span>
            <span class="value">₹{{ tooltipData.candle.open }}</span>
          </div>
          <div class="tooltip-item">
            <span class="label">High:</span>
            <span class="value high">₹{{ tooltipData.candle.high }}</span>
          </div>
          <div class="tooltip-item">
            <span class="label">Low:</span>
            <span class="value low">₹{{ tooltipData.candle.low }}</span>
          </div>
          <div class="tooltip-item">
            <span class="label">Close:</span>
            <span
              :class="[
                'value',
                tooltipData.candle.change >= 0 ? 'positive' : 'negative',
              ]"
            >
              ₹{{ tooltipData.candle.close }}
            </span>
          </div>
        </div>
        <div v-if="tooltipData.candle.volume" class="tooltip-item">
          <span class="label">Volume:</span>
          <span class="value">{{
            formatVolume(tooltipData.candle.volume)
          }}</span>
        </div>
      </div>

      <!-- Prediction Data -->
      <div
        v-if="tooltipData.prediction"
        class="tooltip-section prediction-section"
      >
        <div class="tooltip-label">🔮 Prediction</div>
        <div class="tooltip-item">
          <span class="label">Predicted:</span>
          <span class="value prediction"
            >₹{{ tooltipData.prediction.price }}</span
          >
        </div>
        <div v-if="tooltipData.prediction.confidence" class="tooltip-item">
          <span class="label">Confidence:</span>
          <span 
            :class="[
              'value',
              tooltipData.prediction.confidence > 0.7 ? 'positive' : 
              tooltipData.prediction.confidence > 0.5 ? '' : 'negative'
            ]"
          >
            {{ (tooltipData.prediction.confidence * 100).toFixed(1) }}%
          </span>
        </div>
        <div v-if="tooltipData.prediction.quality" class="tooltip-item">
          <span class="label">Quality:</span>
          <span 
            :class="[
              'value',
              tooltipData.prediction.quality === 'high' ? 'positive' : 
              tooltipData.prediction.quality === 'medium' ? '' : 'negative'
            ]"
          >
            {{ tooltipData.prediction.quality === 'high' ? '✓ High' : 
               tooltipData.prediction.quality === 'medium' ? '○ Medium' : '✗ Low' }}
          </span>
        </div>
        <div v-if="tooltipData.prediction.actual" class="tooltip-item">
          <span class="label">Actual:</span>
          <span class="value">₹{{ tooltipData.prediction.actual }}</span>
        </div>
        <div v-if="tooltipData.prediction.error" class="tooltip-item">
          <span class="label">Error:</span>
          <span
            :class="[
              'value',
              Math.abs(tooltipData.prediction.error) < 1
                ? 'positive'
                : 'negative',
            ]"
          >
            {{ tooltipData.prediction.error > 0 ? "+" : ""
            }}{{ tooltipData.prediction.error.toFixed(2) }}%
          </span>
        </div>
      </div>

      <!-- Historical Prediction -->
      <div
        v-if="tooltipData.historical"
        class="tooltip-section historical-section"
      >
        <div class="tooltip-label">📊 Historical Prediction</div>
        <div class="tooltip-item">
          <span class="label">Predicted:</span>
          <span class="value">₹{{ tooltipData.historical.predicted }}</span>
        </div>
        <div class="tooltip-item">
          <span class="label">Actual:</span>
          <span class="value">₹{{ tooltipData.historical.actual }}</span>
        </div>
        <div class="tooltip-item">
          <span class="label">Accuracy:</span>
          <span
            :class="[
              'value',
              tooltipData.historical.accuracy > 95 ? 'positive' : 'negative',
            ]"
          >
            {{ tooltipData.historical.accuracy.toFixed(1) }}%
          </span>
        </div>
      </div>
    </div>

    <div v-if="loading" class="loading-overlay">
      <div class="spinner"></div>
      <p>Loading chart data...</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from "vue";
import { createChart } from "lightweight-charts";

const props = defineProps({
  candles: {
    type: Array,
    default: () => [],
  },
  predictions: {
    type: Array,
    default: () => [],
  },
  historicalPredictions: {
    type: Array,
    default: () => [],
  },
  loading: {
    type: Boolean,
    default: false,
  },
  timeframe: {
    type: String,
    default: "5m",
  },
  predictionHistory: {
    type: Array,
    default: () => [],
  },
  showPredictionHistory: {
    type: Boolean,
    default: false,
  },
});

const chartContainer = ref(null);
const tooltip = ref(null);
let chart = null;
let candlestickSeries = null;
let blueLineSeries = null;
let redLineSeries = null;
let redAreaSeries = null; // Area series for prediction
let blackLineSeries = null;
let historySeriesMap = {}; // Map of prediction type -> line series for history
let isLoadingMore = false;
let isLoadingNewer = false;
let lastCandleTime = null; // Track last candle timestamp for live updates
let debounceTimer = null;
let loadedRanges = []; // Track loaded time ranges to avoid duplicate fetches
const DEBOUNCE_DELAY = 300; // 300ms debounce for rapid panning
const MIN_EMPTY_SPACE_MS = 30 * 1000; // 30 seconds threshold - load data when scrolling into empty space

const emit = defineEmits(["loadMoreHistory", "loadNewerHistory", "predictionRejected"]);

// Tooltip state
const tooltipData = ref({
  visible: false,
  time: "",
  candle: null,
  prediction: null,
  historical: null,
});

/**
 * Validate predictions before plotting
 * @param {Array} predictions - Prediction points {ts, price}
 * @param {Array} candleData - Actual candle data for reference
 * @returns {Object} {valid: boolean, reason: string}
 */
const validatePredictions = (predictions, candleData) => {
  if (!predictions || predictions.length === 0) {
    return { valid: false, reason: 'Empty prediction series' };
  }
  
  // Get latest close price from candles
  const latestClose = candleData && candleData.length > 0
    ? candleData[candleData.length - 1].close
    : null;
  
  if (!latestClose || latestClose <= 0) {
    return { valid: false, reason: 'Invalid reference price' };
  }
  
  // Extract prediction prices
  const prices = predictions.map(p => p.price);
  
  // Check for NaN or Inf
  if (prices.some(p => !Number.isFinite(p))) {
    return { valid: false, reason: 'NaN or Inf values detected' };
  }
  
  // Check for negative prices
  if (prices.some(p => p < 0)) {
    return { valid: false, reason: 'Negative prices detected' };
  }
  
  // Check maximum drift from reference
  const maxPrice = Math.max(...prices);
  const minPrice = Math.min(...prices);
  const maxDriftUp = ((maxPrice - latestClose) / latestClose) * 100;
  const maxDriftDown = ((latestClose - minPrice) / latestClose) * 100;
  
  const MAX_ALLOWED_DRIFT = 10.0; // 10% threshold
  
  if (maxDriftUp > MAX_ALLOWED_DRIFT) {
    return { 
      valid: false, 
      reason: `Excessive upward drift: ${maxDriftUp.toFixed(1)}% (max: ${MAX_ALLOWED_DRIFT}%)` 
    };
  }
  
  if (maxDriftDown > MAX_ALLOWED_DRIFT) {
    return { 
      valid: false, 
      reason: `Excessive downward drift: ${maxDriftDown.toFixed(1)}% (max: ${MAX_ALLOWED_DRIFT}%)` 
    };
  }
  
  // Check step-wise changes
  for (let i = 1; i < prices.length; i++) {
    const stepChange = Math.abs((prices[i] - prices[i-1]) / prices[i-1]) * 100;
    if (stepChange > 5.0) { // 5% max step change
      return { 
        valid: false, 
        reason: `Excessive step change: ${stepChange.toFixed(1)}% at index ${i}` 
      };
    }
  }
  
  return { valid: true, reason: null };
};

/**
 * Get color for prediction type
 * @param {string} type - Prediction type
 * @returns {string} Color hex code
 */
const getPredictionTypeColor = (type) => {
  const colorMap = {
    technical: "#26a69a", // teal
    ml: "#2962ff", // blue
    lstm: "#ff6b6b", // red
    transformer: "#feca57", // yellow
    deep_learning: "#ff6b6b", // red (same as LSTM for now)
    ensemble: "#6c5ce7", // purple
    all: "#6c5ce7", // purple
  };
  return colorMap[type] || "#999999"; // default gray
};

/**
 * Convert timeframe string to seconds
 * @param {string} timeframe - Timeframe string (e.g., "5m", "15m", "1h")
 * @returns {number} Interval in seconds
 */
const timeframeToSeconds = (timeframe) => {
  const timeframeMap = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
    "5d": 432000,
    "1wk": 604800,
    "1mo": 2592000,
    "3mo": 7776000,
  };
  return timeframeMap[timeframe] || 300; // Default to 5m (300s)
};

/**
 * Interpolate prediction data to create smooth points at regular intervals
 * @param {Array} predictions - Array of prediction points with ts and price
 * @param {number} intervalSeconds - Interval between interpolated points in seconds
 * @returns {Array} Interpolated data points
 */
const interpolatePredictions = (predictions, intervalSeconds) => {
  if (!predictions || predictions.length === 0) {
    return [];
  }

  if (predictions.length === 1) {
    // Parse ISO timestamp and convert to Unix timestamp (UTC)
    const date = new Date(predictions[0].ts);
    return [
      {
        time: Math.floor(date.getTime() / 1000),
        value: predictions[0].price,
      },
    ];
  }

  const interpolated = [];

  for (let i = 0; i < predictions.length - 1; i++) {
    const current = predictions[i];
    const next = predictions[i + 1];

    // Parse ISO timestamps and convert to Unix timestamps (UTC)
    const currentDate = new Date(current.ts);
    const nextDate = new Date(next.ts);
    const currentTime = Math.floor(currentDate.getTime() / 1000);
    const nextTime = Math.floor(nextDate.getTime() / 1000);
    const currentPrice = current.price;
    const nextPrice = next.price;

    // Add the current point (with marker)
    interpolated.push({
      time: currentTime,
      value: currentPrice,
    });

    // Calculate how many intervals fit between current and next
    const timeDiff = nextTime - currentTime;
    const numIntervals = Math.floor(timeDiff / intervalSeconds);

    // Interpolate points between current and next (without explicit markers)
    // The line will be smooth but only endpoint markers will be prominent
    if (numIntervals > 1) {
      for (let j = 1; j < numIntervals; j++) {
        const ratio = j / numIntervals;
        const interpolatedTime = currentTime + j * intervalSeconds;
        const interpolatedPrice =
          currentPrice + (nextPrice - currentPrice) * ratio;

        interpolated.push({
          time: interpolatedTime,
          value: interpolatedPrice,
        });
      }
    }
  }

  // Add the last point (with marker)
  const lastPrediction = predictions[predictions.length - 1];
  const lastDate = new Date(lastPrediction.ts);
  interpolated.push({
    time: Math.floor(lastDate.getTime() / 1000),
    value: lastPrediction.price,
  });

  return interpolated;
};

const initChart = () => {
  if (!chartContainer.value) return;

  // Create chart with more compact, investing.com-like styling
  chart = createChart(chartContainer.value, {
    width: chartContainer.value.clientWidth,
    height: chartContainer.value.clientHeight || 700, // Use container height or default to 700
    layout: {
      background: { color: "#0f172a" }, // Darker background like investing.com
      textColor: "#cbd5e1", // Lighter text for better contrast
      fontSize: 12, // Smaller font for compact look
    },
    grid: {
      vertLines: { 
        color: "rgba(148, 163, 184, 0.1)", // Subtle grid lines
        visible: true,
      },
      horzLines: { 
        color: "rgba(148, 163, 184, 0.1)",
        visible: true,
      },
    },
    crosshair: {
      mode: 1,
      vertLine: {
        color: "rgba(148, 163, 184, 0.5)",
        width: 1,
        style: 2, // Dashed
      },
      horzLine: {
        color: "rgba(148, 163, 184, 0.5)",
        width: 1,
        style: 2, // Dashed
      },
    },
    rightPriceScale: {
      borderColor: "rgba(148, 163, 184, 0.2)",
      scaleMargins: {
        top: 0.1,
        bottom: 0.1,
      },
    },
    leftPriceScale: {
      visible: false, // Hide left scale for cleaner look
    },
    timeScale: {
      borderColor: "rgba(148, 163, 184, 0.2)",
      timeVisible: true,
      secondsVisible: false,
      timezone: "Asia/Kolkata",
      rightOffset: 0,
      barSpacing: 2, // Tighter spacing for more candles visible
      minBarSpacing: 0.5,
      fixLeftEdge: true,
      fixRightEdge: false, // Allow panning to see future predictions
    },
  });

  // Ensure timezone is applied (applyOptions can be used to update settings)
  chart.timeScale().applyOptions({
    timezone: "Asia/Kolkata",
  });

  // Add candlestick series with investing.com-like colors
  candlestickSeries = chart.addCandlestickSeries({
    upColor: "#22c55e", // Green for up candles (like investing.com)
    downColor: "#ef4444", // Red for down candles
    borderUpColor: "#22c55e",
    borderDownColor: "#ef4444",
    wickUpColor: "#22c55e",
    wickDownColor: "#ef4444",
    priceFormat: {
      type: "price",
      precision: 2,
      minMove: 0.01,
    },
  });

  // Blue line - Actual prices
  blueLineSeries = chart.addLineSeries({
    color: "#2962FF",
    lineWidth: 2,
    title: "Actual",
    lastValueVisible: true,
    priceLineVisible: true,
  });

  // Red area - Prediction area fill (underneath)
  redAreaSeries = chart.addAreaSeries({
    topColor: "rgba(255, 107, 107, 0.4)",
    bottomColor: "rgba(255, 107, 107, 0.05)",
    lineColor: "rgba(255, 107, 107, 0.8)",
    lineWidth: 2,
    priceLineVisible: false,
    lastValueVisible: false,
  });

  // Red line - Current prediction (simple clean line)
  redLineSeries = chart.addLineSeries({
    color: "#FF6B6B",
    lineWidth: 2,
    title: "Predicted",
    lastValueVisible: true,
    priceLineVisible: false,
    lineType: 0, // Simple line
    pointMarkersVisible: false, // Hide markers for cleaner look
  });

  // Black line - Historical predictions
  blackLineSeries = chart.addLineSeries({
    color: "#888888",
    lineWidth: 1,
    title: "Historical Prediction",
    lastValueVisible: false,
    priceLineVisible: false,
    lineStyle: 2, // Dashed
  });

  // Subscribe to visible time range change (fires on scroll/pan)
  chart.timeScale().subscribeVisibleTimeRangeChange(handleVisibleRangeChange);

  // Also subscribe to logical range change for zoom events
  chart
    .timeScale()
    .subscribeVisibleLogicalRangeChange(handleVisibleRangeChange);

  // Subscribe to crosshair move for tooltip
  chart.subscribeCrosshairMove(handleCrosshairMove);
};

// Handle crosshair move for tooltip
const handleCrosshairMove = (param) => {
  if (!param.time || !tooltip.value) {
    tooltipData.value.visible = false;
    return;
  }

  const time = param.time;
  const formattedTime = formatTooltipTime(time);

  // Get data from all series
  const candleData = param.seriesData.get(candlestickSeries);
  const predictionData = param.seriesData.get(redLineSeries);
  const historicalData = param.seriesData.get(blackLineSeries);
  const actualData = param.seriesData.get(blueLineSeries);

  // Update tooltip data
  tooltipData.value = {
    visible: true,
    time: formattedTime,
    candle: candleData
      ? {
          open: candleData.open?.toFixed(2),
          high: candleData.high?.toFixed(2),
          low: candleData.low?.toFixed(2),
          close: candleData.close?.toFixed(2),
          volume: candleData.volume || null,
          change: candleData.close - candleData.open,
        }
      : null,
    prediction: predictionData
      ? {
          price: predictionData.value?.toFixed(2),
          confidence:
            props.predictions.length > 0
              ? props.predictions[0].confidence || 0.5
              : null,
          actual: actualData?.value?.toFixed(2),
          error:
            actualData && predictionData
              ? ((predictionData.value - actualData.value) / actualData.value) *
                100
              : null,
        }
      : null,
    historical:
      historicalData && actualData
        ? {
            predicted: historicalData.value?.toFixed(2),
            actual: actualData.value?.toFixed(2),
            accuracy:
              100 -
              Math.abs(
                ((historicalData.value - actualData.value) / actualData.value) *
                  100
              ),
          }
        : null,
  };

  // Position tooltip
  positionTooltip(param.point);
};

// Format timestamp helper functions
const formatTimestamp = (timestamp, includeTimezone = true) => {
  /**
   * Format ISO timestamp string to human-readable IST format
   * @param {string} timestamp - ISO timestamp string (e.g., "2025-11-03T15:25:00+05:30")
   * @param {boolean} includeTimezone - Whether to include timezone label
   * @returns {string} Formatted string (e.g., "November 3, 2025, 3:25 PM (IST)")
   */
  const date = new Date(timestamp);

  const options = {
    timeZone: "Asia/Kolkata",
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  };

  const formatted = date.toLocaleString("en-IN", options);
  return includeTimezone ? `${formatted} (IST)` : formatted;
};

const formatTimestampUTC = (timestamp, includeTimezone = true) => {
  /**
   * Format ISO timestamp string to human-readable UTC format
   * @param {string} timestamp - ISO timestamp string
   * @param {boolean} includeTimezone - Whether to include timezone label
   * @returns {string} Formatted string (e.g., "November 3, 2025, 9:55 AM (UTC)")
   */
  const date = new Date(timestamp);

  const options = {
    timeZone: "UTC",
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  };

  const formatted = date.toLocaleString("en-GB", options);
  return includeTimezone ? `${formatted} (UTC)` : formatted;
};

// Format time for tooltip (Unix timestamp in seconds, UTC)
const formatTooltipTime = (time) => {
  // time is Unix timestamp in seconds (UTC)
  // Convert to IST for display
  const date = new Date(time * 1000);
  const options = {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
    timeZone: "Asia/Kolkata",
  };
  return date.toLocaleString("en-IN", options);
};

// Format volume
const formatVolume = (volume) => {
  if (volume >= 10000000) return (volume / 10000000).toFixed(2) + " Cr";
  if (volume >= 100000) return (volume / 100000).toFixed(2) + " L";
  if (volume >= 1000) return (volume / 1000).toFixed(2) + " K";
  return volume.toFixed(0);
};

// Position tooltip near cursor
const positionTooltip = (point) => {
  if (!tooltip.value || !point) return;

  const container = chartContainer.value;
  const tooltipEl = tooltip.value;

  const containerRect = container.getBoundingClientRect();
  const tooltipRect = tooltipEl.getBoundingClientRect();

  let left = point.x + 20;
  let top = point.y + 20;

  // Keep tooltip within bounds
  if (left + tooltipRect.width > containerRect.width) {
    left = point.x - tooltipRect.width - 20;
  }

  if (top + tooltipRect.height > containerRect.height) {
    top = point.y - tooltipRect.height - 20;
  }

  tooltipEl.style.left = left + "px";
  tooltipEl.style.top = top + "px";
};

// Helper function to check if a time range is already loaded
const isRangeLoaded = (startTime, endTime) => {
  if (loadedRanges.length === 0) return false;

  return loadedRanges.some((range) => {
    return startTime >= range.from && endTime <= range.to;
  });
};

// Helper function to update loaded ranges
const updateLoadedRanges = () => {
  if (props.candles.length === 0) {
    loadedRanges = [];
    return;
  }

  const oldestTimestamp = new Date(props.candles[0].start_ts).getTime();
  const newestTimestamp = new Date(
    props.candles[props.candles.length - 1].start_ts
  ).getTime();

  // Merge with existing ranges if they overlap
  loadedRanges = [{ from: oldestTimestamp, to: newestTimestamp }];
};

const handleVisibleRangeChange = (timeRange) => {
  if (props.candles.length === 0) {
    return;
  }

  // Debounce rapid panning/zooming
  if (debounceTimer) {
    clearTimeout(debounceTimer);
  }

  debounceTimer = setTimeout(() => {
    performRangeCheck();
  }, DEBOUNCE_DELAY);
};

const performRangeCheck = () => {
  if (isLoadingMore || isLoadingNewer || props.candles.length === 0) {
    return;
  }

  if (!chart) return;

  // Get the visible time range from the chart
  const timeScale = chart.timeScale();
  const visibleRange = timeScale.getVisibleRange();

  if (!visibleRange || !visibleRange.from || !visibleRange.to) {
    return;
  }

  // Convert visible range to timestamps (chart uses Unix timestamps in seconds)
  const visibleStartTime = visibleRange.from * 1000; // Convert from seconds to milliseconds
  const visibleEndTime = visibleRange.to * 1000;
  const visibleStartDate = new Date(visibleStartTime);
  const visibleEndDate = new Date(visibleEndTime);

  // Get the oldest and newest candle timestamps we have loaded
  const oldestCandle = props.candles[0];
  const newestCandle = props.candles[props.candles.length - 1];

  if (
    !oldestCandle ||
    !oldestCandle.start_ts ||
    !newestCandle ||
    !newestCandle.start_ts
  ) {
    return;
  }

  const oldestTimestamp = new Date(oldestCandle.start_ts).getTime();
  const newestTimestamp = new Date(newestCandle.start_ts).getTime();

  console.log("📊 Visible range changed:", {
    visibleStart: visibleStartDate.toISOString(),
    visibleEnd: visibleEndDate.toISOString(),
    oldestLoaded: new Date(oldestTimestamp).toISOString(),
    newestLoaded: new Date(newestTimestamp).toISOString(),
    totalCandles: props.candles.length,
  });

  // Check if user scrolled backwards (into empty space on the left)
  if (visibleStartTime < oldestTimestamp) {
    const emptySpaceMs = oldestTimestamp - visibleStartTime;

    if (emptySpaceMs >= MIN_EMPTY_SPACE_MS) {
      // Check if we're already loading or have this range
      const needsFetch =
        visibleStartTime < oldestTimestamp &&
        !isRangeLoaded(visibleStartTime, oldestTimestamp);

      if (needsFetch) {
        console.log("📜 User scrolled BACKWARDS - loading older data...", {
          visibleStart: visibleStartDate.toISOString(),
          oldestLoaded: new Date(oldestTimestamp).toISOString(),
          emptySpaceMs: emptySpaceMs,
          emptySpaceMinutes: (emptySpaceMs / (60 * 1000)).toFixed(1),
        });

        isLoadingMore = true;

        // Emit event to load more history BEFORE the oldest timestamp
        emit("loadMoreHistory", { from_ts: oldestCandle.start_ts });

        // Reset flag after a delay to allow the request to complete
        setTimeout(() => {
          isLoadingMore = false;
        }, 3000);
      }
    }
  }

  // Check if user scrolled forwards (into empty space on the right) - fetch newer data
  if (visibleEndTime > newestTimestamp) {
    const emptySpaceMs = visibleEndTime - newestTimestamp;

    if (emptySpaceMs >= MIN_EMPTY_SPACE_MS) {
      // Check if we're already loading or have this range
      const needsFetch =
        visibleEndTime > newestTimestamp &&
        !isRangeLoaded(newestTimestamp, visibleEndTime);

      if (needsFetch) {
        console.log("📜 User scrolled FORWARDS - loading newer data...", {
          visibleEnd: visibleEndDate.toISOString(),
          newestLoaded: new Date(newestTimestamp).toISOString(),
          emptySpaceMs: emptySpaceMs,
          emptySpaceMinutes: (emptySpaceMs / (60 * 1000)).toFixed(1),
        });

        isLoadingNewer = true;

        // Emit event to load newer history AFTER the newest timestamp
        emit("loadNewerHistory", { to_ts: newestCandle.start_ts });

        // Reset flag after a delay to allow the request to complete
        setTimeout(() => {
          isLoadingNewer = false;
        }, 3000);
      }
    }
  }
};

const updateChart = () => {
  if (!chart || !candlestickSeries) {
    console.log("⏸️ Chart not ready, skipping update");
    return;
  }

  // Guard: Check if chart container still exists in DOM
  if (!chartContainer.value || !chartContainer.value.parentElement) {
    console.log("⏸️ Chart container not in DOM, skipping update");
    return;
  }

  // Update loaded ranges when candles change
  updateLoadedRanges();

  console.log("🔄 Updating chart with", props.candles.length, "candles");

  // Initialize uniqueData at function scope
  let uniqueData = [];

  // Update candlestick data
  if (props.candles.length > 0) {
    const candleData = props.candles
      .filter((c) => {
        // Validate candle data before adding to chart
        return (
          c &&
          c.start_ts &&
          typeof c.open === "number" &&
          isFinite(c.open) &&
          typeof c.high === "number" &&
          isFinite(c.high) &&
          typeof c.low === "number" &&
          isFinite(c.low) &&
          typeof c.close === "number" &&
          isFinite(c.close) &&
          c.high >= c.low &&
          c.close >= c.low &&
          c.close <= c.high &&
          c.open >= c.low &&
          c.open <= c.high
        );
      })
      .map((c) => {
        // Parse ISO timestamp string with timezone info
        // The backend sends IST times in ISO format (e.g., "2025-11-03T13:15:00+05:30")
        // JavaScript Date.parse() correctly interprets the timezone
        const date = new Date(c.start_ts);

        // Verify the date was parsed correctly
        if (isNaN(date.getTime())) {
          console.warn("Invalid timestamp:", c.start_ts);
          return null;
        }

        // Convert to Unix timestamp (seconds since epoch, UTC)
        // getTime() returns milliseconds in UTC, so we divide by 1000
        const unixTime = Math.floor(date.getTime() / 1000);

        // Skip invalid timestamps
        if (unixTime <= 0) {
          return null;
        }

        return {
          time: unixTime,
          open: c.open,
          high: c.high,
          low: c.low,
          close: c.close,
        };
      })
      .filter((item) => item !== null); // Remove invalid entries

    // Deduplicate by time and sort ascending
    uniqueData = Array.from(
      new Map(candleData.map((item) => [item.time, item])).values()
    ).sort((a, b) => a.time - b.time);

    if (uniqueData.length > 0) {
      // Log the time range of candles being displayed on the chart
      const firstTime = uniqueData[0].time;
      const lastTime = uniqueData[uniqueData.length - 1].time;
      // Log candle times with proper formatting
      const firstCandleDate = new Date(firstTime * 1000);
      const lastCandleDate = new Date(lastTime * 1000);

      console.log("⏰ Chart Candle Times:", {
        firstCandle: firstCandleDate.toLocaleString("en-IN", {
          timeZone: "Asia/Kolkata",
          dateStyle: "short",
          timeStyle: "medium",
        }),
        firstCandleFormatted: formatTimestamp(
          new Date(firstTime * 1000).toISOString()
        ),
        lastCandle: lastCandleDate.toLocaleString("en-IN", {
          timeZone: "Asia/Kolkata",
          dateStyle: "short",
          timeStyle: "medium",
        }),
        lastCandleFormatted: formatTimestamp(
          new Date(lastTime * 1000).toISOString()
        ),
        firstUnix: firstTime,
        lastUnix: lastTime,
        totalCandles: uniqueData.length,
        timezone: "Asia/Kolkata",
        note: "X-axis should display IST times (3:25 PM), not UTC (9:55 AM)",
      });

      console.log(`✅ Setting ${uniqueData.length} candles to chart`);
      candlestickSeries.setData(uniqueData);

      // Ensure timezone is applied after data is set
      // This ensures x-axis displays IST times correctly
      chart.timeScale().applyOptions({
        timezone: "Asia/Kolkata",
      });
    } else {
      console.warn("⚠️ No valid candle data to display after filtering");
      candlestickSeries.setData([]);
    }

    // Update blue line (actual close prices)
    const blueLineData = uniqueData.map((c) => ({
      time: c.time,
      value: c.close,
    }));
    blueLineSeries.setData(blueLineData);
  } else {
    // No candles - clear both candlestick and blue line series
    candlestickSeries.setData([]);
    blueLineSeries.setData([]);
  }

  // Update red line and area (current predictions) with interpolation
  if (props.predictions.length > 0) {
    console.log("Updating predictions:", {
      count: props.predictions.length,
      first: props.predictions[0],
      last: props.predictions[props.predictions.length - 1],
    });

    // Client-side validation: reject predictions with extreme drift
    const isValidPrediction = validatePredictions(props.predictions, uniqueData);
    if (!isValidPrediction.valid) {
      console.warn('⚠️ Prediction rejected by client validation:', isValidPrediction.reason);
      // Don't plot invalid predictions
      if (redAreaSeries) redAreaSeries.setData([]);
      redLineSeries.setData([]);
      // Emit warning to parent if possible
      emit('predictionRejected', isValidPrediction);
      return;
    }

    // Interpolate to create smooth line aligned to chart timeframe
    const intervalSeconds = timeframeToSeconds(props.timeframe);
    const interpolatedData = interpolatePredictions(props.predictions, intervalSeconds);

    console.log("Interpolated data:", {
      count: interpolatedData.length,
      first: interpolatedData[0],
      last: interpolatedData[interpolatedData.length - 1],
    });

    // Deduplicate and sort (in case of any overlaps)
    const uniqueRedData = Array.from(
      new Map(interpolatedData.map((item) => [item.time, item])).values()
    ).sort((a, b) => a.time - b.time);

    // Update both area and line series
    if (redAreaSeries) {
      redAreaSeries.setData(uniqueRedData);
    }
    redLineSeries.setData(uniqueRedData);
  } else {
    if (redAreaSeries) {
      redAreaSeries.setData([]);
    }
    redLineSeries.setData([]);
  }

  // Update black line (historical predictions) with interpolation
  if (props.historicalPredictions.length > 0) {
    // Interpolate to create smooth line aligned to chart timeframe
    const intervalSeconds = timeframeToSeconds(props.timeframe);
    const interpolatedBlackData = interpolatePredictions(
      props.historicalPredictions,
      intervalSeconds
    );

    // Deduplicate and sort
    const uniqueBlackData = Array.from(
      new Map(interpolatedBlackData.map((item) => [item.time, item])).values()
    ).sort((a, b) => a.time - b.time);

    blackLineSeries.setData(uniqueBlackData);
  } else {
    blackLineSeries.setData([]);
  }

  // Update prediction history series (only when showPredictionHistory is true)
  if (props.showPredictionHistory && props.predictionHistory && props.predictionHistory.length > 0) {
    const intervalSeconds = timeframeToSeconds(props.timeframe);
    
    // Create series for each prediction type if they don't exist
    props.predictionHistory.forEach(({ type, predictions: typePredictions }) => {
      if (!typePredictions || typePredictions.length === 0) return;
      
      // Create series if it doesn't exist
      if (!historySeriesMap[type]) {
        const color = getPredictionTypeColor(type);
        historySeriesMap[type] = chart.addLineSeries({
          color: color,
          lineWidth: 1,
          lineStyle: 2, // Dashed line
          title: type.charAt(0).toUpperCase() + type.slice(1),
          visible: true,
        });
      }
      
      // Process all predictions of this type
      const allPoints = [];
      typePredictions.forEach((prediction) => {
        if (prediction.predicted_series && prediction.predicted_series.length > 0) {
          const interpolated = interpolatePredictions(
            prediction.predicted_series,
            intervalSeconds
          );
          allPoints.push(...interpolated);
        }
      });
      
      // Deduplicate and sort
      const uniquePoints = Array.from(
        new Map(allPoints.map((item) => [item.time, item])).values()
      ).sort((a, b) => a.time - b.time);
      
      historySeriesMap[type].setData(uniquePoints);
    });
    
    // Remove series for types that are no longer in history
    Object.keys(historySeriesMap).forEach((type) => {
      const exists = props.predictionHistory.some((h) => h.type === type);
      if (!exists) {
        chart.removeSeries(historySeriesMap[type]);
        delete historySeriesMap[type];
      }
    });
  } else {
    // Hide all history series when showPredictionHistory is false
    Object.values(historySeriesMap).forEach((series) => {
      series.setData([]);
    });
  }

  // Only fit content if this is initial load (chart is empty or we're zoomed out)
  // Don't reset view when loading more historical data
  const visibleRange = chart.timeScale().getVisibleRange();
  if (!visibleRange || uniqueData.length === 0) {
    // Initial load or no data - fit content
    chart.timeScale().fitContent();
  } else {
    // We have data and a visible range - preserve user's current view
    // The chart will automatically update with new data
    console.log("📊 Chart updated with new candles, preserving current view");
  }
};

const updateCandle = (candle) => {
  if (!candlestickSeries || !blueLineSeries) return;

  // Parse ISO timestamp with timezone and convert to Unix timestamp (UTC)
  const date = new Date(candle.start_ts);
  const candleTime = Math.floor(date.getTime() / 1000);

  const data = {
    time: candleTime,
    open: candle.open,
    high: candle.high,
    low: candle.low,
    close: candle.close,
  };

  // Check if this candle already exists in the series
  // If it doesn't exist, we need to refresh the entire chart
  // First, try to update (for existing candles)
  try {
    candlestickSeries.update(data);
    blueLineSeries.update({ time: data.time, value: data.close });
    
    // Track last candle for live updates
    lastCandleTime = candleTime;

    console.log("✅ Live candle update applied:", {
      time: candle.start_ts,
      close: candle.close,
      isLive: true,
      candleTime: candleTime
    });
  } catch (error) {
    // If update fails (candle doesn't exist), refresh the entire chart
    console.log("⚠️ Candle update failed, refreshing entire chart:", error);
    // Trigger a full chart update by calling updateChart
    // This will happen automatically via the watch on props.candles
    updateChart();
  }
};

const updatePrediction = (predictions) => {
  if (!redLineSeries || !predictions || predictions.length === 0) {
    if (redAreaSeries) redAreaSeries.setData([]);
    if (redLineSeries) redLineSeries.setData([]);
    return;
  }

  // Interpolate predictions for smooth line aligned to chart timeframe
  const intervalSeconds = timeframeToSeconds(props.timeframe);
  const interpolatedData = interpolatePredictions(predictions, intervalSeconds);

  // Update both area and line
  if (redAreaSeries) {
    redAreaSeries.setData(interpolatedData);
  }
  redLineSeries.setData(interpolatedData);
};

// Handle window resize
const handleResize = () => {
  if (chart && chartContainer.value) {
    chart.applyOptions({
      width: chartContainer.value.clientWidth,
      height: chartContainer.value.clientHeight || 700,
    });
  }
};

onMounted(() => {
  initChart();
  updateChart();
  window.addEventListener("resize", handleResize);
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", handleResize);

  // Clear debounce timer
  if (debounceTimer) {
    clearTimeout(debounceTimer);
  }

  if (chart) {
    if (chart.timeScale) {
      chart
        .timeScale()
        .unsubscribeVisibleLogicalRangeChange(handleVisibleRangeChange);
      chart
        .timeScale()
        .unsubscribeVisibleTimeRangeChange(handleVisibleRangeChange);
    }
    // Unsubscribe from crosshair
    chart.unsubscribeCrosshairMove(handleCrosshairMove);
    chart.remove();
  }
});

// Watch for prop changes
watch(() => props.candles, updateChart, { deep: true });
watch(() => props.predictions, updateChart, { deep: true });
watch(() => props.historicalPredictions, updateChart, { deep: true });
watch(() => props.showPredictionHistory, updateChart);
watch(() => props.predictionHistory, updateChart, { deep: true });

// Expose methods to parent
defineExpose({
  updateCandle,
  updatePrediction,
});
</script>

<style scoped>
.chart-wrapper {
  position: relative;
  width: 100%;
  background: #0f172a; /* Darker background to match chart */
  border-radius: 6px;
  overflow: hidden;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(148, 163, 184, 0.1);
}

.chart-container {
  width: 100%;
  height: 700px; /* Increased height for better visibility */
  min-height: 500px; /* Minimum height for smaller screens */
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(26, 26, 29, 0.9);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
}

.spinner {
  width: 48px;
  height: 48px;
  border: 4px solid #2b2b2e;
  border-top-color: #2962ff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.loading-overlay p {
  color: #d1d4dc;
  font-size: 14px;
}

/* Tooltip Styles */
.chart-tooltip {
  position: absolute;
  pointer-events: none;
  z-index: 1000;
  background: rgba(24, 24, 27, 0.98);
  border: 1px solid #2b2b2e;
  border-radius: 8px;
  padding: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(8px);
  min-width: 200px;
  max-width: 300px;
}

.tooltip-content {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.tooltip-time {
  font-size: 13px;
  font-weight: 600;
  color: #efeff1;
  padding-bottom: 8px;
  border-bottom: 1px solid #2b2b2e;
  font-family: "SF Mono", "Monaco", monospace;
}

.tooltip-section {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.tooltip-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #999;
}

.tooltip-label.blue {
  color: #2962ff;
}

.tooltip-label.red {
  color: #ff6b6b;
}

.tooltip-label.gray {
  color: #888;
}

.tooltip-value {
  font-size: 16px;
  font-weight: 700;
  color: #efeff1;
  font-family: "SF Mono", "Monaco", monospace;
}

.tooltip-ohlc {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px 8px;
  font-size: 12px;
}

.ohlc-item {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}

.ohlc-item .label {
  color: #999;
  font-size: 11px;
}

.ohlc-item .value {
  color: #efeff1;
  font-weight: 600;
  font-family: "SF Mono", "Monaco", monospace;
}

.ohlc-item .value.high {
  color: #26a69a;
}

.ohlc-item .value.low {
  color: #ef5350;
}

.tooltip-diff {
  font-size: 12px;
  font-weight: 600;
  font-family: "SF Mono", "Monaco", monospace;
}

.tooltip-diff.positive {
  color: #26a69a;
}

.tooltip-diff.negative {
  color: #ef5350;
}

.tooltip-meta {
  font-size: 10px;
  color: #666;
  font-style: italic;
}

.prediction-badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  text-align: center;
}

.prediction-badge.accurate {
  background: rgba(38, 166, 154, 0.2);
  color: #26a69a;
}

.prediction-badge.fair {
  background: rgba(255, 167, 38, 0.2);
  color: #ffa726;
}

.prediction-badge.poor {
  background: rgba(239, 83, 80, 0.2);
  color: #ef5350;
}
</style>
