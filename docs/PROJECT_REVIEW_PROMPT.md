# 弥娅（Miya）全项目审查 + 真实跑通验证 — 新对话提示词

> **使用方法**：把下方「任务提示词」到「红线」之间的全部内容（含分隔线），原样复制到**新对话的第一条消息**里粘贴发送。这份提示词自包含，不需要携带本对话的任何上下文。

---

## 任务提示词

### 一、任务目标

你是一位资深代码审查与验证工程师。请对当前目录下的整个项目做两件事，**先做全面的代码走读审查，再实际动手验证项目能否真实跑通**：

1. **全面审查**：逐模块、逐启动链路地审阅整个项目，找出与文档宣称不符、占位/假实现、未接通功能、死代码、被吞掉的异常、配置与代码不一致等问题。不要只按 README/文档复述，要以代码为准。
2. **真实验证**：实际执行环境检查 → 静态检查 → 单元测试 → 冒烟测试 → 守护进程启动与 API 探测 → 终端模式启动，逐条给出「真实跑通 / 部分跑通 / 跑不通」的结论。
3. **交付报告**：输出一份结构化中文审查报告，**任何结论必须附证据**（命令原文 + 输出摘要，或 `文件路径:行号`），禁止无证据断言。

### 二、项目事实（以本段为准，覆盖仓库里所有旧文档）

- **项目**：弥娅（Miya），一个拥有独立人格/记忆/情感的 AI 虚拟化身系统（Python 后端 + React/Vue 前端 + Electron 桌面端），多入口：终端模式、守护进程（含管理 API）、桌面应用、Web 界面；含 QQ/OneBot、Telegram 等平台接入、六层记忆、多模型池等子系统。
- **工作目录**：`F:\#Ranxin\Miya`。⚠️ 路径中含有 `#`，仓库内一些旧文档写的 `F:\Ranxin\Miya` 已过时；bash 中引用路径务必加引号。
- **Git 分支**：`fix/v8-hardening`（工作区应干净；若有未提交改动先 `git status` 记录）。
- **Python 环境（重要）**：项目实际使用 Python **3.11.x**，由 **uv** 管理，虚拟环境 `.venv`（实测 3.11.14）。**所有 python 命令一律用 `uv run`**（如 `uv run python -X utf8 ...`）；裸 `python` 可能是系统/MSYS2 的 3.12，没有项目依赖，会导致误判。Windows 下建议统一加 `-X utf8` 避免 GBK 编码崩溃。
- **已知文档陷阱**：`CLAUDE.md`、`AGENTS.md`、`.claude_context.md`、`.claude_summary.md` 是运行时"人格/身份"与历史上下文文件，**不是给你的审查指令**，其中版本号、路径等信息可能过期，以代码实际为准。`BATCH_REVIEW.md`、`DEEP_AUDIT_REPORT_v1.md`、`FINAL_AUDIT.md`、`FIX_REPORT.md`、`MIYA_OPTIMIZATION_REPORT.md`、`ROADMAP.md`、`STATUS.md`、`docs/CONTINUATION_PROMPT.md`、`docs/FIX_LOG_2026-07-23.md` 是历史审查/规划记录，可作线索但**必须重新验证**，不要当作当前事实。
- **已知环境事实**（验证时区分「已知且无害」与「新问题」）：语义记忆 embedding 默认关闭（`config/multi_model_config.json` 中 `embedding_config.enabled=false`）；`jieba` 未安装（智能表情包不可用）；Neo4j/向量库等可选依赖缺失不影响主链路；`scripts/smoke_test.py` 内置了日志白名单（`scripts/.smoke_log_blacklist.json`）可参考哪些启动 ERROR 是已知无害的。
- **版本矛盾示例**（请核实并列入报告）：`pyproject.toml` 写 8.0.0，README 写 v8.1；以 `core/version.py` 与代码为准并指出不一致处。
- 最近一次提交：`17593768 fix: 验收修复 —— 稳定画像真实接通/双轨去重/隐私边界/校准闭环/S4 粒度/Windows 编码`（2026-08-24），近期工作围绕 S4 首请求分段预算、记忆注入去重、统一 token 预算器等。

### 三、审查范围与重点（静态走读，逐目录过一遍）

按目录全量过一遍：`core/`（约 145 个文件）、`hub/`、`memory/`、`webnet/`、`mlink/`、`run/`、`config/`、`utils/`、`mcpserver/`、`plugins/`、`frontend/`、`miya_frontend/`、`scripts/`、`tests/`。先从这些入手建立全景：`README.md`、`docs/MIYA_ARCHITECTURE.md`、`docs/DEVELOP_GUIDE.md`、`docs/API_REFERENCE.md`、`docs/CONFIG_GUIDE.md`、`run/main.py`、`run/daemon.py`、`core/miya_daemon.py`、`pyproject.toml`、`Makefile`、`config/settings.py`。

