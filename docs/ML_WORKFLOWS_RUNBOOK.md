# ML Workflows Runbook

**Version**: 2.0  
**Last Updated**: November 6, 2025

---

## Quick Start

### 1. View Pure Technical Analysis (No ML)

**Via UI**:
1. Open trading dashboard at `localhost:5155`
2. Select stock symbol (e.g., INFY.NS)
3. Click "Technical Analysis" tab (green theme)
4. Click "Refresh" button

**Via API**:
```bash
curl 'http://localhost:8182/api/recommendation/analysis?symbol=INFY.NS&timeframe=15m&mode=ta_only'
```

**What You Get**:
- RSI, MACD, SMA 20/50, Bollinger Bands, ATR, Volume analysis
- Buy/Sell/Hold recommendation based purely on indicators
- Support/Resistance levels, Stop-loss & Take-profit suggestions
- **Guaranteed**: Computed from 60-90 days of raw candles only

---

### 2. View ML Predictions (Ensemble)

**Via UI**:
1. Open trading dashboard
2. Select stock symbol
3. Click "ML Predictions" tab (blue theme)
4. Click "Refresh" button

**Via API**:
```bash
curl -X POST http://localhost:8182/api/prediction/trigger \
  -H 'Content-Type: application/json' \
  -d '{"symbol":"INFY.NS","timeframe":"15m","horizon_minutes":180}'
```

**What You Get**:
- Ensemble prediction from LSTM, Transformer, Ensemble, TA bots
- Validated predictions (±10% max drift)
- Confidence score with bot contributions
- Sanitization summary (which bots were clipped/rejected)

---

### 3. Train ML Models

**Via UI (Recommended)**:
1. Navigate to "Model Management" section
2. Click "Start Auto Training"
3. Monitor progress in real-time via WebSocket
4. Check health badges: 🟢 Green = Healthy, 🟡 Yellow = Stale, 🔴 Red = Failed

**Via API**:
```bash
# Train specific bot
curl -X POST http://localhost:8182/api/prediction/train \
  -H 'Content-Type: application/json' \
  -d '{"symbol":"INFY.NS","timeframe":"15m","bot_name":"lstm_bot","epochs":50,"batch_size":200}'

# Start auto-training queue
curl -X POST http://localhost:8182/api/training/start-auto \
  -H 'Content-Type: application/json' \
  -d '{"symbols":["INFY.NS","TCS.NS"],"timeframes":["15m"],"bots":["lstm_bot","transformer_bot","ensemble_bot"]}'
```

**What Happens**:
1. Data loader fetches 90 days of data
2. Schema + quality validation
3. Scaler initialization (if missing)
4. Model training with walk-forward validation
5. Baseline comparison (last-value, MA, linear trend)
6. Training record stored with metrics
7. Health status updated

---

## Data Flows

### Technical Analysis Flow
```
User Request
  ↓
/api/recommendation/analysis?mode=ta_only
  ↓
ta_service.analyze(symbol, timeframe)
  ↓
Fetch 60-90 days raw candles (DB or Yahoo)
  ↓
Validate schema (OHLCV columns present)
  ↓
Compute indicators (RSI, MACD, MA, BB, ATR, Volume)
  ↓
Generate signals (bullish/bearish/neutral scores)
  ↓
Compute recommendation (BUY/SELL/HOLD)
  ↓
Return to frontend
  ↓
Display in green-themed TA tab
```

### ML Prediction Flow
```
User Request
  ↓
/api/prediction/trigger
  ↓
freddy_merger.predict()
  ↓
For each bot:
  ↓
bot.predict(candles, horizon, timeframe)
  ↓
prediction_validator.validate_prediction()
  ↓
If invalid → sanitize_prediction()
  ↓
If still invalid → drop bot from ensemble
  ↓
Merge valid predictions (weighted by regime)
  ↓
Store: merged_series + raw_outputs + validation_flags + feature_snapshot
  ↓
Return to frontend
  ↓
Client validates (max ±10% drift)
  ↓
If valid → plot on chart
If invalid → show error, don't plot
```

