# QQ 私聊连续输入合并（DM Merge）线上实测清单

> 适用版本：fix/v8-hardening @ 2026-09-28 之后（含 DM 合并功能）。
> 执行方式：手机 QQ（superadmin）→ 机器人小号私聊；每项测试后用对应 grep 命令核对日志。
> 日志入口：`journalctl -u miya-daemon -f`（服务器）；本清单命令均为 workbench exec 内执行。

## 前置

- [ ] `systemctl is-active miya-daemon` = active
- [ ] `bash /opt/miya/scripts/deploy/post_deploy_check.sh` exit 0
- [ ] NapCat 在线：`docker ps` 有 napcat；弥娅日志近 5 分钟有「NapCat 已连接」

## T1 链路存活

- 操作：私聊发「在吗」
- 期待：秒级回复，内容正常
- 日志三连：
  ```bash
  journalctl -u miya-daemon --since "2 minutes ago" | grep -E "收到消息|开始聊天 \(工具数量|发送回复"
  ```
  三行齐全；「工具数量: N」N ≥ 60（registry 守卫生效证据）

## T2a 连发合并

- 操作：5 秒内连发 3 条不同内容（如「今天天气怎么样」「帮我记一下明天开会」「对了你还记得我上次说的那个事吗」）
- 期待：**只收到 1 条**综合回复，覆盖全部 3 条内容
- 日志：
  ```bash
  journalctl -u miya-daemon --since "3 minutes ago" | grep -cE "开始聊天 \(工具数量"
  ```
  = 1（只生成一次）

## T2b 生成中补输入（重算）

- 操作：发一条需要长回复的问题（如「给我讲讲你今天都做了什么吧，详细说说」），约 5 秒后补发「还有别忘了加上你昨晚的观察」
- 期待：最终回复覆盖两条；出现草稿重算日志
- 日志：
  ```bash
  journalctl -u miya-daemon --since "3 minutes ago" | grep "DM合并"
  ```
  期待看到「轮次#…被新输入替代，回答保留为草稿并重算」

## T2c 发送中补输入（下一轮）

- 操作：发长问题，等回复**开始到达**后立即再发「嗯继续」
- 期待：第二条获得独立回复（作为新一轮）

## T2d 指令旁路

- 操作：连发「状态」+ 一句闲聊
- 期待：「状态」即时回复（不参与合并）；闲聊走正常合并轮回复

## T2e 草稿零泄漏

- 操作：T2b 完成后检查
- 期待：桌面端（若开着）不出现被替代的回答；记忆中无草稿内容
- 抽查：
  ```bash
  journalctl -u miya-daemon --since "5 minutes ago" | grep -i "草稿"
  ```
  只有「保留为草稿」日志，无草稿发送日志

## T3 既有链路回归

- [ ] 指令：「状态」「形态」「余额」各自正常
- [ ] 记忆问答：「你还记得我昨天跟你说过的xxx吗」（换成真实记忆内容）
- [ ] PC 数据问答（家里电脑开机时）：「我今天电脑用了多久」
- [ ] 识图：发一张图，返回描述

## T4 群聊不变性

- [ ] 群内 @ 机器人 + 关键词 → 正常回复
- [ ] 群内非关键词、非 @ → 不插话
- [ ] 群聊日志无「DM合并」字样（合并器只管私聊）

## 失败处置

任一项异常：先 `systemctl restart miya-daemon` 复测一次；仍异常 → 快速回退：
`systemctl stop miya-daemon && sed -i 's/dm_merge_enabled: true/dm_merge_enabled: false/' /opt/miya/config/qq_config.yaml && systemctl start miya-daemon`（回退逐条回复，保留其余新功能），然后排查。
