# 弥娅 (Miya) 全项目代码审查与真实验证报告

- **审查日期**：2026-09-06
- **分支**：`fix/v8-hardening`（最近提交 `17593768`，2026-08-24）
- **审查方式**：静态走读（4 个方向并行深查 + 关键断言人工复核）+ 6 阶段真实验证（环境/静态/单测/冒烟/守护进程 API/终端模式）
- **审查人**：自动化审查agent（ZCode）

---

## 一、总体结论

**⚠️ 部分跑通**：核心链路（终端模式、守护进程、管理 API、Web API、冒烟 S0–S5）**能从源码真实启动并返回真实数据**，单元测试 120/120 全绿；但 Web API 存在 **3 个已实测确认的 P0 级安全漏洞**（无鉴权 RCE、任意文件读取、全站零鉴权），Electron 桌面端与后端 API 系统性错配（30+ 调用必然 404），冒烟测试 S6 探针为脚本自身语法 bug（任何环境都不可能通过），质量门禁中的 black 检查被 `|| true` 掩盖（165 个文件不符合格式仍显示通过）。

---

## 二、⚠️ 安全告警（P0，均已在本地实测确认）

> 以下漏洞在 2026-09-06 17:46–17:48 于本机临时启动的守护进程上用**无害探测**实测确认。Web API 默认绑定 `0.0.0.0:8000`（`run/main.py:637`），局域网/公网暴露即被远程利用。

| 编号 | 漏洞 | 位置 | 实测证据 |
|---|---|---|---|
| SEC-1 | **无鉴权远程命令执行 (RCE)**：`POST /api/tools/task_execute` 将请求体 `command` 字段直接 `subprocess.run(command, shell=True)`，无任何鉴权与权限检查 | `core/web_api/tools.py:295-324`（`tools.py:306-308` 为执行点；路由的 `user_info: Dict = Depends(lambda: {"web_user_id": "web_default"})` 是恒真假依赖） | 无任何认证头，`curl -X POST .../api/tools/task_execute -d '{"command":"echo AUDIT_PROBE_12345"}'` → `{"success":true,"result":"AUDIT_PROBE_12345\n","exit_code":0}` |
| SEC-2 | **任意文件读取**：`GET /api/config/file?path=...` 仅检查路径在 cwd 内，`config/.env`（含全部 API Key/Token）可被直接读取返回 | `core/web_api/__init__.py:324-335` | 无认证头读取 `?path=pyproject.toml` 完整返回全文（本次审查**未**实际读取 .env，按红线执行；可达性已证明） |
| SEC-3 | **Web API (8000) 全站零鉴权**：FastAPI app 创建后仅挂 CORS，无任何鉴权中间件；`miya_api.py` 约 168 条路由无一有 `Depends` 鉴权；`auth.py` 中定义的 `check_api_permission` 从未被挂载（且其本身无 token 时返回 anonymous，fail-open） | `run/main.py:589`（app 创建）、`core/web_api/auth.py:169-194`；高危路由：`/api/plugin/install`（`miya_api.py:1909`，任意 URL 装 zip → 供应链 RCE）、`/api/config/set`（`:1540`，可改 system_prompt）、`/v1/chat/completions`（`core/web_api/__init__.py:838`，无鉴权代理模型池）、`/api/logs`、`/api/live-log`、`/api/desktop/files/*`（任意读写删） | 本轮对 8000 的全部探测（health/status/tools/config-file/task_execute）均未携带任何凭证且全部成功返回数据 |

**次级安全项**：
- SEC-4【P1】管理 API (9800) 的 WebSocket `/api/v1/ws` 绕过 HTTP 鉴权中间件（Starlette HTTP middleware 不拦 WS 握手），`ws.accept()` 后可直接 start/stop/restart 平台；未设 `MIYA_API_TOKEN` 时绑定 0.0.0.0 即可被远程控制（`core/management_api.py:263-291` 与 `:111-134`）。对照：9800 的 HTTP 路由是 fail-closed（loopback 放行 + `hmac.compare_digest`），设计正确但 WS 是旁门。
- SEC-5【P2】`blogs.py` 写操作为假鉴权占位（`Depends(lambda: None)`，`core/web_api/blogs.py:84,106,129`）。
- SEC-6【P2】`/api/tools/data_analyze` 任意路径读 CSV、`/api/tools/chart_generator` 请求直传 `output_path` 任意路径写文件（`core/web_api/tools.py:152,160,188-233`）。
- SEC-7【P2】`MIYA_API_TOKEN`（管理 API 鉴权总开关）**未写入 .env.example**，部署者大概率不设置，放大 SEC-4。
- 正面结论：全仓**未发现硬编码真实密钥**（`sk-` 模式 0 命中；仅 `core/config/validator.py:119,264` 等占位哨兵值）；登录态（scrypt+JWT）实现 fail-closed（`core/web_api/auth_security.py:186-196`）；CORS 两个端口均为白名单非 `*`。

---

## 三、验证记录表

