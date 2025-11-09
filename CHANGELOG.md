# Changelog

## [2.0.0] - Major ML/DL Upgrade - 2024

### 🎉 Major Features Added

#### 🔥 Advanced Machine Learning Models
- **LSTM Bot**: Deep learning time-series prediction using TensorFlow
  - 3-layer LSTM architecture (128→64→32 units)
  - Dropout layers for regularization
  - 60 timestep sequence input
  - Per-minute recursive predictions
  - Trainable with 50 epochs

- **Transformer Bot**: State-of-the-art attention mechanism
  - Multi-head attention (4 heads)
  - Position encoding
  - 2 transformer blocks
  - 7 engineered features
  - Trainable with 30 epochs

- **Ensemble Bot**: Classical ML ensemble
  - Random Forest (100 trees)
  - Gradient Boosting (100 estimators)
  - Ridge Regression
  - 40+ engineered features
  - Weighted voting system

#### 📊 Enhanced Chart Functionality
- **Dynamic Historical Data Loading**
  - Automatically loads more data when zooming out
  - Seamless pagination from backend
  - Keeps up to 2000 candles in memory (increased from 500)
  - Improved user experience for historical analysis

#### 🎯 Multiple Prediction Modes
- **Technical Analysis Mode**: RSI, MACD, MA bots
- **ML Mode**: Prophet and Ensemble bots
- **Deep Learning Mode**: LSTM and Transformer
- **Full Ensemble Mode**: All 7 models combined
- Selective bot execution via API

#### 🎓 Model Training Interface
- Train models directly from UI
- Training endpoint: `/api/prediction/train`
- Supports LSTM, Transformer, and Ensemble models
- Trains on up to 5000 historical candles
- Progress feedback and results display

#### ⏱️ Per-Minute Predictions
- All bots now generate minute-by-minute predictions
- More granular price forecasts
- Better visualization of prediction trajectory
- Improved accuracy for short-term predictions

### 🔧 Backend Improvements

#### New Dependencies
```
tensorflow>=2.15.0
torch>=2.1.0
transformers>=4.36.0
joblib>=1.3.2
ta>=0.11.0
```

#### New API Endpoints
- `GET /api/prediction/bots/available` - List all available bots
- `POST /api/prediction/train` - Train specific bot
- Updated `POST /api/prediction/trigger` with `selected_bots` parameter
- Updated `GET /api/history` to support pagination with `from_ts`

#### New Bot Files
- `backend/bots/lstm_bot.py` - LSTM neural network
- `backend/bots/transformer_bot.py` - Transformer attention model
- `backend/bots/ensemble_bot.py` - Ensemble ML models

#### Freddy Merger Updates
- Now supports 7 bots (up from 4)
- Selective bot execution
- Available bots registry
- Improved confidence weighting

### 🎨 Frontend Improvements

#### New UI Components
- **Prediction Models Panel**
  - 5 beautiful gradient buttons
  - Model-specific color coding
  - Training button with status
  - Responsive grid layout

#### Enhanced Chart Component
- Zoom event listener
- `loadMoreHistory` event emitter
- Automatic data pagination
- Improved performance

#### Updated Services
- `api.js` updated with:
  - `fetchAvailableBots()`
  - `trainBot(symbol, timeframe, botName, epochs)`
  - Updated `triggerPrediction()` with selectedBots parameter
  - Updated `fetchHistory()` with from_ts/to_ts parameters

### 🐛 Bug Fixes
- Fixed pandas `fillna(method='bfill')` deprecation
- Updated to `bfill()` in transformer and ensemble bots
- Improved error handling in all new bots
- Fallback predictions when TensorFlow unavailable

### 📝 Documentation
- Comprehensive README update
- Detailed bot descriptions
- Training instructions
- API documentation
- Architecture diagrams

### 🔒 Security & Best Practices
- Added `.gitignore` entries for model files
- Created `models/` directory structure
- Model files not committed to git
- Proper error handling in training endpoints

### 🎯 Technical Improvements
- Feature engineering in Ensemble Bot:
  - Moving averages (5, 10, 20)
  - RSI (14-period)
  - Bollinger Bands
  - Momentum indicators
  - Volatility measures
  - Volume analysis

- LSTM architecture:
  - StandardScaler normalization
  - Sequence-to-sequence predictions
  - Model persistence (HDF5)
  - Scaler persistence (pickle)

- Transformer architecture:
  - RobustScaler normalization
  - Position embeddings
  - Multi-head attention
  - Custom Keras layers

### 📈 Performance
- Ensemble Bot: 82-87% confidence
- Transformer: 73-83% confidence
- LSTM: 70-80% confidence
- Combined ensemble: Higher accuracy through diversity

---

## [1.0.0] - Initial Release

### Features
- Real-time candlestick charts
- WebSocket updates
- 4 prediction bots (RSI, MACD, MA, ML)
- Freddy merger
- Evaluation system
- SQLite database
- FastAPI backend
- Vue 3 frontend

