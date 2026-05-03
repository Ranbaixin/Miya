# MIYA 系统架构梳理

## 一、整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                          MIYA System                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    入口层 (Entry)                             │  │
│  │   run_miya.py / run_dashboard_api.py / start.bat            │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                               │                                      │
│                               ▼                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    核心层 (Core)                              │  │
│  │   ┌─────────────────────────────────────────────────────────┐ │  │
│  │   │ miya_core.py - MIYACore 统一核心                        │ │  │
│  │   │   ├── provider_manager  - 提供商管理                    │ │  │
│  │   │   ├── platform_manager   - 平台管理                    │ │  │
│  │   │   ├── star_manager       - 插件管理                    │ │  │
│  │   │   ├── knowledge_base     - 知识库管理                  │ │  │
│  │   │   ├── tool_registry      - 工具注册                    │ │  │
│  │   │   ├── event_bus          - 事件总线                    │ │  │
│  │   │   └── dashboard_api     - Dashboard API               │ │  │
│  │   └─────────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                               │                                      │
│         ┌─────────────────────┼─────────────────────┐              │
│         ▼                     ▼                     ▼              │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐        │
│  │ Provider    │      │ Platform    │      │ Agent       │        │
│  │ System      │      │ System      │      │ Runner      │        │
│  └─────────────┘      └─────────────┘      └─────────────┘        │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 二、核心模块详细

### 2.1 MIYACore (miya_core.py)

**职责**：统一协调所有子系统

**主要组件**：
| 组件 | 模块 | 作用 |
|-----|------|-----|
| provider_manager | providers_miya.py | AI 提供商管理 |
| platform_manager | platform_extended.py | 多平台适配 |
| star_manager | star_miya.py | 插件系统 |
| knowledge_base | knowledge_base.py | 知识库 |
| tool_registry | tools.py | 工具注册 |
| event_bus | event_system.py | 事件总线 |
| dashboard_api | dashboard_api.py | Dashboard API |

---

### 2.2 Provider System (AI 模型提供商)

**路径**：`core/providers_*.py`

**模块**：
```
providers_miya.py       - MIYA 自己的 Provider 管理 (推荐使用)
providers_extended.py   - 扩展 Provider
providers_config.py     - Provider 配置
provider_astrbot/       - AstrBot Provider 集成
```

**功能**：
- 管理多个 AI 模型提供商（OpenAI、Claude、DeepSeek 等）
- 模型切换、熔断、负载均衡
- API Key 管理

---

### 2.3 Platform System (多平台适配)

**路径**：`core/platform_*.py`

**模块**：
```
platform_miya.py        - MIYA 自己的平台适配 (推荐使用)
platform_extended.py    - 扩展平台
platforms_config.py     - 平台配置
platform_adapter.py     - 平台适配器基类
platform_astrbot/       - AstrBot 平台集成
```

**支持平台**：
- QQ
- Telegram
- Discord
- WebChat
- 等

---

### 2.4 Star Plugin System (星火插件系统)

**路径**：`core/star_*.py`

**模块**：
```
star_miya.py            - MIYA 自己的插件系统 (推荐使用)
star.py                 - 插件基类
star_astrbot/           - AstrBot 插件集成
```

**功能**：
- 消息处理
- 命令响应
- 定时任务
- 正则匹配
- 事件钩子

---

### 2.5 Knowledge Base (知识库)

**路径**：`core/knowledge_base*.py`

**模块**：
```
knowledge_base.py      - MIYA 知识库 (推荐使用)
enhanced_knowledge_base.py - 增强版
knowledge_base_astrbot/ - AstrBot 知识库集成
```

**功能**：
- 向量存储
- 相似度检索
- 文档管理
- RAG 支持

---

### 2.6 Tools System (工具系统)

**路径**：`core/tools.py`

**功能**：
- 工具注册
- 工具执行
- MCP 工具集成

---

### 2.7 Runtime API Server

**路径**：`core/runtime_api_server.py`

**端口**：6187

**API**：
- `/api/status` - 系统状态
- `/api/endpoints` - 交互端管理
- `/api/cognitive/*` - 认知记忆
- `/api/agents` - Agent管理
- `/api/miya/*` - 弥娅核心

---

### 2.8 Dashboard API

**路径**：`core/dashboard_api.py`, `run_dashboard_api.py`

**端口**：6187 (Dashboard 前端代理)

**功能**：
- 提供 Dashboard 前端所需的所有 API
- 对接 MIYA 核心数据

---

## 三、代码组织问题

### 3.1 存在的重复/混乱

| 功能 | MIYA 版本 | AstrBot 版本 | 位置 |
|-----|---------|-------------|------|
| Provider | providers_miya.py | provider_astrbot/ | core/ |
| Platform | platform_miya.py | platform_astrbot/ | core/ |
| Plugin | star_miya.py | star_astrbot/ | core/ |
| Knowledge Base | knowledge_base.py | knowledge_base_astrbot/ | core/ |
| Tools | tools.py | tools_astrbot/ | core/ |

### 3.2 建议

**保留**：
- `*_miya.py` - 作为主要使用版本
- `*_extended.py` - 作为扩展版本

**整合**：
- 逐步将 AstrBot 能力迁移到 MIYA 版本
- 最终目标是完全使用 MIYA 自己的实现

---

## 四、启动入口

### 4.1 主要入口

| 入口 | 文件 | 端口 | 作用 |
|-----|------|-----|------|
| 主程序 | run_miya.py | - | 启动 MIYA 核心 |
| Dashboard API | run_dashboard_api.py | 6187 | Dashboard 后端 |
| Runtime API | runtime_api_server.py | - | 运行时管理 |

### 4.2 启动方式

```bash
# 启动主程序
python run_miya.py

# 启动 Dashboard API (用于 Dashboard 前端)
python run_dashboard_api.py

# 启动 Runtime API
python core/runtime_api_server.py
```

---

## 五、后续工作

### 5.1 优先级

1. **完善核心模块** - 让 MIYA 自己的实现可用
2. **清理重复代码** - 移除 AstrBot 依赖
3. **完善 API** - Dashboard 后端完全使用 MIYA 数据

### 5.2 需要完善的模块

- [ ] 对话/会话管理
- [ ] 插件系统增强
- [ ] 知识库系统增强
- [ ] 人格系统
- [ ] 定时任务系统

---

*最后更新：2026-04-28*