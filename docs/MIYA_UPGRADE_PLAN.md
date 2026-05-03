# MIYA 系统大升级计划

## 目标

让 MIYA 系统拥有 **AstrBot 完整功能**，同时保持弥娅独有特色（人格、情感、记忆系统），实现完全独立运行。

---

## 一、需要整合的 AstrBot 核心模块

| 序号 | 模块 | 路径 | 功能 | 优先级 |
|-----|------|------|------|-------|
| 1 | Provider | `astrbot/core/provider/` | AI 模型提供商管理 | P0 |
| 2 | Platform | `astrbot/core/platform/` | 多平台消息适配 | P0 |
| 3 | Star Plugin | `astrbot/core/star/` | 插件系统 | P0 |
| 4 | Knowledge Base | `astrbot/core/knowledge_base/` | 知识库 RAG | P1 |
| 5 | Persona | `astrbot/core/persona_mgr.py` | 人格管理 | P1 |
| 6 | Conversation | `astrbot/core/conversation_mgr.py` | 对话管理 | P1 |
| 7 | Tools | `astrbot/core/tools/` | 工具系统 | P1 |
| 8 | Cron | `astrbot/core/cron/` | 定时任务 | P2 |
| 9 | Database | `astrbot/core/db/` | 数据持久化 | P1 |
| 10 | Agent | `astrbot/core/agent/` | Agent 执行 | P2 |

---

## 二、升级路线图

### Phase 1: 核心基础重构 (P0)

#### 1.1 统一 Provider 系统
```
目标：替换现有的 providers_miya.py，使用 AstrBot 的完整实现
文件：
  - core/provider_astrbot/manager.py
  - core/provider_astrbot/entities.py
  - core/provider_astrbot/func_tool_manager.py
任务：
  [x] 分析 AstrBot Provider 结构
  [ ] 创建 MIYA Provider 封装层
  [ ] 保留 MIYA 特色（模型池、负载均衡）
```

#### 1.2 统一 Platform 系统
```
目标：替换现有的 platform_miya.py，使用 AstrBot 的完整实现
文件：
  - core/platform_astrbot/adapter.py
  - core/platform_astrbot/manager.py
任务：
  [ ] 创建 MIYA Platform 封装层
  [ ] 支持更多平台
  [ ] 保留 MIYA 特色（多端适配）
```

#### 1.3 统一 Star 插件系统
```
目标：增强 star_miya.py，集成 AstrBot 的完整插件能力
文件：
  - core/star_astrbot/star_manager.py
  - core/star_astrbot/star_handler.py
  - core/star_astrbot/command_management.py
任务：
  [ ] 集成命令管理系统
  [ ] 集成会话级插件
  [ ] 集成过滤器和上下文
```

---

### Phase 2: 数据层建设 (P1)

#### 2.1 Database 系统
```
目标：集成 AstrBot 的数据库层
文件：
  - core/db_astrbot/base.py
  - core/db_astrbot/conn.py
任务：
  [ ] 创建数据库连接管理
  [ ] 集成 SQLAlchemy
  [ ] 实现会话存储
  [ ] 实现对话历史存储
```

#### 2.2 Conversation 对话管理
```
目标：实现完整的对话管理
文件：
  - astrbot/core/conversation_mgr.py
任务：
  [ ] 会话创建/销毁
  [ ] 对话历史管理
  [ ] 会话上下文
  [ ] 消息存储
```

#### 2.3 Persona 人格系统
```
目标：实现人格管理
文件：
  - astrbot/core/persona_mgr.py
任务：
  [ ] 人格 CRUD
  [ ] 人格切换
  [ ] 默认人格设置
  [ ] 人格 Prompt 管理
```

---

### Phase 3: 高级功能 (P1-P2)

#### 3.1 Knowledge Base 知识库
```
目标：实现完整的 RAG 知识库
文件：
  - core/knowledge_base_astrbot/kb_mgr.py
任务：
  [ ] 向量存储集成 (ChromaDB)
  [ ] 文档管理
  [ ] 分块策略
  [ ] 检索增强
```

#### 3.2 Tools 工具系统
```
目标：实现完整的工具系统
文件：
  - core/tools_astrbot/registry.py
  - core/tools_astrbot/tool_manager.py
任务：
  [ ] 工具注册
  [ ] 工具执行
  [ ] MCP 工具集成
  [ ] 内置工具集
```

#### 3.3 Cron 定时任务
```
目标：实现定时任务系统
文件：
  - astrbot/core/cron/
任务：
  [ ] 任务调度器
  [ ] 任务 CRUD
  [ ] 执行日志
```

#### 3.4 Agent 执行器
```
目标：实现 Agent 执行
文件：
  - astrbot/core/agent/
任务：
  [ ] 主 Agent 逻辑
  [ ] 工具调用
  [ ] 上下文管理
```

---