| 阶段 | 命令（原文） | 结果 | 证据摘要 | 备注 |
|---|---|---|---|---|
| S0 环境 | `git status --short && git log -1` | ✅ | 仅 2 个预存未跟踪文件（`docs/PROJECT_REVIEW_PROMPT.md`、`scripts/_rewrite_memory_ctx.py.bak`），与任务说明一致 | 验证结束后复核仍一致，无意外改动 |
| S0 环境 | `uv run python --version` | ✅ | `Python 3.11.14`，uv 0.9.5 | 与项目宣称一致 |
| S0 环境 | `uv run python -c "import fastapi, aiohttp, yaml, openai"` | ✅ | `core deps OK: 0.141.1 3.14.3 1.109.1` | 关键依赖齐全 |
| S1 静态 | `uv run ruff check . --quiet` | ✅ | 退出码 0，零违规输出 | |
| S1 静态 | `uv run black --check core/ hub/ run/` | ❌（被掩盖） | `165 files would be reformatted, 30 files would be left unchanged` | **Makefile:19 该步骤带 `|| true`**，`make quality` 永远显示通过——门禁形同虚设 |
| S1 单测 | `uv run python -X utf8 -m pytest -q` | ✅ | `120 passed in 30.42s`，exit 0 | 覆盖 memory/platform/permission/utils/hub/config/core 8 域；无 skip/xfail；抽查 3 文件均为真实行为断言 |
| S1 依赖 | `uv run python -X utf8 scripts/check_imports_vs_requirements.py` | ⚠️ | 将标准库（`tarfile`/`wave`/`tracemalloc`）与本地包（`webnet`/`utils`）误报为 `pip install` 项 | 脚本自身缺陷，输出不可用 |
| S2 冒烟 | `uv run python -X utf8 scripts/smoke_test.py --fast` | ✅ | `S0–S4 全 OK，5/5 通过`；enabled_platforms=['aiocqhttp'] | |
| S2 冒烟 | `uv run python -X utf8 scripts/smoke_test.py` | ⚠️ | `7/9`：S6 FAIL、S7 FAIL（详见下方根因） | 跑前对 `data/`（3301 文件）与 `config/.env` 做了 md5 快照，跑后 diff：**无污染** |
| S2 根因 | 阅读 `scripts/smoke_test.py:311-336` | 🔴 | S6 探针代码用分号拼接出 `import asyncio;async def probe():` —— Python 语法不允许复合语句跟分号，`SyntaxError: invalid syntax`，**该阶段在任何环境都不可能通过**（脚本自身 bug） | 分类：代码 bug（测试基建） |
| S2 根因 | S7 日志差分 | ⚠️ | 新增 3 行 Neo4j 连接拒绝日志（`localhost:17687` WinError 10061）不在白名单；`DEFAULT_LOG_WHITELIST`（`smoke_test.py:53-68`）仅覆盖 `Neo4j.*password`/`neo4j.*auth` 模式 | 分类：环境缺依赖（Neo4j 未运行，已知可选）+ 白名单未更新；另注：`scripts/.smoke_log_blacklist.json` 文件实际不存在，靠内置回退 |
| S3 守护 | `uv run python -X utf8 run/daemon.py --list-platforms` | ✅ | 输出 `aiocqhttp: aiocqhttp`（唯一默认启用平台） | |
| S3 守护 | `uv run python -X utf8 run/daemon.py --api-port 19900 --api-host 127.0.0.1 --platforms webchat`（后台） | ✅ | 约 60s 后就绪：`💫 弥娅守护进程已就绪`、`管理 API 已启动: http://127.0.0.1:19900`、`Web API 服务器已在后台启动 (http://0.0.0.0:8000)`；ToolNet 68 工具、模型池 3 模型加载成功 | 日志仅 1 个 ERROR（见 F-22 webchat 未知平台）；主动聊天仅启动轮询未触发生成（无 API 消费） |
| S3 API | `curl http://127.0.0.1:19900/api/v1/health` 等 | ✅ | health→`{"status":"ok","version":"8.0.0",...}`；platforms→真实平台状态数组；daemon/status→真实运行数据；`/docs`→200 | 管理 API 返回真实数据非 404/500 |
| S3 API | `curl http://127.0.0.1:8000/api/health /health /api/status` | ✅ | 全部返回真实 JSON（情绪/身份/状态数据）；`/docs` 200；openapi.json 共 **205 条路由** | |
| S3 安全 | 见「安全告警」SEC-1/2 | 🔴 | RCE echo 成功、任意读成功（均无认证头） | 用无害探测 |
| S3 文档 | 对照 `docs/API_REFERENCE.md` 宣称路由实测 | ⚠️ | 9800：`/api/v1/miya/status`、`/api/v1/memory/search|stats`、`/api/v1/personality/list` 全部 **404**；8000：`/api/terminal/chat` **404**（实际仅 `/api/desktop/terminal/execute`）、`/api/mcp` 404（实际为 `/api/mcp/list|call|reload`）；6185 Dashboard **无监听**；`/api/tools`、`/api/skills` 200 ✓ | 文档大量路由与现实不符（见第六节） |
| S3 退出 | `kill -INT 65840` → `taskkill //PID` → `taskkill //F //PID` | ⚠️ | MSYS2 kill 无法定位进程；Windows taskkill 不带 /F 被拒（"只能强行终止"）→ 强杀成功，端口 8000/19900 全部释放，进程消失 | Windows 下对分离控制台进程无法投递 SIGINT，**daemon 优雅退出路径未能在本环境完整验证**（静态分析见 F-1：daemon 不调用 `Miya.ashutdown()`） |
| S4 终端 | `printf 'status\n再见\n' \| timeout 240 uv run python -X utf8 run/main.py` | ✅ | `EXIT=0`；`弥娅·阿尔缪斯 已启动 (v8.0.0)`；status 命令打印完整系统状态（人格/情绪/记忆）；`再见`→告别语+`对话历史已保存`；`弥娅系统已关闭`；8000 端口随 ashutdown 释放 | 与 daemon 共用 `Miya()` 构造链（`core/miya_daemon.py:151-155` import `run.main.Miya`）；未发生 AI 计费调用（status 命令不经过模型） |
| S5 前端 | `bash scripts/verify_hud_build.sh`（Node v24.11.1/npm 11.6.2） | ✅ | `[3/3] build OK`，tsc+vite 真实构建成功（复制到无 `#` 临时目录绕过 Vite 路径缺陷） | 脚本结束后遗留 `/f/tmp_hud`（无尾部清理），已人工删除 |
| S5 平台 | QQ/NapCat 闭环 | ⏭️ 未执行 | 8095 端口无监听（本机无 NapCat 运行），且红线禁止向真实用户发消息 | 无法验证，如实记录 |
| S5 发布 | build_release.py / Miya.spec / Electron 打包 | ⏭️ 未执行 | 按任务要求只做可行性说明：`Miya.spec`、`build_release.py`、`miya_frontend/package.json`（electron-builder dist:win/mac/linux 齐全）文件齐备、配置完整 | 不实际打包 |
| S6 收尾 | 端口/进程/git 复核 | ✅ | 8000/9800/8095/19900/19901/6185 全部无监听；存活 python.exe 经命令行核验均为用户自有程序（pc-time-tracker/mcp_server），无 Miya 遗留；`git status` 与开始时一致；`/f/tmp_hud` 已清理 | 验证期间 `data/` 仅新增系统正常写入（SQLite WAL checkpoint、`neo4j_migration_checkpoint.json` 时间戳），`.env` md5 未变 |

