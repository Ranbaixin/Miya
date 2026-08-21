#!/usr/bin/env bash
set -e
SRC="F:/#Ranxin/Miya/frontend/ui"
TMP="/f/tmp_hud"
rm -rf "$TMP"
mkdir -p "$TMP"
echo "[1/3] copying frontend (with node_modules) ..."
cp -r "$SRC" "$TMP/ui_build"
echo "[2/3] building in temp dir (no # in path) ..."
cd "$TMP/ui_build"
npm run build > build_tmp.log 2>&1 || { echo BUILD_FAILED; tail -20 build_tmp.log; exit 1; }
echo "[3/3] build OK"
ls -la ../packages/web/dist 2>/dev/null | head
find "$TMP/ui_build" -name dist -type d | head
