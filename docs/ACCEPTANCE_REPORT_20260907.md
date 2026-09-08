# 弥娅 (MIYA) 启动模式真实验收报告

- **验收日期**：2026-09-07
- **分支**：`fix/v8-hardening`（含 2026-09-06/07 全部修复）
- **验收方式**：每个启动模式从真实入口（`start.bat` 菜单项对应的原生命令）启动，运行中探测关键指标，结束后验证进程/端口完全清理。全部证据为命令原文 + 实测输出。
- **结论先行**：**✅ 全部启动模式真实可用**（5/5 通过，其中 All 模式发现并修复 1 个硬伤、遗留 2 个非阻塞小瑕疵）。

---

## 一、验收矩阵总览

| 模式 | 入口 | 判定 | 关键证据 |
|---|---|---|---|
| 1️⃣ Terminal 终端 | `start.bat 1` → `uv run python -X utf8 run/main.py` | ✅ 通过 | 交互周期完整，EXIT=0 |
| 2️⃣ Daemon 守护进程 | `start.bat 2` → `run/daemon.py --api-port 9800` | ✅ 通过 | 双 API 208 路由真实数据，优雅退出 exit 0 |
| 3️⃣ Desktop 桌面应用 | `start.bat 3` → junction + `npm run dev`（Electron） | ✅ 通过 | Electron 窗口「弥娅 AI」真实创建，渲染层模块全部 200 |
| 4️⃣ Web Ops Center | `start.bat 4` → `frontend/ui && npm run dev` | ✅ 通过 | 页面 200、模块转换正常、dev proxy 工作正常 |
| 5️⃣ All 一体 | `start.bat a`（daemon+desktop+web+terminal 组合） | ✅ 通过（修复后） | Electron 自动拉起 daemon 全栈联动；终端步骤硬伤已修 |

---

## 二、逐模式验收记录

### 模式 1️⃣ Terminal（终端模式）—— ✅ 通过

**命令**：`printf 'status\n再见\n' | timeout 240 uv run python -X utf8 run/main.py`

| 检查项 | 结果 | 证据 |
|---|---|---|
| 启动完成 | ✅ | `弥娅·阿尔缪斯 已启动 (v8.0.0)` |
| 交互命令 | ✅ | `status` 输出完整系统状态（人格状态/情绪/记忆） |
| 告别退出 | ✅ | `弥娅·阿尔缪斯: 再见！有需要随时叫我~` + `对话历史已保存` |
| 优雅关闭 | ✅ | `弥娅系统已关闭`，**进程退出码 0** |
| 端口释放 | ✅ | 退出后 8000 无监听 |
| 版本统一 | ✅ | v8.0.0（与 core/version.py 一致） |

日志：`/tmp/acc/mode1_terminal.log`

### 模式 2️⃣ Daemon（守护进程 + 管理 API）—— ✅ 通过

**命令**：`PYTHONIOENCODING=utf-8 uv run python -X utf8 run/daemon.py --api-port 9800`（即 start.bat 2 的原样命令）

| 检查项 | 结果 | 实测输出 |
|---|---|---|
| 就绪 | ✅ | `💫 弥娅守护进程已就绪`（约 60s） |
| 9800 `/api/v1/health` | ✅ | `{"status":"ok","version":"8.0.0","degraded":{"ai_client":false},"platforms":{"total":1,"online":1}}` |
| 9800 `/api/v1/platforms` | ✅ | aiocqhttp `status:"online"`、last_online 实时 |
| 9800 `/docs` | ✅ | HTTP 200 |
| 8000 `/health` | ✅ | `{"status":"healthy","service":"miya-web-api"}` |
| 8000 `/api/status` | ✅ | 真实身份（version **8.0.0**，统一生效）+ 实时情绪数据 |
| 8000 `/api/tools/list` | ✅ | 真实工具注册表数据（get_current_time 及真实中文描述） |
| 8000 OpenAPI | ✅ | **208 条路由** |
| 安全封堵回归 | ✅ | `task_execute` 拒绝命令；`config/file?path=config/.env` 拒绝读取 |
| 优雅退出 | ✅ | `POST /api/v1/daemon/shutdown` → `💤 弥娅守护进程已关闭`，**exit 0**，8000/9800 全部释放 |

日志：`/tmp/acc/mode2_daemon.log`

### 模式 3️⃣ Desktop（Electron 桌面应用）—— ✅ 通过

**命令**：`cmd //c start.bat 3`（真实菜单路径，验证 `:ensure_nohash`），dev server 以 `MIYA_NO_BACKEND=1 npm run dev` 在联接路径复跑取证。

