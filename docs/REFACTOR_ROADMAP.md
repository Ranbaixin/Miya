# 弥娅架构重构路线

## 目标

用 miya_psyarch (APV2.1 白箱认知引擎) 替代 hub/DecisionHub 的 LLM 认知层，
让旧架构从"LLM 全包"退化为纯消息路由和平台适配层。

## 当前架构 vs 目标架构

```
当前:
  run/main.py → DecisionHub.process_perception_cross_platform()
    → AI API 调用 (每消息一次)
    → 人格注入 → 伦理检查 → 仲裁 → 输出

目标:
  run/main.py → MessageRouter (新: 轻量路由)
    → miya_psyarch.MiyaEngine.tick(text)  (AP 认知)
    → AI API 调用 (仅必要时, LLM皮层模式)
    → 输出
```

## Phase 1: 清理 (0.5天)

- [ ] 删除空目录: configgame_profiles/, config/models/, webnet/mcp/
- [ ] 删除 core/miya_system.py (v6.0.0 废弃)  
- [ ] 整理 scripts/test_*.py → tests/
- [ ] 统一版本号到 8.0.0 (core/version.py, docs, pyproject.toml)
- [ ] 标记 hub/memory_engine.py + hub/memory_emotion.py 为 deprecated

## Phase 2: 记忆系统统一 (0.5天)

- [ ] DecisionHub 中移除对 hub/memory_engine.py 的引用
- [ ] 统一使用 memory/core.py (已替代旧引擎)
- [ ] miya_psyarch/memory/miya_memory_bridge.py 直接读 memory/ 的 SQLite

## Phase 3: 认知层替换 (1-2天)

- [ ] 创建 core/miya_psyarch_bridge.py (弥娅旧系统 ↔ AP 引擎桥接)
- [ ] DecisionHub.process_perception() 改为:
      → 消息预处理 (平台适配)
      → miya_psyarch.MiyaEngine.chat(text)  (AP 认知 + LLM 皮层)
      → 后处理 (格式化/日志)
- [ ] 保留 DecisionHub 的平台适配、权限、调度 功能
- [ ] 移除 DecisionHub 中重复的 LLM 调用逻辑

## Phase 4: 消息流优化 (1天)

- [ ] AP 主动消息 → M-Link 消息总线 → 各平台
- [ ] AP 情绪池 + 原情绪系统合并
- [ ] miya_psyarch.observatory 挂载到 dashboard API

## 不做的事

- [ ] 不移除 memory/ 统一记忆系统 (核心依赖)
- [ ] 不移除 webnet/ 子网架构 (独立模块)
- [ ] 不移除 astrbot/ (QQ 多平台)
- [ ] 不移除 mcpserver/ (MCP 服务)
- [ ] 不删除 hub/decision_hub.py (渐进替代, 不直接删除)
