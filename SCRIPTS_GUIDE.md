# 🚀 Quick Start Scripts Guide

This guide explains how to use the automated scripts to manage your Trading Prediction App.

## 📋 Available Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| **start.sh** | Start all services | `./start.sh` |
| **stop.sh** | Stop all services | `./stop.sh` |
| **status.sh** | Check service status | `./status.sh` |

---

## 🎯 start.sh - Complete Startup Script

### What It Does

The `start.sh` script automates the entire startup process:

1. ✅ **Creates log directory** - Sets up `logs/` folder for all output
2. ✅ **Checks ports** - Detects if ports 8182 and 5155 are in use
3. ✅ **Stops old processes** - Kills any existing services on those ports
4. ✅ **Verifies backend** - Checks Python venv, dependencies, and database
5. ✅ **Verifies frontend** - Checks node_modules and dependencies
6. ✅ **Starts backend** - Launches FastAPI server on port 8182
7. ✅ **Starts frontend** - Launches Vite dev server on port 5155
8. ✅ **Displays status** - Shows all service URLs and information
9. ✅ **Tails logs** - Live display of both backend and frontend logs

### Usage

```bash
# Make it executable (only needed once)
chmod +x start.sh

# Run the script
./start.sh
```

### What You'll See

```
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║        📈 AI Trading Prediction App - Startup Script          ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝

================================
Step 1: Preparing Log Directory
================================

✓ Created log directory: logs
✓ Cleared old log files

================================
Step 2: Checking and Stopping Existing Services
================================

ℹ Checking port 8182 for Backend...
✓ Port 8182 is available
ℹ Checking port 5155 for Frontend...
✓ Port 5155 is available
✓ All ports are now available

... (continues through all steps)

🎉 All services started successfully!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                    SERVICE INFORMATION                      
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📱 Frontend (Vue.js)
   URL:      http://localhost:5155
   PID:      12345
   Logs:     tail -f logs/frontend.log

🚀 Backend (FastAPI)
   API:      http://localhost:8182
   Docs:     http://localhost:8182/docs
   Health:   http://localhost:8182/health
   WebSocket: ws://localhost:8182/ws
   PID:      12346
   Logs:     tail -f logs/backend.log
```

### Log Files

All logs are saved to the `logs/` directory:

- **backend.log** - All backend server output (FastAPI, Python)
- **frontend.log** - All frontend output (Vite, npm, Vue.js)
- **combined.log** - Merged view of both logs with prefixes

### Stopping the Log Display

Press **Ctrl+C** to stop viewing logs. The services will **continue running** in the background.

---

## 🛑 stop.sh - Service Shutdown Script

### What It Does

Safely stops all running services:

1. Reads PID files from `logs/` directory
2. Attempts graceful shutdown (SIGTERM)
3. Force kills if necessary (SIGKILL)
4. Cleans up PID files
5. Verifies all ports are freed

### Usage

```bash
./stop.sh
```

### Output Example

```
================================
Stopping Trading Prediction App
================================

ℹ Stopping backend (PID: 12346)...
✓ Backend stopped
ℹ Stopping frontend (PID: 12345)...
✓ Frontend stopped

✓ All services stopped successfully!
```

---

## 📊 status.sh - Status Check Script

### What It Does

Shows real-time status of all services without modifying anything:

- Checks if ports are in use
- Shows process IDs
- Tests HTTP endpoints
- Displays log file sizes
- Shows quick access URLs

### Usage

```bash
./status.sh
```

### Output Example

```
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║                      📊 Service Status                         ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝

━━━ Backend (FastAPI) ━━━
Status:    ● RUNNING
Port:      8182
PID:       12346
Health:    ✓ Responding

━━━ Frontend (Vite) ━━━
Status:    ● RUNNING
Port:      5155
PID:       12345
Health:    ✓ Responding

━━━ Log Files ━━━
backend.log: 2.4M (1523 lines)
frontend.log: 856K (423 lines)
combined.log: 3.2M (1946 lines)

━━━ WebSocket ━━━
Endpoint:  ws://localhost:8182/ws
Status:    Available (if backend is running)

━━━ Quick Links ━━━
Frontend:  http://localhost:5155
Backend:   http://localhost:8182
API Docs:  http://localhost:8182/docs
Health:    http://localhost:8182/health

━━━ Available Commands ━━━
Start:     ./start.sh
Stop:      ./stop.sh
Logs:      tail -f logs/backend.log    (or frontend.log)
```

