#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

show_menu() {
    clear
    echo -e "${BLUE}================================================================================"
    echo "                         MIYA AI VIRTUAL AVATAR SYSTEM"
    echo "                              Version 8.0.0"
    echo -e "================================================================================${NC}"
    echo
    echo "MAIN MENU:"
    echo
    echo "  === Client Startup ==="
    echo "  [1] QQ Client         - QQ Bot Client"
    echo "  [2] Web Client        - Web Interface Client"
    echo "  [3] Desktop Client    - React + Electron Desktop App"
    echo "  [4] Terminal Client  - Command Line Terminal"
    echo
    echo "  === Combined Startup ==="
    echo "  [5] All Clients      - QQ + Web + Desktop + Terminal (Full)"
    echo "  [6] Web + Desktop    - Web Client + Desktop Client"
    echo "  [7] Custom Launch    - Select services to start"
    echo
    echo "  === System Tools ==="
    echo "  [8] Development       - Code analysis and debugging"
    echo "  [9] Test Suite       - Run tests"
    echo "  [B] Build Web         - Build React web interface"
    echo
    echo "  === Quick Start ==="
    echo "  [Q] Quick Start      - Fast launch (Terminal + API)"
    echo
    echo "  [0] Exit             - Close launcher"
    echo
    echo -e "================================================================================"
    read -p "Enter your choice [0-9, B, Q]: " choice
}

check_file() {
    if [ -f "$1" ]; then
        return 0
    else
        return 1
    fi
}

start_terminal() {
    echo -e "${YELLOW}Starting Terminal System...${NC}"
    if check_file "run/miya_main.py"; then
        python run/miya_main.py
    else
        echo -e "${RED}Error: run/miya_main.py not found!${NC}"
    fi
}

start_api() {
    echo -e "${YELLOW}Starting API Server (port 8001)...${NC}"
    if check_file "run/runtime_api_start.py"; then
        python run/runtime_api_start.py
    else
        echo -e "${RED}Error: run/runtime_api_start.py not found!${NC}"
    fi
}

start_web() {
    echo -e "${YELLOW}Starting Web Service (port 8000)...${NC}"
    if check_file "webnet/web_main.py"; then
        python webnet/web_main.py
    else
        echo -e "${RED}Error: webnet/web_main.py not found!${NC}"
    fi
}

start_terminal_with_api() {
    echo -e "${GREEN}Starting Terminal + API...${NC}"
    if check_file "run/runtime_api_start.py"; then
        python run/runtime_api_start.py &
        API_PID=$!
        sleep 3
        echo -e "${GREEN}API Server started (PID: $API_PID)${NC}"
    fi
    
    if check_file "run/miya_main.py"; then
        python run/miya_main.py
    fi
    
    if [ ! -z "$API_PID" ]; then
        kill $API_PID 2>/dev/null
        echo -e "${GREEN}API Server stopped.${NC}"
    fi
}

start_web_with_api() {
    echo -e "${GREEN}Starting Web + API...${NC}"
    if check_file "run/runtime_api_start.py"; then
        python run/runtime_api_start.py &
        API_PID=$!
        sleep 3
        echo -e "${GREEN}API Server started (PID: $API_PID)${NC}"
    fi
    
    if check_file "webnet/web_main.py"; then
        python webnet/web_main.py
    fi
    
    if [ ! -z "$API_PID" ]; then
        kill $API_PID 2>/dev/null
        echo -e "${GREEN}API Server stopped.${NC}"
    fi
}

