# 弥娅 API 参考（2026-09 修订）

> 本文档基于 2026-09-07/08 实测重写（旧版含大量已不存在的路由，见 git 历史）。
> 完整路由清单以运行时 OpenAPI 为准：管理 API `http://localhost:9800/docs`、Web API `http://localhost:8000/docs`（本机访问时）。
> 当前实测规模：管理 API 15 条 REST + 1 条 WS；Web API 约 208 条路由。

---

## 0. 双 API 架构与鉴权（必读）

| 服务 | 端口 | 职责 | 入口代码 |
|---|---|---|---|
| **管理 API** | 9800 | 守护进程控制面：健康/平台热插拔/WS 事件流 | `core/management_api.py` |
| **Web API** | 8000 | 业务面：聊天/记忆/人格/配置/文件/工具/插件/MCP | `core/web_api/`（`run/main.py` 挂载） |

**鉴权规则**（2026-09 加固，`core/web_api/auth_security.py: install_token_gate`，两端口同源）：

- **本机（loopback，127.0.0.1/::1）**：放行（本地前端/桌面无感使用）。
- **远程**：必须携带 `Authorization: Bearer <MIYA_API_TOKEN>` 或 `X-Miya-Token` 头；未设置 `MIYA_API_TOKEN` 时远程一律 403，设置了则错误 token 401（恒时比较）。
- 公开路径：`/docs`、`/openapi.json`、`/redoc`、登录端点、健康探活（见 `install_token_gate(public_paths=...)`）。
- **WebSocket 不受 HTTP 中间件保护**，9800 的 `/api/v1/ws` 在握手前单独校验（`websocket_gate`）。
- 已封堵的历史高危端点：`POST /api/tools/task_execute` 不再执行 shell 命令；`GET /api/config/file` 拒绝读取 `.env*` 且路径边界用 `commonpath` 校验。

---

## 1. 管理 API（9800）

```bash
uv run python -X utf8 run/daemon.py --api-port 9800
```

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/health` | 健康检查；含 `degraded.ai_client`（AI 不可用降级标记）与平台统计 |
| GET | `/api/v1/platforms` | 平台列表（含 online/error_count/latency 等） |
| GET | `/api/v1/platforms/{id}` | 单平台状态 |
| POST | `/api/v1/platforms/{id}/start` | 热启动平台（仅已启用平台，`config/platforms_config.py`） |
| POST | `/api/v1/platforms/{id}/stop` | 热停止 |
| POST | `/api/v1/platforms/{id}/restart` | 热重启 |
| GET | `/api/v1/daemon/status` | 守护进程状态（version/uptime/degraded） |
| POST | `/api/v1/daemon/shutdown` | **优雅关闭**（走完整 ashutdown 关闭链，端口释放后进程退出） |
| GET | `/api/v1/auth/status` | 权限引擎统计 |
| GET | `/api/v1/auth/roles` | 角色列表 |
| GET | `/api/v1/auth/users` | 用户列表 |
| GET | `/api/v1/auth/users/{user_id}` | 单用户权限详情 |
| GET | `/api/v1/auth/check?user_id=&permission=` | 权限判定 |
| WS | `/api/v1/ws` | 实时事件流（见下） |

### WebSocket `/api/v1/ws`

- 连接后服务端即推 `{"type":"initial_state","platforms":[...],"daemon":{...}}`。
- 客户端可发 action：`get_status` / `start_platform` / `stop_platform` / `restart_platform`（带 `platform_id`），回 `action_result` / `status_update` / `error`。
- 广播：平台收发消息会以 `{"type":"platform_event"|"new_message", ...}` 推送（事件源：`core/event_bus.py` ← `message_mixin._emit_realtime_events`）。桌面端 `useMIYARealtime.ts` 消费 `new_message` 实现跨平台消息实时显示。
- 事件负载顶层展开（`{type, timestamp, **event}`），前端取 `data.data || data` 兼容。

---

## 2. Web API（8000，按模块分类）

> 以下为二开发常用端点；全部清单看 `/docs`。所有路由均受第 0 节网关保护。

### 2.1 聊天与会话（`core/web_api/miya_api.py`）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/chat/send` | **主聊天端点**（桌面 UI/终端等价入口）。请求 `{message, session_id="default", platform="web", user_id?}`；响应 `{success, response, emotion{dominant,intensity}, personality, soul, tools_used, memory_retrieved}` |
| POST | `/api/chat` | 兼容端点（非流式，`core/web_api/__init__.py`） |
| GET | `/api/chat/sessions` | 会话列表 → `{success, data:[{session_id, display_name, ...}]}` |
| GET | `/api/chat/get_session?session_id=` | 会话历史 → `{data:{history:[{role,content,timestamp}]}}`。**语义**：`session_id` 与存储层一致（API 透传 `api_session_id`，见下方备注） |
| GET | `/api/chat/new_session` / `delete_session?session_id=` / `update_session_display_name` | 会话管理 |
| POST | `/api/chat/stop?session_id=` | 停止生成（session_id 必填） |

> **会话存储语义（2026-09 修复）**：`chat/send` 的 `session_id` 会透传到存储层（`hub/memory_manager.py` 读取 `perception["api_session_id"]`），保证写读一致。QQ 平台消息不带该字段，仍按 `{platform}_g{群号}_u{用户}` 按群隔离。终端模式写入 `terminal_private_default`，Web/桌面写 `default`。

