# Miya 深度审计报告 · 第一次扫描 (2026-06-14)

## 总览

| 维度 | 发现数 | 严重度 |
|------|:---:|------|
| 硬编码路径/端口 | 23 | 🔴 |
| 边缘情况/空值 | 12 | 🟠 |
| 静默失败/资源泄漏 | 28 | 🟠 |
| 低可行性文件 | 11 | 🟡 |
| 可行但未跑通 | 8 | 🟡 |
| 并发/异步问题 | 15 | 🟠 |
| **总计** | **97** | |

---

## 🔴 最严重问题 TOP 10

### 1. singing 模块全部硬编码 `D:\AIvoice\...` 路径 (7处)
- `core/singing/uvr5_cli.py:6` — `sys.path.insert` + `os.chdir` 到绝对路径
- `core/singing/music_source.py:184` — `D:\AIvoice\RVC...\runtime\python.exe`
- `core/singing/manager.py:380` — `D:\AIvoice\RVC...\ffmpeg.exe`
- `core/singing/provider_builtin.py:106,157,240` — 3处 Python/ffmpeg 路径
- `core/singing/separator.py:177,188,370` — UVR5 Python + 模型权重 + ffmpeg

**影响**: 唱歌/语音功能在任何非开发机完全不可用。  
**修复**: 全部改为环境变量 + `sys.executable` + `shutil.which()` 兜底。

### 2. 权限检查 fails-open
- `webnet/ToolNet/registry.py:249` — except 分支 `return {"allowed": True}`

**影响**: 权限系统故障时所有工具对所有人开放。  
**修复**: 已在前序修复中改为 `allowed: False` ✅

### 3. DingTalk SDK 硬编码路径
- `core/unified_platform_impl/real_platforms.py:186` — `sys.path.insert(0, r"D:\AI_MIYA_Facyory\...")`

**影响**: 飞书/钉钉平台在任何非开发机崩溃。  
**修复**: 用 `pip install` 正确安装 SDK。

### 4. OpenClaw 硬编码 vendor 路径
- `mcpserver/openclaw/runtime.py:88` — `Path("D:/AI_MIYA_Facyory/NagaAgent/vendor/openclaw")`

**影响**: OpenClaw MCP 服务无法定位 vendor 目录。  
**修复**: 环境变量 `OPENCLAW_VENDOR_PATH`。

### 5. Provider bridge 硬编码 localhost 端口
- `core/providers/bridge.py:231` — Ollama/SenseVoice/vLLM/Xinference 端口全部硬编码

**影响**: 任何非 localhost 部署需要手动改代码。  
**修复**: 环境变量。

### 6. CronTask 缺少 status 字段
- `core/cron_system.py:214` — `task.status = TaskStatus.RUNNING` 但 dataclass 无此字段

**影响**: 定时任务调度 AttributeError。  
**修复**: 已在前序修复中添加 `status` 字段 ✅

### 7. OneBot HTTP fallback 硬编码端口
- `core/unified_platform_impl/onebot_platform.py:422` — `http://127.0.0.1:3000/`

**影响**: NapCat HTTP API 在非标准端口不可用。  
**修复**: 从 web_config 读取端口。

### 8. Disk usage 硬编码 C:\
- `core/web_api/desktop.py:273` — 仅 Windows/Linux，无 macOS
- `core/web_api/__init__.py:236` — 同上
- `hub/platform_adapters.py:460` — 同上

**影响**: macOS 上磁盘显示错误；非 C: 系统盘 Windows 上显示错误。  
**修复**: `psutil.disk_usage("/")` 跨平台通用。

---

## 🟠 低可行性文件 (建议删除)

| 文件 | 原因 |
|------|------|
| `plugins/__init__.py` (仅此一个) | 插件系统未实现，空壳 |
| `mcpserver/` 大部分内容 | 路径硬编码，依赖缺失 |
| `examples/` | 引用已删除的类名，无法运行 |
| `astrbot/` (100K+ 行) | 三重复制，仅 `core/astrbot_compat/` 被使用 |
| `frontend/packages/` | Tauri 残留，项目已切到 Electron |
| `miya-desktop/`, `miya-pc-ui/` | .gitignore 标记为 deprecated |

---

## 🟢 后续步骤

1. **等 core/ 深挖完成** (wf_275fbfdc-c14)
2. **启动 hub/ webnet/ memory/ run/ 深挖**
3. **统一修复所有硬编码路径**
4. **删除低可行性文件，思路写入 README**
5. **跑通 broken 功能**