---

## 四、跑通判定矩阵

| 判定项 | 结论 | 依据 |
|---|---|---|
| 环境与依赖 | ✅ 真实跑通 | uv + Python 3.11.14 + 核心依赖 import 全过 |
| 静态检查 (ruff) | ✅ 真实跑通 | 0 违规 |
| 格式检查 (black) | ❌ 名义通过实际失败 | 165 文件不合规，被 Makefile `\|\| true` 掩盖 |
| 单元测试 | ✅ 真实跑通 | 120/120 passed，30.42s |
| 冒烟 --fast (S0–S4) | ✅ 真实跑通 | 5/5 |
| 冒烟全量 (S0–S8) | ⚠️ 部分跑通 | 7/9：S6 为脚本自身语法 bug（永不通过）；S7 为 Neo4j 未运行+白名单缺口；S8 无基线跳过 |
| 守护进程启动 | ✅ 真实跑通 | 就绪日志+双 API 监听，核心构造 0 个 None 子系统 |
| 管理 API (9800) | ✅ 真实跑通 | health/platforms/status/docs 返回真实数据 |
| Web API (8000) | ✅ 真实跑通（携带 P0 漏洞） | 205 条路由、health/status 真实数据；但 `/api/tools/list` 假成功（F-11） |
| 守护进程优雅退出 | ⚠️ 未完整验证 | Windows 无法投递 SIGINT；静态证据显示 daemon 路径不走 `ashutdown`（F-1） |
| 终端模式 | ✅ 真实跑通 | EXIT=0，启动→命令→告别→干净退出全链路 |
| AI 端到端对话 | ⚠️ mock/未触发验证 | 模型池初始化成功（3 个 deepseek 模型加载）但按红线未发起真实对话；`AI_PROVIDER=mock` 在代码中无对应分支（F-24），提示词中的 mock 方案不可用 |
| QQ/OneBot 消息闭环 | ⏭️ 未验证 | 无 NapCat 实例 |
| React HUD (frontend/ui) | ✅ 真实跑通 | verify_hud_build.sh 构建成功 |
| Electron 桌面端 | ❌ 跑不通（静态判定） | 前端调用与自启后端系统性错配，30+ 调用必然 404（F-13）；未实际启动，静态证据充分 |

**总判定：⚠️ 部分跑通**。主链路（终端/守护进程/双 API/冒烟/单测/HUD 构建）真实可用；扣分项：3 个实测 P0 安全漏洞、Electron 契约断裂、S6 冒烟永不通过、black 门禁失效。

---

## 五、审查发现清单

> 级别定义：P0 阻断（安全/数据丢失）、P1 严重（核心功能静默缺失/退出缺陷）、P2 一般（功能/资源/配置问题）、P3 建议（死代码/文档/卫生）。

### P0（安全类见第二节，此处补数据丢失项）

| 编号 | 位置 | 现象与证据 |
|---|---|---|
| F-1(SEC-1) | `core/web_api/tools.py:295-324` | 无鉴权 `shell=True` RCE，实测确认 |
| F-2(SEC-2) | `core/web_api/__init__.py:324-335` | cwd 内任意文件读（含 .env），实测确认 |
| F-3(SEC-3) | `run/main.py:589,637`；`core/web_api/auth.py:169-194`；`miya_api.py:1909,1540` 等 | 8000 全站零鉴权 + 0.0.0.0 绑定 + plugin/install 任意 URL 装包 |
| F-4 | `mcpserver/miya/server.py:148-154` | MCP 记忆文件 JSON 损坏时 `except Exception: pass` 后以空 data **覆盖写盘**，历史记忆不可逆丢失（写路径数据丢失） |

### P1（严重）

| 编号 | 位置 | 现象与证据 |
|---|---|---|
| F-5 | `run/main.py:663,894-898`；`core/miya_daemon.py:304-314` | daemon 退出链从不调用 `Miya.ashutdown()`：uvicorn 运行在 `daemon=False` 线程（main.py:663），`should_exit`+join 只在 ashutdown 内（894-898）；daemon 的 `_close_miya_core` 仅 flush 历史。后果：优雅退出后进程可能悬挂，ai_client/grag/DecisionHub 均不经过关闭链 |
| F-6 | `run/main.py:501-503`；`hub/decision_hub.py:1250-1252`；`core/miya_daemon.py:377-386` | 多模型池初始化失败仅 warning 后返回 None，`DecisionHub(ai_client=None)` 照常构造、daemon 照常上报就绪；此后所有对话静默降级为 `_fallback_response_cross_platform` 罐头回复，`get_daemon_status` 无任何降级字段——"假活" |
| F-7 | `core/web_api/__init__.py:146-190,196-224` | `_init_subroutes` 用单个 try 包住 8 个子路由模块 + TTS 导入，任一失败（如 TTS 依赖缺失）则 10 个属性全置 None，auth/blogs/chat/system/desktop/tools/security 全部子路由静默消失，服务仍"启动成功" |
| F-8 | `webnet/ToolNet/registry.py:418-435`；`webnet/ToolNet/tools/knowledge/search_knowledge.py:41-46` 等 15 文件 | 占位工具已注册进 ToolNet（68 个工具暴露给 LLM）：`return "搜索知识功能占位实现"`；同类的还有 cognitive/get_profile.py:33-35、search_events.py:41-45、group/group_tools.py:7-25（5 函数全裸 pass）、auth/list_groups.py:29-44（硬编码"占位实现"）等。AI 调用这些工具会消耗一轮 function-call 并向用户回复占位文案 |
| F-9 | `core/unified_platform_impl/webhook_platforms.py:172-178,217-223,260-265,339-344`；`core/unified_platform/base.py:304-307` | KOOK/Slack/LINE/Satori 四平台 handler 只调 `route_to_decision_hub` 并**丢弃返回的回复**，无任何平台 API 发送调用；若被启用，消息照处理但用户永远收不到回复。当前因未注册（`__init__.py:7-24` 仅导出 Lark）属休眠缺陷 |
| F-10 | `scripts/smoke_test.py:311-336` | S6 探针 `import asyncio;async def probe():` 语法错误（复合语句不可接分号），**任何环境永不通过**——冒烟的"链路探针"阶段自落地即坏，说明该阶段从未真正验证过链路 |
| F-11 | `core/web_api/miya_api.py:1592-1594`；`webnet/ToolNet/registry.py:50` | `/api/tools/list` 内 `from webnet.ToolNet.registry import get_registry` —— registry.py 根本没有该函数（只有 `class ToolRegistry`），import 失败被吞后返回 `{"success":true,"tools":[],"total":0}`。**实测确认假成功**：ToolNet 实有 68 工具，API 报 0 |
| F-12 | `core/management_api.py:263-291` | 见 SEC-4：WS 绕过 HTTP 鉴权中间件 |
| F-13 | `miya_frontend/src/api/core.ts`（全文）；`miya_frontend/electron/modules/backend.ts:110` | **Electron 桌面端系统性契约错配**：主进程拉起 `run/daemon.py`（9800），渲染层 30+ 个调用却全是 8000 的路由族（`/api/status`、`/api/chat/send`、`/api/memory/*`、`/api/config/*`、`/api/desktop/files/*` 等）→ 必然 404；另有 6 个端点（`/api/desktop/files/parse|upload`、`/api/audio/transcribe`、`/api/telemetry/*`、`/update/latest`）两个后端都不存在。能命中的仅 `/api/v1/platforms` 与 `ws://…:9800/api/v1/ws` |
| F-14 | `Makefile:19` | `black --check core/ hub/ run/ 2>&1 \| head -30 \|\| true` —— 格式门禁失败被强制吞掉，165 文件不合规仍"通过" |

