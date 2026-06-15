# 弥娅 (Miya) v8.0 项目发展路线图

> 基于 6 轮 455 项深度审计 | 2026-06-15

---

# 一、短期目标（1-2 周，立即执行）

## 1.1 安全紧急修复

| # | 事项 | 说明 |
|:---:|------|------|
| S1 | **轮换泄露的 API Key** | DeepSeek/Tavily/Neo4j 密钥已暴露，立即吊销重生成 |
| S2 | **修复 .env 格式错误** |  等号后多余空格 |
| S3 | **移除所有硬编码凭据** | dashboard/routes.py、webnet/webnet.py、miya_api.py 中还有残留 |

## 1.2 运行时崩溃修复

| # | 事项 | 文件 | 影响 |
|:---:|------|------|------|
| R1 | 修复 miya_api.py ~30 路由被 stub 覆盖 | core/web_api/miya_api.py:2298 | Dashboard 全部失效 |
| R2 | 修复 hub/ content 变量覆盖 bug | hub/decision_hub.py:1702 | 用户消息被 reply 覆盖 |
| R3 | 修复 asyncio.run() 在运行 loop 中调用 | hub/decision_hub.py:757 | 高级编排器崩溃 |
| R4 | 修复 emotions list/dict 类型混淆 | hub/decision_hub.py:1650 | AttributeError 崩溃 |
| R5 | 修复 content.lower() 返回值丢弃 | hub/decision_hub.py:1228, 2479 | 关键词匹配失效 |
| R6 | 修复 CQ 码解析崩溃（缺少 = 号） | webnet/qq/message_parser.py:82 | 畸形 CQ 码崩溃 |
| R7 | 修复 OneBot JSON 解析容错 | onebot_platform.py:238 | 坏消息断连 |

## 1.3 数据完整性修复

| # | 事项 | 文件 |
|:---:|------|------|
| D1 | JsonBackend.load() 添加 _index_lock | memory/core.py:540 |
| D2 | _backup_memory() 添加文件锁 | memory/core.py:2107 |
| D3 | store/update/delete 检查返回值 | memory/core.py:1215,1774,1793 |
| D4 | delete_expired() 添加锁保护 | memory/core.py:1830 |
| D5 | _flush_index() 同步保存 tag_index | memory/core.py:1264 |
| D6 | _cache 添加 LRU 淘汰策略 | memory/core.py:812 |
| D7 | Miya.shutdown() 补全资源关闭 | run/main.py:805 |

## 1.4 QQ 用户体验修复

| # | 事项 | 说明 |
|:---:|------|------|
| Q1 | 修复消息批处理丢消息 | message_batcher.py:167 |
| Q2 | 修复拍一拍 bot_qq=0 误触发 | message_handler.py:136 |
| Q3 | 修复图片下载小文件被丢弃 | onebot_platform.py:1489 |
| Q4 | 修复 TTS 临时文件泄漏 | tts_handler.py:418 |
| Q5 | 修复 content.lower() 无效果 | tts_handler.py:178 |

---

# 二、中期目标（1-3 月，架构改进）

## 2.1 架构清理

