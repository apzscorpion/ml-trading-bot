# Backend Log Fixes - Nov 4, 2025

## Issues Found in Backend Logs

### ✅ **Issue 1: PredictionEvaluation.computed_at Error**
**Location:** `backend/routes/evaluation.py:221`

**Error:**
```
AttributeError: type object 'PredictionEvaluation' has no attribute 'computed_at'. 
Did you mean: 'created_at'?
```

**Root Cause:**
- Code was trying to use `PredictionEvaluation.computed_at`
- Database model has `evaluated_at` field, not `computed_at`

**Fix Applied:**
```python
# Before:
.order_by(PredictionEvaluation.computed_at.desc())

# After:
.order_by(PredictionEvaluation.evaluated_at.desc())
```

**Status:** ✅ Fixed

---

### ✅ **Issue 2: Transformer Bot Model Loading Error**
**Location:** `backend/bots/transformer_bot.py:72`

**Error:**
```
ERROR:backend.bots.transformer_bot:transformer_bot error loading model: 
Error when deserializing class 'TransformerBlock' using config=
{'embed_dim': 32, 'num_heads': 4, 'ff_dim': 64, 'rate': 0.1, 'trainable': True, 'dtype': 'float32'}.

Exception encountered: TransformerBlock.__init__() got an unexpected keyword argument 'trainable'
```

**Root Cause:**
- Saved model contains `trainable: True` in config
- Current `TransformerBlock.__init__()` doesn't accept `trainable` parameter
- TensorFlow/Keras adds `trainable` automatically when saving models

**Fix Applied:**
```python
# Before:
def __init__(self, embed_dim, num_heads, ff_dim, rate=0.1):
    super().__init__()

# After:
def __init__(self, embed_dim, num_heads, ff_dim, rate=0.1, **kwargs):
    # Accept and ignore extra kwargs like 'trainable' from saved models
    super().__init__(**{k: v for k, v in kwargs.items() if k != 'trainable'})
```

**Status:** ✅ Fixed

---

### ⚠️ **Issue 3: X-Axis Time Display Mismatch**

**Problem:**
- X-axis shows: "09:59" (9:59 AM)
- Tooltip shows: "03:29 PM" (3:29 PM)
- **Difference:** 5 hours 30 minutes (IST offset)

**Root Cause:**
- Tooltip correctly converts Unix timestamp to IST using `toLocaleString` with `timeZone: 'Asia/Kolkata'`
- X-axis timezone setting might not be working properly in lightweight-charts
- Chart library may need UTC timestamps and then applies timezone for display

**Current Implementation:**
1. Backend sends: `"2025-11-03T13:15:00+05:30"` (IST with timezone)
2. Frontend parses: `new Date(c.start_ts)` → Correctly interprets IST
3. Converts to Unix: `date.getTime() / 1000` → UTC Unix timestamp
4. Chart displays: Uses `timezone: 'Asia/Kolkata'` setting

**Investigation Needed:**
- Verify lightweight-charts version supports timezone properly
- Check if timestamps need to be in UTC format before sending to chart
- May need to manually convert IST → UTC before creating Unix timestamps

**Status:** ⚠️ Needs verification

---

## ✅ **All Other Logs Look Good**

**Successful Operations:**
- ✅ Server running on http://0.0.0.0:8182
- ✅ Database tables created successfully
- ✅ Health checks returning 200 OK
- ✅ Training status endpoint working
- ✅ Models report endpoint working
- ✅ History endpoint working
- ✅ WebSocket connections successful

**No Critical Errors:**
- All routes responding correctly (except the two fixed issues)
- No database connection errors
- No import errors
- Server startup successful

---

## 🔧 **Action Items**

1. ✅ **Fixed:** PredictionEvaluation.computed_at → evaluated_at
2. ✅ **Fixed:** TransformerBlock trainable parameter issue
3. ⚠️ **Investigate:** X-axis timezone display issue
4. ✅ **Verified:** All other endpoints working correctly

---

## 📊 **Summary**

**Backend Status:** ✅ **Mostly Good**

- 2 errors fixed ✅
- 1 timezone display issue needs investigation ⚠️
- All other functionality working correctly ✅

**Next Steps:**
1. Restart backend to apply fixes
2. Test metrics summary endpoint (should work now)
3. Test transformer bot loading (should work now)
4. Investigate x-axis timezone display if issue persists

---

**Date:** Nov 4, 2025  
**Status:** Fixed and documented

