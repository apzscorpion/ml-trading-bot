# Network Access Guide

## 🌐 Your Network Configuration

- **Machine IP**: `192.168.167.178`
- **Backend Port**: `8182`
- **Frontend Port**: `5155`

## 📱 Access URLs

### From This Machine (localhost)
- Frontend: http://localhost:5155
- Backend API: http://localhost:8182
- API Docs: http://localhost:8182/docs

### From Other Devices on Network
- Frontend: http://192.168.167.178:5155
- Backend API: http://192.168.167.178:8182
- API Docs: http://192.168.167.178:8182/docs
- Health Check: http://192.168.167.178:8182/health

## 🚀 Starting the Services

```bash
# Terminal 1: Backend
cd backend
python main.py

# Terminal 2: Frontend
cd frontend
npm run dev
```

## ✅ Changes Made for Network Access

1. **Frontend** (`frontend/vite.config.js`):
   - Added `host: '0.0.0.0'` to allow network connections

2. **Backend** (`backend/config.py`):
   - Added `http://192.168.167.178:5155` to allowed CORS origins

3. **Backend** (`backend/main.py`):
   - Already configured with `host="0.0.0.0"` ✅

## 🔄 After Making Changes

**Restart backend** to apply CORS changes:
```bash
# Stop backend (Ctrl+C) and restart
cd backend
python main.py
```

**Frontend** will hot-reload automatically with Vite.

## 📱 Testing from Mobile/Tablet

1. Ensure device is on the **same WiFi network**
2. Open browser and navigate to: `http://192.168.167.178:5155`
3. You should see the trading dashboard!

## 🔍 Troubleshooting

### Can't connect from other devices?

1. **Check firewall** (macOS):
   - System Settings → Network → Firewall
   - Ensure Python is allowed

2. **Verify backend is running**:
   ```bash
   curl http://192.168.167.178:8182/
   ```

3. **Check if IP changed**:
   ```bash
   ifconfig | grep "inet " | grep -v 127.0.0.1
   ```
   If IP changed, update `backend/config.py` with new IP

4. **CORS errors in browser console?**
   - Add the new origin to `allowed_origins` in `backend/config.py`
   - Restart backend

### WebSocket connection issues?

- WebSocket connects to: `ws://192.168.167.178:8182/ws`
- Check browser console for connection errors
- Ensure backend is running and accessible

## 🔒 Security Notes

### Current Setup (Development)
- ✅ Safe for local network testing
- ✅ Firewall provides basic protection
- ⚠️ Not suitable for public internet

### For Production Deployment
- Use HTTPS with valid certificates
- Implement authentication/authorization
- Set up rate limiting
- Use environment variables for secrets
- Configure proper firewall rules
- Consider reverse proxy (nginx/caddy)
- Use specific CORS origins (not `*`)

## 🎯 Quick Reference

| Service | Local | Network |
|---------|-------|---------|
| Frontend | http://localhost:5155 | http://192.168.167.178:5155 |
| Backend API | http://localhost:8182 | http://192.168.167.178:8182 |
| WebSocket | ws://localhost:8182/ws | ws://192.168.167.178:8182/ws |
| API Docs | http://localhost:8182/docs | http://192.168.167.178:8182/docs |
| Health | http://localhost:8182/health | http://192.168.167.178:8182/health |
| Metrics | http://localhost:8182/metrics | http://192.168.167.178:8182/metrics |

## 📊 Monitoring

Check system health:
```bash
# Health check
curl http://192.168.167.178:8182/health | jq

# Prometheus metrics
curl http://192.168.167.178:8182/metrics
```

## 🎨 Features Available on Network

- ✅ Real-time chart updates (WebSocket)
- ✅ Multi-symbol watchlist
- ✅ AI predictions (LSTM, Transformer, ML, Ensemble)
- ✅ Backtesting
- ✅ Market analysis
- ✅ Intraday trading signals
- ✅ News sentiment analysis
- ✅ Model training interface

---

**Last Updated**: November 7, 2025
**Your IP**: 192.168.167.178 (check if changed)