## 三、技术架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                          MIYA System v2.0                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │                    MIYA Core (统一入口)                        │  │
│  │                    core/miya_core.py                          │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                               │                                      │
│         ┌─────────────────────┼─────────────────────┐              │
│         │                     │                     │              │
│         ▼                     ▼                     ▼              │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐        │
│  │ Provider    │      │ Platform    │      │ Star       │        │
│  │ System      │      │ System      │      │ Plugin     │        │
│  │ (AstrBot)   │      │ (AstrBot)   │      │ (AstrBot)   │        │
│  └─────────────┘      └─────────────┘      └─────────────┘        │
│         │                     │                     │              │
│         └─────────────────────┼─────────────────────┘              │
│                               ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │                    Data Layer (数据层)                       │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │  │
│  │  │Database  │ │Conversation│ │ Persona  │ │ KB       │       │  │
│  │  │(SQLite)  │ │ Manager   │ │ Manager  │ │ Manager   │       │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │                    MIYA Unique (弥娅独有)                      │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │  │
│  │  │Personality│ │ Emotion  │ │ Memory   │ │ Hub      │       │  │
│  │  │System    │ │ Engine   │ │ System   │ │ Decision │       │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 四、实施步骤

### Step 1: 清理依赖 (预计 1 天)
```
1. 移除 run_miya.py 中对 astrbot.core 的直接导入
2. 创建抽象接口层
3. 统一错误处理
```

### Step 2: 集成 Provider (预计 2 天)
```
1. 包装 AstrBot Provider 模块
2. 保持 MIYA 模型池特色
3. 添加配置管理
```

### Step 3: 集成 Platform (预计 2 天)
```
1. 包装 AstrBot Platform 模块
2. 保持 MIYA 适配器特色
3. 添加多端支持
```

### Step 4: 集成 Star 插件 (预计 3 天)
```
1. 包装 AstrBot Star 模块
2. 集成命令管理
3. 保持 MIYA 事件系统
```

### Step 5: 数据库层 (预计 3 天)
```
1. 集成 SQLite 数据库
2. 实现会话存储
3. 实现对话历史
```

### Step 6: 完善功能 (预计 5 天)
```
1. Persona 人格系统
2. Knowledge Base 知识库
3. Tools 工具系统
4. Cron 定时任务
5. Agent 执行器
```

### Step 7: 验证测试 (预计 2 天)
```
1. 单元测试
2. 集成测试
3. 功能验证
```

---

## 五、代码组织

### 目录结构 (升级后)

```
core/
├── miya_core.py              # 统一核心 (保持)
│
├── provider/                 # 提供商系统
│   ├── __init__.py
│   ├── manager.py          # AstrBot Provider 包装
│   ├── entities.py          # 实体定义
│   └── func_tool_manager.py # 函数工具管理
│
├── platform/                 # 平台系统
│   ├── __init__.py
│   ├── manager.py          # AstrBot Platform 包装
│   └── adapter.py          # 适配器
│
├── star/                    # 插件系统
│   ├── __init__.py
│   ├── manager.py          # AstrBot Star Manager 包装
│   ├── handler.py         # 处理器
│   └── command_mgmt.py    # 命令管理
│
├── db/                      # 数据库层 (新)
│   ├── __init__.py
│   ├── connection.py       # 连接管理
│   ├── models.py          # 数据模型
│   └── session_store.py   # 会话存储
│
├── conversation/            # 对话管理 (新)
│   ├── __init__.py
│   └── manager.py
│
├── persona/                # 人格管理 (新)
│   ├── __init__.py
│   └── manager.py
│
├── knowledge_base/         # 知识库 (增强)
│   ├── __init__.py
│   ├── manager.py
│   └── vector_store.py
│
├── tools/                  # 工具系统 (增强)
│   ├── __init__.py
│   ├── registry.py
│   └── mcp_client.py
│
├── cron/                   # 定时任务 (新)
│   ├── __init__.py
│   └── scheduler.py
│
├── agent/                  # Agent 执行器 (新)
│   ├── __init__.py
│   └── executor.py
│
├── # 保留的 MIYA 独有模块
├── personality.py          # 弥娅人格系统
├── emotion_engine.py      # 情感引擎
├── memory_system/         # 记忆系统
└── hub/                   # 决策中心
```

---

## 六、风险与挑战

1. **依赖复杂度** - AstrBot 模块之间高度耦合
2. **接口适配** - 需要大量包装层
3. **数据迁移** - 历史数据兼容
4. **测试覆盖** - 需要全面测试

---

## 七、验收标准

- [ ] MIYA 可以独立启动运行
- [ ] Provider 系统完整可用
- [ ] Platform 系统支持多平台
- [ ] Star 插件系统完整可用
- [ ] 数据库正常存储数据
- [ ] 对话管理正常
- [ ] 人格系统正常
- [ ] Dashboard API 完整
- [ ] 无需依赖 AstrBot 源码

---

*计划创建：2026-04-28*
*开始执行：确认后*