### ML Training Flow
```
User clicks "Train" or Auto-training starts
  ↓
Check for duplicate job (symbol/timeframe/bot already running?)
  ↓
If duplicate → skip
  ↓
ml_data_loader.get_training_window(symbol, timeframe, days=90)
  ↓
Validate schema (OHLCV + required columns)
  ↓
Validate data quality (NaN, Inf, negative, OHLC validity)
  ↓
If invalid → return error
  ↓
bot.train(candles, epochs)
  ↓
Initialize scalers if missing
  ↓
Prepare features
  ↓
Train model (in thread pool executor - non-blocking)
  ↓
Compute test metrics (RMSE, MAE)
  ↓
Compare with baselines (last-value, MA, linear-trend)
  ↓
Save model + scalers
  ↓
Create ModelTrainingRecord (status='active')
  ↓
Compute drift score (compare recent vs training RMSE)
  ↓
Update health status
  ↓
Emit training complete event
```

---

## Troubleshooting

### Issue: "ML bot prediction rejected"

**Symptoms**: Warning in browser console: "Prediction rejected by client validation: excessive upward drift"

**Diagnosis**:
```bash
# Check prediction in DB
sqlite3 trading_predictions.db "SELECT id, symbol, validation_flags FROM predictions ORDER BY id DESC LIMIT 1;"

# Check logs
tail -n 50 logs/backend.log | grep "validation"
```

**Root Causes**:
1. Model not trained on recent data (stale model)
2. Scaler mismatch (feature count changed)
3. Model learned spurious pattern (needs retraining)

**Fix**:
```bash
# Option 1: Retrain model
curl -X POST http://localhost:8182/api/prediction/train \
  -d '{"symbol":"INFY.NS","timeframe":"15m","bot_name":"lstm_bot","epochs":50}'

# Option 2: Clear stale models and retrain
curl -X DELETE http://localhost:8182/api/models/clear-all/INFY.NS/15m
# Then retrain via UI
```

---

### Issue: "Technical Analysis showing N/A values"

**Symptoms**: TA tab shows "N/A" for indicators

**Diagnosis**:
```bash
# Check if enough candles exist
sqlite3 trading_predictions.db "SELECT COUNT(*) FROM candles WHERE symbol='INFY.NS' AND timeframe='15m';"

# Check TA service response
curl 'http://localhost:8182/api/recommendation/analysis?symbol=INFY.NS&timeframe=15m&mode=ta_only'
```

**Root Causes**:
1. Insufficient data (<60 days)
2. Missing OHLCV columns
3. All values are NaN/Inf

**Fix**:
```bash
# Fetch fresh data from Yahoo
curl -X POST http://localhost:8182/api/prediction/trigger \
  -d '{"symbol":"INFY.NS","timeframe":"15m","force_refresh":true}'
# This will populate DB with fresh candles
```

---

### Issue: "NoneType has no attribute 'fit'" during training

**Symptoms**: Training fails with scaler error

**Diagnosis**:
```bash
# Check bot initialization
tail -n 100 logs/backend.log | grep "scaler"
```

**Root Cause**: Scaler not initialized (legacy model or first-time training)

**Fix**: Already fixed in code via scaler guards. If still occurs:
```bash
# Delete stale model files
rm backend/models/lstm_model*.keras
rm backend/models/lstm_scalers.pkl
rm backend/models/transformer_model*.keras
rm backend/models/transformer_scaler.pkl

# Restart backend (recreates models with fresh scalers)
cd backend && ./run.sh
```

---

### Issue: "ensemble_bot scaler mismatch"

**Symptoms**: Warning: "expected 880 features, but have 920 (lookback=40, features_per_period=23)"

**Root Cause**: Feature engineering changed but model wasn't retrained

**Fix**:
```bash
# Clear ensemble models
rm backend/models/ensemble_models*.pkl

# Retrain
curl -X POST http://localhost:8182/api/prediction/train \
  -d '{"symbol":"INFY.NS","timeframe":"15m","bot_name":"ensemble_bot"}'
```

---

### Issue: Chart shows old predictions with runaway values

**Symptoms**: Chart still showing ₹20,000+ spikes after fix

**Root Cause**: Old predictions cached in DB before guardrails were added

**Fix**:
```bash
# Delete old predictions
sqlite3 trading_predictions.db "DELETE FROM predictions WHERE id < 94;"

# Or clear via UI
# Click "Model Management" → "Clear All Models for INFY.NS"

# Then trigger fresh prediction
curl -X POST http://localhost:8182/api/prediction/trigger \
  -d '{"symbol":"INFY.NS","timeframe":"15m"}'
```

