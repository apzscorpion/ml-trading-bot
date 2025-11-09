# Model Diagnostics & Validation

## 🔍 Overview

This directory contains diagnostic tools to validate your trading models and data quality. **Run these before trusting any model predictions!**

## 🚨 Critical Issues You're Experiencing

Based on your logs, you have:

1. **✅ FIXED**: Missing `List` import causing all training to fail
2. **🔴 ACTIVE**: Models generating unrealistic predictions (200% in 2 hours)
3. **⚠️ SUSPECTED**: Time horizon misalignment
4. **⚠️ SUSPECTED**: Insufficient or poor quality training data

## 🛠️ Tools Available

### 1. Model Validation Script

**File**: `model_validation.py`

**Purpose**: Comprehensive diagnostics for your models and data

**Usage**:
```bash
cd backend
python -m diagnostics.model_validation --symbol INFY.NS --timeframe 15m
```

**What it checks**:
- ✅ Data volume (do you have enough data?)
- ✅ Time horizon alignment (are predictions for correct timeframe?)
- ✅ Return distribution (are actual returns realistic?)
- ✅ Prediction sanity (are predictions realistic?)
- ✅ Feature leakage detection (is model cheating?)
- ✅ Regime coverage (does data cover different market conditions?)

### 2. Prediction Sanitizer

**File**: `../utils/prediction_sanitizer.py`

**Purpose**: Prevent unrealistic predictions from reaching production

**Features**:
- Clips extreme price moves
- Validates prediction series
- Logs warnings for suspicious predictions

**Integration**: Already available as `prediction_sanitizer` singleton

## 📊 Running Diagnostics

### Quick Start

```bash
# 1. Fix the import bug (DONE - restart your backend)
# 2. Run diagnostics
cd /Users/pits/Projects/new-bot-trading/backend
python -m diagnostics.model_validation --symbol INFY.NS --timeframe 15m

# 3. Check different symbols/timeframes
python -m diagnostics.model_validation --symbol TCS.NS --timeframe 5m
python -m diagnostics.model_validation --symbol INFY.NS --timeframe 1h
```

### Expected Output

```
================================================================================
🔍 MODEL DIAGNOSTICS: INFY.NS / 15m
================================================================================

📊 1. DATA VOLUME CHECK
✅ Status: OK
  total_candles: 4320
  time_span_days: 90
  recommended_samples: 4320
  coverage_pct: 100.0

⏰ 2. TIME HORIZON VALIDATION
⚠️  Status: WARNING
  horizon_minutes: 180
  horizon_hours: 3.0
  Issues:
    - Prediction has 36 points but horizon is 180min (12.0 expected points)

📈 3. RETURN DISTRIBUTION ANALYSIS
✅ Status: OK
  return_stats:
    4_hours:
      mean: 0.05
      std: 1.2
      min: -8.5
      max: 9.2
      q01: -3.2
      q99: 3.8

🎯 4. PREDICTION SANITY CHECK
🔴 Status: CRITICAL
  extreme_predictions: 15
  Issues:
    - Total return of 45.2% in 3 hours (unrealistic!)

... etc
```

## 🔧 Fixing Common Issues

### Issue 1: "200% gain in 2 hours" predictions

**Causes**:
1. Time horizon mismatch (model thinks it's predicting 1 year, not 2 hours)
2. Feature leakage (using future data)
3. Wrong data scaling
4. Model overfitting to outliers

**Fix**:
```python
# Check your label computation
# WRONG:
df['target'] = df['close'].shift(-1)  # Only 1 step ahead!

# CORRECT for 4-hour horizon with 15min bars:
steps_ahead = int(240 / 15)  # 16 steps
df['target'] = df['close'].shift(-steps_ahead)

# Verify:
print(f"Predicting {steps_ahead} steps = {steps_ahead * 15} minutes = 4 hours")
```

### Issue 2: Insufficient data

**Symptoms**:
- Model trains but performs poorly
- High variance in predictions
- Can't generalize

**Fix**:
```bash
# Fetch more historical data
# Aim for at least 90 days (3 months)
# For 15m timeframe: 90 days * 24 hours * 4 bars/hour = 8,640 bars

# Check current data:
python -m diagnostics.model_validation --symbol INFY.NS --timeframe 15m
```

### Issue 3: Time horizon mismatch

**Symptoms**:
- Prediction series length doesn't match horizon
- Predictions seem to be for wrong timeframe

**Fix**:
```python
# In your model training code, verify:
horizon_minutes = 180  # 3 hours
timeframe_minutes = 15  # 15-minute bars
expected_points = horizon_minutes / timeframe_minutes  # = 12 points

# Your model should output exactly 12 predictions for 3-hour horizon
assert len(predictions) == expected_points
```

### Issue 4: Feature leakage

**Symptoms**:
- Suspiciously high confidence (>95%)
- Perfect predictions in training
- Terrible in production

**Fix**:
```python
# WRONG - uses future data:
df['feature'] = df['close'].shift(-1)  # Leakage!

# CORRECT - only uses past/current:
df['feature'] = df['close'].shift(1)  # Previous close
df['feature'] = df['close'].rolling(20).mean()  # Moving average
```

## 📋 Checklist Before Trusting Model

- [ ] Run `model_validation.py` - all checks pass or only minor warnings
- [ ] Verify data volume: at least 90 days of history
- [ ] Confirm time horizon: predictions match intended timeframe
- [ ] Check return distribution: actual returns are realistic
- [ ] Validate predictions: no extreme/unrealistic values
- [ ] Test on out-of-sample data: model generalizes
- [ ] Backtest with realistic constraints: includes slippage, fees
- [ ] Monitor in paper trading: before risking real money

## 🎯 Next Steps

1. **Restart your backend** (to apply the `List` import fix)
2. **Run diagnostics** on your current models
3. **Review the output** - identify critical issues
4. **Fix data/training pipeline** based on recommendations
5. **Re-train models** with corrected setup
6. **Validate again** before deploying

## 📚 Additional Resources

- See `NETWORK_ACCESS.md` for network setup
- See `README.md` for general documentation
- Check logs in `/logs/` for detailed error messages

## ⚠️ Important Notes

- **Never deploy without validation**: Unrealistic predictions can lead to catastrophic losses
- **Start with paper trading**: Test thoroughly before using real money
- **Monitor continuously**: Market conditions change, models degrade
- **Keep learning**: ML for trading is hard - expect iterations

---

**Remember**: A model that predicts "200% in 2 hours" is broken. Fix it before it costs you money!

