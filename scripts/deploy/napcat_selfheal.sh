#!/usr/bin/env bash
# NapCat 桥接/会话自愈 v2：两种断裂场景分而治之
#
# 场景 A（WS 桥接断裂）：miya 日志窗口内最后事件为"NapCat 断开"——
#   凭据可能仍有效，docker restart napcat 即可恢复（2026-09-10 06:10 型）
# 场景 B（QQ 会话被踢，WS 未必断）：napcat 日志出现 KickedOffLine/登录已失效——
#   2026-09-11 16:20 型。僵尸连接下消息早已不通，但 WS 断开判定永远不会触发。
#   处置：密码回退启用时 → 重启走密码登录（带卡死防护）；
#         密码回退停用（当前状态：密码登录触发短信验证会卡死 NapCat）→
#         不重启（重启只会落在二维码等待），写 NEED_MANUAL_SCAN 标记醒目告警
#
# 防风暴：每日重启上限（状态文件跨重启持久）；NEED_MANUAL_SCAN 当日生效次日自动清除
# 由 miya-napcat-selfheal.timer 每 5 分钟调用

set -u
LOG=/opt/miya/logs/napcat_selfheal.log
STATE=/var/lib/napcat_selfheal_state
SCAN_FLAG=/var/lib/napcat_manual_scan_flag
NAPCAT_ENV=/opt/napcat/.env
DAILY_LIMIT=4
WINDOW="10 minutes ago"

mkdir -p "$(dirname "$LOG")"

log() { echo "[$(date '+%F %T')] $*" >> "$LOG"; }

today=$(date '+%F')

# ---------- 每日状态管理（自愈计数 + 人工扫码标记次日自动清除） ----------
count=0
if [ -f "$STATE" ]; then
    read -r state_date count < "$STATE"
    [ "$state_date" != "$today" ] && count=0
fi
if [ -f "$SCAN_FLAG" ] && [ "$(head -1 "$SCAN_FLAG" 2>/dev/null)" != "$today" ]; then
    rm -f "$SCAN_FLAG"
fi

# ---------- 场景 B：QQ 会话被踢（优先判定，僵尸连接场景） ----------
napcat_events=$(docker logs --since "$WINDOW" napcat 2>&1 | grep -E "KickedOffLine|登录已失效|登录成功" | tail -1)
if [ -n "$napcat_events" ]; then
    if echo "$napcat_events" | grep -qE "KickedOffLine|登录已失效"; then
        if [ -f "$SCAN_FLAG" ]; then
            exit 0  # 已标记需人工扫码，当日不再动作
        fi
        if grep -qE "^NAPCAT_QUICK_PASSWORD" "$NAPCAT_ENV" 2>/dev/null && [ "$count" -lt "$DAILY_LIMIT" ]; then
            count=$((count + 1))
            printf '%s %s\n' "$today" "$count" > "$STATE"
            log "HEAL-B 会话被踢（KickedOffLine），密码回退已启用，第 $count/$DAILY_LIMIT 次重启走密码登录"
            docker restart napcat >> "$LOG" 2>&1
            exit 0
        fi
        printf '%s 需人工扫码\n' "$today" > "$SCAN_FLAG"
        log "ALERT-B 会话被踢且密码回退未启用/已达上限——需人工扫码恢复（QQ 扫码后自动回连）"
        exit 0
    fi
    # 最后事件为登录成功：会话活着
    exit 0
fi

# ---------- 场景 A：WS 桥接断裂 ----------
miya_events=$(journalctl -u miya-daemon --since "$WINDOW" --no-pager 2>/dev/null | grep -E "NapCat 已连接|NapCat 断开" | tail -1)
[ -z "$miya_events" ] && exit 0  # 无事件，纯空闲窗口

if echo "$miya_events" | grep -q "NapCat 已连接"; then
    exit 0  # 最后事件为连接，桥接正常
fi

if [ -f "$SCAN_FLAG" ]; then
    log "SKIP-A 桥接断裂但已标记需人工扫码，等待扫码"
    exit 0
fi
if [ "$count" -ge "$DAILY_LIMIT" ]; then
    log "SKIP-A 桥接断裂但已达每日自愈上限（$count/$DAILY_LIMIT），等待人工介入"
    exit 0
fi

count=$((count + 1))
printf '%s %s\n' "$today" "$count" > "$STATE"
log "HEAL-A 检测到桥接断裂，第 $count/$DAILY_LIMIT 次自愈：docker restart napcat"
docker restart napcat >> "$LOG" 2>&1
log "HEAL-A 重启完成，等待回连（下次运行复核）"