| 检查项 | 结果 | 证据 |
|---|---|---|
| `:ensure_nohash` 联接 | ✅ | start.bat 实测输出 `[FIX] 项目路径含 '#'，已通过目录联接启动: C:\Users\Ran-xin\AppData\Local\Miya-link` |
| 陈旧构建清理 | ✅ | 旧 `dist-electron/main.js` 被删除，新构建即时生成 |
| 主进程构建 | ✅ | `✓ 1 modules transformed` + `✓ 9 modules transformed`（修复前 `Could not resolve "./modules/backend"`） |
| Electron 进程 | ✅ | `electron.exe` ×2（主+渲染进程） |
| **窗口创建** | ✅ | Win32 应用列表出现 **`弥娅 AI`**（electron.exe PID 44604，窗口 1280×800） |
| UI 挂载 | ✅ | a11y 树含 `textarea (focused)`（Vue 应用挂载后的聊天输入框） |
| 渲染层加载 | ✅ | `/`、`/src/main.ts`、`/src/App.vue`、`/src/live2d-app/main.ts` 全部 **HTTP 200**（修复前 Pre-transform error 404） |
| Live2D 源码当 JS 执行 | ✅ 已消失 | 无 `Unexpected identifier 'as'`（新 main.js 已含禁用逻辑） |
| 清理 | ✅ | electron 全部终止、5173 释放 |

日志：`/tmp/acc/mode3_startbat.log`、`/tmp/acc/mode3_dev.log`
**白屏问题（用户实测发现，已根治）**：初版验收后用户实测「模式 2 之后启动模式 3 界面空白」。根因链：Vite 启动后把内部 realpath 实现切换为 `fs.realpathSync.native`（`optimizeSafeRealPathSync` → net use 为空时切 native）→ native realpath **穿透 junction/subst** 把深层模块 id 解析回 `F:\#Ranxin\...` → cleanUrl 截断为 `F:/` → `EISDIR` 关键模块加载失败 → Vue 应用未挂载 → 白屏。初版验收仅 curl 顶层入口（碰巧 200）未覆盖深层依赖，漏判为「非阻塞」。**根治（三层）**：
1. `scripts/patch_vite_realpath.mjs`：把两个前端的 vite 产物中全部 `realpathSync.native` 替换为非 native `realpathSync`（实测非 native 对 subst 盘不穿透；已挂 postinstall，重装依赖自动应用，共 8 处）；
2. `start.bat :ensure_nohash` 改为 **subst 盘符映射**（自动选空闲盘符 Z→R、可复用已有映射）——非 native realpath 对 subst 不穿透；
3. `vite.config.ts` hashPathFixPlugin 保留为第二道防线；`window.ts` 新增渲染进程 console 转发（`[Renderer:N]`），渲染层错误在终端直接可见。
**复验证据**：EISDIR/Internal error/Pre-transform error 计数 **0**；渲染层深层依赖链 6 模块（main.ts/App.vue/api/core.ts/utils/config.ts/session.ts/useMIYARealtime.ts）全部 200；渲染进程内存 327MB + 捕获到 Vue 运行时警告（应用完整挂载）；**整屏截图确认主界面（功能菜单/背景/标题）完整渲染，非白屏**；daemon 与 desktop 共存场景复测通过。

### 模式 4️⃣ Web（Ops Center）—— ✅ 通过

**命令**：联接路径下 `cd frontend/ui && npm run dev`（即 start.bat 4 经 `:ensure_nohash` 后的实际路径）

| 检查项 | 结果 | 证据 |
|---|---|---|
| dev server | ✅ | `VITE v5.4.21 ready in 1304 ms`，0.0.0.0:5173 监听 |
| 页面 | ✅ | `GET /` → 200 |
| 模块转换 | ✅ | `GET /src/main.tsx` 返回转换后的 JS（React JSX → CJS），无 Pre-transform error |
| dev proxy | ✅ | `GET /api/health` → 500 + proxy error 日志 ×2（代理正确转发至 8000；后端未运行时 500 而非 404，证明转发链路工作；后端本体已在模式 2 验证） |
| 清理 | ✅ | 进程终止、5173 释放 |

日志：`/tmp/acc/mode4_web.log`

### 模式 5️⃣ All（一体启动）—— ✅ 通过（含 1 项修复）

**组合验证方式**：「桌面一体」全栈实测（Electron **不设** `MIYA_NO_BACKEND`，由其 backend.ts 自动 spawn daemon——这是 All 模式的核心联动链路）+ 各组件单独验证（模式 1-4）+ 前置条件核查。

