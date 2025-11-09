#!/bin/bash
# Quick script to check your current network IP and test backend accessibility

echo "🌐 Network IP Checker for Trading Bot"
echo "======================================"
echo ""

# Get current IP
CURRENT_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | head -1 | awk '{print $2}')

if [ -z "$CURRENT_IP" ]; then
    echo "❌ No network IP found. Are you connected to a network?"
    exit 1
fi

echo "✅ Your current network IP: $CURRENT_IP"
echo ""

# Test backend accessibility
echo "🔍 Testing backend accessibility..."
if curl -s http://$CURRENT_IP:8182/ > /dev/null 2>&1; then
    echo "✅ Backend is accessible on network at: http://$CURRENT_IP:8182"
else
    echo "⚠️  Backend not accessible on network IP"
    echo "   Make sure backend is running: cd backend && python main.py"
fi

echo ""
echo "📱 Access URLs:"
echo "   Frontend:    http://$CURRENT_IP:5155"
echo "   Backend API: http://$CURRENT_IP:8182"
echo "   API Docs:    http://$CURRENT_IP:8182/docs"
echo "   Health:      http://$CURRENT_IP:8182/health"
echo ""

# Check if IP in config matches
CONFIG_IP=$(grep -o 'http://[0-9.]*:5155' backend/config.py | head -1 | sed 's|http://||' | sed 's|:5155||')

if [ "$CONFIG_IP" != "$CURRENT_IP" ]; then
    echo "⚠️  IP MISMATCH DETECTED!"
    echo "   Config has: $CONFIG_IP"
    echo "   Current IP: $CURRENT_IP"
    echo ""
    echo "   Update backend/config.py with:"
    echo "   allowed_origins: str = \"http://localhost:5155,http://localhost:3000,http://$CURRENT_IP:5155\""
    echo ""
    echo "   Then restart backend!"
else
    echo "✅ Config IP matches current IP"
fi

