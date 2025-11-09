# 📈 ML Trading Bot

A full-stack AI-powered trading prediction system that displays real-time candlestick charts with advanced machine learning models for Indian stocks (NSE/BSE).

## 🎯 Features

### ✨ New Advanced Features
- **🔥 Deep Learning Models**: LSTM and Transformer neural networks for accurate predictions
- **🧠 Ensemble ML**: Random Forest, Gradient Boosting, and Ridge regression models
- **📊 Dynamic Historical Loading**: Automatically loads more data when zooming out on charts
- **🎯 Multiple Prediction Modes**: Choose specific models or combine them all
- **🎓 Model Training**: Train deep learning models directly from the UI
- **⏱️ Per-Minute Predictions**: Each model generates minute-by-minute price predictions

### Core Features
- **Real-time Candlestick Charts** using lightweight-charts
- **Three Visual Series**:
  - 🔵 Blue Line: Actual/live prices
  - 🔴 Red Line: Current AI predictions
  - ⚫ Black Line: Historical predictions (for validation)
- **7 AI Prediction Bots**:
  - RSI Bot (Momentum-based)
  - MACD Bot (Trend-based)
  - Moving Average Bot (Crossover signals)
  - ML Bot (Prophet time-series)
  - **LSTM Bot (Deep Learning)**
  - **Transformer Bot (Attention Mechanism)**
  - **Ensemble Bot (ML Ensemble)**
- **Freddy API**: Intelligent merger that combines all bot predictions using weighted averaging
- **WebSocket Updates**: Real-time candle and prediction updates
- **Evaluation System**: RMSE, MAE, and directional accuracy metrics
- **Bot Performance Dashboard**: See which bots perform best

## 🏗️ Architecture

### Backend (Python FastAPI)
- **Database**: SQLite with SQLAlchemy ORM
- **Data Source**: Yahoo Finance API (yfinance) for Indian stocks
- **WebSocket**: Real-time updates using FastAPI WebSocket
- **Background Scheduler**: APScheduler for periodic data fetch and predictions
- **Prediction Engine**: Multiple bots + Freddy merger

### Frontend (Vue 3)
- **Charts**: lightweight-charts for candlestick visualization
- **WebSocket Client**: Real-time connection to backend
- **UI**: Modern dark theme with controls for symbol, timeframe, and prediction horizon

## 🌐 Network Access

### Quick Start with Network Info

The app now automatically displays your network IP when starting:

```bash
# Start backend (shows network IP on startup)
cd backend
python main.py

# Start frontend (shows network IP on startup)
cd frontend
npm run dev

# OR use the convenience script to start both
./start-with-network-info.sh
```

### Access from Other Devices

**From your local machine:**
- Frontend: `http://localhost:5155`
- Backend: `http://localhost:8182`

**From other devices on your network (phones, tablets, other computers):**
- Frontend: `http://YOUR_IP:5155`
- Backend: `http://YOUR_IP:8182`
- API Docs: `http://YOUR_IP:8182/docs`

**Check your current network IP:**
```bash
./check-network-ip.sh
```

### Network Configuration

Both services are configured to accept network connections:
- ✅ Backend: Binds to `0.0.0.0:8182` (all network interfaces)
- ✅ Frontend: Binds to `0.0.0.0:5155` (all network interfaces)
- ✅ CORS: Configured to allow network origins

See `NETWORK_ACCESS.md` for detailed network setup and troubleshooting.

## 🔌 Network Ports & Services

This application uses the following ports:

| Service | Port | Protocol | Purpose |
|---------|------|----------|---------|
| **Frontend (Vite Dev Server)** | **5155** | HTTP | Main UI application, serves Vue.js frontend |
| **Backend (FastAPI)** | **8182** | HTTP | REST API for predictions, history, and evaluations |
| **WebSocket** | **8182** | WebSocket | Real-time candle and prediction updates (same port as backend) |
| **Database** | N/A | File-based | SQLite database (trading_predictions.db) |