### P2（一般）

| 编号 | 位置 | 现象 |
|---|---|---|
| F-15 | `run/main.py:148,205,322`；`core/miya_daemon.py:316-329`；`hub/scheduler.py:356-361` | 调度器双实例：DecisionHub/ToolNet 持有 `Miya.scheduler`（实例A），daemon 启动全局单例（实例B），仅 OneBot 连接时才同步（`onebot_platform.py:112-118`）——经 tool_context 注册到 A 的定时任务在 daemon 模式静默不触发 |
| F-16 | `run/main.py:163,291-300` | `Miya.neo4j` 驱动构造+verify_connectivity（真实连接池）后**全仓无消费点**，ashutdown 只关 grag 的驱动——占连接、永不关 |
| F-17 | `run/main.py:387-394` vs `:195-212`；`hub/decision_hub.py:152` | 统一记忆系统线程池内真实初始化，但 DecisionHub 构造时未传 `unified_memory`（16 kwargs 无此项）——构造结果被丢弃，靠 `store_unified_memory` 内部单例兜底，双份初始化开销 |
| F-18 | `run/main.py:337-339,550`；`core/web_api/auth.py:44` | WebNet 初始化失败仅 warning，`WebAPI(web_net=None)` 照常构造，`/api/auth/login`、`/api/blogs` 到请求期才 AttributeError |
| F-19 | `core/unified_platform_impl/onebot_platform.py:329-333` vs `:1711-1716` | 反向 WS 的 `AppRunner/TCPSite` 存入 `self._reverse_server` 但 `_do_disconnect` 只关 `self._ws`——平台重启端口冲突、长驻句柄泄漏 |
| F-20 | `core/knowledge_base.py:465-478` | `import_file` 导入文档 `embedding = None  # TODO: 调用 embedding API`——导入路径永不生成向量，混合检索静默退化 |
| F-21 | `run/main.py:1019-1025` | 终端模式 scheduler 启动失败 `except Exception: pass`——定时提醒整体失效且零日志 |
| F-22 | `core/miya_daemon.py:237`（`registry.start(pid)`）；`run/daemon.py:183` | `--platforms` 实测传 help 示例值 `webchat` 报 `ERROR [Registry] 未知平台: webchat`：参数只能在**已启用**（enabled）平台中筛选，而 help 举例的 qqofficial/webchat 默认均未启用——照文档用必错 |
| F-23 | `config/.env.example`（对照代码 grep） | 键不一致：(a) `MIYA_API_TOKEN`/`MIYA_JWT_SECRET`/`MIYA_WEBUI_ADMIN_PASSWORD`/`MIYA_ENCRYPTION_KEY` 等 16 个 MIYA_* 安全/运行键未声明；(b) 错名键 `WEB_API_CORS_ORIGINS`（代码读 `MIYA_CORS_ORIGINS`）、`ONEBOT_WS_URL`/`ONEBOT_BOT_QQ`（代码读 `QQ_ONEBOT_*`，`core/config_loader.py:89`）；(c) 47 个声明但零引用的死键（GITHUB_*、WECOM_*、KOOK_TOKEN、SLACK_*、各模型名键等） |
| F-24 | `core/config_loader.py:59` | `AI_PROVIDER` 仅作默认 provider 字符串（默认 siliconflow），全仓无 `mock` 分支——`AI_PROVIDER=mock` 不会生效（与任务提示/惯例不符，安全验证只能靠不触发对话） |
| F-25 | `plugins/yinmei/core/live_stream_hub.py:75,84,93`；`bilibili_danmaku.py:63`；`sing_engine.py:150`；`draw_engine.py:129` | Live2D 状态/情绪/口型/弹幕/唱/绘全部 `except Exception: pass`——表现层与内部状态静默脱节（PHASE9 治理盲区，同 mcpserver） |
| F-26 | `hub/decision_hub.py:1117` | 对话热路径 `asyncio.create_task(self._handle_smart_emoji(...))` 裸发无引用（RUF006），可被 GC；同类：`core/web_api/__init__.py:564`、`core/web_api/miya_api.py:1216`、`core/miya_daemon.py:337` |
| F-27 | `core/web_api/tools.py:152,160,188-233` | data_analyze 任意路径读 / chart_generator 任意路径写（叠加 SEC-3 无鉴权） |
| F-28 | `run/daemon.py:47` vs `:211-213` | `FileHandler("logs/...")` 在 `setup_logging()` 内执行，而 `log_dir.mkdir` 在其后的 main() 里——全新环境下启动直接 FileNotFoundError 且不在 try 保护内（当前仓库自带 logs/ 未触发） |
| F-29 | 守护进程实测日志（`/tmp/miya_audit_snapshot/daemon_stdout.log` 尾部） | OpenAPI 6 个 Duplicate Operation ID 警告（`miya_api.py` 内 `get_provider_template`/`get_system_prompt`/`set_config` 等函数名重复注册）——路由函数命名冲突 |
| F-30 | 守护进程实测日志 | `INFO: [MiyaAPI] 获取工具列表失败: cannot import name 'get_registry'...` 输出在重定向文件中呈 GBK 乱码（"鑾峰彇宸ュ叿鍒楄〃澶辫触"）——Windows 下日志重定向编码不一致（logger 用 UTF-8，控制台层 GBK 解码） |

