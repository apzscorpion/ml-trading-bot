# 🚀 Deployment Guide - Railway.app

This guide will help you deploy your algorithmic trading application with ML models to Railway.app for **FREE**.

---

## 📋 Prerequisites

1. **GitHub Account** - Your code needs to be in a GitHub repository
2. **Railway Account** - Sign up at [railway.app](https://railway.app) (free)
3. **Git installed** - To push your code to GitHub

---

## 🎯 Quick Deployment (5 minutes)

### Step 1: Prepare Your Repository

```bash
# Make sure all deployment files are committed
git add .
git commit -m "Add Railway deployment configuration"
git push origin main
```

### Step 2: Create Railway Project

1. Go to [railway.app](https://railway.app)
2. Click **"Start a New Project"**
3. Select **"Deploy from GitHub repo"**
4. Choose your `new-bot-trading` repository
5. Railway will automatically detect the configuration

### Step 3: Add PostgreSQL Database

1. In your Railway project dashboard, click **"+ New"**
2. Select **"Database"** → **"PostgreSQL"**
3. Railway will automatically set the `DATABASE_URL` environment variable

### Step 4: Add Redis Cache

1. Click **"+ New"** again
2. Select **"Database"** → **"Redis"**
3. Railway will automatically set the `REDIS_URL` environment variable

### Step 5: Configure Environment Variables

In Railway dashboard, go to your service → **Variables** tab:

**Required:**
```bash
DATABASE_URL=<automatically set by Railway>
REDIS_URL=<automatically set by Railway>
PORT=<automatically set by Railway>
```

**Optional (for enhanced features):**
```bash
# Freddy AI (optional)
FREDDY_API_KEY=your_api_key
FREDDY_ORGANIZATION_ID=your_org_id
FREDDY_ASSISTANT_ID=your_assistant_id
FREDDY_ENABLED=false

# Twelve Data (optional)
TWELVEDATA_API_KEY=your_api_key
TWELVEDATA_ENABLED=false

# CORS (update after deployment)
ALLOWED_ORIGINS=https://your-app.railway.app,https://your-frontend.vercel.app

# Logging
LOG_LEVEL=WARNING
```

### Step 6: Deploy!

Railway will automatically:
- Install Python dependencies
- Build the frontend
- Start the backend server
- Provide you with a public URL: `https://your-app.railway.app`

---

## 🎨 Frontend Deployment Options

### Option A: Deploy Frontend with Backend (Simpler)

The current setup serves the frontend from the backend. Just access:
```
https://your-app.railway.app
```

### Option B: Separate Frontend on Vercel (Better Performance)

1. **Create Vercel Project:**
   ```bash
   cd frontend
   vercel
   ```

2. **Update Frontend API URL:**
   
   Edit `frontend/src/services/api.js`:
   ```javascript
   const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://your-backend.railway.app';
   ```

3. **Update CORS in Railway:**
   
   Add Vercel URL to `ALLOWED_ORIGINS`:
   ```
   ALLOWED_ORIGINS=https://your-frontend.vercel.app
   ```

---

## 🔧 Model Optimization (Important!)

Railway free tier has **~500MB** total storage. Your ML models need optimization.

### Run Model Optimizer:

```bash
cd backend
python ml/model_optimizer.py
```

This will:
- ✅ Compress scikit-learn models (`.pkl` → `.compressed.pkl`)
- ✅ Quantize TensorFlow models (`.keras` → `.tflite`)
- ✅ Optimize PyTorch models (`.pt` → `.optimized.pt`)
- ✅ Reduce total size by 60-80%

### If Models Are Still Too Large:

**Option 1: Skip Model Loading on Startup**
```bash
# In Railway environment variables
SKIP_MODEL_LOADING=true
```

**Option 2: Use Lazy Loading**
- Models load only when needed
- Already implemented in your codebase

**Option 3: Remove Unused Models**
```bash
# Keep only essential models
rm backend/models/old_*.pkl
rm backend/models/experimental_*.keras
```

---

## 📊 Database Migration

Railway uses PostgreSQL (not SQLite). Your code is already configured to handle this!

### Automatic Migration:

When you first deploy, the app will:
1. Detect `DATABASE_URL` (PostgreSQL)
2. Create all tables automatically
3. Run migrations if needed

### Manual Migration (if needed):

```bash
# SSH into Railway container
railway run python backend/migrate_db.py
```

---

## 🔍 Monitoring & Debugging

### View Logs:

**In Railway Dashboard:**
1. Go to your service
2. Click **"Deployments"** tab
3. Click on latest deployment
4. View real-time logs

**Via CLI:**
```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# View logs
railway logs
```

### Health Check:

Your app has a health endpoint:
```bash
curl https://your-app.railway.app/health
```

Should return:
```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected"
}
```

### Common Issues:

**1. App Crashes on Startup**
- Check logs for missing environment variables
- Verify PostgreSQL and Redis are connected
- Try setting `SKIP_MODEL_LOADING=true`

**2. Database Connection Errors**
- Ensure PostgreSQL service is running
- Check `DATABASE_URL` is set correctly
- Railway provides this automatically

**3. Redis Connection Errors**
- Ensure Redis service is running
- Check `REDIS_URL` is set correctly
- Set `REDIS_ENABLED=false` to disable (will use in-memory cache)

**4. Models Not Loading**
- Check model file sizes (Railway has 500MB limit)
- Run model optimizer: `python backend/ml/model_optimizer.py`
- Use `SKIP_MODEL_LOADING=true` for first deployment

---

## 💰 Cost & Limits

### Railway Free Tier:

| Resource | Free Tier | Notes |
|----------|-----------|-------|
| **Execution Time** | $5 credit/month | ~500 hours |
| **Memory** | 512MB - 8GB | Auto-scales |
| **Storage** | 1GB | For code + models |
| **Bandwidth** | 100GB/month | Plenty for most apps |
| **Databases** | Included | PostgreSQL + Redis |

### Staying Within Free Tier:

✅ **Optimize models** - Use compressed versions
✅ **Reduce logging** - Set `LOG_LEVEL=WARNING`
✅ **Cache aggressively** - Use Redis for hot data
✅ **Lazy load models** - Load only when needed
✅ **Monitor usage** - Check Railway dashboard

### When to Upgrade ($5/month):

- Heavy traffic (>1000 requests/day)
- Large models (>500MB)
- 24/7 uptime needed
- Multiple environments (staging + prod)

---

## 🚀 Advanced: CI/CD Pipeline

### Automatic Deployments:

Railway automatically deploys when you push to GitHub:

```bash
git add .
git commit -m "Update trading strategy"
git push origin main
# Railway deploys automatically! 🎉
```

### Branch Deployments:

Deploy different branches:
```bash
# Create staging branch
git checkout -b staging
git push origin staging

# In Railway: Create new service from staging branch
```

### Environment-Specific Configs:

```bash
# .env.production (for Railway)
LOG_LEVEL=WARNING
REDIS_ENABLED=true

# .env.development (for local)
LOG_LEVEL=DEBUG
REDIS_ENABLED=false
```

---

## 🔐 Security Best Practices

### 1. Never Commit Secrets:

```bash
# .gitignore already includes:
.env
.env.local
*.db
```

### 2. Use Railway Environment Variables:

Store all secrets in Railway dashboard, not in code.

### 3. Enable CORS Properly:

```bash
# Only allow your domains
ALLOWED_ORIGINS=https://your-app.railway.app,https://your-frontend.vercel.app
```

### 4. Use HTTPS:

Railway provides HTTPS automatically. Never use HTTP in production.

---

## 📈 Performance Optimization

### 1. Enable Redis Caching:

```bash
REDIS_ENABLED=true
REDIS_TTL_SECONDS=300  # 5 minutes
```

### 2. Use Connection Pooling:

Already configured in `database.py`:
```python
pool_size=10
max_overflow=20
pool_pre_ping=True
```

### 3. Optimize WebSocket Connections:

```python
# Already implemented in websocket_manager.py
# Handles reconnections and backpressure
```

### 4. Compress Responses:

Add to `main.py`:
```python
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

---

## 🧪 Testing Before Deployment

### 1. Test Locally with PostgreSQL:

```bash
# Install PostgreSQL locally
brew install postgresql  # macOS
sudo apt install postgresql  # Ubuntu

# Update .env
DATABASE_URL=postgresql://localhost/trading_test

# Run app
cd backend && python main.py
```

### 2. Test with Docker (Simulates Railway):

```bash
# Create Dockerfile (already included)
docker build -t trading-app .
docker run -p 8000:8000 trading-app
```

### 3. Load Testing:

```bash
# Install hey
go install github.com/rakyll/hey@latest

# Test API
hey -n 1000 -c 10 https://your-app.railway.app/api/health
```

---

## 📚 Useful Commands

### Railway CLI:

```bash
# Install
npm i -g @railway/cli

# Login
railway login

# Link to project
railway link

# View logs
railway logs

# Run commands in Railway environment
railway run python backend/migrate_db.py

# Open dashboard
railway open

# Check status
railway status

# Set environment variable
railway variables set FREDDY_ENABLED=true
```

### Database Commands:

```bash
# Connect to PostgreSQL
railway run psql $DATABASE_URL

# Backup database
railway run pg_dump $DATABASE_URL > backup.sql

# Restore database
railway run psql $DATABASE_URL < backup.sql
```

---

## 🆘 Troubleshooting

### App Won't Start:

1. Check Railway logs
2. Verify all environment variables are set
3. Try `SKIP_MODEL_LOADING=true`
4. Check model sizes: `du -sh backend/models/*`

### Database Errors:

1. Verify PostgreSQL service is running
2. Check `DATABASE_URL` format: `postgresql://user:pass@host:5432/db`
3. Run migrations: `railway run python backend/migrate_db.py`

### Redis Errors:

1. Verify Redis service is running
2. Check `REDIS_URL` format: `redis://default:pass@host:6379`
3. Fallback: Set `REDIS_ENABLED=false`

### WebSocket Issues:

1. Railway supports WebSockets by default
2. Check CORS settings include your frontend URL
3. Verify `wss://` (not `ws://`) in production

### Model Loading Errors:

1. Check model file sizes
2. Run optimizer: `python backend/ml/model_optimizer.py`
3. Remove unused models
4. Use lazy loading (already implemented)

---

## 🎓 Next Steps

After successful deployment:

1. ✅ **Set up monitoring** - Use Railway metrics
2. ✅ **Configure alerts** - Set up uptime monitoring (UptimeRobot)
3. ✅ **Add custom domain** - Point your domain to Railway
4. ✅ **Enable backups** - Set up automated database backups
5. ✅ **Optimize costs** - Monitor usage and optimize as needed

---

## 📞 Support

- **Railway Docs:** https://docs.railway.app
- **Railway Discord:** https://discord.gg/railway
- **This Project Issues:** https://github.com/your-username/new-bot-trading/issues

---

## 🎉 Success!

Your trading app is now live! 🚀

Access it at: `https://your-app.railway.app`

**What's deployed:**
- ✅ FastAPI backend with ML models
- ✅ Vue 3 frontend with real-time charts
- ✅ PostgreSQL database
- ✅ Redis cache
- ✅ WebSocket support for live data
- ✅ Automatic HTTPS
- ✅ Auto-scaling

**Next:** Share your app, monitor performance, and iterate! 🎯