---

## 🔍 Common Scenarios

### First Time Setup

```bash
# Everything is automated!
./start.sh
```

The script will:
- Create virtual environment if needed
- Install all dependencies
- Initialize database
- Start all services

### Daily Development

```bash
# Start your work session
./start.sh

# Check if everything is running
./status.sh

# When done for the day
./stop.sh
```

### Restart After Changes

```bash
# Stop everything
./stop.sh

# Start fresh
./start.sh
```

### Check Logs

```bash
# While script is running - live view
# (started automatically by start.sh)

# After pressing Ctrl+C - view specific logs
tail -f logs/backend.log
tail -f logs/frontend.log
tail -f logs/combined.log

# View last 50 lines
tail -n 50 logs/backend.log

# Search logs for errors
grep -i error logs/backend.log
grep -i warning logs/frontend.log
```

### Troubleshooting

#### Port Already in Use
```bash
# The start.sh script handles this automatically!
# It will detect and stop any processes on ports 8182 and 5155
./start.sh
```

#### Services Won't Start
```bash
# Check what's wrong
./status.sh

# View the logs
tail -f logs/backend.log
tail -f logs/frontend.log

# Force stop and retry
./stop.sh
./start.sh
```

#### Clear Everything and Start Fresh
```bash
# Stop services
./stop.sh

# Remove logs (optional)
rm -rf logs/

# Remove old database (optional - will lose data!)
rm backend/trading_predictions.db

# Start fresh
./start.sh
```

---

## 📝 Log File Formats

### Backend Log (backend.log)
```
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8182 (Press CTRL+C to quit)
2024-11-02 21:30:15,123 - __main__ - INFO - Starting trading prediction app...
2024-11-02 21:30:15,456 - __main__ - INFO - Scheduler started. Running every 300 seconds.
```

### Frontend Log (frontend.log)
```
VITE v4.5.0  ready in 432 ms

➜  Local:   http://localhost:5155/
➜  Network: use --host to expose
➜  press h to show help
```

### Combined Log (combined.log)
```
[BACKEND]  INFO:     Started server process [12346]
[BACKEND]  INFO:     Application startup complete.
[FRONTEND] VITE v4.5.0  ready in 432 ms
[FRONTEND] ➜  Local:   http://localhost:5155/
[BACKEND]  2024-11-02 21:30:15 - INFO - Scheduler started
```

---

## ⚙️ Configuration

### Changing Ports

Edit the port variables at the top of each script:

```bash
# In start.sh, stop.sh, and status.sh
BACKEND_PORT=8182   # Change this
FRONTEND_PORT=5155  # Change this
```

Also update:
- `backend/main.py` (line 320)
- `frontend/vite.config.js` (lines 7, 10, 14)

### Changing Log Location

```bash
# In start.sh
LOG_DIR="logs"  # Change this to your preferred directory
```

---

## 🎓 Tips & Best Practices

1. **Always use start.sh for development** - It handles all the setup automatically
2. **Check status.sh if something seems wrong** - Quick health check
3. **Use stop.sh before pulling code changes** - Clean slate for updates
4. **Monitor logs when debugging** - `tail -f logs/combined.log` shows everything
5. **Keep logs directory in .gitignore** - Don't commit log files

---

## 🐛 Troubleshooting Guide

### "Permission Denied" Error
```bash
chmod +x start.sh stop.sh status.sh
```

### Script Exits Immediately
- Check logs: `cat logs/backend.log` or `cat logs/frontend.log`
- Verify Python: `python3 --version` (need 3.8+)
- Verify Node: `node --version` (need 16+)

### Backend Won't Start
```bash
cd backend
source venv/bin/activate
python main.py
# Watch for error messages
```

### Frontend Won't Start
```bash
cd frontend
npm run dev
# Watch for error messages
```

### Ports Still Showing as Used
```bash
# Manual cleanup
lsof -ti :8182 | xargs kill -9
lsof -ti :5155 | xargs kill -9
```

---

## 📞 Need Help?

1. Check `./status.sh` for current state
2. View logs in `logs/` directory
3. See main `README.md` for application details
4. Check `PORTS_REFERENCE.md` for port configuration

Happy Trading! 📈💰

