#!/bin/bash
# ============================================================
#  MIYA v8.0 - Frontend Build
#
#  ./build.sh             build all (CCE + Desktop + Web)
#  ./build.sh cce         CCE terminal only
#  ./build.sh desktop     Electron desktop app only
#  ./build.sh web         Web Ops Center only
# ============================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# check bun
if ! command -v bun &> /dev/null; then
    echo -e "${RED}[ERROR] bun not found. Install: npm install -g bun${NC}"
    exit 1
fi

# check node
if ! command -v node &> /dev/null; then
    echo -e "${RED}[ERROR] Node.js not found${NC}"
    exit 1
fi

MODE="${1:-all}"

# ==================== CCE ====================
build_cce() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Building Claude Code Engine (CCE)...${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    cd claude-code-engine
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}[INFO] Installing CCE dependencies...${NC}"
        bun install
    fi
    echo -e "${YELLOW}[INFO] Building CCE...${NC}"
    bun run build
    cd ..
    echo -e "${GREEN}[OK] CCE build complete${NC}"
}

# ==================== Desktop ====================
build_desktop() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Building Electron Desktop App...${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    if [ -f "miya_frontend/package.json" ]; then
        cd miya_frontend
        if [ ! -d "node_modules" ]; then
            echo -e "${YELLOW}[INFO] Installing desktop dependencies...${NC}"
            npm install
        fi
        echo -e "${YELLOW}[INFO] Building desktop app...${NC}"
        npm run build
        cd ..
        echo -e "${GREEN}[OK] Desktop build complete${NC}"
    else
        echo -e "${YELLOW}[WARN] miya_frontend not found, skipping...${NC}"
    fi
}

# ==================== Web ====================
build_web() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Building Web Ops Center...${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    if [ -f "frontend/ui/package.json" ]; then
        cd frontend/ui
        if [ ! -d "node_modules" ]; then
            echo -e "${YELLOW}[INFO] Installing web dependencies...${NC}"
            npm install
        fi
        echo -e "${YELLOW}[INFO] Building web frontend...${NC}"
        npm run build
        cd ../..
        echo -e "${GREEN}[OK] Web build complete${NC}"
    else
        echo -e "${YELLOW}[WARN] frontend/ui not found, skipping...${NC}"
    fi
}

case "$MODE" in
    cce)
        build_cce
        ;;
    desktop)
        build_desktop
        ;;
    web)
        build_web
        ;;
    all|*)
        build_cce
        build_desktop
        build_web
        ;;
esac

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Build Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
