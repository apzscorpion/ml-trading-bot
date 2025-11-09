# Watchlist & Live Candle Features - Complete Guide

## 🎯 New Features Overview

### 1. 📋 Watchlist Sidebar
Track and quickly switch between your favorite stocks

### 2. 🕐 Live Candle Updates  
Real-time candle formation (like TradingView)

### 3. ⏱️ Extended Timeframes
Now includes: 1m, 5m, 15m, 1h, 4h, 1d, **5d**, 1wk, 1mo, **3mo**

---

## 📋 Watchlist Feature

### What It Does

A **persistent sidebar** showing your favorite stocks with:
- ✅ Quick one-click switching between stocks
- ✅ Live price updates (when available)
- ✅ Percentage change indicators (green/red)
- ✅ Exchange badges (NSE/BSE)
- ✅ Add/remove stocks easily
- ✅ Saved to localStorage (persists across sessions)

### Location

**Right sidebar** - Always visible, sticky on scroll

### Features

#### Default Stocks
- TCS (Tata Consultancy Services)
- RELIANCE (Reliance Industries)
- HDFCBANK (HDFC Bank)

#### Add New Stock
1. Click **➕** button in watchlist header
2. Search dialog opens
3. Type stock name or symbol
4. Select from dropdown
5. Stock added to watchlist

#### Remove Stock
1. Click **✕** button on any stock item
2. Confirm removal
3. Stock removed from watchlist

#### Switch Stocks
1. Click any stock in watchlist
2. Chart instantly loads that stock
3. Active stock highlighted in blue

### Visual Design

```
┌─────────────────────────┐
│ 📋 Watchlist       ➕   │
├─────────────────────────┤
│ TCS          NSE        │ ← Active (blue highlight)
│ Tata Consultancy...     │
│ ₹3,021.20    +0.10%    │
├─────────────────────────┤
│ RELIANCE     NSE        │
│ Reliance Industries     │
│ ₹2,450.50    -0.25%    │
├─────────────────────────┤
│ HDFCBANK     NSE        │
│ HDFC Bank Ltd           │
│ ₹1,650.75    +0.45%    │
└─────────────────────────┘
```

### Data Structure

```javascript
{
  symbol: "TCS.NS",
  name: "Tata Consultancy Services",
  exchange: "NSE",
  price: 3021.20,
  change: 0.10,
  changePercent: 0.01
}
```

### Persistence

**Saved to localStorage:**
```javascript
key: 'watchlist'
value: JSON.stringify([...stocks])
```

**Loads automatically on page refresh!**

---

## 🕐 Live Candle Updates

### What It Does

Each candlestick **updates in real-time** as it forms, just like TradingView!

### How It Works

#### 1-Minute Candle (1m)
```
Time: 12:00:00
├─ 12:00:00 - Candle opens at ₹3,020
├─ 12:00:15 - Price ₹3,022 (high updates)
├─ 12:00:30 - Price ₹3,019 (low updates)
├─ 12:00:45 - Price ₹3,021 (close updates)
└─ 12:01:00 - Candle completes, new one starts
```

#### 5-Minute Candle (5m)
```
Time: 12:00:00
├─ 12:01:00 - Update 1 (price changes)
├─ 12:02:00 - Update 2 (new high)
├─ 12:03:00 - Update 3 (price dips)
├─ 12:04:00 - Update 4 (recovering)
└─ 12:05:00 - Candle completes, new one starts
```

### Candle States

**🟢 Live (Forming):**
- Current candle within its timeframe
- OHLC values update continuously
- Tagged: `isLive: true`
- Last candle on the chart

**🔵 Completed:**
- Timeframe period ended
- Values are final
- Tagged: `isLive: false`
- All previous candles

### Update Frequency

| Timeframe | Update Interval | Candle Duration |
|-----------|----------------|-----------------|
| 1m        | 1-5 seconds    | 60 seconds      |
| 5m        | 5-10 seconds   | 5 minutes       |
| 15m       | 10-15 seconds  | 15 minutes      |
| 1h        | 30-60 seconds  | 1 hour          |
| 1d        | 1-5 minutes    | 1 day           |

### Console Logs

When live updates happen, you'll see:
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

### Visual Behavior

- **Smooth updates** without flickering
- **OHLC changes** visible in real-time
- **High/Low wicks** adjust as prices move
- **Volume** accumulates during candle formation

---

## ⏱️ Extended Timeframes

### All Available Timeframes

| Timeframe | Display | Yahoo Finance Period | Best For |
|-----------|---------|---------------------|----------|
| 1m        | 1 min   | 1 day               | Scalping |
| 5m        | 5 min   | 5 days              | Day trading |
| 15m       | 15 min  | 5 days              | Intraday |
| 1h        | 1 hour  | 1 month             | Swing trading |
| 4h        | 4 hours | 3 months            | Position trading |
| 1d        | 1 day   | 2 years             | Long-term |
| **5d**    | 5 days  | 2 years             | Weekly view |
| 1wk       | 1 week  | 5 years             | Trend analysis |
| 1mo       | 1 month | 10 years            | Macro trends |
| **3mo**   | 3 months| 10 years            | Long-term trends |

### New Timeframes Added

✅ **5d (5 days)** - Weekly overview with daily candles  
✅ **3mo (3 months)** - Quarterly analysis

### Use Cases

