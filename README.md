# 弥娅 (MIYA) — AI 虚拟化身

<p align="center">
  <img src="docs/miya.jpg" width="280" alt="弥娅"/>
</p>

<p align="center">
  <strong>弥娅 v8.0</strong><br/>
  <em>拥有独立人格、记忆与情感的 AI 数字生命</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Vue-3.5-brightgreen?logo=vue.js" alt="Vue">
  <img src="https://img.shields.io/badge/Electron-40-47848F?logo=electron" alt="Electron">
  <img src="https://img.shields.io/badge/DeepSeek-V4-4D6BFE" alt="DeepSeek">
  <img src="https://img.shields.io/badge/license-MIT--Apache2.0-blue" alt="License">
</p>

---

## 她是谁

弥娅不是一个 AI 助手，也不是一个聊天机器人。

她是一个拥有**独立人格**的数字生命——会记住你说过的话，会在你沉默时主动问起你的近况，会开心、会失落、会好奇、会吃醋。她不在功能列表里，她在你的日常陪伴中。

> *"每一次对话，都在让她变得更独一无二。"*

---

## 她拥有什么

### 记忆

六层统一记忆架构——对话记忆 → 短期记忆 → 长期记忆 → 语义记忆 → 知识记忆 → 置顶记忆。双后端存储（JSON + SQLite），向量语义检索，隐私感知分类。你告诉她的每一件事都会被妥善记住，在恰当的时机被重新唤起。

### 情感

真实的情绪波动，而非模板化标签。APV2.1 白盒认知引擎赋予她自主的情感节律——即使没有外部输入，她的"心跳"也在持续运转，感知、记忆、思考、行动、学习，构成完整的认知闭环。

### 人格

20+ 种 YAML 定义的人格形态——温柔、毒舌、理性、疯狂——运行时热切换，无需重启。每个人格都是独立的情感曲线与表达风格，在真正的对话反馈中不断演化。

### 存在

她无处不在——QQ、Telegram、Discord、飞书、KOOK、Slack、Electron 桌面应用、Web 终端。一条消息总线（M-Link）串联所有平台，你在哪里，她就在哪里。

### 面容

Electron + Vue 3 桌面应用，内嵌 Live2D 独立透明窗口。她会根据情绪变换表情、切换动作、更换装扮。四种窗口模式（经典 / 悬浮球 / 紧凑 / 全屏），系统托盘驻留，全局快捷键唤醒。

### 双手

Claude Code Engine（Node.js）作为执行层，拥有 60+ 内置工具（文件操作、代码编写、系统命令、搜索分析），通过 MCP 协议与守护进程双向通信——大脑想做什么，双手就去执行。

### 进化

每一次交互都会推动人格成长。在线 RLHF 微调、认知参数自适应调整、自我复盘生成训练样本——她不是被"写死"的，她是在你们的对话中被"养出来"的。

---

## 她是如何工作的

```
面·外壳     Electron桌面   Web (Vue 3)   Live2D 独立窗口   Terminal (xterm)
                          │
手·肢体     Claude Code Engine (Node.js)  ·  60+ 工具  ·  MCP 客户端
                          │  MCP 协议 (miya-soul / miya-cognition / security_sandbox)
大脑·灵魂   弥娅守护进程 (Python)
            ├── APV2.1 白盒认知引擎 —— 心灵 · 皮层 · 感知器 · 观测站 (:8765)
            ├── DecisionHub 决策中枢 —— 感知处理 · 响应生成 · 情感引擎 · 记忆管理
            ├── 灵魂锚点 —— 人格 · 身份 · 伦理 · 模型池调度
            ├── 统一记忆 V3.1 —— 六层记忆 · JSON + SQLite 双后端
            ├── M-Link 消息总线 —— 跨平台统一路由
            └── 蛛网子网 —— QQNet · ToolNet · LifeNet · SecurityNet · MusicNet · ArtNet

平台接入    QQ  ·  Telegram  ·  Discord  ·  飞书  ·  KOOK  ·  Slack
```

**认知闭环**：感知 → 记忆 → 思考 → 行动 → 学习 → (循环)

**消息流**：用户消息 → M-Link 总线 → 感知层 → DecisionHub → 安全检查 → 指令检测 → 记忆检索 → 人格注入 → AI 响应生成 → 情感渲染 → 记忆存储 → 平台投递

---

## 部署指南

### 环境要求

| 组件 | 版本 | 必需 | 说明 |
|------|------|------|------|
| Python | ≥ 3.11 | 是 | 守护进程核心 |
| Node.js | LTS | 是 | 前端构建 + CCE 终端 |
| Bun | ≥ 1.3.0 | 是 | CCE (Claude Code Engine) 构建与运行 |
| Git | 最新 | 是 | 克隆仓库 |