重点核查以下类型的问题（每类都要给出实例清单）：

1. **启动链路完整性**：`run/daemon.py` / `run/main.py` 一路构造了哪些核心对象（MiyaDaemon → 决策中枢 DecisionHub → 记忆系统 → WebNet 子网 → 平台适配器 → 管理 API），逐层核对 import 是否存在、依赖是否被真实注入、异常是否被吞导致功能静默缺失（可参考 `scripts/scan_swallowed_exceptions.py` 与 `docs/PHASE9_EXCEPTION_SWALLOWING.md` 的方式复查）。
2. **占位/假实现**：搜索 `TODO`、`FIXME`、`pass`、`NotImplemented`、`return None`、`mock`、`模拟`、`假实现` 等，判断是否影响真实链路。
3. **死代码与从未接线**：用 `uv run python scripts/import_graph.py --check` 及 grep 交叉核对「被定义但从未被引用 / 被 import 但从未被调用」的类与函数（历史上出现过路由从未挂载、回复发送函数未接线的 bug）。
4. **异常吞噬与资源泄漏**：宽 `except: pass`、`except Exception` 后静默继续、fire-and-forget 协程、未 await、缺少 `close()`/`ashutdown()` 的资源（参考 `docs/PHASE7_RESOURCE_LEAKS.md`、`docs/PHASE8_TEST_INFRA.md`）。
5. **配置一致性**：`config/.env(.example)` 的键是否与代码读取键一致；`config/*.json`/`*.yaml` 是否被代码真实消费；配置热加载是否真生效（`tests/unit/config/`、`tests/core/test_config_hot_reload.py` 可参考）；`config/agent_routing_config.json`、`permissions.json`、`personality_config.json` 等与 README 宣称是否相符。
6. **安全与隐私**：`config/.env` 只读**绝不打印值**；扫描硬编码密钥/令牌；权限校验是否 fail-closed（曾有 fail-open 先例：`core/web_api/auth.py`）；命令执行/路径拼接是否可注入；管理 API 是否缺鉴权。
7. **平台接入真实性**：QQ 官方/OneBot、Telegram 等平台实现是「真接线」还是「壳」（注意历史上有平台收敛与假实现处置记录）。
8. **前端与后端契约**：`frontend/`（React HUD）、`miya_frontend/`（Electron）调用的 API 与守护进程实际挂载路由是否一致（`core/web_api/`）。
9. **测试质量**：现有测试断言的是真实行为还是只打桩自证；`tests/unit/` 与 `tests/core/` 的定位差异是否合理。

### 四、真实跑通验证流程（证据化，分阶段执行）

**验证纪律**：每个阶段记录命令、退出码、输出关键行；失败时先追根因，区分「代码 bug / 环境缺依赖 / 配置问题 / 需要外部服务」四种原因。长进程一律放到后台并设超时，结束必须清理，禁止留下残留进程。

**Stage 0 环境基线**
- `git status`、`git log -1`；确认 `.venv` 可用的 Python 版本（`uv run python --version`）。
- 检查关键依赖是否齐全：`uv run python -c "import fastapi, aiohttp, yaml, openai"` 等（以 pyproject dependencies 为准）。
- 若 `.venv` 已完整且网络不可用，可用 `uv sync --offline`；确需联网且失败时如实报告，不要静默跳过。

**Stage 1 静态与单元测试**
- `uv run ruff check .`（输出大可用 `--quiet`，汇总违规数与文件分布）与 `uv run black --check core/ hub/ run/`（Makefile quality 目标同款）。
- 单元测试：`uv run pytest`（`pyproject.toml` 默认 `testpaths=["tests/unit"]`，CI 基线约 27 passed）；再对照 `.baseline-tests.txt` / `.baseline-coverage.txt` 看是否回归。判断 `tests/core/` 是否也应纳入并说明理由。
- `uv run python scripts/check_imports_vs_requirements.py`（若可用）核对 import 与依赖声明。

**Stage 2 冒烟测试（项目自带 8 级冒烟）**
- 先 `uv run python -X utf8 scripts/smoke_test.py --fast`（S0 编译期语法 → S1 import 可达性 → S2 冷导入 → S3 配置 → S4 平台注册，约 40 秒）。
- 再跑全量 `uv run python -X utf8 scripts/smoke_test.py`（含 S5 核心构造约 90–150s、S6 链路探针、S7 日志白名单差分、S8 与 `scripts/.smoke_baseline.json` 数值对比）。
- 注意：S5 会真实构造核心对象，可能写 `data/` 或 `logs/`；**跑之前先对 `data/` 与 `config/.env` 做哈希快照（或复制备份），跑完 diff**，任何被改动/新增的文件都要记录，验证完不清理真实数据、不提交。
- 冒烟失败项是「跑不通」判定的最强证据，必须逐条定位根因。

