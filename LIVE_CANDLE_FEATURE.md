# Live Candle Updates Feature

## 🕐 Real-Time Candle Formation (Like TradingView)

### Feature Overview

Each candlestick now updates in **real-time** as it forms, showing live price action:

- ✅ **1m candle** → Updates every second as prices change
- ✅ **5m candle** → Updates continuously within the 5-minute period
- ✅ **15m candle** → Updates live during the 15-minute window
- ✅ Live OHLC (Open, High, Low, Close) updates
- ✅ Visual indication of "forming" vs "completed" candles

### How It Works

#### 1. Candle States

**Live Candle (Forming):**
- Current candle that's still within its timeframe
- Updates in real-time as prices change
- High/Low adjust based on price movements
- Close updates with latest price
- Tagged with `isLive: true`

**Completed Candle:**
- Timeframe period has ended
- Values are final and don't change
- Tagged with `isLive: false`

#### 2. Update Flow

```
Market Price Changes
    ↓
WebSocket sends update
    ↓
Frontend receives candle data
    ↓
Check: Same timestamp? 
    ├─ YES → Update existing candle (LIVE UPDATE)
    └─ NO  → Mark old as complete, add new (NEW CANDLE)
    ↓
Chart redraws with updated candle
```

#### 3. Technical Implementation

**Backend (WebSocket):**
```python
# Sends candle updates every 5-30 seconds
{
  "type": "candle:update",
  "symbol": "TCS.NS",
  "timeframe": "5m",
  "candle": {
    "start_ts": "2025-11-03T12:05:00",
    "open": 3020.00,
    "high": 3025.50,  # Updates as new high
    "low": 3018.75,   # Updates as new low
    "close": 3021.40, # Updates with latest price
    "volume": 45000
  }
}
```

**Frontend (Chart Update):**
```javascript
// Find existing candle by timestamp
const existingIndex = candles.findIndex(
  c => c.start_ts === newCandle.start_ts
)

if (existingIndex >= 0) {
  // LIVE UPDATE - same timestamp, candle still forming
  candles[existingIndex] = { ...newCandle, isLive: true }
} else {
  // NEW CANDLE - previous completed, new one started
  candles.push({ ...newCandle, isLive: true })
}
```

### Timeframe Examples

#### 1-Minute Candles (1m)
```
12:00:00 - Candle starts
12:00:15 - Update (high: 3022, close: 3021)
12:00:30 - Update (high: 3023, close: 3022)
12:00:45 - Update (high: 3023, close: 3020)
12:01:00 - Candle completes, new one starts
```

#### 5-Minute Candles (5m)
```
12:00:00 - Candle starts
12:01:00 - Update (price changes)
12:02:00 - Update (new high)
12:03:00 - Update (price dips)
12:04:00 - Update (recovering)
12:05:00 - Candle completes, new one starts
```

### Console Logging

**Live candle updates show in console:**
```javascript
📊 Live candle update received: {
  symbol: "TCS.NS",
  timeframe: "5m",
  time: "2025-11-03T12:05:00",
  close: 3021.40
}

Live candle update: {
  time: "2025-11-03T12:05:00",
  close: 3021.40,
  isLive: true
}
```

### Visual Indicators

While the chart library doesn't show explicit "live" indicators by default, the candle:
- **Updates smoothly** without flickering
- **Redraws** with new OHLC values
- **Last candle** is always the "live" one

### Data Structure

```javascript
{
  start_ts: "2025-11-03T12:05:00",
  open: 3020.00,
  high: 3025.50,
  low: 3018.75,
  close: 3021.40,
  volume: 45000,
  isLive: true  // ← Indicates candle is still forming
}
```

### Benefits

1. **Immediate Feedback** - See price changes instantly
2. **Better Trading Decisions** - Watch candle formation in real-time
3. **Professional Feel** - Matches TradingView behavior
4. **Accurate Data** - High/Low adjust as prices move

### Timeframe-Specific Behavior

| Timeframe | Update Frequency | Candle Duration |
|-----------|-----------------|-----------------|
| 1m        | Every 1-5 sec   | 60 seconds      |
| 5m        | Every 5-10 sec  | 5 minutes       |
| 15m       | Every 10-15 sec | 15 minutes      |
| 1h        | Every 30-60 sec | 1 hour          |
| 1d        | Every 1-5 min   | 1 day           |

### WebSocket Configuration

**Current Settings:**
- Heartbeat: Every 30 seconds
- Update interval: Depends on market data frequency
- Auto-reconnect: Yes
- Validation: Symbol + timeframe matching

### Testing Live Updates

1. **Open the app** with any stock
2. **Watch the last candle** on the chart
3. **It should update** as prices change
4. **Open console** (F12) to see update logs
5. **Wait for timeframe to complete** (e.g., 5 minutes for 5m)
6. **New candle appears** when period ends

### Accuracy

- **Source:** Yahoo Finance via yfinance library
- **Latency:** 5-30 seconds depending on data provider
- **Updates:** Real-time during market hours (9:15 AM - 3:30 PM IST)
- **After Hours:** No updates (market closed)

---

**Feature Status:** ✅ Implemented  
**Version:** 1.4.0  
**Date:** Nov 3, 2025