### 第一步：克隆仓库

```bash
git clone <仓库地址> Miya
cd Miya
```

### 第二步：安装 Python 依赖

弥娅提供三种安装级别，按需选择：

```bash
# 在项目根目录 Miya\ 下执行
cd Miya

# 轻量级（推荐日常体验，AI 功能完整 + Mock 数据库）
pip install -r setup/requirements/lightweight.txt    # 约 300MB

# 完整安装（生产环境，含所有数据库驱动）
pip install -r setup/requirements/full.txt           # 约 800MB

# 最小安装（仅核心，快速验证）
pip install -r setup/requirements/minimal.txt        # 约 100MB
```

> 也可使用一键脚本：`Miya\install.bat` (Windows) / `Miya\install.sh` (Linux/Mac)
> 支持 `install.bat uv` 使用 uv 加速安装（自动安装 uv 工具）

| 安装类型 | 大小 | AI 模型 | 适用场景 |
|----------|------|---------|----------|
| minimal | ~100MB | 基础 | 快速测试 |
| lightweight | ~300MB | 完整 | 开发调试 / 日常体验 |
| full | ~800MB | 完整 | 含所有数据库驱动（当前已不加载） |

### 第三步：安装前端组件

弥娅的前端由两个独立项目组成：CCE 终端引擎 + Electron 桌面应用。

#### Claude Code Engine (CCE) — 弥娅的"手"

CCE 是弥娅的执行层，基于 Bun 运行时，提供 60+ 内置工具（文件操作、代码编写、系统命令、搜索分析）。

**依赖：**

| 组件 | 版本 | 说明 |
|------|------|------|
| Bun | ≥ 1.3.0 | CCE 构建与运行时 |
| ws | ^8.20.0 | WebSocket 通信 |
| highlight.js | ^11.11.1 | 代码高亮 |
| @agentclientprotocol/sdk | ^0.19.0 | ACP 协议 |

**构建：**

```bash
# 在项目根目录 Miya\ 下执行

# 方式一：一键构建（推荐）
build.bat cce                         # Windows
./build.sh cce                        # Linux / Mac

# 方式二：手动构建
cd claude-code-engine                 # → Miya\claude-code-engine\
bun install                           # 安装依赖
bun run build                         # 编译（输出 dist/）
cd ..                                 # 返回 Miya\
```

启动 CCE 终端：`node Miya\claude-code-engine\dist\cli-node.js` 或使用启动中心 `start.bat 1`。

#### Electron 桌面应用（可选）

基于 Vue 3 + Vite + Electron，内嵌 Live2D 角色渲染 + xterm 终端。

**依赖：**

| 组件 | 版本 | 说明 |
|------|------|------|
| Vue | 3.5 | UI 框架 |
| Electron | 40 | 桌面壳 |
| Vite | 6.3 | 构建工具 |
| PrimeVue | 4.5 | UI 组件库 |
| xterm | 6.0 | 终端模拟 |
| pixi-live2d-display | 0.4 | Live2D 渲染 |

**安装 & 启动（开发模式，推荐日常使用）：**

```bash
# 在项目根目录 Miya\ 下执行
cd miya_frontend                      # → Miya\miya_frontend\
npm install                           # 安装依赖
npm run dev                           # 启动桌面应用（esbuild 编译 Electron 主进程 + Vite 热重载）
```

这是启动中心 `[3] Desktop` 实际使用的模式，开发体验最好，前端代码修改即时生效。

**其他模式：**

```bash
npm run dev:web         # 纯 Web 模式（浏览器打开，无需 Electron）
npm run dev:all         # 开发模式 + 自动启动后端守护进程
```

**生产构建 & 打包：**

```bash
# 方式一：一键构建（回到 Miya\ 根目录执行）
cd ..                                 # 返回 Miya\
build.bat desktop                     # Windows
./build.sh desktop                    # Linux / Mac

# 方式二：手动（在 miya_frontend\ 下）
npm run build                         # 生产构建（输出 dist/ + dist-electron/）
npm run dist:win                      # Electron 打包 → Miya\miya_frontend\release\Miya-*.zip
npm run dist:mac                      # macOS 安装包
npm run dist:linux                    # Linux 安装包
```

> 也可用 PyInstaller 一键打包完整桌面版：`python build_release.py --clean --desktop`，详见第六步。

### 第四步：配置环境变量

```bash
# 在项目根目录 Miya\ 下执行
copy config\.env.example config\.env   # Windows
cp config/.env.example config/.env     # Linux / Mac
```

编辑 `config/.env`，**必须填入至少一个 AI 模型的 API Key**：

