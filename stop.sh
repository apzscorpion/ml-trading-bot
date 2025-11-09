#!/bin/bash

##############################################################################
# Trading Prediction App - Stop Script
# Stops all running backend and frontend services
##############################################################################

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

BACKEND_PORT=8182
FRONTEND_PORT=5155
LOG_DIR="logs"

print_header() {
    echo -e "\n${CYAN}================================${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

print_header "Stopping Trading Prediction App"

# Stop by PID files
if [ -f "$LOG_DIR/backend.pid" ]; then
    BACKEND_PID=$(cat "$LOG_DIR/backend.pid")
    if kill -0 $BACKEND_PID 2>/dev/null; then
        print_info "Stopping backend (PID: $BACKEND_PID)..."
        kill $BACKEND_PID 2>/dev/null
        sleep 1
        if ! kill -0 $BACKEND_PID 2>/dev/null; then
            print_success "Backend stopped"
        else
            kill -9 $BACKEND_PID 2>/dev/null
            print_success "Backend force stopped"
        fi
    fi
    rm "$LOG_DIR/backend.pid"
fi

if [ -f "$LOG_DIR/frontend.pid" ]; then
    FRONTEND_PID=$(cat "$LOG_DIR/frontend.pid")
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        print_info "Stopping frontend (PID: $FRONTEND_PID)..."
        kill $FRONTEND_PID 2>/dev/null
        sleep 1
        if ! kill -0 $FRONTEND_PID 2>/dev/null; then
            print_success "Frontend stopped"
        else
            kill -9 $FRONTEND_PID 2>/dev/null
            print_success "Frontend force stopped"
        fi
    fi
    rm "$LOG_DIR/frontend.pid"
fi

# Stop by port
BACKEND_PIDS=$(lsof -ti :$BACKEND_PORT 2>/dev/null)
if [ -n "$BACKEND_PIDS" ]; then
    print_info "Stopping processes on backend port $BACKEND_PORT..."
    echo "$BACKEND_PIDS" | xargs kill -9 2>/dev/null
    print_success "Backend port cleared"
fi

FRONTEND_PIDS=$(lsof -ti :$FRONTEND_PORT 2>/dev/null)
if [ -n "$FRONTEND_PIDS" ]; then
    print_info "Stopping processes on frontend port $FRONTEND_PORT..."
    echo "$FRONTEND_PIDS" | xargs kill -9 2>/dev/null
    print_success "Frontend port cleared"
fi

# Verify
sleep 1
BACKEND_CHECK=$(lsof -ti :$BACKEND_PORT 2>/dev/null)
FRONTEND_CHECK=$(lsof -ti :$FRONTEND_PORT 2>/dev/null)

echo ""
if [ -z "$BACKEND_CHECK" ] && [ -z "$FRONTEND_CHECK" ]; then
    print_success "All services stopped successfully!"
else
    print_error "Some processes may still be running"
    [ -n "$BACKEND_CHECK" ] && print_error "Port $BACKEND_PORT: $BACKEND_CHECK"
    [ -n "$FRONTEND_CHECK" ] && print_error "Port $FRONTEND_PORT: $FRONTEND_CHECK"
fi

echo ""