### Port Configuration Details

#### Frontend (Port 5155)
- Access the UI at: `http://localhost:5155`
- Vite development server with hot module replacement
- Proxies API calls to backend automatically
- Proxies WebSocket connections to backend

#### Backend (Port 8182)
- REST API base: `http://localhost:8182/api`
- API Documentation: `http://localhost:8182/docs` (Swagger UI)
- WebSocket endpoint: `ws://localhost:8182/ws`
- Health check: `http://localhost:8182/health`

#### WebSocket Communication
- Frontend connects via: `ws://localhost:5155/ws` (proxied by Vite)
- Backend listens on: `ws://localhost:8182/ws`
- Real-time updates for:
  - New candle data
  - Prediction results
  - Model training progress

### How Services Communicate

```
┌─────────────────────────────────────────────────────┐
│  User Browser                                       │
│  http://localhost:5155                              │
└───────────────┬─────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────┐
│  Frontend (Vite Dev Server) - Port 5155             │
│  - Serves Vue.js application                        │
│  - Proxies /api → http://localhost:8182             │
│  - Proxies /ws → ws://localhost:8182                │
└───────────────┬─────────────────────────────────────┘
                │
                │ REST API + WebSocket
                ▼
┌─────────────────────────────────────────────────────┐
│  Backend (FastAPI) - Port 8182                      │
│  - REST API endpoints                               │
│  - WebSocket server                                 │
│  - Prediction engine (7 bots + Freddy merger)      │
│  - Background scheduler                             │
└───────────────┬─────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────┐
│  SQLite Database                                    │
│  trading_predictions.db                             │
│  - Candles, Predictions, Evaluations                │
└─────────────────────────────────────────────────────┘
```

### Changing Default Ports

If you need to change the default ports:

1. **Frontend Port (5155)**:
   - Edit `frontend/vite.config.js`
   - Change `server.port: 5155` to your desired port

2. **Backend Port (8182)**:
   - Edit `backend/main.py` (line 320)
   - Change `port=8182` in the uvicorn.run() call
   - Also update `frontend/vite.config.js` proxy targets

## 📦 Installation

### Backend Setup

1. **Navigate to backend directory**:
```bash
cd backend
```

2. **Create virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Create .env file** (copy from .env.example):
```bash
cp .env.example .env
```

Edit `.env` if needed. Key settings:
```
DATABASE_URL=sqlite:///./trading_predictions.db
DEFAULT_SYMBOL=TCS.NS
PREDICTION_INTERVAL=300
YAHOO_FINANCE_INTERVAL=5m
LOG_LEVEL=INFO

# Redis (Optional - falls back to in-memory cache if not available)
REDIS_ENABLED=true
REDIS_HOST=localhost
REDIS_PORT=6379
```

**Note**: Redis is optional. If Redis is not installed or unavailable, the system will automatically fall back to in-memory LRU cache. To disable Redis, set `REDIS_ENABLED=false` in `.env`.

5. **Initialize database**:
```bash
python database.py
```

6. **Run backend server**:
```bash
python main.py
```

Backend will run on `http://localhost:8182`
- API docs: http://localhost:8182/docs
- WebSocket: ws://localhost:8182/ws
- Health check: http://localhost:8182/health

### Frontend Setup

1. **Navigate to frontend directory**:
```bash
cd frontend
```

2. **Install dependencies**:
```bash
npm install
```

3. **Run development server**:
```bash
npm run dev
```

Frontend will run on `http://localhost:5155`

## 🚀 Quick Start (Recommended)

### One-Command Startup 🎯

Use the automated startup script that handles everything:

```bash
# From project root
./start.sh
```

This script will:
- ✅ Check and stop any existing services on ports 8182 and 5155
- ✅ Verify and install all dependencies
- ✅ Initialize database if needed
- ✅ Start backend server (port 8182)
- ✅ Start frontend server (port 5155)
- ✅ Display all service URLs
- ✅ Tail logs from both services in real-time

