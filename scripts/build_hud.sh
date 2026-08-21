#!/usr/bin/env bash
# ============================================================
#  构建 React Ops Center (frontend/ui -> frontend/packages/web/dist)
#  (2026-08) 背景：项目路径含 '#'（如 F:/#Ranxin/...），Vite/Rollup
#  无法解析该路径下的模块（URL fragment 截断），因此在无 '#' 的临时
#  目录构建，产物拷回项目内，再由 run/main.py 的 Web API 挂载。
#  用法: bash scripts/build_hud.sh
# ============================================================
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/frontend/ui"
DIST="$ROOT/frontend/packages/web/dist"
TMP_BASE="${TMPDIR:-/tmp}/miya_hud_build"

if [ ! -f "$SRC/package.json" ]; then
  echo "[build_hud] 未找到 $SRC/package.json"
  exit 1
fi

echo "[build_hud] 清理临时目录: $TMP_BASE"
rm -rf "$TMP_BASE"
mkdir -p "$TMP_BASE"

# 可选：注入管理 API token（若 .env 设置了 MIYA_API_TOKEN）
API_TOKEN=""
if [ -f "$ROOT/config/.env" ]; then
  API_TOKEN=$(grep -E '^MIYA_API_TOKEN=' "$ROOT/config/.env" | head -1 | cut -d= -f2-)
fi

echo "[build_hud] 复制前端到无#临时目录 ..."
cp -r "$SRC" "$TMP_BASE/ui"
cd "$TMP_BASE/ui"

echo "[build_hud] npm run build ..."
if [ -n "$API_TOKEN" ]; then
  VITE_API_KEY="$API_TOKEN" npm run build
else
  npm run build
fi

mkdir -p "$DIST"
cp -r "$TMP_BASE/packages/web/dist/." "$DIST/"
echo "[build_hud] 构建完成: $DIST"