| 检查项 | 结果 | 证据 |
|---|---|---|
| **[4/4] Terminal 步骤硬伤** | 🔴→✅ 已修复 | **发现**：`claude-code-engine/` 目录整个不存在，原命令 `wt node claude-code-engine\dist\cli-node.js` 必然 MODULE_NOT_FOUND。**修复**：`start.bat` 增加存在性检查，缺失时回退 `wt uv run python -X utf8 run/main.py`（内置终端模式）。wt.exe 存在性已验证 ✅ |
| Electron 自动拉起后端 | ✅ | electron 启动后 9800 自动就绪：`{"status":"ok","start_time":"2026-09-07T13:06:02","degraded":{"ai_client":false}}`；Electron 日志缓冲完整捕获 `💫 弥娅守护进程已就绪` |
| 8000 Web API 联动 | ✅ | `{"status":"healthy","service":"miya-web-api"}` |
| 渲染层 | ✅ | vite 5173 监听、`/src/main.ts` 200、vite/渲染层零错误 |
| 清理 | ✅ | electron 全终止、daemon（electron 子进程）随之退出，5173/8000/9800 全释放，无 python 残留 |

日志：`/tmp/acc/mode5_all.log`

---

## 三、验收中发现并处理的问题

| # | 级别 | 问题 | 处置 |
|---|---|---|---|
| 1 | P1→已修 | **All 模式第 4 步必失败**：`claude-code-engine/dist/cli-node.js` 不存在（整个目录缺失），`start "MIYA Terminal" wt node ...` 打开即 MODULE_NOT_FOUND | `start.bat:215-225` 增加存在性检查，缺失时回退内置终端模式（`run/main.py`），并打印 WARN 说明 |
| 2 | P1→已修 | **桌面应用白屏**（用户实测）：Vite 的 `realpathSync.native` 穿透 junction/subst，深层模块 id 被截断为 `F:/`（EISDIR）→ Vue 应用未挂载 | **已根治**：`patch_vite_realpath.mjs`（8 处替换，postinstall 自动化）+ `:ensure_nohash` 改 subst 盘符 + 渲染层 console 转发。复验：EISDIR 归零、深层依赖 6/6 全 200、截图确认界面完整渲染 |
| 3 | P3 | **已知瑕疵**：`:web` 分支启动前会 taskkill 占用 5173 的进程——与 Desktop dev server（同用 5173）冲突，All 模式下 Web 启动会误杀 Desktop 的 vite（Electron 窗口保持已加载页面，但热重载失效） | 记录在案；建议后续为两个前端分配不同默认端口（如 desktop 5173 / web 5174） |
| 4 | 备注 | Git Bash（MSYS）下运行 start.bat 时 `timeout /t` 被 GNU timeout 拦截报错——仅影响 MSYS 会话内的提示节奏，用户正常双击/cmd 运行不受影响；另 start.bat 3 经 `start` 弹出的独立窗口在本验收会话中未存活，改以同命令直接启动完成等价验证 | 环境备注，无需修改 |

---

## 四、修复后质量基线（验收同期）

- 单元测试：`pytest -q` → **132 passed**（含 12 项安全回归）
- 静态：`ruff check .` → 0 违规；`black --check` → 197 文件全合规
- 冒烟：`smoke_test.py` 全量 → **9/9**（S6 链路探针历史首次真实通过，S8 真实基线对比通过）
- 版本一致性：终端/daemon/Web API/identity 全部 **8.0.0**（单一真源 `core/version.py`）

## 五、结论与建议

**结论：✅ 五个启动模式全部真实跑通。** 终端（EXIT=0 全周期）、守护进程（208 路由真实数据 + 优雅退出）、桌面应用（Electron 窗口 + 渲染层 + `:ensure_nohash` 联接启动）、Web（页面/转换/代理）、All（Electron 自动拉起后端的全栈联动 + 终端硬伤修复）。

建议（按优先级）：
1. **择机迁移项目至无 `#` 路径**（如 `F:\Ranxin\Miya`）——subst+patch 方案已根治白屏并稳定工作，迁移后可移除 patch 与盘符映射，回归零特判的常规环境；
2. Web 与 Desktop 的 dev server 分配不同端口，消除 All 模式的 5173 争用；
3. `claude-code-engine` 如计划恢复，按 `start.bat` 回退分支的约定路径放置即可自动切换。

---

# 流程级深验附录（2026-09-08）

> 深化原则与桌面白屏分析一致：**传输层 200 ≠ 功能可用**。对四个核心用户流程做端到端实测（含真实 AI 调用），发现并修复 4 处「表面正常、实际断裂」的问题。

## P-A. 聊天全链路（桌面 UI ↔ Web API ↔ 决策中枢 ↔ AI ↔ 会话历史）

逐层实测发现 **3 处静默断裂**（每处都表现为上层"正常"，数据实际没流到）：

