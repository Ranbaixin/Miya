# Miya 依赖管理目录说明

本目录包含所有依赖管理和安装相关的文件。

## 目录结构

```
setup/
├── INSTALL.md              # 本文件，安装说明
├── dependencies/           # 依赖分类配置（按模块分层）
│   ├── base.txt           # 基础核心依赖
│   ├── ai.txt             # AI 模型依赖
│   ├── database.txt       # 数据库依赖
│   ├── network.txt        # 网络通信依赖
│   ├── office.txt         # 文档处理依赖
│   ├── tts.txt            # 语音合成依赖
│   ├── viz.txt            # 数据可视化依赖
│   ├── qq_extras.txt      # QQ 扩展功能依赖
│   ├── platform_adapters.txt  # 多平台适配器依赖
│   ├── observability.txt  # 可观测性依赖 (OpenTelemetry)
│   ├── dev.txt            # 开发工具依赖
│   └── win32.txt          # Windows 平台特定依赖
├── requirements/           # 预设组合入口
│   ├── full.txt           # 完整依赖（生产环境）
│   ├── minimal.txt        # 最小依赖（开发测试）
│   ├── lightweight.txt    # 轻量级依赖（无外部数据库）
│   ├── dev.txt            # 开发环境（完整 + 工具）
│   └── desktop.txt        # 桌面应用依赖
└── scripts/               # 安装脚本
    ├── quick_install.sh   # Linux/Mac 安装脚本
    ├── install.ps1        # Windows 安装脚本
    ├── check_deps.py      # 依赖检查脚本（动态解析）
    └── verify_install.py  # 安装验证脚本（动态解析）
```

## 快速开始

### 一键安装（推荐）

```bash
# Linux/Mac
./setup/scripts/quick_install.sh

# Windows
.\setup\scripts\install.ps1
```

### 手动安装

```bash
# 完整安装（生产环境）
pip install -r setup/requirements/full.txt

# 轻量级安装（无外部数据库）
pip install -r setup/requirements/lightweight.txt

# 最小安装（仅核心功能）
pip install -r setup/requirements/minimal.txt

# 开发环境
pip install -r setup/requirements/dev.txt
```

### 分层安装

```bash
# 1. 安装基础核心
pip install -r setup/dependencies/base.txt

# 2. 根据需要安装其他模块
pip install -r setup/dependencies/ai.txt
pip install -r setup/dependencies/database.txt
pip install -r setup/dependencies/tts.txt
```

## 安装脚本说明

### quick_install.sh

```bash
./setup/scripts/quick_install.sh [选项]

选项：
  --full         完整安装（默认）
  --minimal      最小安装
  --lightweight  轻量级安装
  --dev          开发环境安装
  --check        仅检查依赖
  --upgrade      升级已安装的依赖
```

### install.ps1

```powershell
.\setup\scripts\install.ps1 [选项]

选项：
  -Full          完整安装（默认）
  -Minimal       最小安装
  -Lightweight   轻量级安装
  -Dev           开发环境安装
  -Check         仅检查依赖
  -Upgrade       升级已安装的依赖
```

### check_deps.py

动态解析 `setup/dependencies/*.txt`，检查所有依赖是否已安装：

```bash
python setup/scripts/check_deps.py
```

### verify_install.py

动态解析并验证依赖是否可正确导入：

```bash
python setup/scripts/verify_install.py
```

## 特殊说明

### 模拟模式

使用轻量级安装时，在 `config/.env` 中设置：

```bash
SIMULATION_MODE=true
```

### GPU 支持

```bash
# CUDA 11.8
pip install torch --index-url https://download.pytorch.org/whl/cu118

# CUDA 12.1
pip install torch --index-url https://download.pytorch.org/whl/cu121

# CUDA 12.4
pip install torch --index-url https://download.pytorch.org/whl/cu124
```

## 安装对比

| 安装方式 | 包大小 | 依赖数量 | 数据库 | AI | 可视化 | 适用场景 |
|----------|--------|----------|--------|-----|--------|----------|
| minimal.txt | ~100MB | 20 | Mock | 基础 | ❌ | 快速测试 |
| lightweight.txt | ~300MB | 35 | Mock | ✅ | ❌ | 开发调试 |
| full.txt | ~800MB | 70 | ✅ | ✅ | ✅ | 生产环境 |
| dev.txt | ~1GB | 85 | ✅ | ✅ | ✅ | 开发者 |

## 验证安装

```bash
# 检查依赖
python setup/scripts/check_deps.py

# 验证安装
python setup/scripts/verify_install.py
```
