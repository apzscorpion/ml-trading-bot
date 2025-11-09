#!/bin/bash

##############################################################################
# Trading Prediction App - Complete Startup Script
# This script stops any running instances, starts backend and frontend,
# and logs all output to files and console
##############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Port configuration
BACKEND_PORT=8182
FRONTEND_PORT=5155

# Log directory
LOG_DIR="logs"
BACKEND_LOG="${LOG_DIR}/backend.log"
FRONTEND_LOG="${LOG_DIR}/frontend.log"
COMBINED_LOG="${LOG_DIR}/combined.log"

# Get project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

##############################################################################
# Helper Functions
##############################################################################

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

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

##############################################################################
# Step 1: Create log directory
##############################################################################

create_log_dir() {
    print_header "Step 1: Preparing Log Directory"
    
    if [ ! -d "$LOG_DIR" ]; then
        mkdir -p "$LOG_DIR"
        print_success "Created log directory: $LOG_DIR"
    else
        print_info "Log directory already exists"
    fi
    
    # Clear old logs
    > "$BACKEND_LOG"
    > "$FRONTEND_LOG"
    > "$COMBINED_LOG"
    print_success "Cleared old log files"
}

##############################################################################
# Step 2: Check and stop processes on ports
##############################################################################

stop_process_on_port() {
    local port=$1
    local service_name=$2
    
    print_info "Checking port $port for $service_name..."
    
    # Find process using the port
    local pids=$(lsof -ti :$port 2>/dev/null)
    
    if [ -n "$pids" ]; then
        print_warning "Found process(es) on port $port: $pids"
        echo "$pids" | xargs kill -9 2>/dev/null || true
        sleep 1
        
        # Verify it's killed
        local check_pids=$(lsof -ti :$port 2>/dev/null)
        if [ -z "$check_pids" ]; then
            print_success "Successfully stopped $service_name on port $port"
        else
            print_error "Failed to stop process on port $port"
            return 1
        fi
    else
        print_success "Port $port is available"
    fi
}

check_and_stop_services() {
    print_header "Step 2: Checking and Stopping Existing Services"
    
    stop_process_on_port $BACKEND_PORT "Backend"
    stop_process_on_port $FRONTEND_PORT "Frontend"
    
    print_success "All ports are now available"
}

##############################################################################
# Step 3: Verify Backend Setup
##############################################################################

verify_backend() {
    print_header "Step 3: Verifying Backend Setup"
    
    cd "$PROJECT_ROOT/backend"
    
    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        print_error "Virtual environment not found"
        print_info "Creating virtual environment..."
        python3 -m venv venv
        print_success "Virtual environment created"
    else
        print_success "Virtual environment exists"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Check if requirements are installed
    print_info "Checking Python dependencies..."
    pip install -q -r requirements.txt
    print_success "All Python dependencies are installed"
    
    # Check database
    if [ ! -f "trading_predictions.db" ]; then
        print_warning "Database not found, initializing..."
        python database.py
        print_success "Database initialized"
    else
        print_success "Database exists"
    fi
    
    cd "$PROJECT_ROOT"
}

##############################################################################
# Step 4: Verify Frontend Setup
##############################################################################

verify_frontend() {
    print_header "Step 4: Verifying Frontend Setup"
    
    cd "$PROJECT_ROOT/frontend"
    
    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        print_warning "Node modules not found"
        print_info "Installing dependencies (this may take a while)..."
        npm install
        print_success "Frontend dependencies installed"
    else
        print_success "Node modules exist"
    fi
    
    cd "$PROJECT_ROOT"
}

##############################################################################
# Step 5: Start Backend Server
##############################################################################

start_backend() {
    print_header "Step 5: Starting Backend Server"
    
    cd "$PROJECT_ROOT/backend"
    source venv/bin/activate
    
    print_info "Starting FastAPI server on port $BACKEND_PORT..."
    
    # Set PYTHONPATH to project root
    export PYTHONPATH="$PROJECT_ROOT:${PYTHONPATH}"
    
    # Start backend in background with logging
    nohup python main.py > "../$BACKEND_LOG" 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > "../logs/backend.pid"
    
    print_success "Backend started (PID: $BACKEND_PID)"
    print_info "Backend logs: $BACKEND_LOG"
    
    # Wait for backend to be ready
    print_info "Waiting for backend to be ready..."
    for i in {1..30}; do
        if curl -s http://localhost:$BACKEND_PORT/health > /dev/null 2>&1; then
            print_success "Backend is ready!"
            curl -s http://localhost:$BACKEND_PORT/health | python3 -m json.tool 2>/dev/null || echo ""
            break
        fi
        if [ $i -eq 30 ]; then
            print_error "Backend failed to start within 30 seconds"
            print_error "Check logs: tail -f $BACKEND_LOG"
            return 1
        fi
        sleep 1
        echo -n "."
    done
    
    cd "$PROJECT_ROOT"
}

##############################################################################
# Step 6: Start Frontend Server
##############################################################################