**1m, 5m, 15m** - Day Trading
- Real-time price action
- Quick entries/exits
- Scalping opportunities

**1h, 4h** - Swing Trading  
- Medium-term trends
- Better signal quality
- Less noise

**1d, 5d, 1wk** - Position Trading
- Long-term trends
- Major support/resistance
- Portfolio decisions

**1mo, 3mo** - Investment Analysis
- Macro trends
- Long-term patterns
- Strategic planning

---

## 🎨 UI Layout Changes

### Grid Layout

```
┌────────────────────────────────────┬──────────┐
│                                    │          │
│         Main Content               │ Watch    │
│         (Chart, Controls)          │ list     │
│                                    │          │
│                                    │ (Sticky) │
│                                    │          │
└────────────────────────────────────┴──────────┘
        1400px                         300px
```

### Responsive Design

- **Desktop:** Full layout with sidebar
- **Tablet:** Sidebar becomes collapsible
- **Mobile:** Sidebar becomes bottom sheet

---

## 🔧 Technical Implementation

### Backend Changes

**1. Extended Timeframes**
```python
# backend/config.py
supported_timeframes = [
    "1m", "5m", "15m", "1h", "4h", 
    "1d", "5d", "1wk", "1mo", "3mo"
]

# backend/bots/base_bot.py
interval_map = {
    '5d': 1440,    # Daily candles
    '3mo': 129600  # ~90 days
}
```

**2. Live Updates**
```python
# WebSocket sends candle updates
@app.websocket("/ws")
async def websocket_endpoint():
    # Sends candle:update messages
    await websocket.send_json({
        "type": "candle:update",
        "symbol": "TCS.NS",
        "timeframe": "5m",
        "candle": {...}
    })
```

### Frontend Changes

**1. Watchlist Component**
```vue
// components/Watchlist.vue
- Stock list with live prices
- Add/remove functionality
- localStorage persistence
- Click to switch stocks
```

**2. Live Candle Handler**
```javascript
// App.vue
handleCandleUpdate(message) {
  // Check if same timestamp → Update
  // Different timestamp → New candle
  // Mark old as complete
  // Update chart in real-time
}
```

**3. Grid Layout**
```css
.main-content {
  display: grid;
  grid-template-columns: 1fr 300px;
  /* Main content | Watchlist */
}
```

---

## 📊 Testing

### Test Watchlist

1. ✅ Add TCS to watchlist
2. ✅ Add RELIANCE to watchlist
3. ✅ Click TCS → Should load TCS chart
4. ✅ Click RELIANCE → Should switch to RELIANCE
5. ✅ Remove stock → Should disappear
6. ✅ Refresh page → Watchlist should persist

### Test Live Candles

1. ✅ Select 1m timeframe
2. ✅ Watch last candle on chart
3. ✅ Open console (F12)
4. ✅ See "📊 Live candle update received"
5. ✅ Candle should update every few seconds
6. ✅ Wait 1 minute → New candle appears

### Test Timeframes

1. ✅ Try 1m → Should show intraday data
2. ✅ Try 5d → Should show 5 days of daily candles
3. ✅ Try 3mo → Should show 3 months of data
4. ✅ Each should load appropriate historical data

---

## 🚀 Performance

### Optimizations

- **Lazy loading** - Only active stock loads data
- **Debouncing** - Updates throttled to prevent spam
- **Efficient rendering** - Chart updates, not full redraw
- **localStorage** - Fast watchlist loading
- **WebSocket** - Single connection for all updates

### Memory Usage

- Watchlist: < 1KB
- Candles: ~500KB for 2000 candles
- Updates: Minimal per message

---

## 🐛 Known Issues & Solutions

### Issue: Watchlist not showing prices

**Solution:** Prices require live data. Will show "Loading..." until data arrives.

### Issue: Live updates not working

**Check:**
1. Is WebSocket connected? (Check header status)
2. Is market open? (9:15 AM - 3:30 PM IST)
3. Check console for error messages

### Issue: Timeframes not loading

**Check:**
1. Is symbol valid?
2. Does Yahoo Finance support that symbol/timeframe combo?
3. Check network tab for API errors

---

## 📝 Future Enhancements

### Potential Features

1. **Watchlist Groups** - Organize stocks by sector
2. **Price Alerts** - Notifications when price hits target
3. **Notes** - Add notes to each watchlist stock
4. **Sorting** - Sort by price change, volume, etc.
5. **Import/Export** - Share watchlists
6. **Real-time Prices** - More frequent updates
7. **Candle Patterns** - Auto-detect patterns
8. **Live Prediction Updates** - Predictions update with candles

---

## 🎯 Summary

### What You Get

✅ **Watchlist** - Track favorite stocks, quick switching  
✅ **Live Candles** - Real-time candle formation  
✅ **10 Timeframes** - From 1m to 3mo  
✅ **Persistent State** - Everything saved  
✅ **Professional UI** - Clean, modern design  
✅ **Real-time Data** - Live market updates  

### Ready to Use!

1. **Add stocks to watchlist** (click ➕)
2. **Select timeframe** (1m, 5m, 1d, etc.)
3. **Watch live candles form** in real-time
4. **Switch stocks** with one click
5. **Generate predictions** as usual

---

**Version:** 1.5.0  
**Date:** Nov 3, 2025  
**Status:** ✅ All Features Implemented  
**No Linting Errors:** ✅

