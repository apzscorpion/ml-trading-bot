# 🚀 Quick Start Guide

Get your AI Trading Prediction Chart running in 5 minutes!

## Prerequisites

- Python 3.8+ installed
- Node.js 16+ and npm installed
- Terminal access

## Step 1: Backend Setup (2 minutes)

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python database.py
```

## Step 2: Start Backend (30 seconds)

```bash
# Make sure you're in the backend directory with venv activated
python main.py
```

You should see:
```
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
```

✅ Backend is running! Leave this terminal open.

API Documentation: http://localhost:8000/docs

## Step 3: Frontend Setup (2 minutes)

Open a **NEW terminal window**:

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install
```

## Step 4: Start Frontend (30 seconds)

```bash
# Make sure you're in the frontend directory
npm run dev
```

You should see:
```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:3000/
```

✅ Frontend is running!

## Step 5: Open the App

1. Open your browser
2. Go to: **http://localhost:3000**
3. You should see the Trading Prediction Chart! 🎉

## First Prediction

1. The app loads with **TCS.NS** (Tata Consultancy Services) by default
2. Click **"🔮 Generate Prediction"** button
3. Wait a few seconds while the AI bots analyze the data
4. Watch the red prediction line appear on the chart!

## Understanding the Chart

- **Candlesticks**: Historical price data (green = up, red = down)
- **Blue Line**: Actual closing prices
- **Red Line**: AI predictions for the next 3 hours
- **Bot Panel**: Shows which AI bots contributed and their confidence

## Trying Different Stocks

1. Click the **Symbol** dropdown
2. Select another Indian stock (e.g., RELIANCE.NS, INFY.NS)
3. The chart will reload with new data
4. Generate a new prediction!

## Changing Timeframe

Click the timeframe buttons:
- **1m**: 1-minute candles (most detailed)
- **5m**: 5-minute candles (default)
- **15m**: 15-minute candles
- **1h**: 1-hour candles (broader view)

## Adjusting Prediction Horizon

Use the slider to change how far ahead you want predictions:
- Minimum: 30 minutes
- Maximum: 6 hours (360 minutes)
- Default: 3 hours (180 minutes)

## Real-time Updates

The app automatically:
- Connects via WebSocket (see green "Connected" indicator)
- Receives new candle data every 5 minutes
- Updates predictions automatically
- No refresh needed!

## Using Helper Scripts (Optional)

### Backend
```bash
cd backend
./run.sh
```

### Frontend
```bash
cd frontend
./run.sh
```

## Troubleshooting

### Backend won't start?
```bash
# Make sure virtual environment is activated
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies again
pip install -r requirements.txt

# Check Python version (needs 3.8+)
python --version
```

### Frontend won't start?
```bash
# Delete node_modules and reinstall
rm -rf node_modules
npm install

# Check Node version (needs 16+)
node --version
```

### Can't connect to backend?
- Make sure backend is running on port 8000
- Check http://localhost:8000/health in your browser
- Look for error messages in the backend terminal

### Charts not showing?
- Open browser Developer Tools (F12)
- Check Console tab for errors
- Make sure you clicked "Generate Prediction"

## What's Happening Behind the Scenes?

1. **Data Fetching**: Yahoo Finance API provides Indian stock data
2. **AI Bots**: 4 different prediction bots analyze the data:
   - RSI Bot (momentum patterns)
   - MACD Bot (trend analysis)
   - MA Bot (moving average crossovers)
   - ML Bot (machine learning features)
3. **Freddy Merger**: Combines all predictions intelligently
4. **WebSocket**: Pushes real-time updates to your browser
5. **Evaluation**: Compares predictions to actual prices later

## Next Steps

- Try different stocks and timeframes
- Watch how bot confidence changes
- Compare predictions to actual price movements
- Check the metrics panel for accuracy stats
- Explore the API docs at http://localhost:8000/docs

## Need Help?

- Check the main README.md for detailed documentation
- Review the API documentation at http://localhost:8000/docs
- Look at browser console for frontend errors
- Check backend terminal for server errors

---

Enjoy predicting! 📈🤖

