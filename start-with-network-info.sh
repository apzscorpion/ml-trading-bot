#!/bin/bash
# Convenient startup script that shows network information and starts both services

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ""
echo "========================================================================"
echo "🚀 Trading Bot - Network Startup"
echo "========================================================================"
echo ""

# Get network IP
NETWORK_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | head -1 | awk '{print $2}')

if [ -z "$NETWORK_IP" ]; then
    echo "⚠️  Warning: Could not detect network IP"
    NETWORK_IP="[Not detected]"
fi

echo -e "${BLUE}📍 Your Network IP: ${GREEN}$NETWORK_IP${NC}"
echo ""
echo "========================================================================"
echo "🌐 Access URLs"
echo "========================================================================"
echo ""
echo "From this machine (localhost):"
echo "  Frontend:  http://localhost:5155"
echo "  Backend:   http://localhost:8182"
echo "  API Docs:  http://localhost:8182/docs"
echo ""
echo "From other devices on your network:"
echo -e "  ${GREEN}Frontend:  http://$NETWORK_IP:5155${NC}"
echo -e "  ${GREEN}Backend:   http://$NETWORK_IP:8182${NC}"
echo "  API Docs:  http://$NETWORK_IP:8182/docs"
echo "  Health:    http://$NETWORK_IP:8182/health"
echo ""
echo "========================================================================"
echo ""

# Check if backend is already running
if lsof -Pi :8182 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${YELLOW}⚠️  Backend already running on port 8182${NC}"
else
    echo "Starting backend..."
fi

# Check if frontend is already running
if lsof -Pi :5155 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${YELLOW}⚠️  Frontend already running on port 5155${NC}"
else
    echo "Starting frontend..."
fi

echo ""
echo "========================================================================"
echo "📱 To access from mobile/tablet:"
echo "   1. Connect to the same WiFi network"
echo "   2. Open browser and go to: http://$NETWORK_IP:5155"
echo "========================================================================"
echo ""
echo "Press Ctrl+C to stop both services"
echo ""

# Start backend in background
cd backend
python main.py &
BACKEND_PID=$!

# Wait a bit for backend to start
sleep 2

# Start frontend in background
cd ../frontend
npm run dev &
FRONTEND_PID=$!

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Stopping services..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo "Services stopped."
    exit 0
}

# Trap Ctrl+C
trap cleanup INT TERM

# Wait for both processes
wait

