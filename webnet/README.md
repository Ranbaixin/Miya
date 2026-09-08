# webnet/ — 蛛网子网

| 子网 | 说明 | 2026-09 变更 |
|---|---|---|
| `ToolNet/` | 工具注册表（`registry.py`）+ 68+ 工具实现（`tools/`）+ AgentHub | **占位工具暂停注册**：knowledge/cognitive/group/auth 系列曾直接把占位文案暴露给 LLM，已在 `_load_*_tools` 注释掉注册；接真实现后恢复。`get_tool_registry()`/`get_tool_subnet()` 是单例访问点（`__init__.py`），Web API `/api/tools/list` 依赖它 |
| `memory.py` | MemoryNet：装配 `ConversationHistoryManager`（`data/conversations/`）+ M-Link 注册 | 会话历史的唯一宿主；`get_history(session_id)` 读取（无 get_session 方法） |
| `miya_webui.py` | `/api/management/*`、`/api/runtime/*` 管理路由（挂 8000） | — |
| `AuthNet/EntertainmentNet/...` | 其余子网按需加载；缺失依赖时诚实降级（如 EntertainmentNet 打印"0 个娱乐工具"） | — |

注意：`NetManager`/`CrossNetEngine`（"蛛网架构"壳）已于 2026-09 从 run/main.py 移除（死对象）。
`web_main.py` 已删除——8000 端口的 Web API 由 `run/main.py` 挂载 `core/web_api/` 提供。