| # | 事项 | 说明 | 收益 |
|:---:|------|------|:---:|
| A1 | **删除 astrbot/ (100K+ 行)** | 三重复制，仅 compat 层使用 | 减 60% 代码量 |
| A2 | **删除 core/platform_astrbot/** | core/platform/ 已有完整实现 | 去重 73 文件 |
| A3 | **消除 core→run 循环导入** | 创建 core/miya_app.py | 架构清晰 |
| A4 | **统一 6 套配置系统** | memory_config/text_config/multi_model/platforms/personalities/skills → 单一入口 | 配置易管理 |
| A5 | **全局单例 → 依赖注入** | MemoryManager/Scheduler/CognitiveEngine 等 7 个单例 | 可测试性 |
| A6 | **编码设置集中化** | 4 处独立 UTF-8 设置 → core/encoding_setup.py | 减少重复 |

## 2.2 平台功能补全

| # | 事项 | 说明 |
|:---:|------|------|
| P1 | **补全 6 个平台回复发送** | KOOK/Slack/钉钉/Satori/微信/企业微信 调 AI 但不发回复 |
| P2 | **导入微信完整实现** | wechat_platforms.py 有完整实现但从未 import |
| P3 | **实现 EntertainmentNet 工具加载** | _init_tools() 是空 pass |
| P4 | **修复 LINE 平台回复发送** | webhook_platforms.py:261 丢弃返回值 |
| P5 | **Telegram/Discord 支持非文本消息** | 照片/语音/视频/文件/贴纸 |

## 2.3 核心功能修复

| # | 事项 | 说明 |
|:---:|------|------|
| C1 | 修复 terminal 模式 main_loop 死代码 | run/main.py:1026 交互式聊天从未运行 |
| C2 | 修复 TOCTOU 并发竞争 | decision_hub.py:1250 _in_v3_execution 布尔标志 |
| C3 | 修复 MLinkCore 双重创建 | run/main.py:146 和 347 创建两个实例 |
| C4 | 补全 IntelligentExecutor 功能 | advanced_orchestrator.py:346 缺失 execute_tasks |
| C5 | 格式塔系统接入消息管道 | 当前完全未连接 |

## 2.4 性能提升

| # | 事项 | 预期收益 |
|:---:|------|:---:|
| F1 | JsonBackend.query() 用索引替代 rglob | 检索 10-100x 提速 |
| F2 | working_memory 用户-会话索引 | 避免扫描所有文件 |
| F3 | embedding_cache 添加 LRU | 防止 120MB+ 内存泄漏 |
| F4 | _access_frequency 关联清理 | 防止无限增长 |
| F5 | 数据库连接池 / 客户端复用 | 减少重连开销 |
| F6 | LifeBook 全量写改为追加写 | 日记写入 O(1) |

---

# 三、长期目标（3-12 月，愿景规划）

## 3.1 架构重构

| # | 方向 | 说明 |
|:---:|------|------|
| V1 | **插件系统** | 当前 plugins/ 目录为空。设计标准插件接口，支持第三方扩展 |
| V2 | **微服务化** | 将记忆/决策/工具/平台拆分为独立服务，通过 M-Link 通信 |
| V3 | **配置热重载** | 修改配置文件无需重启守护进程 |
| V4 | **Web Dashboard 完整化** | 修复所有 API，实现配置管理/监控/调试一体化 |
| V5 | **统一工具注册中心** | gestalt 和 ToolNet 两套工具系统合并 |

## 3.2 能力增强

| # | 方向 | 说明 |
|:---:|------|------|
| E1 | **多模态增强** | 语音识别(STT)/语音合成(TTS)/视频理解 完善 |
| E2 | **Agent 协作框架** | 多 Agent 分工：分析师+创作者+审核员，自动编排 |
| E3 | **自主学习系统** | 从对话中持续学习用户偏好，优化回复策略 |
| E4 | **记忆图谱可视化** | Neo4j 知识图谱的 Web 可视化浏览 |
| E5 | **跨平台记忆同步** | QQ/微信/Discord/Telegram 用户身份关联 |
| E6 | **Live2D 角色完善** | 补全物理/表情配置文件, 增加互动手势/语音口型同步 |

## 3.3 工程质量

| # | 方向 | 说明 |
|:---:|------|------|
| Q1 | **测试覆盖率 > 60%** | 当前 18 测试文件 0% 运行率，pytest 未安装 |
| Q2 | **类型注解全覆盖** | 逐步迁移到 mypy strict 模式 |
| Q3 | **CI/CD 完整流水线** | 自动测试 + 自动部署 + 自动备份 |
| Q4 | **日志系统标准化** | 统一日志格式、级别、轮转策略 |
| Q5 | **监控告警** | 守护进程健康检查、API 响应时间、内存/磁盘监控 |
| Q6 | **安全审计常态化** | 每季度全量安全扫描 + 依赖漏洞检查 |

## 3.4 文档与社区

| # | 方向 | 说明 |
|:---:|------|------|
| D1 | **开发者文档** | 模块架构说明、API 参考、贡献指南 |
| D2 | **用户手册** | 安装部署、配置指南、常见问题 |
| D3 | **架构决策记录 (ADR)** | 关键设计决策的背景与权衡 |
| D4 | **发布 Changelog** | 标准化版本发布流程 |

---

# 四、执行优先级矩阵



---

# 五、里程碑时间线


