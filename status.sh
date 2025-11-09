#!/bin/bash

##############################################################################
# Trading Prediction App - Status Check Script
# Shows the current status of all services
##############################################################################

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

BACKEND_PORT=8182
FRONTEND_PORT=5155
LOG_DIR="logs"

print_header() {
    echo -e "\n${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║$(printf '%64s' | tr ' ' ' ')║${NC}"
    echo -e "${CYAN}║$(printf '%20s%-44s' ' ' "$1")║${NC}"
    echo -e "${CYAN}║$(printf '%64s' | tr ' ' ' ')║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}\n"
}

check_service() {
    local port=$1
    local name=$2
    local url=$3
    
    echo -e "${CYAN}━━━ $name ━━━${NC}"
    
    # Check if port is in use
    local pid=$(lsof -ti :$port 2>/dev/null)
    
    if [ -n "$pid" ]; then
        echo -e "Status:    ${GREEN}● RUNNING${NC}"
        echo -e "Port:      ${GREEN}$port${NC}"
        echo -e "PID:       ${GREEN}$pid${NC}"
        
        # Try to get more info
        if [ -n "$url" ]; then
            local response=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)
            if [ "$response" == "200" ]; then
                echo -e "Health:    ${GREEN}✓ Responding${NC}"
            else
                echo -e "Health:    ${YELLOW}⚠ Port open but not responding (HTTP $response)${NC}"
            fi
        fi
    else
        echo -e "Status:    ${RED}○ STOPPED${NC}"
        echo -e "Port:      ${RED}$port (not in use)${NC}"
    fi
    echo ""
}

print_header "📊 Service Status"

# Check Backend
check_service $BACKEND_PORT "Backend (FastAPI)" "http://localhost:$BACKEND_PORT/health"

# Check Frontend
check_service $FRONTEND_PORT "Frontend (Vite)" "http://localhost:$FRONTEND_PORT"

# Additional info
echo -e "${CYAN}━━━ Log Files ━━━${NC}"
if [ -d "$LOG_DIR" ]; then
    for log in "$LOG_DIR"/*.log; do
        if [ -f "$log" ]; then
            local size=$(du -h "$log" | cut -f1)
            local lines=$(wc -l < "$log")
            echo -e "$(basename $log): ${YELLOW}$size${NC} ($lines lines)"
        fi
    done
else
    echo -e "${RED}No log directory found${NC}"
fi
echo ""

# WebSocket check
echo -e "${CYAN}━━━ WebSocket ━━━${NC}"
if [ -n "$(lsof -ti :$BACKEND_PORT 2>/dev/null)" ]; then
    echo -e "Endpoint:  ${GREEN}ws://localhost:$BACKEND_PORT/ws${NC}"
    echo -e "Status:    ${GREEN}Available${NC} (if backend is running)"
else
    echo -e "Status:    ${RED}Unavailable${NC} (backend not running)"
fi
echo ""

# URLs
echo -e "${CYAN}━━━ Quick Links ━━━${NC}"
echo -e "Frontend:  ${GREEN}http://localhost:$FRONTEND_PORT${NC}"
echo -e "Backend:   ${GREEN}http://localhost:$BACKEND_PORT${NC}"
echo -e "API Docs:  ${GREEN}http://localhost:$BACKEND_PORT/docs${NC}"
echo -e "Health:    ${GREEN}http://localhost:$BACKEND_PORT/health${NC}"
echo ""

# Commands
echo -e "${CYAN}━━━ Available Commands ━━━${NC}"
echo -e "${YELLOW}Start:${NC}     ./start.sh"
echo -e "${YELLOW}Stop:${NC}      ./stop.sh"
echo -e "${YELLOW}Logs:${NC}      tail -f logs/backend.log    (or frontend.log)"
echo ""