Then open your browser to **http://localhost:5155**

### Managing Services

```bash
# Start everything
./start.sh

# Check status
./status.sh

# Stop everything
./stop.sh

# View logs
tail -f logs/backend.log
tail -f logs/frontend.log
tail -f logs/combined.log
```

📖 **For detailed script documentation, see [SCRIPTS_GUIDE.md](SCRIPTS_GUIDE.md)**

---

## 🛠️ Manual Usage (Alternative)

If you prefer to start services manually:

### Backend
```bash
cd backend
source venv/bin/activate
python main.py
# Runs on http://localhost:8182
```

### Frontend
```bash
cd frontend
npm run dev
# Runs on http://localhost:5155
```

### Individual Shell Scripts
```bash
# Backend
cd backend
./run.sh

# Frontend
cd frontend
./run.sh
```

### Using the App

1. **Select Symbol**: Choose an Indian stock (NSE symbols like TCS.NS, RELIANCE.NS)
2. **Select Timeframe**: Choose 1m, 5m, 15m, or 1h candle intervals
3. **Adjust Prediction Horizon**: Use the slider to set prediction horizon (30-360 minutes)
4. **Choose Prediction Mode**:
   - 📊 **Technical Analysis**: Uses RSI, MACD, MA bots
   - 🧠 **ML Models**: Uses Prophet and Ensemble bots
   - 🔥 **LSTM + Transformer**: Deep learning models
   - 🚀 **Full Ensemble**: All 7 models combined
5. **Train Models** (Optional):
   - Click "🎓 Train DL Models" to train LSTM, Transformer, and Ensemble
   - Training uses up to 5000 historical candles
   - Takes 1-2 minutes depending on data size
6. **View Results**:
   - Blue line shows actual prices
   - Red line shows AI predictions (minute-by-minute)
   - Bot contributions panel shows which bots contributed and their confidence
   - Metrics panel shows accuracy statistics
7. **Zoom & Explore**:
   - Zoom out on chart to automatically load more historical data
   - Up to 2000 candles kept in memory
   - Seamless historical data loading

### WebSocket Updates

The app automatically connects via WebSocket and receives:
- New candle updates every 5 minutes
- New predictions when generated
- Updates are shown in real-time on the chart

## 📊 Prediction Bots

### Technical Indicator Bots

#### 1. RSI Bot (Momentum)
- Uses Relative Strength Index (RSI)
- Identifies overbought/oversold conditions
- Confidence: 0.6-0.9 based on RSI extremity
- **Per-minute predictions** with momentum analysis

#### 2. MACD Bot (Trend)
- Uses Moving Average Convergence Divergence
- Detects trend changes via crossovers
- Confidence: 0.5-0.85 based on histogram strength
- **Minute-by-minute trend following**

#### 3. Moving Average Bot (Crossover)
- Uses SMA(20), SMA(50), EMA(21)
- Identifies golden/death crosses
- Confidence: 0.5-0.95 based on MA separation
- **Real-time crossover detection**

### Machine Learning Bots

#### 4. ML Bot (Prophet)
- Facebook Prophet time-series model
- Seasonal decomposition and trend analysis
- Confidence: 0.3-1.0 based on recent accuracy
- **Minute-level granularity**

#### 5. **LSTM Bot (Deep Learning)** ⚡
- **Long Short-Term Memory neural network**
- Uses last 60 candles as sequence input
- 3-layer LSTM architecture with dropout
- Features: OHLCV data
- Confidence: 0.70-0.80
- **Trainable model** with 50 epochs default
- **Per-minute recursive predictions**

#### 6. **Transformer Bot (Attention)** 🔥
- **Multi-head attention mechanism**
- Position encoding for time-series
- 2 transformer blocks with 4 attention heads
- Enhanced features with technical indicators
- Confidence: 0.73-0.83
- **Trainable model** with 30 epochs default
- **Sequential minute predictions**

