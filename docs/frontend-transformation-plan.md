# 弥娅前端改造清单

> 整理日期：2026-05-02
> 目标：打造专属于弥娅系统的 Web 前端

---

## 一、项目现状概览

### 1.1 三个前端应用

| 应用 | 技术栈 | 定位 | 状态 |
|------|--------|------|------|------|
| `frontend/packages/web` | Vue 3 + Vuetify + Pinia | AstrBot 控制台 | ⚠️ 部分保留 |
| `frontend/ui` | React + Tailwind + Framer Motion | 弥娅专属 HUD | ✅ 基础完善 |
| `miya_frontend` | PyQt5 | 桌面客户端 | ✅ 保留 |

### 1.2 React 前端 (frontend/ui) 现状

**技术栈：**
- React 18.2.0
- Tailwind CSS 3.4.3
- Framer Motion 12.38.0 (动画)
- Vite 5.2.0 (构建)

**已有组件（47个）：**
- UI 基础：Panel, BackgroundLayer, StatusBar
- 头部/底部：HeaderBar, FooterBar, Sidebar, Header
- HUD 组件：HudRing, MiniHudRing, DataRing, VoiceWavePanel
- 弥娅专属面板：IdentityPanel, EmotionPanel, EmotionTimelinePanel, MemoryPanel, CognitivePanel, PsychologicalPanel, VectorPanel, ConversationPanel, RelationshipPanel, InnerThoughtPanel, ModelPoolPanel
- 功能组件：SystemMonitorPanel, RuntimeInfoPanel, ConnectionStatusPanel, QuickActionsPanel, ToolLogPanel, AiResponsePanel, MessageHistoryPanel, CharacterCard
- 工具面板：PersonalityFormPanel, QQAccountPanel

**已有页面（12个）：**
- DashboardPage, EmotionPage, MemoryPage, CognitivePage
- ToolsPage, SettingsPage, LogsPage, AccountPage
- SystemsPage, GroupsPage, FriendsPage, MessagesPage

**API 服务：** `miyaApi.ts` 已对接 Runtime API

---

## 二、必须保留的功能模块

### 2.1 平台适配系统 ⭐（重要）

弥娅系统支持 **18 个平台**，这些都需要在前端配置和管理：

#### 2.1.1 平台列表

| 平台ID | 名称 | 类型 | 前端需保留 |
|--------|------|------|-----------|-----------|
| `qqofficial` | QQ 官方机器人 | QQ 系列 | ✅ |
| `qqofficial_webhook` | QQ 官方 Webhook | QQ 系列 | ✅ |
| `aiocqhttp` | OneBot/NapCat | QQ 系列 | ✅ |
| `telegram` | Telegram | 国际平台 | ✅ |
| `discord` | Discord | 国际平台 | ✅ |
| `slack` | Slack | 国际平台 | ✅ |
| `lark` | 飞书 | 国内平台 | ✅ |
| `dingtalk` | 钉钉 | 国内平台 | ✅ |
| `wecom` | 企业微信 | 国内平台 | ✅ |
| `wecom_ai_bot` | 企业微信 AI Bot | 国内平台 | ✅ |
| `weixin_oc` | 微信开放平台 | 国内平台 | ✅ |
| `weixin_official_account` | 微信公众号 | 国内平台 | ✅ |
| `line` | LINE | 国际平台 | ✅ |
| `kook` | KOOK | 社区平台 | ✅ |
| `mattermost` | Mattermost | 社区平台 | ✅ |
| `misskey` | Misskey | 社区平台 | ✅ |
| `satori` | Satori | 通用协议 | ✅ |
| `webchat` | 网页聊天 | 特殊平台 | ✅ |

#### 2.1.2 需保留的平台组件

