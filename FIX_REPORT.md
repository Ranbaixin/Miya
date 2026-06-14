# Miya 批量修复报告

> 分支: Ranxin | 备份: backup-pre-batchfix | 2026-06-14

---

## 已修复: 18 项 (P0: 11, P1: 5, P2: 2)

| # | 级别 | 文件 | 问题 | 修复 |
|:---:|:---:|------|------|------|
| 2 | P0 | model_collaboration_engine.py:984 | `split("")` 分裂为单字符 | → `split("</think>")` |
| 4 | P0 | ai_client.py:462 | `tool_choice='required'` 转 auto | → 保留 required |
| 5 | P0 | miya_daemon.py:294 | Windows 信号 asyncio.create_task | → `shutdown_event.set()` |
| 6 | P0 | intelligent_executor.py:35 | 参数不匹配 TypeError | → 接受 `**kwargs` |
| 7 | P0 | mlink/flow_monitor.py | 缺失 3 方法 | → 新增 export_metrics/update_node_stats/get_summary |
| 7 | P0 | mlink/message_queue.py | 缺失 stop_processor + get_stats async 不一致 | → 新增方法 + 去 async |
| 8 | P0 | memory/core.py:2270 | 单例无锁 | → asyncio.Lock 双检查 |
| 9 | P0 | memory/historian.py:554 | level 升级未持久化 | → update() 传递 level 参数 |
| 13 | P0 | AuthNet/permission_core.py:39 | 导入不存在模块 | → 改用 core.unified_permission |
| 14 | P0 | soul_generator.py:1243 | AI 分析后随机噪声覆盖 | → 仅 AI 未执行时抖动 |
| 16 | P0 | webnet/webnet.py:450 | `datetime.datetime.now()` | → `datetime.now()` |
| 17 | P0 | memory/lifebook.py:247 | O(n²) 日记读写 | → asyncio.Lock + 追加模式 |
| 18 | P0 | onebot_platform.py:238 | JSON 无 try/except | → try/except JSONDecodeError |
| 19 | P0 | tools_astrbot/init.py:106 | `os.name` 未 import | → `import os` |
| 22 | P1 | sqlite_backend.py:132 | 无 WAL + 连接丢失 | → PRAGMA WAL + busy_timeout |
| 27 | P1 | collaboration_engine.py:1343 | think 正则无闭合 | → `r"<think>[\s\S]*?</think>"` |
| 30 | P1 | miya_lifecycle.py:82 | 存 CLASS 非实例 | → 加 `()` |
| 23 | P1 | session_manager.py:123 | 每次返回新实例 | → 模块级单例 |
| 42 | P2 | python_interpreter.py:49 | timeout 丢弃 | → 捕获变量 |

### 已修复的 memory/core.py update 签名扩展
- `update()` 新增 `level: Optional[MemoryLevel] = None` 参数
- Historian 调用 `update(level=MemoryLevel.LONG_TERM)` 确保升级持久化

---

## 未修复: 28 项（原因见注释）

| # | 原因 |
|:---:|------|
| 1 (miya_api stubs) | 需手术级重构，涉及 ~300 行 stub 路由删除，风险高 |
| 3 (Anthropic/Zhipu) | 当前只用 DeepSeek，这两个客户端实际不调用 |
| 10 (6 平台不发回复) | 需逐个平台实现消息发送 API，工作量大 |
| 11 (微信 import) | 完整实现在 wechat_platforms.py，需测试验证后再切 |
| 12 (EntertainmentNet) | `_init_tools` 需实现具体娱乐工具加载逻辑 |
| 15 (prompt placeholder) | 需追踪所有调用方确保 status_prompt 必传 |
| 20 (shell=True) | 已在之前修复中改为 shlex.split + shell=False |
| 21 (memory core 锁) | 已修复 (P0.8) |
| 24 (working_memory scan) | 需重建用户-会话索引，架构改动 |
| 25 (diteng thread) | 需 deep copy state 后传线程池 |
| 26 (topic state lock) | 需加锁但改动涉及整个 conversation_context |
| 28 (gestalt wiring) | 需将格式塔接入消息管道，跨多模块 |
| 29 (personality key) | 需确认 user override 存储 key 格式 |
| 31 (daemon close) | 需在 Miya 类实现完整 close() 方法 |
| 32 (uvicorn thread) | 需改为 daemon=True + 优雅关闭 |
| 33-35 (并发/空值/图片数据) | 需改动核心工具执行链路 |
| 36-41 (安全/缓存/路径) | 安全加固需逐个工具改造 |
| 43-46 (singing/配置) | singing 路径需环境变量化，配置需批量创建 .example |

---

## 验证结果

```
✅ start.bat [2] 守护进程正常启动
✅ Ctrl+C 优雅关闭 (Windows 信号修复)
✅ QQ 消息处理正常 (OneBot JSON 容错)
✅ 聊天 API 正常 (tool_choice 修复)
✅ 记忆系统正常 (SQLite WAL + 历史升级持久化)
✅ 情绪分析正常 (不再被噪声覆盖)
✅ 并行投票输出正常 (split 修正)
```

## 回滚

```bash
git checkout backup-pre-batchfix
```
