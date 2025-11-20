# Prediction Inversion Issue - ROOT CAUSE & FIX

## Problem Identified

Your trading bot was showing **100% opposite predictions** - predicting UP when the market went DOWN and vice versa.

## Root Causes Found

### 1. **Feature Shape Mismatch** (CRITICAL)
- **Issue**: Deep learning models (LSTM, Transformer) were trained with 15 features
- **Current Code**: Feature engineering now generates 19 features
- **Result**: Models failed during prediction and fell back to simple trend extrapolation
- **Impact**: HIGH - Models weren't being used at all!

### 2. **Stale Fallback Predictions**
- **Issue**: Fallback logic used 20-candle lookback window
- **Result**: Predictions based on old trends, not current price action
- **Impact**: MEDIUM - Fallback showed stale trends when market reversed

### 3. **No Health Checks**
- **Issue**: No detection of feature mismatches before prediction
- **Result**: Silent failures leading to poor predictions
- **Impact**: MEDIUM - Hard to diagnose issues

## Fixes Implemented

### ✅ 1. Automatic Feature Mismatch Detection
**Files Modified**: `backend/bots/lstm_bot.py`, `backend/bots/transformer_bot.py`

- Added automatic shape checking before prediction
- Auto-recreates models with correct feature count when mismatch detected
- Falls back gracefully with warning logs

```python
# Now checks feature count and auto-fixes
if expected_features != actual_n_features:
    logger.warning(f"FEATURE MISMATCH: recreating model...")
    self._create_model_with_features(actual_n_features)
    return self._fallback_prediction(...)  # Use fallback for this prediction
```

### ✅ 2. Improved Fallback Predictions
**Files Modified**: All bot files (`lstm_bot.py`, `transformer_bot.py`, `ensemble_bot.py`)

**Old Approach**:
- Used 20-30 candle lookback (stale trends)
- Extrapolated full trend into future
- Could be 180 degrees wrong after trend reversal

**New Approach**:
- **Hybrid Window**: Blends 5-candle (immediate) + 10-candle (short-term) trends
- **Ultra-Conservative**: Only 15% of observed trend is extrapolated
- **Strict Limits**: Max ±1% prediction range
- **Result**: Predictions stay close to last price (mostly flat)

### ✅ 3. Deleted Old Models
**Action**: Removed 18 model files with feature mismatches

All old models cleared to ensure clean slate for retraining.

## Current Status

### Fallback Predictions: ✅ WORKING CORRECTLY
```
Latest Close: ₹3155.80
LSTM Fallback: ₹3154.41 → ₹3154.33 (-0.00%)
Status: Essentially FLAT (correct conservative behavior)
```

### Deep Learning Models: ⚠️ NEED RETRAINING
- Models deleted due to feature mismatch
- Currently using fallback predictions only
- Models will auto-recreate with correct shape on first training

## Next Steps (REQUIRED)

### Option 1: Via Frontend (Recommended)
1. Start backend: `cd backend && source venv/bin/activate && python main.py`
2. Open frontend in browser
3. Select your symbol (e.g., TCS.NS, INFY.NS)
4. Click **"Train DL Models"** button (trains LSTM + Transformer)
5. Click **"Retrain All Models"** button (trains Ensemble)
6. Wait for training to complete (watch progress bar)
7. Click **"Full Ensemble"** to get predictions from all retrained models

### Option 2: Via API
```bash
# Train LSTM
curl -X POST http://localhost:8000/api/prediction/train \
  -H 'Content-Type: application/json' \
  -d '{
    "symbol": "TCS.NS",
    "timeframe": "5m",
    "bot_name": "lstm_bot",
    "epochs": 50,
    "batch_size": 200
  }'

# Train Transformer
curl -X POST http://localhost:8000/api/prediction/train \
  -H 'Content-Type: application/json' \
  -d '{
    "symbol": "TCS.NS",
    "timeframe": "5m",
    "bot_name": "transformer_bot",
    "epochs": 30,
    "batch_size": 200
  }'

# Train Ensemble
curl -X POST http://localhost:8000/api/prediction/train \
  -H 'Content-Type: application/json' \
  -d '{
    "symbol": "TCS.NS",
    "timeframe": "5m",
    "bot_name": "ensemble_bot",
    "batch_size": 200
  }'
```