start_frontend() {
    print_header "Step 6: Starting Frontend Server"
    
    cd "$PROJECT_ROOT/frontend"
    
    print_info "Starting Vite dev server on port $FRONTEND_PORT..."
    
    # Start frontend in background with logging
    nohup npm run dev > "../$FRONTEND_LOG" 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > "../logs/frontend.pid"
    
    print_success "Frontend started (PID: $FRONTEND_PID)"
    print_info "Frontend logs: $FRONTEND_LOG"
    
    # Wait for frontend to be ready
    print_info "Waiting for frontend to be ready..."
    for i in {1..30}; do
        if curl -s -o /dev/null -w "%{http_code}" http://localhost:$FRONTEND_PORT | grep -q "200\|301\|302\|304"; then
            print_success "Frontend is ready!"
            break
        fi
        if [ $i -eq 30 ]; then
            print_error "Frontend failed to start within 30 seconds"
            print_error "Check logs: tail -f $FRONTEND_LOG"
            return 1
        fi
        sleep 1
        echo -n "."
    done
    
    cd "$PROJECT_ROOT"
}

##############################################################################
# Step 7: Display Status and Instructions
##############################################################################

display_status() {
    print_header "Step 7: Application Status"
    
    echo -e "${GREEN}🎉 All services started successfully!${NC}\n"
    
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}                    SERVICE INFORMATION                      ${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    
    echo -e "${MAGENTA}📱 Frontend (Vue.js)${NC}"
    echo -e "   URL:      ${GREEN}http://localhost:$FRONTEND_PORT${NC}"
    echo -e "   PID:      $(cat logs/frontend.pid 2>/dev/null || echo 'N/A')"
    echo -e "   Logs:     ${BLUE}tail -f $FRONTEND_LOG${NC}\n"
    
    echo -e "${MAGENTA}🚀 Backend (FastAPI)${NC}"
    echo -e "   API:      ${GREEN}http://localhost:$BACKEND_PORT${NC}"
    echo -e "   Docs:     ${GREEN}http://localhost:$BACKEND_PORT/docs${NC}"
    echo -e "   Health:   ${GREEN}http://localhost:$BACKEND_PORT/health${NC}"
    echo -e "   WebSocket: ${GREEN}ws://localhost:$BACKEND_PORT/ws${NC}"
    echo -e "   PID:      $(cat logs/backend.pid 2>/dev/null || echo 'N/A')"
    echo -e "   Logs:     ${BLUE}tail -f $BACKEND_LOG${NC}\n"
    
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    
    echo -e "${YELLOW}📋 Useful Commands:${NC}"
    echo -e "   View backend logs:  ${BLUE}tail -f $BACKEND_LOG${NC}"
    echo -e "   View frontend logs: ${BLUE}tail -f $FRONTEND_LOG${NC}"
    echo -e "   View all logs:      ${BLUE}tail -f $COMBINED_LOG${NC}"
    echo -e "   Stop services:      ${BLUE}./stop.sh${NC}"
    echo -e "   Check status:       ${BLUE}./status.sh${NC}\n"
    
    echo -e "${GREEN}🌐 Open your browser and navigate to:${NC}"
    echo -e "${GREEN}   http://localhost:$FRONTEND_PORT${NC}\n"
    
    echo -e "${YELLOW}⚡ Press Ctrl+C to stop tailing logs (services will continue running)${NC}\n"
}

##############################################################################
# Step 8: Tail Logs
##############################################################################

tail_logs() {
    print_header "Step 8: Tailing Logs (Press Ctrl+C to exit)"
    
    # Check if running in interactive terminal
    if [ ! -t 1 ]; then
        print_info "Non-interactive terminal detected, skipping log tail"
        print_info "View logs with: tail -f logs/backend.log"
        return 0
    fi
    
    # Create a combined log view
    (
        tail -f "$BACKEND_LOG" 2>/dev/null | sed "s/^/[BACKEND]  /" &
        tail -f "$FRONTEND_LOG" 2>/dev/null | sed "s/^/[FRONTEND] /" &
        wait
    ) | tee -a "$COMBINED_LOG"
}

##############################################################################
# Cleanup on exit
##############################################################################

cleanup() {
    echo -e "\n\n${YELLOW}Logs are still being written to:${NC}"
    echo -e "  - $BACKEND_LOG"
    echo -e "  - $FRONTEND_LOG"
    echo -e "  - $COMBINED_LOG"
    echo -e "\n${GREEN}Services are still running in the background.${NC}"
    echo -e "${YELLOW}To stop them, run: ./stop.sh${NC}\n"
}

trap cleanup EXIT

##############################################################################
# Main Execution
##############################################################################

main() {
    # Clear screen if terminal supports it
    if [ -t 1 ]; then
        clear || true
    fi
    
    echo -e "${CYAN}"
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║                                                                ║"
    echo "║        📈 AI Trading Prediction App - Startup Script          ║"
    echo "║                                                                ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}\n"
    
    print_info "Project root: $PROJECT_ROOT"
    print_info "Backend port: $BACKEND_PORT"
    print_info "Frontend port: $FRONTEND_PORT\n"
    
    # Execute all steps
    create_log_dir
    check_and_stop_services
    verify_backend
    verify_frontend
    start_backend
    start_frontend
    display_status
    
    # Tail logs
    tail_logs
}

# Run main function
main

