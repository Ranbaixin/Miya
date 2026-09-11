#!/usr/bin/env bash
# NapCat 桥接自愈：检测反向 WS 断开 → 自动重启 napcat 容器恢复
#
# 判定逻辑与 core/doctor.py C8 一致：journalctl 最近 10 分钟内
# "NapCat 断开" 是最后事件（断开后无重连）= 当前断裂 → 触发自愈
# 频控：每日最多自愈 2 次（状态文件比对日期），防止重启风暴加重 QQ 风控；
#       超限时只记日志，依赖 doctor 每日 04:00 报告与 systemd failed 状态告警
#
# 由 miya-napcat-selfheal.timer 每 5 分钟调用；也可手动执行：bash napcat_selfheal.sh

set -u
LOG=/opt/miya/logs/napcat_selfheal.log
STATE=/var/lib/napcat_selfheal_state
DAILY_LIMIT=2
WINDOW="10 minutes ago"

mkdir -p "$(dirname "$LOG")"

log() { echo "[$(date '+%F %T')] $*" >> "$LOG"; }

# 当日自愈计数（跨重启持久在 /var/lib）
today=$(date '+%F')
if [ -f "$STATE" ]; then
    read -r state_date count < "$STATE"
else
    state_date=""; count=0
fi
if [ "$state_date" != "$today" ]; then
    state_date="$today"; count=0
fi

# 判定：窗口内是否有 NapCat 日志事件，最后事件是否为断开
events=$(journalctl -u miya-daemon --since "$WINDOW" --no-pager 2>/dev/null | grep -E "NapCat 已连接|NapCat 断开" | tail -1)
if [ -z "$events" ]; then
    exit 0  # 无事件（纯空闲窗口），不判定
fi

if echo "$events" | grep -q "NapCat 已连接"; then
    exit 0  # 最后事件为连接，桥接正常
fi

# 最后事件为断开 = 当前断裂
if [ "$count" -ge "$DAILY_LIMIT" ]; then
    log "SKIP 桥接断裂但已达每日自愈上限（$count/$DAILY_LIMIT），等待人工介入（docker restart napcat）"
    exit 0
fi

count=$((count + 1))
printf '%s %s\n' "$today" "$count" > "$STATE"
log "HEAL 检测到桥接断裂（窗口内最后事件为断开），第 $count/$DAILY_LIMIT 次自愈：docker restart napcat"
docker restart napcat >> "$LOG" 2>&1
log "HEAL 重启完成，等待回连（下次运行复核）"
