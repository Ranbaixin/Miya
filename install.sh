#!/bin/bash
# ============================================================
#  MIYA v8.0 - Dependencies Installer (pip / uv 双模式)
#
#  pip 模式:
#    ./install.sh              完整安装
#    ./install.sh dev          开发环境
#    ./install.sh minimal      最小安装
#    ./install.sh lightweight  轻量级 (Mock 模式)
#    ./install.sh check        仅检查依赖
#    ./install.sh upgrade      升级全部依赖
#
#  uv 模式:
#    ./install.sh uv           完整安装
#    ./install.sh uv dev       开发环境
#    ./install.sh uv minimal   最小安装
#    ./install.sh uv lightweight  轻量级
#    ./install.sh uv sync      仅同步 uv.lock (离线/锁定)
# ============================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m'

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
            uv sync --extra full --group dev
            ;;
        minimal)
            uv sync
            ;;
        lightweight)
            uv sync --extra ai
            ;;
        sync)
            uv sync --extra full --group dev --frozen
            ;;
        *)
            uv sync --extra full
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

case "$MODE" in
    dev)
        pip install -r requirements.txt
        pip install -r setup/dependencies/dev.txt
        ;;
    minimal)
        pip install -r setup/requirements/minimal.txt
        ;;
    lightweight)
        pip install -r setup/requirements/lightweight.txt
        ;;
    check)
        python3 setup/scripts/check_deps.py
        exit 0
        ;;
    upgrade)
        pip install -r requirements.txt --upgrade
        ;;
    *)
        pip install -r requirements.txt
        ;;
esac

echo ""
echo -e "${BLUE}Verify installation...${NC}"
python3 setup/scripts/verify_install.py

echo ""
echo -e "${GREEN}Done! Run ./start.sh to launch MIYA.${NC}"