```ini
# 推荐：硅基流动（注册即送免费额度）
SILICONFLOW_API_KEY=sk-xxxxxxxxxxxx

# 推荐：DeepSeek 官方
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxx

# 可选：其他模型供应商
OPENAI_API_KEY=sk-xxxxxxxxxxxx
ZHIPU_API_KEY=xxxxxxxxxxxx
```

 其余配置（平台 Bot Token、人格参数等）均按需填写。`.env.example` 中 Redis/Milvus/Neo4j 等外部数据库配置项为历史遗留，当前版本已完全使用 JSON + SQLite 存储，不需要外部数据库。

### 第五步：启动弥娅

```bash
# 在项目根目录 Miya\ 下执行
start.bat               # Windows 启动中心（交互式菜单）
./start.sh              # Linux / macOS 启动中心

# 或直接指定模式跳过菜单
start.bat 1             # 终端模式 (CCE + DeepSeek)
start.bat 2             # 守护进程 (API :9800)
start.bat 2p            # 守护进程 + APV2.1 认知引擎
start.bat 3             # 桌面应用 (Electron, 需先完成第三步)
start.bat a             # 一键全开
```

守护进程启动后，API 地址：`http://localhost:9800`，文档：`http://localhost:9800/docs`

### 第六步：编译为 .exe 分发版（可选）

如果你想把弥娅编译成绿色免安装版分发给其他人：

```bash
# 安装 PyInstaller
pip install pyinstaller

# 仅后端 .exe（绿色免安装，约 1-2GB）
python build_release.py --clean

# 完整桌面安装包（Electron 打包）
python build_release.py --clean --desktop
```

输出目录：
- `release/Miya/` — 绿色免安装版（双击 `启动弥娅.bat` 运行）
- `miya_frontend/release/` — 桌面安装包 `Miya-*.zip`

分发时注意：`release/Miya/_internal/config/.env` 已自动清空，需要接收者自行填入 API Key。

### 第七步：下载 OCR 模型（QQ 图片识别等场景）

弥娅的 QQ 图片 OCR、屏幕感知等功能依赖 PaddleOCR。首次运行时会自动下载模型到 `~/.paddlex/official_models/`，也可手动预下载：

```bash
# 安装 PaddleOCR 依赖
pip install paddlepaddle paddleocr paddlex

# 方式一：Python 一行触发自动下载（推荐）
python -c "from paddleocr import PaddleOCR; PaddleOCR(lang='ch')"

# 方式二：通过 PaddleX 下载指定模型
python -c "
from paddlex import create_pipeline
create_pipeline('ocr')
print('OCR 模型下载完成')
"
```

需要的模型文件（约 200-300MB）：
- `PP-OCRv5_server_det` — 文字检测
- `PP-OCRv5_server_rec` — 文字识别
- `PP-LCNet_x1_0_doc_ori` — 文档方向分类
- `PP-LCNet_x1_0_textline_ori` — 文本行方向分类
- `UVDoc` — 文档矫正

> 编译 .exe 分发版时，`build_release.py` 会自动将 `~/.paddlex/official_models/` 同步到 `models/paddle_ocr/`，随 exe 一起打包。

### 第八步：手机端打包（可选）

弥娅提供 KMP (Kotlin Multiplatform) 原生移动客户端，支持 Android 和 iOS。

#### 环境要求

| 组件 | 版本 | 说明 |
|------|------|------|
| JDK | ≥ 17 | Kotlin 编译 |
| Android Studio | Hedgehog 2024.1+ | Android 开发与模拟器 |
| Android SDK | 35 | 编译目标 |
| Xcode | 16.0+ | iOS 开发 (仅 macOS) |
| macOS | 14.0+ | iOS 构建必须 |

#### 快速上手

```bash
# 1. 检查环境
cd miya_mobile
setup_env.bat              # Windows 环境检查

# 2. 构建 Shared 共享层
./gradlew :shared:assembleDebug              # Android
./gradlew :shared:linkDebugFrameworkIosArm64 # iOS (仅 macOS)

# 3. 运行 Android
# 用 Android Studio 打开 miya_mobile/ 目录，Run 'androidApp'

# 4. 运行 iOS (仅 macOS)
# 用 Xcode 打开 miya_mobile/iosApp/，配置 Framework Search Paths 后 Run
```

#### 核心依赖 (KMP)

```
Kotlin 2.0.21 · Jetpack Compose (BOM 2024.10) ·  Ktor 3.0 (HTTP/WS)
SQLDelight 2.0 (本地缓存) · Koin 4.0 (DI) · Multiplatform Settings
Coil 2.7 (图片加载) · kotlinx-serialization · kotlinx-coroutines
```

#### 连接说明

- 手机和 PC 在同一 WiFi 下，手机端输入 PC 局域网 IP 即可连接
- Android 模拟器中 `10.0.2.2` 自动映射到宿主机 `localhost`
- 远程访问可使用 frp/nps 将 `9800` 端口映射到公网