| 文件 | 说明 | 融合方案 |
|------|------|----------|
| `views/PlatformPage.vue` | 平台管理主页面 | **迁移**到 React `PlatformPage.tsx` |
| `components/platform/AddNewPlatform.vue` | 添加平台对话框 | **迁移**到 React |
| `components/shared/PluginPlatformChip.vue` | 平台标签芯片 | **迁移**到 React |
| `utils/platformUtils.ts` | 平台工具函数 | **迁移**到 React |
| `i18n/translations.ts` | 平台国际化 | **迁移**到 React |

#### 2.1.3 平台相关 API

| 端点 | 功能 | 状态 |
|------|------|------|------|
| `GET /api/platform/list` | 平台列表 | ✅ 后端已有 |
| `GET /api/platform/stats` | 平台统计 | ✅ 后端已有 |
| `GET /api/platform/config` | 平台配置 | ✅ 后端已有 |
| `GET /api/platform/metadata` | 平台元数据 | ✅ 后端已有 |

---

### 2.2 插件/MCP 生态系统 ⭐（重要）

弥娅采用双轨制扩展架构：

#### 2.2.1 MCP 服务系统

**当前配置的 MCP 服务器：**
- `miya-soul` - 弥娅灵魂功能 MCP 服务器
- `playwright` - 浏览器自动化服务

**需保留的 MCP 功能：**

| 功能 | 说明 | 前端需保留 |
|------|------|-----------|-----------|
| MCP 服务器列表 | 显示已配置的 MCP 服务 | ✅ |
| MCP 服务状态 | 在线/离线状态 | ✅ |
| MCP 工具调用日志 | 工具调用记录 | ✅ |
| MCP 配置编辑器 | 编辑 `mcp.json` | ✅ |

**相关文件：**
- `config/mcp.yaml` - MCP 主配置
- `config/mcp.json` - MCP 服务器详细配置
- `mcpserver/` - MCP 服务目录

#### 2.2.2 插件市场 ⭐（重要）

弥娅有自己的插件市场，对接 **AstrBot 官方插件市场**：

**约 90 个可安装插件**，分类如下：

| 分类 | 示例插件 | 功能 |
|------|---------|------|
| 实用工具 | `astrbot_plugin_uapipro_toolbox` | 天气、IP 查询 |
| 媒体 | `astrbot_plugin_daily_card` | 每日卡片 |
| 生图 | `astrbot-plugin-omnidraw` | 文生图、图生图 |
| 社交 | `astrbot_plugin_twitter` | Twitter 转发 |
| 生活 | `astrbot_plugin_course` | 课表查询 |
| 记忆 | `astrbot_plugin_scriptor` | 长期记忆 |
| 订阅 | `astrbot_plugin_rsshub` | RSS 推送 |
| 管理 | `astrbot_plugin_essentials` | 权限、经济 |

**数据源：**
- 主数据源: `https://api.soulter.top/astrbot/plugins`
- GitHub 镜像: AstrBotDevs 插件仓库

**需保留的插件功能：**

| 功能 | 说明 | 前端需保留 |
|------|------|-----------|-----------|
| 插件市场浏览 | 搜索/浏览可用插件 | ✅ |
| 插件安装 | 一键安装插件 | ✅ |
| 插件卸载 | 卸载已安装插件 | ✅ |
| 插件启用/禁用 | 开关插件状态 | ✅ |
| 插件热重载 | 无需重启刷新 | ✅ |
| 插件信息显示 | 作者、版本、描述 | ✅ |

**相关文件：**
- `core/miya_plugin_manager.py` - 插件管理器
- `core/plugin_market.py` - 插件市场客户端
- `core/skills/miya_plugins/` - 插件安装目录
- `run/data/plugin_cache/plugins_market.json` - 插件缓存

#### 2.2.3 插件市场相关 API

