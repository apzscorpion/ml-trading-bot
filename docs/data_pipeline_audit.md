% Data Pipeline & TA/ML Separation Audit

# Overview
This audit captures the current data flow for candles, indicator generation, caching, and how the Technical Analysis (TA) paths interact with Machine Learning (ML) outputs. It serves as the baseline for Phase 1 of the stabilisation plan.

# Current Sources & Storage Layers
- **Primary provider:** Yahoo Finance via `backend/utils/data_fetcher.py` (`yfinance`); filters out non-trading days, off-session candles, and future data.
- **Fallback provider:** Twelve Data (if enabled via settings); same filtering logic.
- **Data pipeline:** `backend/data_pipeline/DataPipeline` promotes fetched candles through `raw → bronze → silver` parquet layers (see `ingestion.py`, `storage.py`).
- **Feature store:** `FeatureStore.load_features()` reads silver-layer parquet snapshots; optional `lookback` truncation but no time-window enforcement.
- **Database:** `Candle` table stores recent candles for API reads (`backend/routes/history.py`).
- **Caches:**
  - Redis “hot” cache (`utils/redis_cache`), keyed by symbol/interval/period.
  - In-memory LRU “warm” cache in `DataFetcher` (30-second TTL, max 100 entries).
  - Parquet datasets versioned by dataset namespace + run id (`storage.py`).

# Technical Analysis Path
- **Endpoint:** `GET /api/history` (file `backend/routes/history.py`).
  - Reads from DB first; applies trading-day/hour filters.
  - Fetches fresh Yahoo/Twelve data when cache bypassed, stale, or insufficient rows; stores back into DB and pipeline.
  - Returns merged list of candles (chronological order).
- **TA frontend:** `frontend/src/components/ChartComponent.vue` consumes `/api/history` + live websocket updates; overlays TA indicators client-side (see indicator composables).
- **Coupling issues:**
  - TA fetch relies on the same merged candle list later reused by ML components (no isolation of TA-only store).
  - Absence of deterministic 60–90 day window guarantee—depends on `limit` query (default 500) and fetch period map.
  - Cached ML predictions may overwrite chart overlays when ML bots emit extreme values; no sanitisation at merge.

# ML Prediction Path
- **Pipeline:** `/api/prediction/trigger` → `freddy_merger.predict()` aggregates bot predictions.
- **Bots:** `ml_bot`, `lstm_bot`, `transformer_bot`, `ensemble_bot`, etc. Each pulls candles via the DB query (limited recent candles) without a shared rolling-window loader.
- **Artifacts:** Predictions stored in `Prediction` table; chart consumes latest prediction and overlays on TA line.
- **Known issues:**
  - Outlier predictions (e.g., >±20%) leak into chart because TA & ML share the same overlay channel.
  - Training tasks for Transformer/LSTM fail fast when scaler/model missing; no diagnostics persisted.
  - ML path does not provide fallback when sanitisation fails—frontend still reuses last prediction.

# Dependencies & Configuration Touchpoints
- `backend/config/settings` – toggles providers, dataset versions, Redis, etc.
- `backend/utils/exchange_calendar` – trading-day validation used by both TA and ML.
- `backend/websocket_manager.py` – broadcasts live updates consumed by TA chart.
- `frontend/src/services/api.js` – orchestrates history + prediction requests; lacks explicit separation between TA refresh and ML overlay refresh.

# Gaps Identified
1. **TA window control:** No central guarantee that TA always uses latest 60–90 day slice; depends on API `limit` and dynamic Yahoo periods.
2. **TA/ML isolation:** Shared data structures allow ML outliers to bleed into TA displays.
3. **Sanitisation:** Missing post-prediction guard to reject NaN/Inf/extreme ML values before persistence.
4. **Diagnostics:** Lack of aggregated metrics/logs to quickly observe data freshness, cache hits, or prediction sanitisation results.

# Next Steps (per plan)
- Implement deterministic window loader for TA endpoints (Phase 1 `ta-refactor`).
- Introduce prediction sanitiser layer prior to DB/log persistence (`ml-sanitizer`).
- Refactor frontend to request TA and ML data through separate channels during Phase 4.

