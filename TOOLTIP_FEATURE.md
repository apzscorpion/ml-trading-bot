# Chart Tooltip Feature

## Overview

Rich, contextual tooltips that appear when hovering over any point on the chart, showing all relevant data at that specific time.

## What the Tooltip Shows

### 1. **Time & Date**
```
Nov 4, 02:15 PM
```
- Formatted in IST (Asia/Kolkata)
- 12-hour format with AM/PM
- Month, day, hour, and minute

### 2. **Candlestick Data** (OHLC)
```
Candlestick
Open:  ₹3,020.00
High:  ₹3,025.50  (green)
Low:   ₹3,018.75  (red)
Close: ₹3,021.40
```
- All four price points
- High in green, Low in red
- Only shows when hovering over a candle

### 3. **Actual Price** (Blue Line)
```
Actual Price
₹3,021.40
```
- Current/historical actual price
- From the blue line series
- Shows what really happened

### 4. **Predicted Price** (Red Line)
```
Predicted Price
₹3,015.80
+₹-5.60 (-0.18%)
✓ Accurate
```
- What the model predicted
- Difference from actual (if actual exists)
- Percentage difference
- Accuracy badge:
  - ✓ Accurate (< 1% error)
  - ⚠ Fair (1-3% error)
  - ✗ Poor (> 3% error)

### 5. **Historical Prediction** (Gray Line)
```
Historical Prediction
₹3,018.25
Past forecast
```
- Old predictions shown for comparison
- Helps see past prediction accuracy
- Labeled as "Past forecast"

## Tooltip Behavior

### Positioning
- **Default**: Right of cursor (+15px)
- **Near right edge**: Left of cursor (-15px - width)
- **Vertically centered**: On cursor Y position
- **Stays in bounds**: Never goes off screen

### Visibility
- Shows when hovering over chart
- Hides when cursor leaves chart
- Follows cursor smoothly
- No flickering or lag

### Smart Display
- Only shows data that exists at that point
- If no prediction → prediction section hidden
- If no candle → only shows lines
- Adapts to available data

## Visual Design

### Appearance
- Semi-transparent dark background
- Subtle border and shadow
- Backdrop blur effect
- Rounded corners (8px)
- Professional, minimal design

### Color Coding
- **Blue labels**: Actual price
- **Red labels**: Predictions
- **Gray labels**: Historical data
- **Green values**: Gains/highs
- **Red values**: Losses/lows

### Typography
- Monospace fonts for prices (SF Mono, Monaco)
- Clear hierarchy (time → data → status)
- Different font sizes for importance
- Good contrast for readability

## Use Cases

### 1. **Comparing Prediction to Reality**
Hover over any prediction point to see:
- What was predicted: ₹3,000
- What actually happened: ₹3,020
- Error: +₹20 (+0.67%)
- Status: ✓ Accurate

### 2. **Analyzing Historical Predictions**
See past predictions that were made:
- Gray line shows old forecast
- Compare to what actually happened
- Evaluate model performance over time

### 3. **Checking Candle Details**
Get exact OHLC at any moment:
- Entry/exit prices
- High/low of period
- Exact timestamps
- Price movements

### 4. **Tracking Live Candles**
During market hours:
- See forming candle data
- Current prices updating
- Predictions in real-time

## Technical Implementation

### Data Sources
```javascript
candleData    → Candlestick series
blueData      → Actual price line
redData       → Current prediction line
blackData     → Historical prediction line
```

### Crosshair Events
```javascript
chart.subscribeCrosshairMove((param) => {
  // Get time
  // Get all series data at this point
  // Format and display in tooltip
  // Position tooltip near cursor
})
```

### Time Formatting
```javascript
date.toLocaleString('en-IN', {
  timeZone: 'Asia/Kolkata',  // IST
  month: 'short',            // Nov
  day: 'numeric',            // 4
  hour: '2-digit',           // 02
  minute: '2-digit',         // 15
  hour12: true               // PM
})
```

## Example Scenarios

### Scenario 1: Hover Over Actual Price
```
┌────────────────────────┐
│ Nov 4, 10:30 AM       │
├────────────────────────┤
│ CANDLESTICK           │
│ Open:  ₹3,020.00      │
│ High:  ₹3,025.50      │
│ Low:   ₹3,018.75      │
│ Close: ₹3,021.40      │
├────────────────────────┤
│ ACTUAL PRICE          │
│ ₹3,021.40             │
└────────────────────────┘
```

### Scenario 2: Hover Over Prediction
```
┌────────────────────────┐
│ Nov 4, 11:00 AM       │
├────────────────────────┤
│ ACTUAL PRICE          │
│ ₹3,025.00             │
├────────────────────────┤
│ PREDICTED PRICE       │
│ ₹3,020.00             │
│ -₹5.00 (-0.17%)       │
│ ✓ Accurate            │
└────────────────────────┘
```

### Scenario 3: All Data Available
```
┌────────────────────────┐
│ Nov 4, 02:15 PM       │
├────────────────────────┤
│ CANDLESTICK           │
│ Open:  ₹3,020.00      │
│ High:  ₹3,025.50      │
│ Low:   ₹3,018.75      │
│ Close: ₹3,021.40      │
├────────────────────────┤
│ ACTUAL PRICE          │
│ ₹3,021.40             │
├────────────────────────┤
│ PREDICTED PRICE       │
│ ₹3,015.80             │
│ -₹5.60 (-0.18%)       │
│ ✓ Accurate            │
├────────────────────────┤
│ HISTORICAL PREDICTION │
│ ₹3,018.25             │
│ Past forecast         │
└────────────────────────┘
```

## Prediction Accuracy Indicators

### ✓ Accurate (Green)
- Error < 1%
- Highly reliable prediction
- Trade with confidence

### ⚠ Fair (Orange)
- Error 1-3%
- Moderately reliable
- Use with caution

### ✗ Poor (Red)
- Error > 3%
- Low reliability
- Don't trade on this

## Benefits

### For Traders
1. **Quick analysis** - All data at a glance
2. **Informed decisions** - See prediction accuracy
3. **Historical context** - Compare old forecasts
4. **Precise timing** - Exact timestamps

### For Analysis
1. **Evaluate models** - See prediction quality
2. **Identify patterns** - When predictions fail
3. **Compare timeframes** - Different periods
4. **Track performance** - Over time

## Keyboard Shortcuts

While hovering over chart:
- **Move mouse** - Tooltip follows
- **ESC** - Hide tooltip (leave chart)
- **Click** - Tooltip stays visible
- **Drag** - Scroll chart with tooltip

## Performance

- **Zero lag** - Instant display
- **Smooth movement** - Follows cursor
- **Efficient rendering** - No redraws
- **Memory efficient** - Single tooltip instance

## Accessibility

- High contrast colors
- Clear font sizes
- Readable typography
- Consistent positioning
- Semantic color coding

---

**Status:** ✅ Implemented  
**Version:** 1.7.0  
**Date:** Nov 4, 2025