| 端点 | 功能 | 状态 |
|------|------|------|------|
| `GET /api/plugin/market_list` | 市场插件列表 | ✅ 后端已有 |
| `GET /api/plugin/get` | 已安装插件列表 | ✅ 后端已有 |
| `POST /api/plugin/install` | 安装插件 | ✅ 后端已有 |
| `POST /api/plugin/uninstall` | 卸载插件 | ✅ 后端已有 |
| `POST /api/plugin/on` | 启用插件 | ✅ 后端已有 |
| `POST /api/plugin/off` | 禁用插件 | ✅ 后端已有 |
| `POST /api/plugin/reload` | 重载插件 | ✅ 后端已有 |
| `GET /api/mcp/list` | MCP 服务器列表 | ✅ 后端已有 |
| `GET /api/tools/mcp/servers` | MCP 服务详情 | ✅ 后端已有 |

---

### 2.3 知识库系统

弥娅使用 **enhanced_knowledge_base**，前端���保留：

| 功能 | 说明 | 融合方案 |
|------|------|----------|
| 知识库列表 | 查看已创建的知识库 | **迁移**到 React |
| 知识库详情 | 查看/编辑知识库 | **迁移**到 React |
| 文档管理 | 上传/删除/编辑文档 | **迁移**到 React |
| 向量检索测试 | 测试检索效果 | **迁移**到 React |

---

## 三、冗余模块清单（需删除）

### 3.1 页面级冗余

| 文件 | 说明 | 删除原因 |
|------|------|----------|--------------|
| `views/CronJobPage.vue` | 定时任务页 | AstrBot 特有，弥娅无 cron 需求 |
| `views/SubAgentPage.vue` | 子代理页 | AstrBot 特有，弥娅用 Agent 系统 |
| `views/TracePage.vue` | 追踪页 | AstrBot 调试功能 |
| `views/alkaid/*` | Alkaid 功能 | AstrBot/Alkaid 特有 |
| `views/stats/StatsPage.vue` | AstrBot 统计 | **合并**到 React Dashboard |

### 3.2 组件级冗余

| 文件 | 说明 | 删除原因 |
|------|------|----------|--------------|
| `components/AstrBotConfig*.vue` | AstrBot 配置 | 直接调用 AstrBot restart |
| `components/config/*` | AstrBot 核心配置 | AstrBot 特有 |
| `components/extension/*` | **部分保留** | MCP/插件组件需迁移 |
| `components/provider/*` | 提供者组件 | 冗余，后端统一管理 |
| `views/persona/PersonaForm.vue` | 旧人格表单 | 需重构为弥娅风格 |
| `views/persona/PersonaManager.vue` | 旧人格管理 | 需重构为弥娅风格 |

### 3.3 工具函数冗余

| 文件 | 说明 | 删除原因 |
|------|------|----------|--------------|
| `utils/restartAstrBot.ts` | 重启 AstrBot | 弥娅使用后端统一接口 |
| `scss/ pages/_dashboards.scss` | AstrBot 仪表盘 | 弥娅使用 HUD 风格 |
| `scss/_override.scss` | Vuetify 覆盖 | Vue 特有 |

---

## 四、缺失模块清单（React 前端 - 需新增）

### 4.1 灵魂发生器（情绪系统）

| 模块 | 优先级 | 说明 |
|------|--------|------|------|
| 情��池可视化 | 高 | 70+情绪类别雷达图 |
| 情境检测面板 | 高 | 关系/时间/话题识别 |
| 心理学剖析引擎 | 中 | 归因/识别/预测/反思 |
| 情绪记忆锚点 | 中 | 情绪事件时间线 |
| 情绪恢复曲线 | 低 | 衰减可视化 |
| 社交面具状态 | 低 | 真实 vs 表达分离 |

### 4.2 人格向量系统

| 模块 | 优先级 | 说明 |
|------|--------|------|------|
| 人格向量雷达图 | 高 | 6维度可视化 |
| 形态切换器 | 高 | normal/alpha/amics |
| 核心信念编辑器 | 中 | YAML 配置编辑 |
| 专属称呼管理 | 中 | 称呼体系配置 |
| 人格关联可视化 | 低 | 人格间关系图 |

### 4.3 统一记忆系统 V3.1

