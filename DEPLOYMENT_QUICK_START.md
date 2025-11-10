# ⚡ Quick Start: Deploy to Railway in 5 Minutes

The fastest way to get your trading app live on the internet for **FREE**.

---

## 🎯 One-Command Deployment

```bash
./deploy.sh
```

This interactive script will:
- ✅ Check prerequisites
- ✅ Optimize models
- ✅ Commit changes
- ✅ Push to GitHub
- ✅ Deploy to Railway

---

## 📋 Manual Deployment (Step-by-Step)

### 1. Install Railway CLI

```bash
npm install -g @railway/cli
```

### 2. Login to Railway

```bash
railway login
```

### 3. Initialize Project

```bash
railway init
```

Choose "Create new project" and give it a name.

### 4. Add PostgreSQL

```bash
railway add --plugin postgresql
```

### 5. Add Redis

```bash
railway add --plugin redis
```

### 6. Deploy

```bash
railway up
```

### 7. Set Environment Variables

Go to Railway dashboard and set:

```bash
# Required (auto-set by Railway)
DATABASE_URL=<auto>
REDIS_URL=<auto>
PORT=<auto>

# Optional
LOG_LEVEL=WARNING
FREDDY_ENABLED=false
TWELVEDATA_ENABLED=false
```

### 8. Open Your App

```bash
railway open
```

---

## 🎉 That's It!

Your app is now live at: `https://your-app-name.railway.app`

---

## 🔧 Common Commands

```bash
# View logs
railway logs

# Open dashboard
railway open

# Check status
railway status

# Set environment variable
railway variables set KEY=VALUE

# Redeploy
railway up
```

---

## 🆘 Troubleshooting

### App Won't Start?

1. Check logs: `railway logs`
2. Verify PostgreSQL is running in Railway dashboard
3. Try: `railway variables set SKIP_MODEL_LOADING=true`

### Database Errors?

1. Ensure PostgreSQL plugin is added
2. Check `DATABASE_URL` is set automatically
3. Run: `railway run python backend/migrate_db.py`

### Models Too Large?

1. Run: `python backend/ml/model_optimizer.py`
2. Or set: `railway variables set SKIP_MODEL_LOADING=true`

---

## 📚 Full Documentation

For detailed instructions, see [DEPLOYMENT.md](./DEPLOYMENT.md)

---

## 💡 Pro Tips

1. **Free Tier Limits:** $5 credit/month (~500 hours)
2. **Model Size:** Keep under 500MB total
3. **Monitoring:** Use `railway logs` to debug
4. **Updates:** Just `git push` - Railway auto-deploys!

---

## 🚀 Alternative: Vercel Frontend + Railway Backend

For better performance, deploy frontend separately:

```bash
# Deploy backend to Railway (as above)
railway up

# Deploy frontend to Vercel
cd frontend
vercel

# Update frontend API URL
# Edit frontend/src/services/api.js
# Set: const API_BASE_URL = 'https://your-backend.railway.app'
```

---

**Need help?** Check [DEPLOYMENT.md](./DEPLOYMENT.md) for comprehensive guide.