### P3（建议）

| 编号 | 位置 | 现象 |
|---|---|---|
| F-31 | `core/version.py`=`8.0.0`、`pyproject.toml`=`8.0.0`、`README.md:8,50`=`v8.1`、Web API `/api/status` 的 `identity.version`=`"1.0.0"`（`miya_api.py` 硬编码）、daemon 自述"v8.0"（`run/daemon.py:166`） | **同一系统 4 处版本号三套值** |
| F-32 | `run/main.py:154-155`、`:139` | `NetManager`+`CrossNetEngine`（"蛛网式分布式架构"组件）与 `arbitrator` 构造后全仓零引用——死对象 |
| F-33 | `core/web_api.py` 与 `core/web_api/` 包同名共存（前者自述兼容层，实际被包遮蔽）；`core/web_api/__init__.py.backup` 残留 | 死文件 |
| F-34 | 仓库根 `%SystemDrive%/ProgramData/Microsoft/Windows/Caches/*.db` | Windows 环境变量未展开导致系统缓存写进仓库目录；全仓代码无引用（来源为某次以异常环境运行的系统组件）。建议删除并 gitignore |
| F-35 | `scripts/_rewrite_memory_ctx.py.bak` | 一次性"自我改写源码"脚本残留，无主体无引用（git 未跟踪，即任务开始时已存在） |
| F-36 | `scripts/verify_hud_build.sh` | 构建验证后不清理临时目录（实测遗留 `/f/tmp_hud`，含整份 node_modules 拷贝，已人工清理） |
| F-37 | `scripts/build_web_frontend.sh` | 已失效：`cd frontend/packages/web` 后 `npm install`，但该目录只有 dist/ 无 package.json；结尾提示的入口 `webnet/web_main.py` 也不符——旧架构残留 |
| F-38 | `config/diteng_strategy_config.json` | 全仓无代码引用——死配置 |
| F-39 | `config/platforms_config.py:325-334` vs `.env` 键 | aiocqhttp 双配置通道（写死 ws_reverse_host=127.0.0.1:8095/token="" vs `QQ_ONEBOT_*` 环境变量） |
| F-40 | `core/unified_platform_impl/generic_platform.py:58-69` | WebChatPlatform `_do_connect` 仅打日志不启动任何服务器、healthcheck 恒 True——纯健康状态摆设（真实 Web 聊天走 `core/web_api/chat.py` 直连 decision_hub） |
| F-41 | `core/unified_platform_impl/webhook_platforms.py:81-84` | Lark 直接调 SDK 私有方法 `_connect()/_ping_loop()/_receive_message_loop()`——SDK 升级即断 |
| F-42 | `core/proactive_chat.py:661-663` | `_try_get_ai_message` 死存根（`return None # 覆盖在 async 调用中`），全仓无调用点，注释误导 |
| F-43 | `hub/platform_adapters.py:585-605` | 平台适配映射"万物皆 QQ"（lark/telegram/discord/webchat/kook 全映射 QQAdapter） |
| F-44 | `tests/conftest.py` | 6 个 fixture `pytest.importorskip` 指向不存在的模块（cognitive.*、services.queue_manager、skills.auto_pipeline）——死 fixture；`cleanup_after_test` 只 gc 不还原 environ |
| F-45 | `.baseline-tests.txt` | 内容是一份历史 pytest 失败 traceback（F:\PY 系统 Python 路径）——基线文件本身是失败记录，无参考价值 |
| F-46 | 终端模式实测输出 | 「对话历史已保存」打印两次（`run/main.py:1078-1079` 与 `:1044-1046` 双路径重复） |
| F-47 | `docs/PHASE7_RESOURCE_LEAKS.md`、`docs/PHASE9_EXCEPTION_SWALLOWING.md` | 头部状态"待执行"但抽查 9 项中 7 项已在代码落地（如 memory/core.py:1991-1994 error+raise、run/main.py:860-898 关闭链、utils/singleton.py）——文档状态过时；2 项与代码偏离（灵魂客户端 warning 未 raise、proactive_chat 配置 error 未 raise） |

### 静态走读正面结论（真实接通的证据）

- **入口链零断链**：`run/daemon.py:98` → `core/miya_daemon.py:151-155`（`from run.main import Miya`）→ 终端 `run/main.py:998` 同一构造路径；全部静态 import 与 26 个延迟导入逐一核验存在；DecisionHub 16 个注入 kwargs 与形参一一匹配（`run/main.py:195-212` vs `hub/decision_hub.py:135-154`）。
- **平台→中枢链真实**：`registry.start(miya_core=...)` → `set_miya_core` → `MessageMixin._miya_core` → `route_to_decision_hub`（`message_mixin.py:179-210`）→ `decision_hub.process_perception_cross_platform`。
- **OneBot/QQ官方/Telegram/Discord/Lark/DingTalk 均为真实接线**（ws_connect/SDK reply/im.message.create 等，详见证据表）；仅 KOOK/Slack/LINE/Satori 是壳（F-9）。
- **记忆双通道接通**：GRAG 注入（`main.py:699-700`）+ daemon 补调 `grag.initialize()`（`miya_daemon.py:167-173`，修复了历史"从未调用"bug）。
- **异常治理大体落地**：宽 except 1377 处中 core/hub/memory 的吞噬已基本清零（带 noqa 理由注解+日志率 90%+），残余集中在 mcpserver/ 与 plugins/yinmei/ 两个盲区。
- **测试质量良好**：120 个测试无 skip/无空断言，抽查均为真实行为断言（真实 scrypt/JWT 往返、具体数值公式），mock 只作用于协作者。
- **React HUD 与 8000 契约基本对齐**（约 46 路径消费，4 个断点：POST /api/config/file 405、/api/terminal/chat 404、/api/tools/history 404、/api/chat/history 404，均定位到代码行）。