| 模块 | 优先级 | 说明 |
|------|--------|------|------|
| 记忆层级面板 | 高 | 短/长/语义/知识分层 |
| 记忆来源标注 | 中 | DIALOGUE/EXTRACT/MANUAL |
| 隐私记忆管理 | 中 | 隐私分类显示 |
| 记忆优先级设置 | 低 | LOW/NORMAL/HIGH/CRITICAL |
| 人生手册（Lifebook） | 中 | 人生事件记录 |

### 4.4 平台适配界面（新增）

| 模块 | 优先级 | 说明 |
|------|--------|------|------|
| 平台管理主页 | 高 | 平台列表/状态/操作 |
| 添加平台对话框 | 高 | 新增平台向导 |
| 平台详情面板 | 高 | 平台配置编辑 |
| 平台状态监控 | 高 | 连接状态实时显示 |
| 平台切换器 | 中 | 多平台快速切换 |
| 平台教程链接 | 中 | 接入教程/帮助文档 |

### 4.5 插件/MCP 管理界面（新增）

| 模块 | 优先级 | 说明 |
|------|--------|------|------|
| 插件市场页面 | 高 | 浏览/搜索插件 |
| 插件管理页面 | 高 | 已安装插件列表 |
| MCP 服务器页面 | 高 | MCP 服务管理 |
| 插件安装弹窗 | 高 | 一键安装 |
| 插件详情面板 | 中 | 插件信息/配置 |
| MCP 配置编辑器 | 中 | mcp.json 编辑器 |
| MCP 工具调用日志 | 中 | 工具调用历史 |

### 4.6 自主性系统

| 模块 | 优先级 | 说明 |
|------|--------|------|------|
| 自主性开关/等级 | 中 | 自主性配置 |
| 自主引擎可视化 | 中 | 决策过程显示 |
| 自主探索日志 | 低 | 探索行为日志 |

### 4.7 语音系统

| 模块 | 优先级 | 说明 |
|------|--------|------|------|
| TTS 配置面板 | 中 | 语音引擎选择 |
| 情绪化语音参数 | 中 | emotion 参数控制 |
| 声纹一致性管理 | 低 | 声音一致性设置 |

---

## 五、融合方案（React + Vue → 纯 React）

### 5.1 融合原则

1. **保留 React 前端为基础** - `frontend/ui` 是弥娅专属
2. **Vue 前端作为参考** - 部分逻辑可复用
3. **逐步迁移** - 弥娅功能迁移到 React
4. **保持 HUD 风格** - 弥娅的科技感 UI

### 5.2 功能融合对照表

| 功能 | Vue 前端 | React 前端 | 融合方案 |
|------|---------|-----------|----------|----------|--------------|
| **聊天功能** | ChatPage, ChatBoxPage | 工具聊天 | **迁移**并重构 |
| **人格选择** | PersonaPage | PersonalityFormPanel | **增强** 对接 API |
| **平台管理** | PlatformPage | 无 | **新增** PlatformPage |
| **插件市场** | ExtensionPage | 无 | **新增** PluginMarketPage |
| **插件管理** | ExtensionPage | 无 | **新增** PluginManagerPage |
| **MCP 管理** | ExtensionPage | 无 | **新增** MCPServerPage |
| **知识库** | KBList, KBDetail | 无 | **新增** KnowledgeBasePage |
| **会话管理** | SessionManagement | ConversationPanel | **合并** |
| **Dashboard** | StatsPage | DashboardPage | **合并** |
| 系统监控 | 无 | SystemMonitorPanel | ✅ |
| 情绪面板 | 无 | EmotionPanel | ✅ |
| 记忆面板 | 无 | MemoryPanel | ✅ |
| 认知面板 | 无 | CognitivePanel | ✅ |

### 5.3 迁移优先级

```
第一阶段（立即）
├── 融合聊天功能 → React
├── 新增平台管理界面
├── 新增插件市场界面
├── 新增 MCP 管理界面
└── 扩展 miyaApi.ts

第二阶段（短期）
├── 人格向量可视化
├── 情绪池可视化
├── 记忆层级面板
└── 知识库管理界面

第三阶段（中期）
├── 自主性系统
├── 代理/Agent 系统
└── 语音系统
```

