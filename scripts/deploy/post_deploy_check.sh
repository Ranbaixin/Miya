#!/usr/bin/env bash
# 部署后自动冒烟（在服务器上执行）：
#   服务状态 → 健康端点 → doctor 运行时诊断（错误签名 / crash-loop / 记忆一致性）
# 用法：bash scripts/deploy/post_deploy_check.sh   （部署 + 重启后立刻跑）
# 退出码非 0 = 存在 FAIL，部署未通过验证
set -u
cd /opt/miya

FAIL=0

# 1. 服务状态
if systemctl is-active --quiet miya-daemon; then
  echo "✅ 服务 active"
else
  echo "❌ 服务未运行"
  exit 1
fi

# 2. 健康端点
CODE=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:9800/api/v1/health || echo 000)
if [ "$CODE" = "200" ]; then
  echo "✅ 健康端点 200"
else
  echo "❌ 健康端点 HTTP $CODE"
  FAIL=1
fi

# 3. NapCat 连接（5 分钟窗口内应有连接日志）
if journalctl -u miya-daemon --since "5 minutes ago" --no-pager 2>/dev/null | grep -q "NapCat 已连接"; then
  echo "✅ NapCat 已连接"
else
  echo "⚠️ 窗口内未见 NapCat 连接日志（若未重启 NapCat 可忽略）"
fi

# 4. doctor 运行时诊断（错误签名扫描 / crash-loop / 记忆一致性）
echo "---- doctor 运行时诊断 ----"
if .venv/bin/python scripts/doctor.py --runtime --since "5 minutes ago"; then
  echo "✅ doctor 运行时诊断通过"
else
  echo "❌ doctor 运行时诊断存在 FAIL"
  FAIL=1
fi

echo "=================================="
if [ "$FAIL" = "0" ]; then
  echo "✅ 部署冒烟全部通过"
else
  echo "❌ 部署冒烟未通过 — 按上方 FAIL 项修复后重试"
fi
exit $FAIL