---

## Maintenance Procedures

### Daily Health Check
```bash
# 1. Check drift scores
curl http://localhost:8182/api/models/report | jq '.models[] | select(.config.drift_score > 0.2)'

# 2. Check training queue
curl http://localhost:8182/api/training/status

# 3. Check for failed predictions
tail -n 200 logs/backend.log | grep -i "prediction rejected"
```

### Weekly Model Refresh
```bash
# Retrain all stale models (>48h old)
# Via UI: Model Manager → "Start Auto Training"

# Or via script:
for symbol in INFY.NS TCS.NS RELIANCE.NS HDFCBANK.NS; do
  for timeframe in 15m 1h 1d; do
    for bot in lstm_bot transformer_bot ensemble_bot; do
      curl -X POST http://localhost:8182/api/prediction/train \
        -d "{\"symbol\":\"$symbol\",\"timeframe\":\"$timeframe\",\"bot_name\":\"$bot\",\"epochs\":50}"
      sleep 5  # Rate limit
    done
  done
done
```

### Monthly Audit
1. Review `ML_PIPELINE_REFACTOR_SUMMARY.md` for compliance
2. Check `prediction_evaluations` table for accuracy trends
3. Verify drift scores in `model_training_records.config.drift_score`
4. Archive old predictions: `DELETE FROM predictions WHERE produced_at < datetime('now', '-30 days');`

---

## Assumptions & Constraints

### Data Assumptions
- **Yahoo Finance limitations**:
  - 1m: max 5 days
  - 5m/15m: max 60 days
  - 1h/4h: max 730 days
  - 1d+: max 2000 days
- **NSE/BSE trading hours**: 9:15 AM - 3:30 PM IST (market hours)
- **Candle completeness**: Gaps expected during weekends, holidays, pre-market

### Model Assumptions
- **Training window**: 90 days rolling (adjustable via `days` param)
- **Minimum candles**: 200 for training, 100 for prediction
- **Feature stability**: Indicator definitions must remain consistent across retraining
- **No lookahead bias**: Walk-forward validation ensures temporal ordering

### Validation Thresholds
- **Backend**:
  - ML validator: ±10% total drift, 3% step change
  - ml_bot internal: ±5% total, 0.5% step change
  - Freddy merger: 12% envelope, 6% step change
- **Frontend**:
  - Client validator: ±10% total drift, 5% step change

### Performance Constraints
- **TA analysis**: <2s response time (no ML dependencies)
- **ML prediction**: <10s with 5 bots
- **Training**: LSTM/Transformer 30-50 epochs = 2-5 min per symbol/timeframe
- **Drift computation**: <500ms (queries last 7 days)

---

## Monitoring Alerts

### When to Retrain (Automated)
- ✅ Model age >24h: auto-triggered by `/api/prediction/trigger` (if stale threshold enabled)
- ✅ Drift score >0.2 (20% error increase): logged as WARNING
- ✅ Training failure: creates `status='failed'` record

### Manual Intervention Required
- 🔴 All bots rejected for a symbol/timeframe (check validation logs)
- 🔴 TA service returns error: "insufficient_data" (need to fetch more history)
- 🔴 Drift score >0.5 (50%+ degradation): model likely broken, clear and retrain
- 🔴 Client repeatedly rejects predictions: backend guardrails may be misconfigured

---

## API Reference

### Technical Analysis

**GET /api/recommendation/analysis**
- Query params: `symbol`, `timeframe`, `mode` (default: "combined")
- Modes: `ta_only`, `ml_only`, `combined`
- Returns: indicators, signals, recommendation, support/resistance

### ML Predictions

**POST /api/prediction/trigger**
- Body: `{"symbol":"INFY.NS","timeframe":"15m","horizon_minutes":180,"selected_bots":["lstm_bot"]}`
- Returns: prediction_id, status, result with validation details

**GET /api/prediction/latest**
- Query params: `symbol`, `timeframe`
- Returns: latest stored prediction (may be stale)

### Training

**POST /api/prediction/train**
- Body: `{"symbol":"INFY.NS","timeframe":"15m","bot_name":"lstm_bot","epochs":50}`
- Returns: training_id, queues background job