start_full_system() {
    echo -e "${GREEN}Starting Full System (Terminal + Web + API)...${NC}"
    PIDS=()
    
    if check_file "run/runtime_api_start.py"; then
        python run/runtime_api_start.py &
        PIDS+=($!)
        echo -e "${GREEN}[OK] API Server started (PID: ${PIDS[-1]})${NC}"
        sleep 2
    fi
    
    if check_file "webnet/web_main.py"; then
        python webnet/web_main.py &
        PIDS+=($!)
        echo -e "${GREEN}[OK] Web Service started (PID: ${PIDS[-1]})${NC}"
        sleep 1
    fi
    
    echo
    echo "Access URLs:"
    echo "  Web:    http://localhost:8000"
    echo "  API:    http://localhost:8001"
    echo "  Docs:   http://localhost:8001/docs"
    echo
    echo "Press Ctrl+C to stop all services."
    
    if check_file "run/miya_main.py"; then
        python run/miya_main.py
    fi
    
    for pid in "${PIDS[@]}"; do
        kill $pid 2>/dev/null
    done
    echo -e "${GREEN}All services stopped.${NC}"
}

build_web() {
    echo -e "${YELLOW}Building Web Frontend...${NC}"
    if command -v node &> /dev/null; then
        if [ -f "frontend/ui/package.json" ]; then
            cd frontend/ui
            npm run build
            cd ../..
        else
            echo -e "${RED}Frontend not found!${NC}"
        fi
    else
        echo -e "${RED}Node.js not installed!${NC}"
    fi
}

run_tests() {
    if command -v pytest &> /dev/null; then
        python -m pytest tests/ -v
    else
        echo -e "${RED}pytest not installed!${NC}"
    fi
}

while true; do
    show_menu
    
    case $choice in
        0)
            echo "Goodbye!"
            exit 0
            ;;
        1)
            start_api &
            sleep 2
            if check_file "run/qq_main.py"; then
                python run/qq_main.py
            else
                echo -e "${RED}QQ Bot script not found!${NC}"
            fi
            ;;
        2)
            start_web_with_api
            ;;
        3)
    # Desktop client
            echo -e "${YELLOW}Desktop client is not available in current version${NC}"
            ;;
        4)
            start_terminal_with_api
            ;;
        5)
            start_full_system
            ;;
        6)
            PIDS=()
            if check_file "run/runtime_api_start.py"; then
                python run/runtime_api_start.py &
                PIDS+=($!)
                sleep 2
            fi
            if check_file "webnet/web_main.py"; then
                python webnet/web_main.py &
                PIDS+=($!)
            fi
            echo "Desktop client is not available in current version"
            echo "Press Ctrl+C to stop all services."
            wait
            for pid in "${PIDS[@]}"; do
                kill $pid 2>/dev/null
            done
            ;;
        7)
            echo "Enter service numbers (1:API 2:Web 3:QQ 4:Desktop 5:Terminal):"
            read services
            PIDS=()
            
            if [[ $services == *"1"* ]] && check_file "run/runtime_api_start.py"; then
                python run/runtime_api_start.py &
                PIDS+=($!)
                echo "[OK] API Server started"
                sleep 2
            fi
            
            if [[ $services == *"2"* ]] && check_file "webnet/web_main.py"; then
                python webnet/web_main.py &
                PIDS+=($!)
                echo "[OK] Web Service started"
            fi
            
            if [[ $services == *"3"* ]] && check_file "run/qq_main.py"; then
                python run/qq_main.py &
                PIDS+=($!)
                echo "[OK] QQ Client started"
            fi
            
            if [[ $services == *"4"* ]]; then
                echo "[WARN] Desktop client is not available in current version"
            fi
            
            if [[ $services == *"5"* ]] && check_file "run/miya_main.py"; then
                python run/miya_main.py
            fi
            
            echo "Press Ctrl+C to stop all services."
            wait
            for pid in "${PIDS[@]}"; do
                kill $pid 2>/dev/null
            done
            ;;
        8)
            echo "Development Tools:"
            echo "[1] Debug Mode"
            echo "[2] Code Analysis"
            read dev_choice
            case $dev_choice in
                1) python run/miya_main.py --debug ;;
                2) python -m pylint core/ ;;
            esac
            ;;
        9)
            run_tests
            ;;
        B|b)
            build_web
            ;;
        Q|q)
            start_terminal_with_api
            ;;
        *)
            echo "Invalid choice!"
            ;;
    esac
    
    echo
    read -p "Press Enter to continue..."
done