---

## 六、API 对接清单

### 6.1 后端已有 API - 需对接

| 端点 | 功能 | 前端状态 |
|------|------|----------|--------------|
| `/api/platform/list` | 平台列表 | ❌ 缺失 |
| `/api/platform/stats` | 平台统计 | ❌ 缺失 |
| `/api/platform/config` | 平台配置 | ❌ 缺失 |
| `/api/plugin/market_list` | 市场插件 | ❌ 缺失 |
| `/api/plugin/get` | 已安装插件 | ❌ 缺失 |
| `/api/plugin/install` | 安装插件 | ❌ 缺失 |
| `/api/plugin/uninstall` | 卸载插件 | ❌ 缺失 |
| `/api/plugin/on` | 启用插件 | ❌ 缺失 |
| `/api/plugin/off` | 禁用插件 | ❌ 缺失 |
| `/api/mcp/list` | MCP 服务器 | ❌ 缺失 |
| `/api/knowledge_base/list` | 知识库列表 | ❌ 缺失 |
| `/api/knowledge_base/create` | 创建知识库 | ❌ 缺失 |
| `/api/knowledge_base/query` | 检索知识库 | ❌ 缺失 |

### 6.2 现有 API (miyaApi.ts)

| 端点 | 功能 | 状态 |
|------|------|------|------|------|
| `/api/management/runtime/meta` | 运行时元数据 | ✅ |
| `/api/management/system` | 系统信息 | ✅ |
| `/api/management/runtime/chat` | 聊天 | ✅ |
| `/api/v1/memory` | 记忆 | ✅ |
| `/api/v1/memes` | 表情包 | ✅ |
| `/api/cognitive/*` | 认知 | ✅ |

### 6.3 待扩展 API

| 端点 | 功能 | 优先级 |
|------|------|--------|------|------|
| `/api/v1/soul/state` | 灵魂/情绪状态 | 高 |
| `/api/v1/soul/emotion_pool` | 情绪池数据 | 高 |
| `/api/v1/personality/vectors` | 人格向量 | 高 |
| `/api/v1/personality/form` | 当前形态 | 高 |
| `/ws/chat` | WebSocket 聊天 | 高 |
| `/api/v1/autonomy/state` | 自主性状态 | 中 |
| `/api/v1/agent/intention` | 意图引擎 | 中 |
| `/api/v1/memory/layers` | 记忆层级 | 中 |

---

## 七、改造计划

### 7.1 第一阶段：核心功能

**目标：** 聊天 + 平台 + 插件生态

**任务：**
- [ ] 删除 Vue 冗余页面
- [ ] 迁移 `PlatformPage.vue` → React `PlatformPage.tsx`
- [ ] 迁移 `AddNewPlatform.vue` → React
- [ ] 新增 `PluginMarketPage.tsx`（插件市场浏览）
- [ ] 新增 `PluginManagerPage.tsx`（插件管理）
- [ ] 新增 `MCPServerPage.tsx`（MCP 管理）
- [ ] 迁移聊天功能 → React
- [ ] 扩展 miyaApi.ts（平台/插件 API）
- [ ] 完善 Dashboard

**产出：** 完整的弥娅控制台

### 7.2 第二阶段：弥娅特色

**目标：** 情绪、人格、记忆可视化

**任务：**
- [ ] 情绪池可视化（雷达图）
- [ ] 人格向量雷达图
- [ ] 形态切换器
- [ ] 记忆层级面板
- [ ] 认知事件时间线
- [ ] 知识���管理界面

**产出：** 完整的弥娅 HUD

### 7.3 第三阶段：高级功能

**目标：** 灵魂发生器、代理系统

**任务：**
- [ ] 心理学剖析引擎界面
- [ ] 情绪恢复曲线可视化
- [ ] 自主性开关/可视化
- [ ] 意图引擎监控
- [ ] 语音配置面板

