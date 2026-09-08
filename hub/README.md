# hub/ — 决策中枢

消息进出弥娅的唯一大脑：感知 → 上下文检索 → 策略 → AI 生成 → 后处理。

| 模块 | 职责 | 2026-09 变更 |
|---|---|---|
| `decision_hub.py` | `process_perception_cross_platform`（统一消息入口）→ `_generate_response_cross_platform`（Phase 1 并行上下文/谛听 → AI 生成） | **`fetch_diting_strategy` 对 `terminal`/`web` 平台跳过**（用户主动界面不受防打扰策略管辖；此前配置缺失时消息被静默丢弃）。谛听 `should_respond=False` → `return None` 的行为仅对 QQ 类平台生效 |
| `memory_manager.py` | 对话写入 `ConversationHistoryManager` + 统一记忆 | **session_id 优先读 `perception["api_session_id"]`**（API 透传，保证 `/api/chat/get_session` 写读一致）；无该字段按 `{platform}_private_{user_id}`（群聊 `{platform}_g{群}_u{用户}`）推导——QQ 行为不变 |
| `scheduler.py` | 定时任务调度器。`get_global_scheduler()` 全局单例；daemon 启动时由 `miya_daemon` 把 `Miya.scheduler` 登记为该单例（消除双实例） | 新代码一律经 `get_global_scheduler()` 取实例 |
| `platform_adapters.py` | 平台消息 ↔ M-Link Message（`TerminalAdapter` 等） | `TerminalAdapter.to_message` 产出 `{input, user_id, platform, ...}` 信封 |
| `platform_tools.py` | 平台场景化工具包 | — |

关键调用链（二开发最常用）：

```
任何平台/终端/API 消息
  → decision_hub.process_perception_cross_platform(Message)
      → content 提取（perception["content"]，终端信封取 ["input"]）
      → Phase 1 并行：会话上下文/知识/侧写/意识感知/搜索/工作记忆/谛听(QQ only)
      → _generate_response_cross_platform（AI 客户端；ai_client=None 时罐头回复）
      → memory_manager.store_user_message / store_unified_memory（写会话+统一记忆）
  → 返回响应文本
```

注意事项：
- 宽异常均带 `# noqa: BLE001` 理由注解（PHASE9 规范）；新增代码遵循同款。
- `ai_client=None` 不抛错而走 fallback——排查"回复千篇一律"先看 `/api/v1/health` 的 `degraded.ai_client`。
