#!/usr/bin/env bash
# ============================================================
#  MIYA v8.1 启动中心 (Linux/macOS)
#  用法:
#    ./start.sh          显示菜单
#    ./start.sh 1        终端模式 (run/main.py)
#    ./start.sh 2        守护进程 (run/daemon.py, API 9800)
#    ./start.sh 3        构建并启动 Web Ops Center (React HUD)
#  依赖: uv (https://docs.astral.sh/uv/) + Python 3.11
# ============================================================
set -e
cd "$(dirname "$0")"

if ! command -v uv >/dev/null 2>&1; then
    echo "[ERROR] 未找到 uv，请先安装: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

PY="uv run python"

case "$1" in
    1)
        exec $PY -X utf8 run/main.py
        ;;
    2)
        exec $PY -X utf8 run/daemon.py --api-port 9800
        ;;
    3)
        echo "[1/2] 构建 Web Ops Center ..."
        bash scripts/build_hud.sh
        echo "[2/2] 启动 daemon（含 Web API: 8000 与管理 API: 9800）..."
        exec $PY -X utf8 run/daemon.py --api-port 9800
        ;;
    "")
        echo "MIYA v8.1"
        echo "  [1] 终端模式   ./start.sh 1"
        echo "  [2] 守护进程   ./start.sh 2"
        echo "  [3] Web 界面   ./start.sh 3 (构建 HUD + 启动 daemon)"
        ;;
    *)
        echo "用法: ./start.sh [1|2|3]"
        exit 1
        ;;
esac