**产出：** 专业 AI 系统控制台

---

## 八、页面路由规划

### 8.1 React 前端页面结构

```
frontend/ui/src/pages/
├── DashboardPage.tsx       # 首页仪表盘
├── ChatPage.tsx           # 主聊天页面 [新增]
├── EmotionPage.tsx        # 情绪面板
├── MemoryPage.tsx         # 记忆面板
├── CognitivePage.tsx      # 认知面板
├── PersonalityPage.tsx    # 人格向量 [新增/重构]
├── PlatformPage.tsx       # 平台管理 [新增/迁移]
├── PluginMarketPage.tsx   # 插件市场 [新增]
├── PluginManagerPage.tsx  # 插件管理 [新增]
├── MCPServerPage.tsx     # MCP 服务器 [新增]
├── KnowledgeBasePage.tsx  # 知识库 [新增]
├── SoulPage.tsx          # 灵魂发生器 [新增]
├── AutonomyPage.tsx      # 自主性系统 [新增]
├── VoicePage.tsx         # 语音配置 [新增]
├── SettingsPage.tsx      # 设置
├── LogsPage.tsx          # 日志
└── AboutPage.tsx         # 关于
```

### 8.2 侧边栏导航

```
Sidebar.tsx
├── 仪表盘
├── 聊天
├── 情绪
├── 记忆
├── 认知
├── 人格
├── 灵魂 [新增]
├── 平台 [新增]
├── 插件市场 [新增]
├── 插件管理 [新增]
├── MCP 服务 [新增]
├── 知识库 [新增]
├── 自主性 [新增]
├── 语音 [新增]
├── 设置
└── 关于
```

---

## 九、技术债务

### 9.1 已识别问题

| 问题 | 位置 | 影响 | 优先级 |
|------|------|------|--------|------|------|------|
| React `src/` 目录重复 | `frontend/ui/src/` vs `frontend/ui/src/` | 构建问题 | 高 |
| miyaApi.ts 缺少平台 API | `services/miyaApi.ts` | 平台功能缺失 | 高 |
| miyaApi.ts 缺少插件 API | `services/miyaApi.ts` | 插件功能缺失 | 高 |
| WebSocket 聊天未实现 | `frontend/ui` | 只能轮询 | 中 |
| 缺失人格向量 API | `services/miyaApi.ts` | 人格可视化缺失 | 中 |

### 9.2 建议修复

```bash
# 1. 清理重复目录
frontend/ui/src/      # 保留这个
frontend/ui/src/src/  # 删除这个

# 2. 扩展 miyaApi.ts
# - 添加 platform_* 方法
# - 添加 plugin_* 方法
# - 添加 mcp_* 方法
# - 添加 soul_*, personality_* 方法
# - 添加 WebSocket 连接
# - 完善类型定义

# 3. 新增页面
# - ChatPage, PlatformPage
# - PluginMarketPage, PluginManagerPage
# - MCPServerPage, KnowledgeBasePage
# - SoulPage, AutonomyPage, VoicePage
```

---

## 十、总结

| 类别 | 数量 |
|------|------|------|------|------|------|------|------|
| 需删除的 Vue 冗余页面 | 5+ |
| 需删除的 Vue 冗余组件 | 15+ |
| 需保留的 React 组件 | 47 |
| 需迁移的平台组件 | 4 |
| 需新增的插件/MCP 组件 | 6 |
| 需新增的弥娅特色组件 | 15+ |
| 需扩展的 API | 20+ |
| 改造阶段 | 3 阶段 |

**最终目标：** 一个纯 React 技术栈、专为弥娅系统打造的 Web 前端，包含：
- ✅ 平台适配系统（18 平台）
- ✅ 插件/MCP 生态（约 90 插件 + MCP 服务）
- ✅ 灵魂发生器可视化
- ✅ 人格向量系统
- ✅ 统一记忆系统 V3.1

---

*文档由弥娅系统自动生成 | 2026-05-02*