### 2.2 记忆

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/memory/stats` | 记忆统计（tide/dream 计数、redis/milvus/neo4j mode） |
| GET | `/api/memory/list?limit=` | `{data:{items:[...]}}` |
| GET | `/api/memory/search?query=&user_id=&limit=` | 语义搜索 → `{memories:[...]}`（2026-09 修复：query 从 query 参数读取，此前恒空） |
| POST | `/api/memory/add` | `{text}` 或五元组 `{subject,predicate,object}`（兼容） |
| GET | `/api/plug/alkaid/ltm/graph` | 记忆图（MindView 可视化用） |

### 2.3 人格 / 情绪 / 灵魂

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/persona/list` / `current`；POST `/api/persona/switch` | 人格切换 |
| GET | `/api/emotion` | 当前情绪 |
| GET | `/api/soul/current` | 最近一次灵魂输出（emotions/inner_thought/attribution） |

### 2.4 配置

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/config/get` | 平台配置展开（注意：可能含敏感键，勿暴露公网） |
| POST | `/api/config/set` | `{type: platform|personality|system_prompt, ...}` |
| GET/POST | `/api/config/system_prompt` | 读/写系统提示词（写 `config/text_config.json` 并热重载） |
| GET | `/api/config/file?path=` | 读工作目录内文件；**拒绝 `.env*`**，`commonpath` 边界校验 |
| GET | `/api/config/provider/list`、`/api/config/abconf` 等 | 供应商/AB 配置 |

### 2.5 工具 / MCP / 插件 / Agent

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/tools/list`（=`/api/tools`） | ToolNet 实时工具表（2026-09 修复假成功：现在返回真实注册表，失败时 `success:false`） |
| POST | `/api/mcp/call` | `{service, tool, ...params}`（openclaw/screen_vision 等经此调用） |
| GET | `/api/plugin/market_list` | 插件市场 |
| GET | `/api/agents` | AgentHub 列表 |
| POST | `/api/tools/task_execute` | **已封堵 shell 执行**：带 `command` 字段直接拒绝；仅允许按 `type` 走工具子网 |

### 2.6 桌面/文件（`core/web_api/desktop.py`）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/desktop/files/list?path=&recursive=` | 列目录（限项目目录内） |
| GET | `/api/desktop/files/read?path=&offset=&limit=` | 读文件（10MB 上限）→ `{lines:[...]}` |
| POST | `/api/desktop/files/write` | **JSON body** `{path, content}`（2026-09 修复：原 query 签名前端必 422） |
| POST | `/api/desktop/files/parse` | 上传解析为文本（文本类；PDF/DOCX 明确报不支持）→ `{truncated, content}` |
| POST | `/api/desktop/files/upload` | 上传到 `data/uploads/` → `{filePath}` |
| DELETE | `/api/desktop/files/delete?path=` | 删除 |
| POST | `/api/desktop/terminal/execute` | 终端命令（有权限校验；见 `desktop.py`） |

### 2.7 系统 / 运维

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health/`（health_monitor，注意带斜杠） | `{status:"healthy", checks, metrics}` |
| GET | `/api/health`、`/api/status` | 兼容健康探活 / 系统状态（identity.version 统一 `core/version.py`） |
| GET | `/api/logs?limit=&level=` | 日志读取（2026-09 新增 level 过滤：ERROR/WARNING/INFO/DEBUG） |
| GET | `/resources/*` | 资源监控（resource_manager） |
| GET | `/api/management/*`、`/api/runtime/*` | WebUI 管理面（`webnet/miya_webui.py`） |
| POST | `/api/audio/transcribe` | 语音转写：**当前无后端，恒 501**（前端据此提示不可用） |
| POST | `/v1/chat/completions` | OpenAI 兼容代理（直连模型池；生产环境务必设置 `MIYA_API_TOKEN`） |
| POST | `/tts/speech` | TTS（`core/web_api/tts_routes.py`） |
| GET/POST | `/api/auth/login`、`/api/auth/me` | JWT 登录（scrypt + HS256，`auth_security.py`） |

---

## 3. 客户端对接速查（二开发）

| 客户端 | 端口 | 代码位置 |
|---|---|---|
| Electron 桌面 | 业务 8000（`src/api/core.ts`，`VITE_CORE_PORT` 可覆盖）+ 管理 9800（WS 与平台状态） | `miya_frontend/src/api/` |
| Web HUD | 直连 8000（`frontend/ui/src/services/miyaApi.ts`，`VITE_CORE_URL` 可覆盖） | `frontend/ui/src/` |
| QQ/OneBot 等平台 | 经 `message_mixin.route_to_decision_hub` 进决策中枢（不走 HTTP） | `core/unified_platform_impl/` |

常见对接错误（历史教训，勿重蹈）：

- 把业务调用打到 9800（管理面）→ 404。业务路由全在 8000。
- 读会话用 `data.history`，列表用 `data`/`tools`/`personas` 等包裹键（前端 camelCase 转换已由 `miya_frontend/src/api/index.ts` 统一处理）。
- `files/write` 必须 JSON body（不是 query）。