#### 7. **Ensemble Bot (ML Ensemble)** 🧠
- Combines 3 classical ML models:
  - Random Forest (100 trees)
  - Gradient Boosting (100 estimators)
  - Ridge Regression
- **40+ engineered features**:
  - Moving averages (5, 10, 20 periods)
  - RSI, Bollinger Bands
  - Momentum, volatility
  - Volume indicators
- Weighted ensemble (RF: 40%, GB: 35%, Ridge: 25%)
- Confidence: 0.77-0.87
- **Trainable on 5000+ candles**
- **Most accurate predictions**

### Freddy Merger 🤖
- Combines selected bot predictions using weighted averaging
- Weights based on individual bot confidence scores
- Supports selective bot execution
- Returns merged prediction series with overall confidence
- **Can use specific models or all 7 models together**

## 🗄️ Database Schema

### Candles Table
- Stores OHLCV candle data
- Indexed by symbol, timeframe, and timestamp

### Predictions Table
- Stores all predictions with bot contributions
- Includes confidence scores and metadata

### Prediction Evaluations Table
- Stores metrics comparing predictions vs actuals
- RMSE, MAE, MAPE, directional accuracy

## 🔌 API Endpoints

### History
- `GET /api/history` - Fetch historical candles
- `GET /api/history/latest` - Get latest candle
- `GET /api/history/symbols` - List available symbols

### Predictions
- `POST /api/prediction/trigger` - Generate new prediction (with optional `selected_bots` parameter)
- `GET /api/prediction/latest` - Get latest prediction
- `GET /api/prediction/{id}` - Get specific prediction
- `GET /api/prediction/history/all` - Get prediction history
- `GET /api/prediction/bots/available` - List all available bots
- `POST /api/prediction/train` - Train a specific bot model

### Evaluation
- `POST /api/evaluation/evaluate/{id}` - Evaluate a prediction
- `GET /api/evaluation/bot-performance` - Get bot performance metrics
- `GET /api/evaluation/metrics/summary` - Get accuracy summary

### WebSocket
- `ws://localhost:8182/ws` - WebSocket endpoint (direct)
- `ws://localhost:5155/ws` - WebSocket endpoint (via Vite proxy, used by frontend)
- Messages:
  - Subscribe: `{"action": "subscribe", "symbol": "TCS.NS", "timeframe": "5m"}`
  - Unsubscribe: `{"action": "unsubscribe"}`
  - Ping: `{"action": "ping"}`
- Server messages:
  - Subscribed confirmation: `{"type": "subscribed", "symbol": "...", "timeframe": "..."}`
  - Candle updates: `{"type": "candle:update", "symbol": "...", "candle": {...}}`
  - Prediction updates: `{"type": "prediction:update", "symbol": "...", "predicted_series": [...]}`
  - Pong response: `{"type": "pong"}`

## 🎨 Indian Stock Symbols

The app supports NSE and BSE stocks:
- **NSE**: Add `.NS` suffix (e.g., `TCS.NS`, `RELIANCE.NS`)
- **BSE**: Add `.BO` suffix (e.g., `RELIANCE.BO`)

Pre-configured popular stocks:
- TCS.NS, RELIANCE.NS, HDFCBANK.NS, INFY.NS, ICICIBANK.NS
- HINDUNILVR.NS, ITC.NS, SBIN.NS, BHARTIARTL.NS, KOTAKBANK.NS

## 📈 Metrics & Evaluation

The system automatically evaluates predictions when actual data becomes available:

- **RMSE**: Root Mean Square Error
- **MAE**: Mean Absolute Error
- **MAPE**: Mean Absolute Percentage Error
- **Directional Accuracy**: % of correct price direction predictions

View metrics in:
1. Frontend metrics panel
2. `/api/evaluation/bot-performance` endpoint
3. `/api/evaluation/metrics/summary` endpoint

## ⚙️ Configuration

