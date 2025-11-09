# 🚀 Quick Start Guide

## Network Access Made Easy

Your trading bot app now shows network information automatically when you start it!

## 📱 Three Ways to Start

### Option 1: Start Both Services (Recommended)
```bash
./start-with-network-info.sh
```
This will:
- Show your network IP
- Start backend and frontend together
- Display all access URLs

### Option 2: Start Services Separately
```bash
# Terminal 1: Backend
cd backend
python main.py

# Terminal 2: Frontend
cd frontend
npm run dev
```
Each will show network access information on startup.

### Option 3: Check Network IP Anytime
```bash
./check-network-ip.sh
```
Shows your current IP and verifies backend accessibility.

## 🌐 What You'll See

When you start the backend, you'll see:

```
======================================================================
🚀 Starting Trading Prediction API
======================================================================
📍 Local Access:   http://localhost:8182
📍 Network Access: http://192.168.167.178:8182
📍 API Docs:       http://192.168.167.178:8182/docs
📍 Health Check:   http://192.168.167.178:8182/health

📱 Access from other devices:
   Frontend: http://192.168.167.178:5155
   Backend:  http://192.168.167.178:8182
======================================================================
```

When you start the frontend, you'll see:

```
======================================================================
🎨 Trading Prediction Frontend
======================================================================
📍 Local Access:   http://localhost:5155
📍 Network Access: http://192.168.167.178:5155

📱 Access from other devices on your network:
   Open browser and go to: http://192.168.167.178:5155
======================================================================
```

## 📱 Access from Mobile/Tablet

1. **Connect to same WiFi** as your computer
2. **Open browser** on your mobile device
3. **Navigate to** the network URL shown (e.g., `http://192.168.167.178:5155`)
4. **Enjoy** your trading dashboard!

## 🔍 Troubleshooting

### Can't connect from other devices?

1. **Check firewall** (macOS):
   - System Settings → Network → Firewall
   - Ensure Python/Node are allowed

2. **Verify services are running**:
   ```bash
   # Check if backend is accessible
   curl http://YOUR_IP:8182/
   
   # Check if frontend is accessible
   curl http://YOUR_IP:5155/
   ```

3. **IP changed?**
   - Your IP can change when you reconnect to WiFi
   - Run `./check-network-ip.sh` to see current IP
   - If changed, restart backend to update CORS settings

### Still having issues?

See `NETWORK_ACCESS.md` for detailed troubleshooting.

## 🎯 Quick Reference

| What | Local | Network |
|------|-------|---------|
| **Frontend** | http://localhost:5155 | http://YOUR_IP:5155 |
| **Backend** | http://localhost:8182 | http://YOUR_IP:8182 |
| **API Docs** | http://localhost:8182/docs | http://YOUR_IP:8182/docs |
| **Health** | http://localhost:8182/health | http://YOUR_IP:8182/health |

## 🔒 Security Note

This setup is perfect for:
- ✅ Local network testing
- ✅ Development
- ✅ Accessing from your own devices

**Not suitable for:**
- ❌ Public internet exposure
- ❌ Production deployment without additional security

For production, see `NETWORK_ACCESS.md` security section.

---

**Need help?** Check `README.md` for full documentation or `NETWORK_ACCESS.md` for network details.

