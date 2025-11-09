# Timezone Fix for Indian Stock Market

## Problem

Chart was showing incorrect times (7:00 AM / 7:00 PM) when NSE market isn't even open at those hours.

**NSE Trading Hours:**
- Pre-market: 9:00 AM - 9:15 AM IST
- Regular Trading: 9:15 AM - 3:30 PM IST
- Post-market: 3:40 PM - 4:00 PM IST

## Root Cause

1. Yahoo Finance returns data in IST (Asia/Kolkata timezone)
2. Conversion was removing timezone but changing the time
3. Chart library wasn't configured for IST timezone

## Solution Applied

### 1. Backend Data Fetcher (`data_fetcher.py`)

**Before:**
```python
# Was converting to UTC and changing times
ts = ts.astimezone(None).replace(tzinfo=None)
```

**After:**
```python
# Keep IST time, just remove timezone marker
if ts.tzinfo is not None:
    ts = ts.replace(tzinfo=None)  # Preserves actual IST hours
```

### 2. Chart Configuration

**Added:**
```javascript
timeScale: {
  timezone: 'Asia/Kolkata',  // Use IST for Indian stocks
}
```

### 3. Simplified Prediction Line

**Removed:**
- Large circular markers (pointMarkersRadius: 4)
- Marker visibility

**Result:**
- Clean simple line chart
- Reduced line width from 3px to 2px
- No distracting dots

## Expected Behavior

### Chart Times

**1-Minute Candles:**
```
09:15 - Market opens
09:16
09:17
...
15:29
15:30 - Market closes
```

**5-Minute Candles:**
```
09:15
09:20
09:25
...
15:25
15:30 - Last candle
```

### Outside Market Hours

**No candles should appear for:**
- Before 9:15 AM
- After 3:30 PM
- Weekends
- Market holidays

## Timezone Details

### IST (Indian Standard Time)
- UTC+5:30
- No daylight saving
- Used for NSE/BSE exchanges

### Data Flow

```
Yahoo Finance (IST)
    ↓
Backend receives (IST timestamps)
    ↓
Store in database (timezone-naive, IST hours)
    ↓
Send to frontend (IST timestamps as strings)
    ↓
Chart displays (configured for Asia/Kolkata)
    ↓
User sees correct IST times ✅
```

## Testing

### Verify Correct Times

1. Open chart with any NSE stock
2. Check x-axis timestamps
3. Should show times like:
   - 09:15, 09:20, 09:25... (morning)
   - 14:00, 14:30, 15:00... (afternoon)
   - 15:30 (market close)

### Should NOT show:
- ❌ 07:00 (7 AM)
- ❌ 19:00 (7 PM)
- ❌ 00:00 (midnight)
- ❌ Any time before 9:15 or after 15:30

## Visual Improvements

### Prediction Line

**Before:**
- Thick line (3px)
- Large dots at every point
- Cluttered appearance

**After:**
- Clean line (2px)
- No markers/dots
- Simple, professional look
- Gradient area fill still present

## Additional Notes

### Market Holidays

Even with correct timezone, data won't be available on:
- National holidays (Republic Day, Independence Day, etc.)
- Festival holidays (Diwali, Holi, etc.)
- Weekends (Saturday, Sunday)

This is expected behavior - no trading = no candles.

### Live Data

During market hours (9:15 AM - 3:30 PM IST):
- Last candle updates in real-time
- Timestamps match current IST time
- New candles appear at correct intervals

### Historical Data

For historical candles:
- All timestamps in IST
- Matches actual trading times
- No artificial time shifts

---

**Status:** ✅ Fixed  
**Version:** 1.6.0  
**Date:** Nov 4, 2025

