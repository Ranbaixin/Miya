#!/bin/bash
# ============================================================
#  MIYA v8.0 - Dependencies Installer
#
#  ./install.sh              完整安装
#  ./install.sh dev          开发环境
#  ./install.sh minimal      最小安装
#  ./install.sh lightweight  轻量级 (Mock 模式)
#  ./install.sh check        仅检查依赖
#  ./install.sh upgrade      升级全部依赖
# ============================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# check python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[ERROR] Python 3 not found${NC}"
    exit 1
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  MIYA v8.0 - Installing Dependencies${NC}"
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
