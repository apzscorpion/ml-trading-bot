# ML Stack Audit (Nov 2025)

## Current Architecture Overview

- **API Layer (`backend/main.py`)**: FastAPI service orchestrating scheduled candle ingestion, prediction requests, WebSocket broadcasting, and auto-training jobs.
- **Bots Library (`backend/bots/`)**: Mix of rule-based (RSI, MACD, MA), classical ML (`ml_bot.py`), ensemble (`ensemble_bot.py`), and deep learning models (`lstm_bot.py`, `transformer_bot.py`).
- **Merger (`backend/freddy_merger.py`)**: Synchronously invokes all bots per request, applies fixed confidence-weighted averaging, and emits a single price trajectory plus trend metadata.
- **Data Access (`backend/utils/data_fetcher.py`, `redis_cache.py`)**: Yahoo Finance primary source with TwelveData fallback. Implements Redis hot cache + in-memory LRU warm cache, basic IST trading-hour filtering, and handles per-symbol/timeframe context.
- **Persistence (`backend/database.py`)**: SQLite with tables for candles, predictions, training history, trend summaries, etc. Training metadata stored per bot/timeframe but lacks versioned dataset references.
- **Frontend (`frontend/`)**: Vite + Vue 3 SPA using lightweight-charts, WebSocket streaming, manual cache busting, and direct API bindings.

## Data Flow Summary

1. **Ingestion**: `scheduled_data_fetch_and_predict` fetches latest candles (default symbol/timeframe) every `prediction_interval`. Additional live streaming handled by `scheduled_realtime_candle_updates` with 5s polling.
2. **Storage**: Latest candles appended to SQLite `candles` table; caches warmed via Redis/in-memory layers. No historical partitioning or Parquet archival.
3. **Prediction**: `freddy_merger.predict` hydrates each bot with current symbol/timeframe context, gathers predictions, merges with static confidence weights, logs metrics.
4. **Serving**: REST `/api/prediction` triggers ad-hoc predictions, ensures stale model retraining, writes outputs to `predictions` table, broadcasts over WebSocket.
5. **Evaluation**: `/api/evaluation` computes RMSE/MAE/MAPE/directional accuracy for historical predictions, storing results in `prediction_evaluations`.
6. **Training**: `/api/prediction/train` and background auto-training queue call each bot’s `train` method; deep models save Keras artifacts, ensembles persist pickled estimators.

## Observed Gaps & Risks

- **Data Provenance**: No raw/bronze/silver layering, limited dataset versioning, missing archived snapshots for reproducible research.
- **Temporal Leakage Controls**: Feature engineering happens inline within bots without strict walk-forward splits or leakage guards.
- **Model Lifecycle**: Single active model per bot/timeframe, no champion/challenger evaluation, regime awareness, or probabilistic calibration.
- **Latency & Resiliency**: Predictions executed sequentially inside request path; heavy TensorFlow models can block event loop despite executor usage.
- **Monitoring**: Prometheus metrics cover counts/latency but lack financial KPIs (Sharpe, drawdown), feature drift, or data feed health dashboards.
- **Frontend UX**: SPA without SSR, limited indicator presets, no fallback when WebSocket drops; chart updates rely on manual merges.

## Target KPIs & Financial Metrics

- **Risk-Adjusted Performance**: Sharpe ≥ 1.8, Sortino ≥ 2.2 for live-deployed strategies over rolling 6-month window.
- **Capital Growth**: CAGR ≥ 18% with max drawdown ≤ 12% on validated walk-forward backtests.
- **Trading Quality**: Hit rate ≥ 55%, average reward/risk ≥ 1.6, latency budget ≤ 150ms P95 per prediction call.
- **Operational Metrics**: Data freshness ≤ 60s, WebSocket availability ≥ 99.5%, model retrain SLA ≤ 2h after stale detection.

## Immediate Priorities

1. Stand up auditable data lakehouse (raw → bronze → silver) with Parquet storage, exchange-aware time alignment, and metadata catalog.
2. Introduce experiment registry + walk-forward pipeline covering statistical, tree, deep, and probabilistic models with consistent evaluation protocols.
3. Replace static merger with regime-sensitive orchestrator using baseline fallback and forecast uncertainty outputs.
4. Modernize frontend via Nuxt 3 SSR + WebGL charting, indicator presets, and resilient socket/client caching.
5. Expand monitoring to cover feed gaps, model drift, and financial KPIs; document runbooks for outages and redeployments.

## Dependencies & Assumptions

- Continue leveraging Yahoo Finance + TwelveData but abstract provider adapters for future NSE direct feed integration.
- Use IST (UTC+5:30) as canonical timestamp; all new pipelines must enforce timezone normalization and trading-session validation.
- Maintain SQLite for local dev, but plan ClickHouse/DuckDB targets for production analytics.
- ML experiments expected to run on separate worker tier with GPU optionality for deep models.