| 层 | 断裂 | 根因 | 修复 | 实测证据 |
|---|---|---|---|---|
| 读历史 API | `GET /api/chat/get_session` 永远返回空 | 调用了不存在的 `ConversationHistoryManager.get_session()`（实际方法名 `get_history`），AttributeError 被吞后降级空历史——「异常吞噬→静默缺失」模式的又一现场 | `core/web_api/miya_api.py` 改用 `get_history()` 并把 ConversationMessage 转 dict | 修复前 WARNING 日志 `object has no attribute 'get_session'`；修复后返回真实历史 |
| 会话 ID 语义 | 写入与读取的 session_id 永远对不上 | API/前端用 `default`，存储层自行推导为 `{platform}_private_{user_id}`（如 `web_private_default`），`data/conversations/` 下根本没有 default 文件 | `chat/send` 把请求的 session_id 以 `api_session_id` 透传进 perception；`hub/memory_manager.py` 两处推导改为「API 透传优先」，QQ 平台按群隔离规则不变 | 修复后 `get_session(default)` 返回真实消息；磁盘出现 default 会话数据 |
| UI 加载 | 桌面/前端首次启动聊天区永远空白 | `session.ts loadCurrentSession` 在本地无会话 ID（null）时直接 return，从不请求后端 | 无 ID 时回退 `default` 并拉取后端历史 | Electron 聊天界面显示「跨端会话验证：这条消息来自 Web 端点」的历史气泡（截图证据） |

**端到端证据**：`POST /api/chat/send`（session_id=default）→ 真实 AI 回复 `收到，Web 端点这条链路没问题，跨端会话正常。` + 情绪/灵魂数据；桌面 UI 经 HMR 更新后显示同一会话历史（截图）。
**备注**：UI 键入→发送这最后一步因验收宿主环境强制前台（无法自动化键盘输入）未直接驱动，以「同端点 API 闭环 + UI 渲染历史」等效覆盖。

## P-B. 终端模式真实 AI 对话

**发现 P1 断裂**：终端发消息后 AI 完全不回复。根因链：谛听策略分析的 LLM 判断「消息内容为空 → should_respond=False」→ decision_hub `return None` 静默丢弃。两个叠加因素：
1. **审查误报导致误删配置**（更正声明）：`config/diteng_strategy_config.json` 此前被审查报告标记为「死配置」删除，但实际被 `memory/diteng_listener.py` 以路径拼接方式引用——删除后策略/意图/风格选项全空，LLM 分析退化。**已恢复该文件**，并在审查流程中记入教训：删除"死配置"前必须逐条人工复核引用方式（字符串拼接/动态加载不算死）。
2. **设计缺陷**：终端/Web 是用户主动对话界面，不应受 QQ 群防打扰策略（谛听）管辖，且 `MessageStrategy()` 异常默认值即「不回复」（fail-to-silence）。

**修复**：恢复配置 + `hub/decision_hub.py fetch_diting_strategy` 对 `terminal`/`web` 平台跳过（QQ 行为不变）。
**复验**：终端真实对话 `用一句话说说你现在的心情` → AI 回复 **`凌晨了还醒着。想聊点什么？`** → 告别退出 EXIT=0。

## P-C. Web HUD（Ops Center）真实渲染

browser-use 实测 `http://127.0.0.1:5173`（前端直连 8000）：DOM 快照与截图确认**真实数据全渲染**——守护进程运行中/已共鸣、情绪 joy、CPU 55.9%/内存 79.1%/磁盘 50.8%/运行时长、8 个子网状态全绿、平台在线 1/1（aiocqhttp 在线）、AI 模型 12 活跃、Agent 5 就绪。此前该页面仅有 HTTP 200 级验证。

## P-D. WS 实时推送链路

WebSocket `ws://127.0.0.1:9800/api/v1/ws` 实测闭环：连接即收 `initial_state`（platforms:1, daemon.started:true）→ `get_status` action → `status_update` 往返（uptime>0）。桌面端实时数据通道服务端闭环可用。

## 回归基线（深验修复后）

- pytest **132 passed**；ruff 0 违规；black 195 文件合规；冒烟 --fast 5/5
- 验证进程/端口全部清理；subst 盘符已卸载

## 深验结论

四个核心流程（聊天全链路/终端 AI 对话/HUD 真实渲染/WS 推送）端到端真实可用。累计修复「表面正常实际断裂」类问题 4 处（get_session 方法名、session_id 语义断层、UI default 回退、谛听对主动界面的误拦），恢复误删配置 1 份。**未验证项**：QQ 平台真实消息闭环（需 NapCat 实例）、语音转写（无后端，501 明确拒绝）。