---

## 六、与仓库文档/README 的矛盾点对照表

| 文档宣称 | 代码/实测事实 | 证据 |
|---|---|---|
| README:8 「弥娅 v8.1」 | version.py/pyproject 均 8.0.0；Web API identity 报 1.0.0 | F-31 |
| README:50 「终端模式 v8.1 重构」、README:204「daemon.py 231 行」 | daemon.py 实为 234 行（自述 v8.0） | `run/daemon.py:166`、wc -l |
| docs/API_REFERENCE.md：9800 有 `/api/v1/miya/status`、`/api/v1/memory/search|stats`、`/api/v1/personality/list|switch` | 全部 404（management_api.py 无这些路由，只有 health/platforms/daemon/status/auth） | 实测 404 ×4 |
| docs/API_REFERENCE.md：8000 有 `POST /api/terminal/chat`、`GET /api/mcp` | 前者 404（仅 `/api/desktop/terminal/execute`）；后者实为 `/api/mcp/list|call|reload` | openapi.json 实测 |
| docs/API_REFERENCE.md：「管理 Dashboard API (端口 6185)」 | 6185 无任何监听，全仓无启动点 | 实测 connection refused |
| Makefile `quality` 目标（ruff+black 检查） | black 步带 `\|\| true`，165 文件失败仍通过 | F-14 |
| .env.example 声明的 `ONEBOT_WS_URL`/`WEB_API_CORS_ORIGINS` 等键 | 代码实际读 `QQ_ONEBOT_*`/`MIYA_CORS_ORIGINS`，声明键零引用 | F-23 |
| CLAUDE.md/AGENTS.md 路径 `F:\Ranxin\Miya` | 实际 `F:\#Ranxin\Miya`（任务书已声明，复核属实） | — |
| docs/PHASE7、PHASE9 状态「待执行」 | 大部分已执行落地 | F-47 |
| 任务提示「tests/conftest.py 有 mock provider 用法（AI_PROVIDER=mock）」 | 代码无 AI_PROVIDER=mock 分支；conftest 的 mock 是 pytest fixture 注入，非环境变量 | F-24 |
| 任务提示「scripts/.smoke_log_blacklist.json 内置白名单」 | 该文件不存在，实际靠脚本内置 DEFAULT_LOG_WHITELIST 回退 | 实测 ls |
| pyproject `testpaths=["tests/unit"]`（CI 基线约 27 passed 的历史说法） | 当前 120 passed；tests/core/（16 测试）不被默认收集，需显式运行 | 实测 |

---

## 七、修复建议（按优先级）

| 优先级 | 建议 | 涉及文件 | 风险 |
|---|---|---|---|
| 🔴 1 | **止血 P0**：8000 的 app 全局挂鉴权依赖（可复用 auth_security 的 JWT）；删除或白名单化 `/api/tools/task_execute` 的 shell 执行；`/api/config/file` 增加扩展名/路径黑名单（至少拒绝 `.env`、`*.json` 凭证文件）；`/api/plugin/install` 加管理员校验；WS endpoint 复用 auth_gate 逻辑 | `core/web_api/tools.py`、`core/web_api/__init__.py`、`run/main.py`、`core/management_api.py` | 低（增量加鉴权，不动物理链路） |
| 🔴 2 | mcpserver 记忆写盘：读档失败改为备份原文件后再写（或拒绝写入），杜绝空覆盖 | `mcpserver/miya/server.py:148-154` | 低 |
| 🟠 3 | daemon 关闭链补 `await self._miya.ashutdown()`（或至少设 uvicorn `should_exit`+join）；顺带修复 logs/ 目录先建后用的顺序 | `core/miya_daemon.py`、`run/daemon.py` | 中（需测试退出时序） |
| 🟠 4 | 初始化失败可观测：AI 客户端/WebNet/子路由失败时在 `get_daemon_status`/`/api/health` 暴露 `degraded` 字段；`_init_subroutes` 拆分为每模块独立 try | `run/main.py`、`core/miya_daemon.py`、`core/web_api/__init__.py` | 低 |
| 🟠 5 | 修复 `/api/tools/list`：为 `webnet/ToolNet/registry.py` 补模块级 `get_registry()`（或改用现有单例访问点），失败时返回 5xx 而非空列表假成功 | `core/web_api/miya_api.py:1592`、`webnet/ToolNet/registry.py` | 低 |
| 🟠 6 | 冒烟脚本：S6 探针改为 `exec(textwrap.dedent(...))` 多行字符串（消除分号拼接）；S7 白名单补 Neo4j 连接拒绝模式并落盘 `.smoke_log_blacklist.json` | `scripts/smoke_test.py` | 低 |
| 🟠 7 | Electron 端契约修复（大工程）：统一 `CoreApiClient` 指向 8000，或在 daemon 侧为 9800 补齐 `/api/*` 反代；先删两个后端都无的 6 个死端点调用 | `miya_frontend/src/api/*` | 高（前端面广） |
| 🟡 8 | Makefile 去掉 black 的 `\|\| true`，一次性 `black core/ hub/ run/` 重排（165 文件，纯格式无语义变化，单独提交） | `Makefile:19` + 全量格式化 | 低（注意与在途分支冲突） |
| 🟡 9 | 统一版本号到 `core/version.py` 单一来源（README/pyproject/identity 均引用它）；同步更新 .env.example（补 MIYA_* 键、删 47 死键、纠正 ONEBOT_*/CORS 键名） | 多文件 | 低 |
| 🟡 10 | 占位工具治理：15 个占位工具要么接真实现（knowledge 系列可桥接 `core/knowledge_base/bridge.py`），要么先从注册表摘除，避免 LLM 消耗调用 | `webnet/ToolNet/tools/`、`registry.py:418-435` | 低 |
| 🟢 11 | 卫生清理：删 `%SystemDrive%/`、`core/web_api.py`、`*.backup`、`_rewrite_memory_ctx.py.bak`、`diteng_strategy_config.json`、死对象（NetManager/CrossNetEngine/arbitrator/Miya.neo4j）、死 fixture、失效的 build_web_frontend.sh；verify_hud_build.sh 补 `trap 'rm -rf "$TMP"' EXIT` | 多文件 | 低 |
| 🟢 12 | 文档校正：API_REFERENCE.md 按实测重写；PHASE7/9 状态改「已执行」并补 2 项偏离说明 | docs/ | 低 |