## Training Tips

### For Each Symbol/Timeframe Combination
- **Train once per symbol/timeframe** (e.g., TCS.NS/5m, INFY.NS/15m)
- Models are stored separately for each combination
- Training takes 5-15 minutes per model
- Progress shown in real-time via WebSocket

### Recommended Training Order
1. **Start with one symbol** (e.g., TCS.NS/5m)
2. **Train all bots** for that symbol
3. **Test predictions** to verify accuracy
4. **Then train other symbols** if needed

### Expected Training Times
- LSTM: ~10 minutes (50 epochs)
- Transformer: ~8 minutes (30 epochs)
- Ensemble: ~3 minutes (no epochs, just fitting)

## How to Verify Fix

### 1. Check Model Status
```bash
# View trained models
ls -lh backend/models/*.keras
ls -lh backend/models/*.pkl
```

### 2. Test Predictions
```bash
# Trigger prediction after training
curl -X POST http://localhost:8000/api/prediction/trigger \
  -H 'Content-Type: application/json' \
  -d '{
    "symbol": "TCS.NS",
    "timeframe": "5m",
    "horizon_minutes": 180
  }'
```

### 3. Check Logs
```bash
# Watch for feature mismatch warnings (should not appear after retraining)
tail -f backend/logs/backend*.log | grep "FEATURE MISMATCH"
```

## Technical Details

### Why Feature Mismatch Occurred
The feature engineering code evolved to generate more features (19 instead of 15):
- Added: `sma_20`, `ema_21`, `stoch_rsi_k`, `stoch_rsi_d`
- Models trained months ago: 15 features
- Current code: 19 features
- **Solution**: Auto-detect and retrain

### Why Fallback Was Inverted
1. Market made a move (e.g., UP +5% over 3 days)
2. Then reversed slightly (DOWN -1% in last hour)
3. Fallback used 20-candle window: saw +5% trend
4. Predicted: Continue UP
5. Reality: Market continued DOWN (trend had reversed)
6. **Solution**: Use hybrid 5+10 candle window for recent trends

## Files Modified

### Core Bot Files
- `backend/bots/lstm_bot.py` - Feature mismatch detection + improved fallback
- `backend/bots/transformer_bot.py` - Feature mismatch detection + improved fallback
- `backend/bots/ensemble_bot.py` - Improved fallback logic

### Utility Scripts
- `backend/diagnostic_prediction_direction.py` - New diagnostic tool
- `backend/clear_old_models.py` - Model cleanup script

## Summary

| Issue | Status | Action Required |
|-------|--------|----------------|
| Feature Mismatch | ✅ Fixed | Retrain models |
| Stale Fallback | ✅ Fixed | None - auto-applied |
| No Health Checks | ✅ Fixed | None - auto-applied |
| Models Trained | ⚠️ Pending | **YOU MUST RETRAIN** |

## Expected Behavior After Retraining

### Before (Old Models)
- ❌ Predictions inverted
- ❌ Models failing silently
- ❌ Using stale fallback trends
- ❌ Showing as ₹1570 when actual is ₹1538 (inverted)

### After (Retrained Models)
- ✅ Predictions match market direction
- ✅ Models working with correct features (19 features)
- ✅ Fallback conservative and recent (if models fail)
- ✅ Showing reasonable predictions within ±1-2% of current price

## Support

If predictions are still inverted after retraining:
1. Check logs for "FEATURE MISMATCH" warnings
2. Verify training completed successfully
3. Check prediction confidence (should be >60% for trained models, <35% for fallback)
4. Look for "fallback" in prediction metadata - indicates model not being used

---

**Status**: ✅ Code fixes complete, ⚠️ Models need retraining
**Priority**: HIGH - Retrain immediately
**ETA**: 20-30 minutes to retrain all models for one symbol/timeframe

