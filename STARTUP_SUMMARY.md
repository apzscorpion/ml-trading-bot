# 🚀 Startup Summary - Quick Reference

## ⚡ TL;DR - Get Started in 10 Seconds

```bash
./start.sh
```

Then open: **http://localhost:5155**

---

## 📋 What You Get

### 3 Powerful Scripts

| Script | Command | What It Does |
|--------|---------|--------------|
| **Start** | `./start.sh` | Starts everything automatically |
| **Stop** | `./stop.sh` | Stops all services |
| **Status** | `./status.sh` | Shows what's running |

---

## 🎯 Complete Feature List

### start.sh Does Everything:

```
✅ Creates logs/ directory
✅ Checks if ports 8182 and 5155 are free
✅ Kills old processes if ports are busy
✅ Checks Python virtual environment
✅ Installs Python dependencies
✅ Checks/creates database
✅ Checks Node.js dependencies
✅ Installs npm packages if needed
✅ Starts backend on port 8182
✅ Waits for backend to be healthy
✅ Starts frontend on port 5155
✅ Waits for frontend to be ready
✅ Shows all URLs and info
✅ Tails live logs from both servers
✅ Saves logs to files for later
```

### All Logs Are Saved:

- `logs/backend.log` - Python/FastAPI output
- `logs/frontend.log` - Vite/Vue.js output  
- `logs/combined.log` - Both servers merged with [BACKEND]/[FRONTEND] tags
- `logs/backend.pid` - Backend process ID
- `logs/frontend.pid` - Frontend process ID

---

## 🔌 Port Configuration

| Service | Port | URL |
|---------|------|-----|
| Frontend | 5155 | http://localhost:5155 |
| Backend API | 8182 | http://localhost:8182 |
| API Docs | 8182 | http://localhost:8182/docs |
| WebSocket | 8182 | ws://localhost:8182/ws |

---

## 💡 Common Commands

### Starting Your Work Session
```bash
./start.sh
# Press Ctrl+C when you see logs (services keep running)
# Open http://localhost:5155 in browser
```

### Checking If Everything Is Running
```bash
./status.sh
```

Expected output:
```
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
```

### Viewing Logs While Working
```bash
# Backend logs only
tail -f logs/backend.log

# Frontend logs only
tail -f logs/frontend.log

# Both together (with tags)
tail -f logs/combined.log

# Last 50 lines of backend
tail -n 50 logs/backend.log

# Search for errors
grep -i error logs/backend.log
```

### Stopping Everything
```bash
./stop.sh
```

### Restarting After Code Changes
```bash
./stop.sh && ./start.sh
```

---

## 🎨 What start.sh Looks Like

When you run `./start.sh`, you'll see:

```
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║             📈 ML Trading Bot - Startup Script                ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝

ℹ Project root: /Users/pits/Projects/new-bot-trading
ℹ Backend port: 8182
ℹ Frontend port: 5155

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

================================
Step 3: Verifying Backend Setup
================================

✓ Virtual environment exists
ℹ Checking Python dependencies...
✓ All Python dependencies are installed
✓ Database exists

================================
Step 4: Verifying Frontend Setup
================================

✓ Node modules exist

================================
Step 5: Starting Backend Server
================================

ℹ Starting FastAPI server on port 8182...
✓ Backend started (PID: 76890)
ℹ Backend logs: logs/backend.log
ℹ Waiting for backend to be ready...
✓ Backend is ready!
{
  "status": "healthy",
  "active_connections": 0,
  "scheduler_running": true
}

================================
Step 6: Starting Frontend Server
================================

ℹ Starting Vite dev server on port 5155...
✓ Frontend started (PID: 76901)
ℹ Frontend logs: logs/frontend.log
ℹ Waiting for frontend to be ready...
✓ Frontend is ready!

================================
Step 7: Application Status
================================

🎉 All services started successfully!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                    SERVICE INFORMATION                      
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📱 Frontend (Vue.js)
   URL:      http://localhost:5155
   PID:      76901
   Logs:     tail -f logs/frontend.log

🚀 Backend (FastAPI)
   API:      http://localhost:8182
   Docs:     http://localhost:8182/docs
   Health:   http://localhost:8182/health
   WebSocket: ws://localhost:8182/ws
   PID:      76890
   Logs:     tail -f logs/backend.log

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 Useful Commands:
   View backend logs:  tail -f logs/backend.log
   View frontend logs: tail -f logs/frontend.log
   View all logs:      tail -f logs/combined.log
   Stop services:      ./stop.sh
   Check status:       ./status.sh

🌐 Open your browser and navigate to:
   http://localhost:5155

⚡ Press Ctrl+C to stop tailing logs (services will continue running)

================================
Step 8: Tailing Logs (Press Ctrl+C to exit)
================================

[BACKEND]  INFO:     Started server process [76890]
[BACKEND]  INFO:     Waiting for application startup.
[BACKEND]  INFO:     Application startup complete.
[FRONTEND] VITE v4.5.0  ready in 432 ms
[FRONTEND] ➜  Local:   http://localhost:5155/
...
```

