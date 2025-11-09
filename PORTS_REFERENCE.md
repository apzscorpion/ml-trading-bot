# 🔌 Ports Reference Guide

## Active Ports in Trading Prediction App

### Quick Reference Table

| Service | Port | URL | Purpose |
|---------|------|-----|---------|
| **Frontend** | **5155** | http://localhost:5155 | Vue.js UI |
| **Backend API** | **8182** | http://localhost:8182 | REST API |
| **WebSocket** | **8182** | ws://localhost:8182/ws | Real-time updates |
| **API Docs** | **8182** | http://localhost:8182/docs | Swagger UI |

## Service Details

### 🎨 Frontend (Port 5155)
- **Technology**: Vue 3 + Vite
- **Access**: http://localhost:5155
- **Features**:
  - Trading chart visualization
  - Model selection interface
  - Real-time updates via WebSocket
  - Proxies all `/api` and `/ws` requests to backend

### 🚀 Backend (Port 8182)
- **Technology**: Python FastAPI
- **Access**: http://localhost:8182
- **Endpoints**:
  - `/` - Root endpoint
  - `/health` - Health check
  - `/docs` - Interactive API documentation
  - `/api/*` - All API routes
  - `/ws` - WebSocket endpoint

### 🔄 WebSocket (Port 8182)
- **Endpoint**: `ws://localhost:8182/ws` (direct) or `ws://localhost:5155/ws` (via proxy)
- **Used for**:
  - Real-time candle updates
  - Live prediction broadcasts
  - Model training status
- **Message Types**:
  - Client → Server: `subscribe`, `unsubscribe`, `ping`
  - Server → Client: `candle:update`, `prediction:update`, `subscribed`, `pong`

## Starting the Services

### Backend
```bash
cd backend
source venv/bin/activate
python main.py
# Or use the run script:
./run.sh
```

### Frontend
```bash
cd frontend
npm run dev
# Or use the run script:
./run.sh
```

## Troubleshooting Ports

### Check if Port is in Use
```bash
# Check backend port
lsof -i :8182

# Check frontend port
lsof -i :5155
```

### Kill Process on Port
```bash
# Kill backend process
lsof -ti :8182 | xargs kill -9

# Kill frontend process
lsof -ti :5155 | xargs kill -9
```

### Change Ports

#### Change Backend Port
Edit `backend/main.py` (line 320):
```python
uvicorn.run(
    "main:app",
    host="0.0.0.0",
    port=8182,  # Change this
    reload=True,
    log_level="info"
)
```

Then update `frontend/vite.config.js`:
```javascript
proxy: {
  '/api': {
    target: 'http://localhost:8182',  // Change this
    changeOrigin: true
  },
  '/ws': {
    target: 'ws://localhost:8182',  // Change this
    ws: true
  }
}
```

#### Change Frontend Port
Edit `frontend/vite.config.js`:
```javascript
server: {
  port: 5155,  // Change this
  proxy: { ... }
}
```

## Network Architecture

```
Browser (http://localhost:5155)
    │
    ├─ GET /                → Vite serves Vue app
    ├─ GET /api/*           → Proxy → Backend :8182
    └─ WebSocket /ws        → Proxy → Backend :8182
                                │
                                ▼
                        FastAPI Backend (:8182)
                                │
                                ├─ REST API (/api/*)
                                ├─ WebSocket (/ws)
                                └─ Database (SQLite)
```

## External Services

| Service | Description | Rate Limits |
|---------|-------------|-------------|
| **Yahoo Finance API** | Stock data source | ~2000 requests/hour |
| **SQLite Database** | Local file-based DB | No network port |

## Security Notes

⚠️ **Development Mode Only**
- Current setup is for development only
- CORS is set to `allow_origins=["*"]` (allow all)
- Backend binds to `0.0.0.0` (all interfaces)

🔒 **For Production**:
- Configure specific CORS origins
- Use reverse proxy (nginx/Apache)
- Enable HTTPS/WSS
- Use environment-based port configuration
- Implement authentication

## Quick Health Check

```bash
# Check if backend is running
curl http://localhost:8182/health

# Expected response:
# {
#   "status": "healthy",
#   "active_connections": 0,
#   "scheduler_running": true
# }

# Check if frontend is running
curl -I http://localhost:5155

# Expected: HTTP/1.1 200 OK
```

## Common Issues

### WebSocket Not Connected
1. Ensure backend is running: `curl http://localhost:8182/health`
2. Ensure frontend is running: `curl -I http://localhost:5155`
3. Check browser console for errors
4. Verify proxy config in `frontend/vite.config.js`

### Port Already in Use
```bash
# Find and kill the process
lsof -ti :8182 | xargs kill -9  # Backend
lsof -ti :5155 | xargs kill -9  # Frontend
```

### Can't Access from Another Device
- Backend binds to `0.0.0.0`, so it's accessible from network
- Frontend (Vite) only binds to `localhost` by default
- To access from another device, change Vite config:
```javascript
server: {
  host: '0.0.0.0',  // Add this
  port: 5155,
  // ...
}
```

