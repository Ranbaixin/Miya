# core/ — 灵魂锚点与核心服务

人格/伦理/身份等"灵魂"组件，以及 Web API、平台抽象、AI 客户端等核心服务。

## 2026-09 变更与新增（二开发重点）

| 模块 | 说明 |
|---|---|
| `web_api/auth_security.py` | **统一访问网关**：`install_token_gate(app)`（本机放行/远程验 `MIYA_API_TOKEN`）与 `websocket_gate(ws)`（WS 握手校验）。JWT（HS256）签发/校验、scrypt 口令。9800/8000 同源复用。新增敏感端点勿入 public_paths |
| `event_bus.py` | **轻量事件总线**（2026-09 新增）：`emit_event`/`on_event`，零依赖、监听器异常不影响主链路。当前用于平台消息 → ManagementAPI WS `new_message` 推送。新增实时通知走这里 |
| `web_api/miya_api.py` | 8000 业务主路由（120+ 条）。2026-09 修复：`get_session` 用 `get_history()`（原方法名不存在导致历史永远为空）；`chat/send` 透传 `api_session_id`；`/api/memory/search` query 参数修复；重复路由注册清理；版本号统一 `core/version.py` |
| `web_api/tools.py` | `/api/tools/task_execute` **已移除 shell 执行分支**（P0 RCE 封堵）；`subprocess` 导入已删 |
| `web_api/__init__.py` | `/api/config/file` 加 `commonpath` 边界校验 + `.env*` 黑名单（P0 任意读封堵）；新增 `/api/audio/transcribe`（501 占位） |
| `web_api/desktop.py` | `files/write` 改 JSON body（原 query 签名前端必 422）；新增 `files/parse`、`files/upload` |
| `web_api.py` | ⚠️ 已删除（与 `web_api/` 包同名遮蔽的死文件） |
| `miya_daemon.py` | 关闭链补 `ashutdown()`（进程不再悬挂）；`get_daemon_status` 暴露 `degraded.ai_client`；`--platforms` 未知 id 显式报错；启动前 `set_global_scheduler(miya.scheduler)` 消除调度器双实例 |
| `management_api.py` | 网关重构为复用 `install_token_gate`；WS 握手前 `websocket_gate`；新增 `POST /api/v1/daemon/shutdown`；版本号引用 `core/version.py` |
| `unified_platform_impl/webhook_platforms.py` | KOOK/Slack/LINE/Satori 为「只收不发」壳且**未注册**——接入前无暴露；实现收发后需同时注册到 `miya_daemon._create_platform` |
| `proactive_chat.py` | 死存根 `_try_get_ai_message` 已删除 |
| `version.py` | **版本号单一真源**（`VERSION`），任何显示点禁止硬编码 |

## 稳定组件（语义未变）

`personality.py` / `ethics.py` / `identity.py`（version 引自 core/version.py）/ `entropy.py` /
`prompt_manager.py` / `ai_client.py` / `model_pool_manager.py` / `stable_persona.py` /
`knowledge_base/` / `singing/` / `tts/` / `config_hot_reload.py` / `unified_permission.py`（fail-closed）/ `grag_memory.py`

## 约定提醒

- 初始化失败**禁止静默吞**：要么 raise，要么按 `ai_degraded` 模式在 daemon status 暴露降级。
- Web API 路由注册失败不再允许「try 吞掉后照常启动」——历史上曾因一个未导入符号导致 168 条路由
  全部静默消失（`tests/unit/webapi/` 有回归覆盖）。