---

## 🔧 What Gets Fixed Automatically

The scripts handle common issues:

### ✅ Port Already in Use
**Problem:** Port 8182 or 5155 is busy  
**Solution:** Script detects and kills old processes

### ✅ Missing Dependencies
**Problem:** npm packages or Python packages not installed  
**Solution:** Script checks and installs automatically

### ✅ No Database
**Problem:** trading_predictions.db doesn't exist  
**Solution:** Script initializes it automatically

### ✅ No Virtual Environment
**Problem:** Python venv doesn't exist  
**Solution:** Script creates it automatically

### ✅ Services Not Responding
**Problem:** Backend/frontend started but not responding  
**Solution:** Script waits up to 30 seconds and reports status

---

## 📖 Documentation Files

| File | Purpose |
|------|---------|
| `README.md` | Main project documentation |
| `SCRIPTS_GUIDE.md` | Detailed guide for start/stop/status scripts |
| `PORTS_REFERENCE.md` | Port configuration and networking |
| `STARTUP_SUMMARY.md` | This file - quick reference |
| `QUICK_START_GUIDE.md` | Application usage guide |

---

## 🎓 Pro Tips

1. **Always use ./start.sh** - It's foolproof and handles everything
2. **Press Ctrl+C after seeing logs** - Services keep running in background
3. **Use ./status.sh to check health** - Quick health check anytime
4. **Check logs if something breaks** - All output is saved
5. **Use ./stop.sh before git pull** - Clean state for updates

---

## 🆘 Troubleshooting

### Script Won't Run
```bash
chmod +x start.sh stop.sh status.sh
```

### Services Start But Won't Load
```bash
# Check if they're actually running
./status.sh

# View logs for errors
tail -50 logs/backend.log
tail -50 logs/frontend.log
```

### Everything Seems Stuck
```bash
# Force stop everything
./stop.sh

# Clean logs
rm -rf logs/

# Try again
./start.sh
```

### Port Conflicts After Restart
```bash
# The start.sh script handles this automatically!
# But if you need manual cleanup:
lsof -ti :8182 | xargs kill -9
lsof -ti :5155 | xargs kill -9
```

---

## 🎬 First Time Setup (Complete Flow)

```bash
# 1. Clone the repo (if not done)
git clone <repo-url>
cd new-bot-trading

# 2. Make scripts executable
chmod +x start.sh stop.sh status.sh

# 3. Start everything (installs deps automatically)
./start.sh

# 4. Press Ctrl+C when you see logs

# 5. Open browser
# Go to http://localhost:5155

# 6. When done working
./stop.sh
```

That's it! Everything else is automatic! 🎉

---

## 📊 Daily Workflow

```bash
# Morning - Start your session
./start.sh
# Wait for "All services started successfully!"
# Press Ctrl+C
# Open http://localhost:5155

# During work - Check if still running
./status.sh

# During work - View logs if needed
tail -f logs/combined.log

# End of day - Stop everything
./stop.sh
```

---

## 🚀 That's All You Need!

Three commands run everything:
- `./start.sh` - Start
- `./status.sh` - Check
- `./stop.sh` - Stop

All logs saved to `logs/` directory.
All ports configured correctly.
All dependencies installed automatically.

**Just run `./start.sh` and you're ready to trade! 📈💰**