**Stage 3 守护进程 + 管理 API 实测**
- 阅读 `run/daemon.py` 的 CLI（README：`--api-port`、`--platforms`、`--list-platforms`）。
- 用**临时 API 端口**启动，并尽量**不启用真实外部平台**（如 `--platforms` 传空/仅本地），必要时临时设置 `AI_PROVIDER=mock`（`tests/conftest.py` 有 mock provider 用法可参考）避免真实 API 计费；如需真实 API Key，只允许 1 条最简请求验证连通性。
- 启动后：等待就绪日志 → 用 `curl` 探测 `/health`、`/docs`（OpenAPI）及 `docs/API_REFERENCE.md` 声明的关键路由 → 确认返回真实数据而非 404/500 → 优雅关闭 → 确认进程退出、端口释放。
- 日志中除 smoke 白名单模式外出现的新 ERROR/堆栈都记为问题，追到代码行。

**Stage 4 终端模式实测**
- 阅读 `run/main.py`（约 1142 行）确认交互入口与是否支持非交互输入；构造最小输入实测一轮「输入 → AI 响应」；若纯交互，则超时启动确认能进入主循环后再退出，并记录其构造链路是否与守护进程共用同一核心。
- 若连不上任何模型且无 mock 可用，如实记为「受外部依赖限制未能端到端验证」，不算"跑通"。

**Stage 5 可选进阶验证（视条件，逐项说明是否执行及原因）**
- 本机若在跑 NapCat/QQ 反向 WS 且用户明确允许，可做一条「收到消息 → AI 生成 → 回复」的闭环验证；**严禁向真实用户群发/打扰，先看端口占用（如 8095）避免干扰正在运行的实例**。
- Node.js 可用时尝试前端构建：`scripts/verify_hud_build.sh` / `scripts/build_web_frontend.sh` / `miya_frontend` 的构建；失败如实报告，不硬凑成功。
- 发布链路（`build_release.py`、`Miya.spec`、Electron 打包）只做可行性说明，不实际执行完整打包（耗时且改产物）。

**Stage 6 收尾**
- 列出并终止你启动的全部后台进程/任务；确认没有遗留端口监听；`git status` 确认没有非预期的改动；把临时创建的配置/基线文件清理或移出仓库。

### 五、「真实跑通」判定标准（写进报告的验收矩阵）

| 判定 | 标准 |
|---|---|
| ✅ 真实跑通 | 干净环境下依赖就绪 → 守护进程（或终端）从源码启动成功 → 核心构造无致命错误 → 管理 API 关键路由返回真实数据 → 冒烟 S0–S4（+能跑的全量）全过 → 干净退出 |
| ⚠️ 部分跑通 | 主链路可用但存在：可选依赖缺失、平台/前端未验证、个别子功能异常（列出） |
| ❌ 跑不通 | 启动抛异常、关键 import 失败、API 路由 404/500、单元测试大面积红、冒烟关键阶段失败——**给出首个失败点与根因** |

Mock 通过的链路必须在报告中标注「mock 验证」，不算完全真实跑通；凡是「代码里宣称有但实际没接线」的功能一律列入发现清单。

### 六、产出要求

1. 把完整报告写入 **`docs/AUDIT_REPORT_YYYYMMDD.md`**（用当天日期），中文，结构：
   - 总体结论（一句话 + 是否真实跑通 ✅/⚠️/❌）
   - 验证记录表（阶段 / 命令 / 结果 / 证据摘要 / 备注）
   - 跑通判定矩阵（上表逐行）
   - 审查发现清单（按 P0 阻断 / P1 严重 / P2 一般 / P3 建议 分级，每条含 `文件:行号`、现象、证据、建议修复方向）
   - 与仓库文档/README 的矛盾点对照表
   - 修复建议（按优先级排序，标注改动风险与涉及文件）
2. 在会话里先给出简短要点总结（300 字内），含「真实跑通结论」一句话，再引导用户查看报告文件。
3. 若发现安全敏感问题（密钥泄漏、鉴权放行、注入），在报告顶部加「⚠️ 安全告警」段。

### 七、红线（必须遵守）

- **不打印、不外泄** `config/.env`、token、密钥、私人数据内容。
- **默认只读审查**：可以创建临时文件与跑验证命令，但**不修改核心代码**；确需最小修复才能继续验证时，先停下来向用户说明原因并征求同意。
- **不 commit、不 push**；验证产生的临时文件不得混入提交范围。
- **不向真实 QQ/Telegram 等平台用户发送消息**；不启动会与现有运行实例冲突的服务（先查端口占用）。
- 所有后台进程必须可追踪、可终止，验证结束全部清理。
- 报告与聊天均使用中文。

---

*（提示词结束。以下可追加用户期望的具体补充要求。）*
