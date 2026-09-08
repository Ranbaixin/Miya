# 弥娅开发指南

面向开发者的模块详解、扩展开发和调试指南。

---

## 目录

- [项目结构总览](#项目结构总览)
- [核心模块详解](#核心模块详解)
- [扩展开发](#扩展开发)
- [调试与测试](#调试与测试)
- [代码规范](#代码规范)

---

## 项目结构总览

```
Miya/
├── run/           # 入口脚本 (main.py 终端 / daemon.py 守护进程)
├── core/          # 灵魂锚点 (平台适配、AI 客户端、认证、Web API)
├── hub/           # 决策中枢 (DecisionHub 门面)
├── memory/        # 统一记忆系统 (六层架构)
├── webnet/        # 蛛网子网 (ToolNet 工具网等)
├── mlink/         # M-Link 消息总线（当前主链路为直连调用，总线预留）
├── config/        # 配置文件
├── frontend/      # React Ops Center (frontend/ui → packages/web/dist)
├── miya_frontend/ # Electron 桌面应用
├── mcpserver/     # MCP 服务 (独立进程)
├── plugins/       # 插件 (yinmei 虚拟主播)
├── data/          # 运行时数据（不入库，gitignore 全量忽略）
├── docs/          # 文档
├── scripts/       # 实用脚本 (含 build_hud.sh / scan_secrets.py)
├── tests/         # 测试 (tests/unit/ 为可信回归基线)
├── setup/         # 依赖清单
└── utils/         # 工具函数
```

> 2026-08 更新：perceive/detect/evolve/trust/storage/astrbot/claude-code-engine 目录已随清理移除。

---

## 核心模块详解

### run/ — 系统入口

#### `run/main.py` — 终端模式

- `Miya` 类 (1142 行) 协调所有子系统
- 初始化顺序：Settings → Core → Hub → MLink → Perceive → WebNet → Detect → Trust → Evolve → Memory
- 使用 Claude Code Engine 提供 CLI 交互

```python
class Miya:
    def __init__(self):
        self.settings = Settings()
        self.personality = Personality()
        self.ethics = Ethics()
        self.identity = Identity()
        self.arbitrator = Arbitrator()
        self.entropy = Entropy()
        # ... 更多初始化
        self.decision_hub = DecisionHub(...)
```

#### `run/daemon.py` — 守护进程

- 基于 `core/miya_daemon.py` 的 `MiyaDaemon` 类
- 可选管理 API (REST + WebSocket，端口 9800)
- 支持热插拔平台

```bash
python run/daemon.py                  # 启动
python run/daemon.py --api-port 9800  # 指定端口
python run/daemon.py --platforms qqofficial,telegram
```

---

### hub/ — 决策中枢

核心是 `DecisionHub` (3860 行)，门面模式设计：

```python
class DecisionHub:
    def __init__(self):
        self.perception = PerceptionHandler()
        self.response = ResponseGenerator()
        self.emotion = Emotion()
        self.memory_manager = MemoryManager()
        self.scheduler = Scheduler()
        # 协调各子系统处理消息
```

**关键方法**：

| 方法 | 说明 |
|------|------|
| `process_perception_cross_platform()` | 跨平台消息处理入口 |
| `_detect_commands()` | 命令检测 |
| `_security_check()` | 安全注入检测 |
| `_handle_image()` | 图片分析 |
| `_generate_response()` | AI 响应生成 |
| `_apply_emotion_color()` | 情感色彩渲染 |

---

### memory/ — 记忆系统

#### MiyaMemoryCore (V3.1)

核心记忆引擎，六层架构：

```python
from memory import MiyaMemoryCore, MemoryLevel, MemoryItem

# 单例初始化
core = await MiyaMemoryCore.get_instance(data_dir="data/memory")

# 存储
await core.store(
    content="我喜欢喝咖啡",
    level=MemoryLevel.LONG_TERM,
    user_id="user_123",
    tags=["偏好", "饮食"],
    priority=0.7
)

# 检索
results = await core.retrieve(
    query="咖啡",
    user_id="user_123",
    limit=10
)

# 语义搜索
results = await core.semantic_search("用户喜欢什么饮品？")
```

**便捷存储函数**：

```python
from memory import (
    store_dialogue,    # 存储对话
    store_important,   # 存储重要记忆
    store_auto,        # 自动提取存储
    store_knowledge,   # 存储知识图谱
    store_cognition,   # 存储认知记忆
    search_memory,     # 搜索记忆
    get_user_profile,  # 获取用户画像
    get_memory_stats,  # 获取统计
)
```

---

### webnet/ — 蛛网子网

#### 子网架构

```
WebNet
  ├── NetManager      — 子网生命周期管理
  ├── CrossNetEngine  — 跨子网通信
  ├── QQNet           — QQ 消息收发
  ├── ToolNet         — 工具注册/执行
  ├── MemoryNet       — 全局记忆共享
  ├── LifeNet         — 生活管理
  └── HealthNet       — 健康监控
```

#### 创建新子网

```python
from webnet.subnet_base import BaseSubnet

class MyNet(BaseSubnet):
    def __init__(self):
        super().__init__(name="MyNet")

    async def on_start(self):
        await super().on_start()

    async def on_message(self, msg):
        # 处理消息
        pass

# 注册到 NetManager
net_manager.register(MyNet())
```

#### 现状说明（2026-09）

- `NetManager`/`CrossNetEngine` 已于 2026-09 从 `run/main.py` 移除（构造后无消费者的死对象）；
  ToolNet（68+ 工具注册表，`webnet/ToolNet/`）与 MemoryNet（`webnet/memory.py`，装配
  `ConversationHistoryManager`）是当前真正活跃的子网。
- 8000 端口的 Web API 由 `run/main.py` 挂载 `core/web_api/` 提供（**不是** web_main.py，该文件已删）；
  `webnet/miya_webui.py` 提供 `/api/management/*` 管理路由。路由清单见 `docs/API_REFERENCE.md`。
- `webnet/ToolNet/registry.py` 的占位工具（knowledge/cognitive/group 等）已于 2026-09 暂停注册，
  接入真实现后在 `_load_*_tools` 中恢复。

---

### core/ — 灵魂锚点

#### AI 客户端 (`ai_client.py`)

```python
from core.ai_client import AIClientFactory

# 创建客户端
client = AIClientFactory.create("deepseek")

# 发送消息
response = await client.chat([
    {"role": "system", "content": "你是弥娅"},
    {"role": "user", "content": "你好"}
])
```

支持的客户端：`OpenAIClient`, `DeepSeekClient`, `AnthropicClient`, `ZhipuAIClient`

#### 人格系统 (`personality.py`)

```python
from core.personality import Personality

personality = Personality()
personality.set("kafka")  # 切换人格
current = personality.get_current()  # 获取当前人格
traits = personality.get_traits()    # 获取性格特征
```

人格文件位于 `config/personalities/*.yaml`。

#### 模型池 (`model_pool_manager.py`)

```python
from core.model_pool_manager import ModelPoolManager

pool = ModelPoolManager()
model = await pool.get_best_model(complexity=0.8)
response = await model.generate(prompt)
```

---

### mlink/ — 消息总线

```python
from mlink import MLinkCore, Message, Router

# 创建消息
msg = Message(
    type="chat",
    content="你好",
    sender="user_123",
    platform="qq"
)

# 发送到总线
await mlink.send(msg)

# 订阅消息
@mlink.on("chat")
async def handle_chat(msg: Message):
    pass
```

---

## 扩展开发

### 添加新人格

1. 在 `config/personalities/` 创建 YAML 文件：

```yaml
name: "my_persona"
display_name: "我的自定义人格"
traits:
  warmth: 0.9
  logic: 0.6
  creativity: 0.8
  empathy: 0.85
speech_style: "热情、开放、富有想象力"
```

2. 在 `config/personality_config.json` 中注册。

### 添加新平台

1. 创建平台适配器，继承 `core/unified_platform.py` 中的 `BasePlatform`
2. 在 `config/platforms_config.py` 中注册
3. 实现 `on_message()` 和 `send_message()` 方法

### 添加新工具

1. 在 `webnet/ToolNet/tools/` 创建工具函数
2. 使用装饰器注册：

```python
from webnet.ToolNet import get_tool_registry

@get_tool_registry().register("my_tool")
async def my_tool(param: str) -> str:
    """工具描述"""
    return f"处理结果: {param}"
```

---

## 调试与测试

### 运行测试

```bash
# 全部测试
pytest tests/

# 特定模块
pytest tests/test_memory.py

# 带日志
pytest tests/ -v -s
```

### 日志

日志配置在 `config/.env`：

```env
LOG_LEVEL=DEBUG    # 详细日志
LOG_LEVEL=INFO     # 正常 (默认)
LOG_LEVEL=WARNING  # 精简
```

日志文件：`logs/miya.log`

### 常用脚本（全部用 `uv run python -X utf8` 执行）

```bash
# 质量门禁（三道全绿才算合格）
uv run ruff check .
uv run black --check core/ hub/ run/
uv run python -X utf8 -m pytest -q

# 冒烟测试（--fast 跳过核心构造；全量含 S6 链路探针/S7 日志白名单/S8 基线对比）
uv run python -X utf8 scripts/smoke_test.py --fast
uv run python -X utf8 scripts/smoke_test.py
uv run python -X utf8 scripts/smoke_test.py --write-baseline   # 结构性删改后重建基线

# 导入图检查（删除模块后跑；可达集变化需 --write-baseline 重建）
uv run python -X utf8 scripts/import_graph.py --check

# HUD 构建（路径含 '#' 时自动复制到无#临时目录构建）
bash scripts/build_hud.sh
bash scripts/verify_hud_build.sh

# 依赖一致性（扫描 import 与 pyproject/setup 声明）
uv run python -X utf8 scripts/check_imports_vs_requirements.py

# vite realpath 补丁（miya_frontend/frontend-ui 的 postinstall 自动执行）
node scripts/patch_vite_realpath.mjs
```

> 冒烟基线文件：`scripts/.smoke_baseline.json` 与 `scripts/.import_baseline.json`。
> 删除模块/工具/配置属结构性变更，S1/S8 对比失败时重建基线即可；日志新增 ERROR 属预期时更新
> `DEFAULT_LOG_WHITELIST`（`scripts/smoke_test.py` 顶部）。详见 `scripts/README.md`。

---

## 代码规范

### Python

- Python 3.10+
- 使用 `ruff` 进行代码检查
- 类型注解 (type hints) 推荐使用

### 检查命令

```bash
ruff check .           # 代码检查
ruff format .          # 代码格式化
```

### 命名约定

- 模块文件：`snake_case.py`
- 类名：`PascalCase`
- 函数/方法：`snake_case()`
- 常量：`UPPER_CASE`
- 私有方法：`_private_method()`

### Git 提交

- 提交前运行 `pre-commit` 钩子
- 配置：`.pre-commit-config.yaml`
- Pylint 检查：`.pylintrc`

---

## 构建与发布流水线

### 产物概览

| 产物 | 路径 | 说明 |
|------|------|------|
| 独立后端 | `release/Miya/Miya.exe` | Python 守护进程，API 服务 |
| 桌面便携版 | `miya_frontend/release/Miya 1.0.0.exe` | Electron 前端 + 后端，双击即用 |
| 桌面解压版 | `miya_frontend/release/win-unpacked/` | 已解压的 Electron 应用（调试用） |

### 一键构建

```bash
# 仅构建独立后端
python build_release.py --clean

# 构建桌面应用（后端 + Electron 前端）
python build_release.py --clean --desktop
```

### 流水线步骤

```
[0] 清理 → 删除 dist/ build/ release/
[1] 编译 → PyInstaller (Miya.spec) → dist/Miya/
[2] 组装 → 复制 dist/Miya/ → release/Miya/ + 创建启动脚本 + .env 安全处理
[3] 同步 → release/Miya/ → miya_frontend/resources/backend/ (miya-backend.exe)
[4] 构建 → npm run build (Vite) + npx electron-builder --win portable
[5] 清理 → 删除中间产物 dist/ build/
```

### 关键配置

| 文件 | 作用 |
|------|------|
| `Miya.spec` | PyInstaller 编译配置 (入口、排除模块、数据文件) |
| `miya_frontend/package.json` | Electron-builder 配置 (extraResources、图标、目标) |
| `miya_frontend/vite.config.ts` | Vite 构建配置 (别名、Electron 插件) |
| `miya_frontend/electron/main.ts` | Electron 主进程 (窗口管理、后端启动) |
| `miya_frontend/electron/modules/backend.ts` | 后端 spawn 逻辑 |

### 已知问题与解决方案

| 问题 | 原因 | 解决 |
|------|------|------|
| ToolNet 初始化失败 `No module named 'unittest'` | PyInstaller excludes 了 `unittest`，但 `pyparsing.testing` 需要它 | `Miya.spec` excludes 移除 `unittest`，保留 `test` |
| `config/permissions.json` 找不到 | CWD 设为 `resources/backend/`，但配置文件在 `_internal/config/` | `backend.ts` 将 spawn CWD 设为 `resources/backend/_internal/` |
| Claude Code Engine `ws` 缺失 | Rollup 打包的外部依赖未跟随 | 复制 `claude-code-engine/node_modules/ws` 到 `resources/claude-code-engine/dist/node_modules/` |
| 独立版的 config/ 是 junction，复制后失效 | Windows mklink /J 使用绝对路径 | `build_release.py` 改用 `shutil.copytree` 创建真实目录副本 |
| NSIS 安装包失败 | 2.3GB 的 7z 文件 mmap 失败 | 改用 `electron-builder --win portable` |
| DeepSeek API 401 认证失败 | `.env` 中密钥为占位符（安全设计） | 发布前替换 `_internal/config/.env` 中的 `DEEPSEEK_API_KEY` |

### 分发

```bash
# 独立后端 — 压缩 release/Miya/ 为 ZIP/7z
# 接收者解压后编辑 _internal/config/.env 即可运行

# 桌面应用 — 直接分发 miya_frontend/release/Miya 1.0.0.exe
# 接收者双击运行，首次启动后在 _internal/config/.env 填入 API key
```

---

## 2026-09 二次开发须知（重要新约定）

> 本节记录 2026-09 加固/修复引入的架构约定。改动相关代码前先读；完整背景见
> `docs/AUDIT_REPORT_20260906.md` 与 `docs/ACCEPTANCE_REPORT_20260907.md`。

### 1. 质量门禁（提交前三道全绿）

```bash
make quality   # ruff + black --check（已移除 || true，格式失败会真实拦截）
make test      # pytest tests/unit -q（当前基线 132 passed）
make smoke     # 冒烟全量 9 阶段
```

- `core/ hub/ run/` 受 black 管辖（line-length 120），**改完先 `black` 再提交**。
- 新增测试放 `tests/unit/<域>/`；`tests/unit/webapi/` 是 Web API 安全回归（token gate/RCE 封堵/假成功），动鉴权或工具路由前先跑。

### 2. API 鉴权网关（勿绕过）

- 两端口统一走 `core/web_api/auth_security.py: install_token_gate()`（本机放行、远程验 `MIYA_API_TOKEN`）。
- **新增敏感端点必须**：不加入 `public_paths`；如仅限本机，加入 `local_only_paths`。
- WebSocket 新端点必须在握手前调用 `websocket_gate(ws)`（HTTP 中间件不拦 WS）。

### 3. 会话存储语义

- 写路径统一经 `hub/memory_manager.py`（`store_user_message`/`store_unified_memory`），session_id 取
  `perception["api_session_id"]`（API 透传）否则按 `{platform}_private_{user_id}` 推导。
- 读路径 `/api/chat/get_session` 用 `ConversationHistoryManager.get_history()`（**没有** `get_session` 方法）。
- 新增平台接入时若希望会话与桌面/终端共享，在 perception 里带 `api_session_id`。

### 4. 事件总线（跨组件解耦通知）

- `core/event_bus.py`：`emit_event({...})` / `on_event(fn)`。零依赖、监听器异常绝不影响主链路。
- 当前消费者：ManagementAPI → WS `/api/v1/ws` 推送 `new_message`/`platform_event`。
- 新增实时通知需求走事件总线，不要在业务代码里直接持有 WS 客户端。

### 5. AI 降级可观测

- AI 客户端初始化失败置 `miya.ai_degraded=True`，经 `MiyaDaemon.get_daemon_status()["degraded"]`
  暴露到 `/api/v1/health`。新增子系统时按此模式暴露降级状态，禁止"失败后静默继续"。
- 决策层 `ai_client=None` 时走 `_fallback_response_cross_platform` 罐头回复——排查"回复千篇一律"先看 health。

### 6. 谛听（消息策略）边界

- `memory/diteng_listener.py` 只管 QQ 类平台的防打扰；`terminal`/`web` 平台在
  `decision_hub.fetch_diting_strategy` 入口直接跳过（用户主动界面不拦截）。
- `config/diteng_strategy_config.json` 是谛听的策略选项配置（response_strategies/intent_types/reply_styles），
  **不是死配置**——它被路径拼接方式引用，删除会导致 LLM 分析退化、消息被静默丢弃（2026-09 实际事故）。

### 7. 项目路径含 `#` 的工具链规避

- Vite 把路径中 `#` 当 URL 锚点截断，Node 的 `realpathSync.native` 会穿透目录映射。
- 方案：`start.bat :ensure_nohash` 自动创建 **subst 盘符**（从 Z: 找空闲）+ `scripts/patch_vite_realpath.mjs`
  把 vite 内部 `realpathSync.native` 替换为非 native（已挂两个前端的 postinstall，重装依赖自动生效）。
- 新增前端工程时：package.json 加同款 postinstall，vite.config 参考 `miya_frontend/vite.config.ts`
  的 `hashPathFixPlugin`。
- 根治方案仍是把项目迁到无 `#` 路径；迁移后可移除 patch 与 subst。

### 8. 版本号单一真源

- 一切版本显示引用 `core/version.py: VERSION`（README/identity/management_api 均已统一）。
- 新增显示点禁止硬编码。