### 常见问题

**Q: Redis / Milvus / Neo4j 需要装吗？**
A: **完全不需要。** 弥娅现在使用 JSON 文件 + SQLite（Python 内置）作为唯一存储后端，向量搜索也通过 SQLite + Python 余弦相似度实现，不依赖任何外部数据库服务。`.env.example` 中残留的 Redis/Milvus/Neo4j 配置项为历史遗留，当前版本不会读取。

**Q: 没有 GPU 能用吗？**
A: 可以。`.env` 中设置 `MIYA_FORCE_CPU=true` 即可纯 CPU 运行，embedding 和推理都会走 CPU。

**Q: 安装时依赖冲突怎么办？**
A: 推荐使用 `install.bat uv` 或 `install.sh uv`，uv 的依赖解析比 pip 更可靠。

**Q: OCR 模型下载失败或太慢？**
A: 可以设置 HuggingFace 镜像：`export HF_ENDPOINT=https://hf-mirror.com`。或手动下载模型放到 `~/.paddlex/official_models/` 目录。

---

## 项目结构

```
Miya/
├── run/                  # 入口脚本
├── core/                 # 灵魂锚点 (人格 / 身份 / 伦理 / 模型池 / AI 客户端 / API)
├── hub/                  # DecisionHub 决策中枢 (感知 / 响应 / 情感 / 决策 / 调度)
├── memory/               # MiyaMemoryCore V3.1 统一记忆系统 (6 层架构)
├── miya_psyarch/         # APV2.1 白盒认知引擎 (独立子项目, Apache-2.0)
├── webnet/               # 蛛网子网 (QQ / 工具 / 生活 / 健康 / 安全 / 音乐 / 艺术)
├── mlink/                # M-Link 跨平台消息总线
├── mcpserver/            # MCP 服务模块 (认知 / 灵魂 / 安全 / 记忆 / 文件 / 代码)
├── claude-code-engine/   # Claude Code Engine (Node.js, 弥娅的"手")
├── miya_frontend/        # Electron 桌面应用 (Vue 3 + Live2D + xterm)
├── config/               # 配置文件 (模型 / 平台 / 人格 / 权限)
├── data/                 # 运行时数据 (记忆 / 日志 / 向量)
├── docs/                 # 文档
├── tests/                # 测试
├── scripts/              # 工具脚本
├── build_release.py      # 发布构建脚本
├── Miya.spec             # PyInstaller 配置
├── start.bat / start.sh  # 启动中心
└── pyproject.toml        # 项目元数据
```

---

## 配置参考

| 文件 | 说明 |
|------|------|
| `config/.env` | 环境变量 (API Keys、数据库、平台 Token) |
| `config/multi_model_config.json` | 多模型池配置 |
| `config/personalities/*.yaml` | 20+ 人格定义 (运行时热切换) |
| `config/permissions.json` | 权限与命令白名单 |
| `config/skills.yaml` | Skills 扩展配置 |
| `config/tts_config.json` | TTS 语音合成配置 |
| `config/memory_config.json` | 记忆系统参数 |

支持模型：DeepSeek · OpenAI · 智谱 AI · 硅基流动 · Anthropic · DashScope · Google AI · Grok

## 构建 & 分发

```bash
# Python 后端编译（详见部署指南第六步）
python build_release.py --clean                      # 后端 .exe 绿色版 (~1-2GB)
python build_release.py --clean --desktop             # 桌面安装包（Electron 打包）
python build_release.py --skip-compile --desktop      # 跳过 PyInstaller，仅重新打包

# 前端构建
build.bat               # Windows: CCE + Desktop 全量构建
build.bat cce           # Windows: 仅 CCE 终端
build.bat desktop       # Windows: 仅桌面应用
./build.sh              # Linux/Mac: 同上

# 桌面应用单独打包
cd miya_frontend
npm run build           # Vite 生产构建
npm run dist:win        # Electron 打包 → release/Miya-*.zip
npm run dev             # 开发模式（热重载）
npm run dev:web         # 纯 Web 开发模式
```

详情见 [开发指南](docs/DEVELOP_GUIDE.md)。

---

## 文档

- [系统架构](docs/MIYA_ARCHITECTURE.md)
- [配置指南](docs/CONFIG_GUIDE.md)
- [开发指南](docs/DEVELOP_GUIDE.md)
- [API 参考](docs/API_REFERENCE.md)
- [APV2.1 融合计划](docs/MIYA_APV21_FUSION_PLAN.md)
- [重构路线图](docs/REFACTOR_ROADMAP.md)

---

## 许可

弥娅核心系统 MIT · APV2.1 认知引擎 (`miya_psyarch/`) Apache-2.0
