#!/bin/bash
# ============================================================
#  MIYA v8.0 - Dependency Installer (pip / uv dual mode)
#
#  pip mode:
#    ./install.sh              all deps
#    ./install.sh dev          all + dev tools
#    ./install.sh minimal      minimal
#    ./install.sh lightweight  lightweight (Mock mode)
#    ./install.sh check        check only
#    ./install.sh upgrade      upgrade all
#
#  uv mode:
#    ./install.sh uv           full
#    ./install.sh uv dev       dev
#    ./install.sh uv minimal   minimal
#    ./install.sh uv lightweight lightweight
#    ./install.sh uv sync      sync uv.lock (offline/locked)
# ============================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m'

export PYTHONUTF8=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# check python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[ERROR] Python 3 not found${NC}"
    exit 1
fi

# ==================== uv mode ====================
if [ "${1:-}" = "uv" ]; then
    shift
    install_uv_if_needed() {
        if ! command -v uv &> /dev/null; then
            echo -e "${YELLOW}[INFO] uv not found. Installing uv...${NC}"
            curl -LsSf https://astral.sh/uv/install.sh | sh
            # reload PATH
            export PATH="$HOME/.local/bin:$PATH"
        fi
    }
    install_uv_if_needed

    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  MIYA v8.0 - Installing Dependencies (uv)${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""

    MODE="${1:-full}"

    case "$MODE" in
        dev)
            uv sync --all-extras --group dev
            ;;
        minimal)
            uv sync
            ;;
        lightweight)
            uv sync --extra ai
            ;;
        sync)
            uv sync --all-extras --group dev --frozen
            ;;
        *)
            uv sync --all-extras
            ;;
    esac

    echo ""
    echo -e "${BLUE}Verify installation...${NC}"
    python3 setup/scripts/verify_install.py 2>/dev/null || echo -e "${YELLOW}[WARN] verify_install.py not found, skipping...${NC}"

    echo ""
    echo -e "${GREEN}Done! Run ./start.sh to launch MIYA.${NC}"
    exit 0
fi

# ==================== pip mode ====================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  MIYA v8.0 - Installing Dependencies (pip)${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

MODE="${1:-full}"

# Quick pre-check: skip pip if ALL dependencies already installed
if [ "$MODE" = "full" ]; then
    if python3 setup/scripts/verify_install.py --all > /dev/null 2>&1; then
        echo -e "${GREEN}[OK] All dependencies already installed, skipping...${NC}"
        echo ""
        echo -e "${GREEN}Done! Run ./start.sh to launch MIYA.${NC}"
        exit 0
    fi
    echo -e "${YELLOW}[INFO] Missing dependencies detected, installing...${NC}"
    echo ""
fi

case "$MODE" in
    dev)
        pip install -q -r setup/requirements/full.txt
        pip install -q -r setup/dependencies/dev.txt
        ;;
    minimal)
        pip install -q -r setup/requirements/minimal.txt
        ;;
    lightweight)
        pip install -q -r setup/requirements/lightweight.txt
        ;;
    check)
        python3 setup/scripts/check_deps.py
        exit 0
        ;;
    upgrade)
        pip install -r requirements.txt --upgrade
        ;;
    *)
        pip install -q -r requirements.txt
        ;;
esac

echo ""
echo -e "${BLUE}Verify installation...${NC}"
python3 setup/scripts/verify_install.py

echo ""
echo -e "${GREEN}Done! Run ./start.sh to launch MIYA.${NC}"