**POST /api/training/start-auto**
- Body: `{"symbols":["INFY.NS"],"timeframes":["15m"],"bots":["lstm_bot","transformer_bot"]}`
- Queues multiple training jobs

**GET /api/training/status**
- Returns: is_running, queue_length, current_training, completed_count, failed_count

**POST /api/training/pause** / **POST /api/training/resume** / **POST /api/training/stop**
- Control training queue execution

### Models

**GET /api/models/report**
- Returns: all trained models with status, age, metrics, health

**DELETE /api/models/clear-all/{symbol}**
- Deletes all model files and training records for a symbol

**DELETE /api/models/clear-all/{symbol}/{timeframe}**
- Deletes models for specific symbol/timeframe

---

## Code Locations

### Backend Services
- **TA Service**: `backend/services/technical_analysis_service.py`
- **Data Loader**: `backend/ml/data_loader.py`
- **Validators**: `backend/ml/validators.py`
- **Baselines**: `backend/ml/baselines.py`
- **Drift Monitor**: `backend/monitoring/drift_monitor.py`

### ML Bots
- **Linear Regression**: `backend/bots/ml_bot.py` (with clamping)
- **LSTM**: `backend/bots/lstm_bot.py` (with scaler guards)
- **Transformer**: `backend/bots/transformer_bot.py` (with scaler guards)
- **Ensemble**: `backend/bots/ensemble_bot.py` (RF + GBM + Ridge)

### Routes
- **Recommendation**: `backend/routes/recommendation.py` (TA/ML modes)
- **Prediction**: `backend/routes/prediction.py` (trigger, latest, history)
- **Training**: `backend/routes/training.py` (queue management)

### Frontend Components
- **Chart**: `frontend/src/components/ChartComponent.vue` (with client validation)
- **Analysis**: `frontend/src/components/ComprehensivePrediction.vue` (TA/ML tabs)
- **Model Manager**: `frontend/src/components/ModelManager.vue` (health badges)

---

## Best Practices

### Do's ✅
- ✅ Use TA tab for deterministic, clean indicator analysis
- ✅ Check model health badges before trusting ML predictions
- ✅ Retrain models every 24-48 hours for fresh data
- ✅ Monitor drift scores weekly
- ✅ Validate predictions before acting on them
- ✅ Use walk-forward validation for new model experiments
- ✅ Compare ML models against baselines

### Don'ts ❌
- ❌ Don't mix TA and ML data sources manually
- ❌ Don't train multiple bots on same symbol/timeframe concurrently
- ❌ Don't trust predictions with >10% drift without investigation
- ❌ Don't deploy models that don't beat baselines
- ❌ Don't ignore drift alerts (>20% error increase)
- ❌ Don't use ML predictions older than 30 minutes for live trading
- ❌ Don't skip validation when integrating new bots

---

## Production Readiness Checklist

Before using this system for live trading:

### Data Quality
- [ ] Verified data sources (Yahoo Finance vs exchange data alignment)
- [ ] Handled corporate actions (splits, dividends, bonus issues)
- [ ] Implemented IST timezone handling throughout
- [ ] Added exchange calendar (holidays, early closures)

### Model Quality
- [ ] All models beat baselines on walk-forward validation
- [ ] Drift scores monitored and below 0.2 for 7 days
- [ ] Backtesting with realistic fills, slippage, transaction costs
- [ ] Sharpe ratio >1.0, max drawdown <15% in backtests

### System Resilience
- [ ] Redis caching enabled (currently using in-memory fallback)
- [ ] Database backups scheduled
- [ ] Model versioning with rollback capability
- [ ] Alerting for drift, training failures, data gaps

### Compliance & Governance
- [ ] Prediction audit trail complete (raw outputs stored)
- [ ] Model lineage documented (training data, hyperparams, version)
- [ ] Risk disclaimers in UI
- [ ] User consent for automated trading

---

## Contact & Support

For issues or questions:
1. Check logs: `logs/backend.log`, `logs/combined.log`
2. Review summary: `ML_PIPELINE_REFACTOR_SUMMARY.md`
3. Inspect database: `sqlite3 trading_predictions.db`
4. API health: `curl http://localhost:8182/health`

**Critical Alerts**: Check `logs/backend.log` for lines with `[ERROR]` or `DRIFT ALERT`

**Model Health**: Navigate to Model Manager UI or call `/api/models/report`

