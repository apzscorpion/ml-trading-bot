# Backend Startup Issues - Explanation & Fixes

## Issues Found

### 1. Redis Connection Error (Non-Critical) ⚠️
**Error**: `Redis connection failed, falling back to in-memory cache: Error 61 connecting to localhost:6379. Connection refused.`

**Explanation**: 
- This is **expected** if Redis is not installed or running
- The app automatically falls back to in-memory caching
- **Not a critical error** - the app works fine without Redis

**Fix Options**:
- **Option 1 (Recommended)**: Ignore it - in-memory cache works fine for development
- **Option 2**: Install and start Redis:
  ```bash
  # macOS
  brew install redis
  brew services start redis
  
  # Or disable Redis in config
  # Set redis_enabled=false in backend/config.py
  ```

### 2. Keras Optimizer Warning (Harmless) ⚠️
**Warning**: `Skipping variable loading for optimizer 'adam', because it has 32 variables whereas the saved optimizer has 2 variables.`

**Explanation**:
- This happens when loading Keras models saved with different Keras/TensorFlow versions
- The model weights load correctly, only optimizer state is skipped
- **Harmless** - models will still work, just optimizer state isn't restored

**Fix Options**:
- **Option 1 (Recommended)**: Ignore it - models work fine
- **Option 2**: Retrain models with current Keras version to save optimizer state
- **Option 3**: Suppress warning by setting logging level

### 3. Database Schema Mismatch (CRITICAL - FIXED) ✅
**Error**: `no such column: prediction_evaluations.rmse`

**Root Cause**:
- Database had old schema with `actual_series`, `metrics`, `computed_at` columns
- Model expects new schema with `rmse`, `mae`, `mape`, `directional_accuracy` columns
- Migration script was only adding `symbol`/`timeframe`, not the metric columns

**Fix Applied**:
- ✅ Updated migration script to add all missing metric columns
- ✅ Added data migration from old `metrics` JSON column to new individual columns
- ✅ Fixed path resolution to ensure SQLAlchemy and migration use same database file

**After Restart**:
- Migration will add `rmse`, `mae`, `mape`, `directional_accuracy` columns
- Old data from `metrics` JSON will be migrated to new columns
- All errors should be resolved

## Summary

1. **Redis Error**: Non-critical, can be ignored
2. **Keras Warning**: Harmless, can be ignored  
3. **Database Error**: **FIXED** - restart backend to apply migration

## Next Steps

1. **Restart backend server**:
   ```bash
   ./stop.sh
   ./start.sh
   ```

2. **Verify migration**:
   - Check logs for: "Adding rmse column...", "Adding mae column...", etc.
   - Check logs for: "✅ Migrated metrics data from JSON to individual columns"

3. **Test endpoint**:
   - `/api/evaluation/metrics/summary?symbol=INFY.NS&timeframe=15m` should work without errors

## Expected Log Output After Fix

```
✅ Adding rmse column to prediction_evaluations...
✅ Adding mae column to prediction_evaluations...
✅ Adding mape column to prediction_evaluations...
✅ Adding directional_accuracy column to prediction_evaluations...
✅ Migrated metrics data from JSON to individual columns
✅ Database columns: ['actual_series', 'computed_at', 'created_at', 'directional_accuracy', 'evaluated_at', 'id', 'mae', 'mape', 'metrics', 'prediction_id', 'rmse', 'symbol', 'timeframe']
✅ Model columns: ['created_at', 'directional_accuracy', 'evaluated_at', 'id', 'mae', 'mape', 'prediction_id', 'rmse', 'symbol', 'timeframe']
```

The old columns (`actual_series`, `metrics`, `computed_at`) will remain but won't be used by the model. They can be dropped later if needed.

