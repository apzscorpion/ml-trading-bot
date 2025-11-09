# 📦 Installation & Deployment Guide

Complete guide to install, run, and deploy your AI Trading Prediction Chart App.

---

## 🖥️ Local Development Setup

### Prerequisites

Ensure you have these installed:
- **Python 3.8 or higher** ([Download](https://www.python.org/downloads/))
- **Node.js 16 or higher** ([Download](https://nodejs.org/))
- **Git** (optional, for cloning)

### Quick Verification

Run the setup checker:
```bash
python verify_setup.py
```

---

## 📥 Installation Steps

### Step 1: Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install all dependencies
pip install -r requirements.txt

# Initialize database
python database.py
```

**Expected output:**
```
Database initialized successfully!
```

### Step 2: Frontend Setup

```bash
# Open a new terminal
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install
```

**Expected output:**
```
added XXX packages in XXs
```

---

## 🚀 Running the Application

### Method 1: Using Run Scripts (Recommended)

**Terminal 1 - Backend:**
```bash
cd backend
./run.sh
```

**Terminal 2 - Frontend:**
```bash
cd frontend
./run.sh
```

### Method 2: Manual Start

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate
export PYTHONPATH="${PYTHONPATH}:$(dirname $(pwd))"  # Linux/Mac only
python main.py
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

---

## ✅ Verification

### Check Backend
1. Backend should be running on: http://localhost:8000
2. Open http://localhost:8000 in browser - should see API info
3. Open http://localhost:8000/docs - should see API documentation
4. Check health: http://localhost:8000/health

### Check Frontend
1. Frontend should be running on: http://localhost:3000
2. Open http://localhost:3000 in browser
3. Should see the Trading Prediction Chart
4. Connection status should show "Connected" (green)

---

## 🔧 Configuration

### Backend Configuration

Edit `backend/.env`:

```env
# Database
DATABASE_URL=sqlite:///./trading_predictions.db

# Default settings
DEFAULT_SYMBOL=TCS.NS
PREDICTION_INTERVAL=300  # seconds (5 minutes)
YAHOO_FINANCE_INTERVAL=5m

# Logging
LOG_LEVEL=INFO
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./trading_predictions.db` | Database connection string |
| `DEFAULT_SYMBOL` | `TCS.NS` | Default stock symbol |
| `PREDICTION_INTERVAL` | `300` | Seconds between predictions |
| `YAHOO_FINANCE_INTERVAL` | `5m` | Yahoo Finance data interval |
| `LOG_LEVEL` | `INFO` | Logging level |

---

## 🐳 Docker Deployment (Optional)

### Backend Dockerfile

Create `backend/Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/
ENV DATABASE_URL=sqlite:///./data/trading_predictions.db

EXPOSE 8000

CMD ["python", "main.py"]
```

### Frontend Dockerfile

Create `frontend/Dockerfile`:

```dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]
```

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    environment:
      - DATABASE_URL=sqlite:///./data/trading_predictions.db
      - DEFAULT_SYMBOL=TCS.NS
    restart: unless-stopped

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend
    environment:
      - VITE_API_URL=http://localhost:8000
    restart: unless-stopped
```

Run with Docker:
```bash
docker-compose up -d
```

---

## ☁️ Cloud Deployment

### Option 1: Render.com (Free Tier)

#### Backend Deployment

1. Create account on [Render.com](https://render.com)
2. Click "New +" → "Web Service"
3. Connect your Git repository
4. Configure:
   - **Name**: `trading-prediction-backend`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`
   - **Plan**: `Free`
5. Add environment variables from `.env`
6. Deploy!

#### Frontend Deployment

1. Click "New +" → "Static Site"
2. Connect your Git repository
3. Configure:
   - **Name**: `trading-prediction-frontend`
   - **Build Command**: `cd frontend && npm install && npm run build`
   - **Publish Directory**: `frontend/dist`
4. Deploy!

### Option 2: Railway.app (Free Tier)

1. Create account on [Railway.app](https://railway.app)
2. Click "New Project"
3. Deploy from GitHub
4. Add two services:
   - Python service for backend
   - Node service for frontend
5. Configure environment variables
6. Deploy!

### Option 3: Vercel (Frontend) + Railway (Backend)

**Frontend on Vercel:**
```bash
cd frontend
npm install -g vercel
vercel
```

**Backend on Railway:**
- Follow Railway steps above

---

## 🔒 Production Considerations

### Security

1. **Add Authentication**
```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

@app.get("/api/protected")
async def protected_route(token = Depends(security)):
    # Verify token
    pass
```

2. **Configure CORS Properly**
```python
# In main.py, replace "*" with actual frontend URL
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

3. **Use HTTPS**
- Enable SSL/TLS on your hosting provider
- Use environment variables for secrets

### Database

For production, consider PostgreSQL:

```env
DATABASE_URL=postgresql://user:password@host:5432/dbname
```

Update `requirements.txt`:
```
psycopg2-binary==2.9.9
```

### Monitoring

Add logging and monitoring:

```python
import logging
from logging.handlers import RotatingFileHandler

# Configure file logging
handler = RotatingFileHandler('app.log', maxBytes=10000000, backupCount=3)
logger.addHandler(handler)
```

### Rate Limiting

Add rate limiting:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.get("/api/prediction/trigger")
@limiter.limit("10/minute")
async def trigger_prediction():
    pass
```

---

## 🧪 Testing

### Backend Tests

Create `backend/tests/test_bots.py`:

```python
import pytest
from backend.bots.rsi_bot import RSIBot

@pytest.mark.asyncio
async def test_rsi_bot():
    bot = RSIBot()
    # Add test candles
    candles = [...]
    result = await bot.predict(candles, 180, "5m")
    assert result["confidence"] > 0
```

Run tests:
```bash
cd backend
pytest
```

### Frontend Tests

Add to `package.json`:
```json
{
  "devDependencies": {
    "@vue/test-utils": "^2.4.0",
    "vitest": "^1.0.0"
  }
}
```

Run tests:
```bash
cd frontend
npm test
```

---

## 📊 Performance Optimization

### Backend

1. **Add Redis caching**:
```bash
pip install redis aioredis
```

2. **Use connection pooling**:
```python
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10
)
```

3. **Optimize queries**:
```python
# Add indexes
query = query.filter(Candle.symbol == symbol).order_by(
    Candle.start_ts.desc()
).limit(limit)
```

### Frontend

1. **Code splitting**:
```javascript
const ChartComponent = defineAsyncComponent(() =>
  import('./components/ChartComponent.vue')
)
```

2. **Lazy loading**:
```javascript
import { lazy } from 'vue'
```

3. **Production build**:
```bash
npm run build
```

---

## 🐛 Troubleshooting

### Common Issues

#### "ModuleNotFoundError: No module named 'backend'"

**Solution:**
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

Or on Windows:
```cmd
set PYTHONPATH=%PYTHONPATH%;%cd%
```

#### "CORS policy" error in browser

**Solution:** Check backend CORS configuration in `main.py`

#### WebSocket connection fails

**Solution:**
1. Check backend is running
2. Check port 8000 is accessible
3. Look for firewall blocking

#### Yahoo Finance rate limiting

**Solution:**
1. Increase `PREDICTION_INTERVAL` in .env
2. Add caching layer
3. Use different data provider

#### Database locked error

**Solution:**
```bash
rm backend/trading_predictions.db
cd backend
python database.py
```

---

## 📈 Scaling

### Horizontal Scaling

1. **Load Balancer**: Use nginx or cloud load balancer
2. **Multiple Instances**: Deploy multiple backend instances
3. **Shared Database**: Use PostgreSQL or MySQL
4. **Redis**: Share WebSocket state across instances

### Vertical Scaling

1. Increase server resources (CPU, RAM)
2. Optimize database queries
3. Add caching layer
4. Use faster data sources

---

## 🔄 Updates & Maintenance

### Updating Dependencies

**Backend:**
```bash
cd backend
pip install --upgrade -r requirements.txt
```

**Frontend:**
```bash
cd frontend
npm update
```

### Database Migrations

For schema changes, use Alembic:

```bash
pip install alembic
alembic init migrations
alembic revision --autogenerate -m "description"
alembic upgrade head
```

---

## 📱 Mobile Support

The app is responsive but for native mobile:

### React Native Version
```bash
npx react-native init TradingPredictionMobile
# Port Vue components to React Native
```

### Flutter Version
```bash
flutter create trading_prediction_mobile
# Port Vue components to Flutter
```

---

## 🎓 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Vue 3 Documentation](https://vuejs.org/)
- [Lightweight Charts Docs](https://tradingview.github.io/lightweight-charts/)
- [Yahoo Finance API](https://pypi.org/project/yfinance/)
- [WebSocket Guide](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)

---

## 💬 Support

For issues:
1. Check this documentation
2. Review logs (backend terminal output)
3. Check browser console (F12)
4. Run `python verify_setup.py`

---

**Your AI Trading Prediction Chart is ready to deploy!** 🚀

