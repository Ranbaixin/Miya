# Miya 全面审计终版报告

> 分支: Ranxin | 备份: backup-pre-batchfix | 2026-06-15

---

## 审计规模

| 轮次 | 模块 | Agent | 发现 |
|------|------|:---:|:---:|
| 全项目基础扫描 | 全局 | 6 | 97 |
| core/ 深挖 | core/ | 8 | 180 |
| hub/ 深挖 | hub/ | 4 | 32 |
| webnet/ 深挖 | webnet/ | 4 | 70 |
| memory/ 深挖 | memory/ | 3 | 33 |
| run/config/mlink 深挖 | run/config/mlink | 3 | 43 |
| **合计** | **全项目** | **28** | **455** |

---

## 已修复统计

| 轮次 | 修复数 | 说明 |
|------|:---:|------|
| 前序对话修复 | ~25 | 版本/BOM/Neo4j/安全/性能/记忆优化 |
| BATCH_REVIEW.md P0-P2 | 18 | 运行时崩溃+数据完整性+功能恢复 |
| 四轮深挖后修复 | - | 未新增修复(仅审计发现) |
| **合计** | **43** | |

---

## 四轮深挖新增 TOP 10 关键发现

| # | 文件 | 问题 | 严重度 |
|:---:|------|------|:---:|
| 1 | run/main.py:1026 | terminal main_loop未调用,交互式聊天死代码 | high |
| 2 | run/main.py:146/347 | MLinkCore双重创建,第一个实例泄漏 | high |
| 3 | run/main.py:805 | shutdown()不关闭Neo4j/vector/AI client/uvicorn | high |
| 4 | hub/decision_hub.py:1702 | content变量被reply覆盖,用户消息丢失 | high |
| 5 | hub/decision_hub.py:757 | asyncio.run()在运行loop中调用→RuntimeError | high |
| 6 | hub/decision_hub.py:1650 | emotions返回list时调用.items()→AttributeError | high |
| 7 | webnet/qq/message_parser.py:82 | CQ码无=号参数时崩溃 | high |
| 8 | onebot_platform.py:519 | CQ image file含逗号时截断 | high |
| 9 | memory/core.py:540 | load()无锁→读写并发数据损坏 | high |
| 10 | memory/core.py:2107 | 备份文件无锁→并发写数据丢失 | high |

---

## 守护进程自检结果



## 待处理优先清单

1. 实施 miya_app.py 重构(消除 run→core 循环导入)
2. 补全 Miya.shutdown() 资源关闭
3. 修复 hub/ content 覆盖 bug
4. 修复 terminal 模式 main_loop
5. 补全平台回复发送(KOOK/Slack/钉钉/微信)
6. 清理 miya_api.py stub 路由
7. 清理低可行性文件(astrbot/platform_astrbot/旧前端)