### Backend Configuration (config.py)
- `PREDICTION_INTERVAL`: How often to fetch data and predict (seconds)
- `DEFAULT_SYMBOL`: Default stock symbol
- `YAHOO_FINANCE_INTERVAL`: Candle interval for data fetching
- `DEFAULT_HORIZON_MINUTES`: Default prediction horizon

### Timeframe Support
- 1m: 1-minute candles (intraday)
- 5m: 5-minute candles (default)
- 15m: 15-minute candles
- 1h: 1-hour candles

## 🐛 Troubleshooting

### Backend Issues

**"No module named 'backend'"**
- Make sure you're in the correct directory
- Run: `export PYTHONPATH="${PYTHONPATH}:$(pwd)"`

**Yahoo Finance rate limits**
- Data is cached for 1 minute
- Reduce `PREDICTION_INTERVAL` if needed
- Consider using different data sources for production

**Database locked error**
- Close other connections to the database
- Delete `trading_predictions.db` and reinitialize

### Frontend Issues

**WebSocket connection failed**
- Ensure backend is running on port 8182 (`http://localhost:8182/health` should respond)
- Ensure frontend is running on port 5155
- Frontend automatically proxies WebSocket through Vite dev server
- Check browser console for connection errors
- Verify proxy configuration in `frontend/vite.config.js`
- Look for CORS issues in browser console

**Port already in use**
- Backend port 8182 busy: `lsof -i :8182` to find process, then kill it
- Frontend port 5155 busy: `lsof -i :5155` to find process, then kill it
- Or change ports in respective config files

**Charts not rendering**
- Check browser console for errors
- Ensure candle data is being received
- Verify lightweight-charts is installed

## 🎯 Technical Details

### Deep Learning Architecture

#### LSTM Bot
```
- Input: (batch, 60, 5) - 60 timesteps, 5 features (OHLCV)
- LSTM Layer 1: 128 units, return sequences
- Dropout: 0.2
- LSTM Layer 2: 64 units, return sequences
- Dropout: 0.2
- LSTM Layer 3: 32 units
- Dropout: 0.2
- Dense: 32 units (ReLU)
- Dense: 16 units (ReLU)
- Output: 1 unit (price prediction)
- Loss: Huber loss
- Optimizer: Adam (lr=0.001)
```

#### Transformer Bot
```
- Input: (batch, 50, 7) - 50 timesteps, 7 features
- Position Encoding: Learnable embeddings
- Projection: Dense(32)
- Transformer Block 1: 4 heads, 64 FFN dim
- Transformer Block 2: 4 heads, 64 FFN dim
- Global Average Pooling
- Dense: 64 units (ReLU) + Dropout(0.3)
- Dense: 32 units (ReLU) + Dropout(0.2)
- Output: 1 unit
- Loss: Huber loss
- Optimizer: Adam (lr=0.0005)
```

### Feature Engineering (Ensemble Bot)
- Price features: OHLC, volume
- Moving averages: 5, 10, 20 periods
- Returns: 1-period and 5-period
- Volatility: 10 and 20 period rolling std
- RSI: 14-period
- Bollinger Bands: 20-period, 2 std
- Momentum: 5 and 10 period
- Volume moving average

## 🚧 Future Enhancements

- [x] ~~Add deep learning models (LSTM, Transformer)~~
- [x] ~~Ensemble ML models~~
- [x] ~~Per-minute predictions~~
- [x] ~~Dynamic historical data loading~~
- [x] ~~Model training interface~~
- [ ] Implement user authentication
- [ ] Support for multiple symbols simultaneously
- [ ] Export predictions to CSV
- [ ] Mobile-responsive design
- [ ] Real-time alerts for significant predictions
- [ ] Backtesting dashboard with walk-forward validation
- [ ] Automatic model retraining based on performance
- [ ] Options and derivatives prediction
- [ ] Sentiment analysis integration
- [ ] Portfolio optimization

## 📝 License

MIT License - feel free to use and modify!

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📧 Support

For issues or questions, please open an issue on GitHub.

---

Built with ❤️ using Python, FastAPI, Vue 3, and AI