---

## 附：验证环境与红线执行声明

- 全程未读取/未输出 `config/.env` 任何键值（仅 md5 哈希前后比对，值 `c5f837f1…` 前后一致）；未向任何真实平台账号发送消息；未发生 AI 计费调用。
- 后台进程全部清理：daemon PID 65840 已终止，端口 8000/9800/8095/19900/19901/6185 复核无监听；`/f/tmp_hud` 已删除；`git status` 与验证前一致（仅任务开始前既存的 2 个未跟踪文件）；未创建/未提交任何 commit。
- 验证产生的系统正常写入（SQLite WAL、neo4j 迁移检查点时间戳、logs/*.log）为程序自身行为，按任务要求未清理真实数据。

---

# 修复记录（2026-09-07 附录）

> 本章节记录审查发现后的完整修复实施与验收结果。全部修复已在 `fix/v8-hardening` 分支完成并逐项验收。

## H1. 3号启动（桌面模式）根因与修复

**根因**：项目路径 `F:\#Ranxin\Miya` 含 `#`。Vite 的 `cleanUrl`（`postfixRE=/[?#].*$/`）把绝对路径中 `#` 后内容当 URL 锚点截断 → 主进程构建失败（`Could not resolve "./modules/backend"`，文件本身存在）→ Electron 回退执行 6月14日 旧 `dist-electron/main.js` → 旧代码仍创建 Live2D 窗口 → `src/live2d-app/main.ts` 未经转换被当 JS 执行 → `main.ts:6 Unexpected identifier 'as'`。渲染层 `/src/main.ts` 404 同理。日志证据：`logs/miya_2026-06-14.log` 显示当时路径为 `F:\Ranxin\Miya`（无 #）。

**修复（三层）**：
1. `start.bat`：新增 `:ensure_nohash` 子程序——路径含 `#` 时自动创建目录联接 `%LOCALAPPDATA%\Miya-link`（junction 无需管理员）并从联接路径启动；启动前删除陈旧 `dist-electron/main.js` 防旧代码假活。`:desktop`/`:web`/`:all` 三条链路全部接入。
2. `miya_frontend/vite.config.ts`：`preserveSymlinks` 阻止 `fs.realpathSync.native` 穿透联接 + `miya-hash-path-fix` 插件（把 Vite 内部 realpath 切换仍产生的含 `#` 真实路径 id/importer 确定性映射回联接路径）。
3. `frontend/ui/vite.config.ts`：同款修复（4号 Web 启动一并修复）。

**实测**：junction 下 `vite build` 全绿（Electron 渲染层 914 模块 + main.js + preload.cjs）；`WEB_ONLY` dev server 下 `/src/main.ts`、`/src/live2d-app/main.ts` 转换正常、0 个 Pre-transform error；HUD `tsc --noEmit` + `vite build` 通过。

## H2. 安全修复（P0，全部实测验收）

| 项 | 修复 | 验收证据 |
|---|---|---|
| SEC-1 RCE | `core/web_api/tools.py` 删除 `shell=True` 命令执行分支 | `POST /api/tools/task_execute {"command":"echo PWNED"}` → `{"success":false,"error":"已禁用直接命令执行…"}` |
| SEC-2 任意读 | `/api/config/file` 改 `os.path.commonpath` 边界校验 + `.env*` 黑名单 | `?path=config/.env` → `{"error":"该文件受安全策略保护，禁止读取"}`；兄弟目录前缀绕过（`../Ranxin-evil/x`）同样被封 |
| SEC-3 零鉴权 | 新增 `core/web_api/auth_security.install_token_gate()` 统一网关挂载 8000：本机放行、远程需 `MIYA_API_TOKEN`（恒时比较）；登录/文档/健康路径公开 | 单测 6 项（loopback 放行/远程 403/401/公开路径/local-only）；daemon 实测 loopback 200 |
| SEC-4 WS 绕过 | 9800 重构复用同一 `install_token_gate` + `websocket_gate()`（WS 握手前校验，HTTP middleware 不拦 WS） | `core/management_api.py` 网关单源；单测覆盖 |
| 数据丢失 | `mcpserver/miya/server.py save_memory` 读档失败先备份原文件再重建 | 代码审查确认；写路径不再空覆盖 |

另：`AI 客户端降级标记`（`ai_degraded` → `/api/v1/health` 暴露 `"degraded":{"ai_client":false}`，daemon 实测）；`/api/memory/search` query 参数修复（原 GET 无 body 恒空串）；`Makefile black 门禁去 `|| true``。

## H3. Electron 契约对齐（30+ 调用 404 → 修复）

- `src/api/core.ts:231` 端口 9800→8000（支持 `VITE_CORE_PORT` 覆盖）；8 处直连 fetch（config/session/MessageView/MindView/ConfigView/tts）改 8000；`live2d-window.ts:88` 注入端口 9800→8000。
- 字段归一化（core.ts 包装层）：`listSessions→{sessions}`、`getSession→{messages}`、`getSystemPrompt→systemPrompt`、`memory/list→items`、`persona/list→personas`、`plugin/market_list→data`、`tools/list→tools`、`memoryStats→nodeCount`。
- 后端补路由：`POST /api/desktop/files/parse`（文本类解析）、`POST /api/desktop/files/upload`（存 data/uploads）、`POST /api/audio/transcribe`（明确 501 未配置）；`files/write` 参数改 JSON Body（原 query 签名前端必 422）；`/api/memory/add` 兼容五元组。
- 实时推送：新增 `core/event_bus.py`；`message_mixin.py` 平台收发消息 → 总线 → `ManagementAPI` 桥接 WS `new_message`（桌面端聊天窗实时显示 QQ/Telegram 等跨平台消息；桌面自身走 HTTP 响应不回显）。
- 死方法清理：chatStream/chatStop/newSession/searchQuintuples/telemetry×2 删除。

## H4. Web HUD 断点（4 → 修复）

- 配置中心保存 405 → 改用 `/api/desktop/files/write`（JSON Body 版）；`/api/terminal/chat`（前后两处）→ `/api/chat/send`；`/api/chat/history` → `/api/chat/get_session`；无意义 404 轮询 `/api/tools/history` 移除；后端 `/api/logs` 补 `level` 过滤参数（原来被静默忽略）。

## H5. 稳定性与卫生

- daemon 关闭链：`_close_miya_core` 调 `ashutdown()`；新增 `POST /api/v1/daemon/shutdown`。**实测**：shutdown API → `弥娅系统正在关闭…已关闭` → `弥娅守护进程已关闭`，进程 exit 0、端口全释放（修复前必须 taskkill /F 强杀）。
- 调度器双实例：daemon 启动前 `set_global_scheduler(miya.scheduler)`。
- `--platforms` 未知 id 显式报错并列出可用值；help 示例修正。
- `/api/tools/list` 假成功修复（import 不存在的 `get_registry` → `decision_hub.tool_subnet.registry` 兜底 `get_tool_registry()`），实测返回真实工具与描述。
- 冒烟 S6 探针重写（原分号拼接 `async def` 语法错误，**该阶段历史上从未通过过**）；S3/S4 基线采集补 `import json`（原 NameError 静默产出空基线 `{}`）；S7 白名单补 Neo4j 连接拒绝；`--write-baseline` 修复后重建真实基线。
- 版本统一 `core/version.py` 单一真源（miya_api 两处 "1.0.0"、management_api 硬编码、README v8.1 全部改正）。
- 卫生清理：删除 `core/web_api.py`（包遮蔽死文件）、`__init__.py.backup`、`_rewrite_memory_ctx.py.bak`、`diteng_strategy_config.json`（死配置）、仓库根 `%SystemDrive%/` 垃圾目录、失效 `build_web_frontend.sh`；`verify_hud_build.sh` 补 trap 清理；死对象 arbitrator/net_manager/cross_net_engine/死存根 `_try_get_ai_message` 移除；`Miya.neo4j` 死驱动接入 ashutdown 关闭；11 个占位工具暂停注册（group/knowledge/cognitive 系列，防 LLM 调到占位文案）；`.env.example` 删 43 个死键 + 补 9 个安全键名声明；`check_imports_vs_requirements.py` 修复（标准库扩充/本地包/pyproject 可选组解析/连字符映射，修复后 `所有 import 对应的依赖均已声明`）。
- 修复过程中发现并修正自查引入的问题：`miya_api.py` 缺 `Optional` 导入导致 MiyaAPI 168 条路由静默注册失败（这正是审查发现的"异常吞掉→静默缺失"模式的现场复现，靠新增单测捕获）。

## H6. 修复后验收矩阵

| 门禁 | 修复前 | 修复后 |
|---|---|---|
| ruff check | ✅ 0 违规 | ✅ 0 违规 |
| black --check | ❌ 165 文件不合规（被 `\|\| true` 掩盖） | ✅ 197 文件全部合规（全量格式化 + 门禁生效） |
| pytest | ✅ 120 passed | ✅ **132 passed**（新增 token_gate 6 项 + webapi 安全 6 项） |
| 冒烟 --fast | ✅ 5/5 | ✅ 5/5 |
| 冒烟全量 | ⚠️ 7/9（S6 语法 bug、S7 白名单缺口） | ✅ **9/9**（S6 首次真实通过；S8 真实基线对比通过） |
| SEC-1 RCE | 🔴 可无鉴权执行命令 | ✅ 已封堵（实测） |
| SEC-2 任意读 | 🔴 可读 config/.env | ✅ 已封堵（实测） |
| SEC-3 零鉴权 | 🔴 8000 全裸 + 0.0.0.0 | ✅ 网关生效（本机放行/远程 token，单测覆盖） |
| Electron 构建 | ❌ `Could not resolve` + 旧代码假活 | ✅ build 914 模块全绿 + dev 转换正常 |
| Electron 契约 | ❌ 30+ 调用 404 | ✅ 端口/字段对齐 + 补 3 路由 + WS 实时推送 |
| HUD 断点 | ⚠️ 4 个 404/405 | ✅ 全部修复（tsc + build 通过） |
| daemon 优雅退出 | ⚠️ 无法退出（需强杀） | ✅ shutdown API → exit 0、端口释放、完整关闭链日志 |
| 终端模式 | ✅ EXIT=0 | ✅ EXIT=0（回归无恙） |

**总结论：✅ 全模式真实跑通**（终端 / 守护进程+双 API / 桌面应用构建与 dev / Web HUD 构建；QQ 平台消息闭环仍需 NapCat 实例，属外部依赖；聊天端到端 AI 调用按红线未在验收中执行，链路经模型池初始化与降级路径验证）。

## H7. 遗留事项（后续路线图）

1. 占位工具的真实现（knowledge 桥接 `core/knowledge_base/bridge.py`、cognitive/group/auth）——已暂停注册，接入后恢复。
2. KOOK/Slack/LINE/Satori 平台收发实现（当前未注册，接入前无暴露）。
3. 语音转写后端选型接入（当前 501 明确拒绝）。
4. Electron 端建议后续接入 `VITE_CORE_PORT` 环境变量统一端口管理；Live2D 窗口的 `__MIYA_API_PORT__` 注入值与后端端口探测联动。
5. `core/knowledge_base`、`core/unified_platform` 仍存在同名包/模块遮蔽（import_graph 基线已记录，建议后续合并）。
6. 建议将项目迁移至不含 `#` 的路径以彻底消除工具链隐患（当前 junction 方案已可稳定工作，但属于规避而非根除）。
