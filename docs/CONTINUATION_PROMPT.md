# Miya v8.1 完善计划 — 新对话提示词

> 复制以下全部内容，在新 Claude Code 会话中粘贴。

---

## 项目上下文

你正在维护 **弥娅 (Miya) v8.1** —— 一个拥有独立人格、记忆与情感的 AI 虚拟化身系统。
项目位于 `F:\Ranxin\Miya`，当前分支 `fix/v8-hardening`。

> ⚠️ **Python 版本注意（2026-07-31 校准）**：项目实际 Python 是 **3.11.x**
> （uv `.venv` = 3.11.14、旧 `venv/` = 3.11.9），**不是** CLAUDE.md 所述的 3.13。
> 所有 python 命令请用 `uv run`（见「关键命令」），裸 `python` 是 MSYS2 的 3.12（无项目依赖）。

## 已完成（不要重复做）

### P-1 ~ P6、P10（12 个提交，已稳定）
三层备份 / 安全网脚本 / fail-closed 止血 / 依赖修复 / 死代码清理 / 平台收敛 / 单事件循环重构 / 假实现处置 / 文档对齐。

### P7 — 资源泄漏与并发修复 ✅（commit `9db4963a`）
- **P7.1** `Miya.ashutdown()` 重写：`_safe_close(name, close_fn)` 统一关闭链（`asyncio.wait_for` 10s 超时），补齐 4 处真实关闭：
  - 多模态分析器（模块级 `_global_analyzer`，`core/multi_vision_analyzer.py`，`get_vision_analyzer()` 惰性创建）
  - Neo4j（`self.grag_memory.close()`，`core/grag_memory.py:447`，关 `_neo4j_driver`）
  - MemoryNet 后端（`_close_memory_backends` → `get_memory_core().close()`）
  - Uvicorn（`_start_api_server` 改造为 `uvicorn.Server` + `should_exit` + `thread.join`）
- **P7.2** 10 处 RUF006 fire-and-forget 引用持有清零（`BasePlatform._spawn` + `Miya._tasks`）
- **P7.3** 新增 `utils/singleton.py`（`sync_singleton` / `async_singleton`），12 个全局单例加锁
- **环境修复（重要）**：
  - pyproject.toml 补 `[tool.hatch.build.targets.wheel]`（src-less 布局列 packages）
  - `run/`、`utils/` 加 `__init__.py` 显式化为正规包 —— 修复 hatchling editable 把 namespace 包静态拷贝到 site-packages、导致源码改动运行时**不生效**的问题（这是 P7 阶段排查出最深的一个坑）

### P8 — 测试基建重建 ✅（commit `1981164f`）
- `tests/unit/{memory,platform,config,permission}/` 目录 + **27 个测试全绿**：
  - 记忆读写 8（store/retrieve/update/delete/归档/衰减/并发）
  - 平台契约 16（能力现状快照 + 生命周期契约）
  - 权限 fail-closed 3
- 验收达标：`pytest tests/unit/` 27 passed（≥15）、coverage 基线 `.baseline-coverage.txt`（21%）、Makefile test、CI 无 `|| true`
- **测试暴露并修复的 bug**：MiyaMemoryCore 无 `close()`（P7.1 依赖）、`_match_query` 缺归档过滤、`update()` 不同步 SQLite、`SQLiteBackend.query` 缺归档过滤
- `webnet/ToolNet/tools/__init__.py` 惰性化（PEP 562 `__getattr__`）—— 消除 16 个 star import 强制加载全部可选依赖；`beautifulsoup4` 提升到主依赖

## 待完成（本次会话目标）

### P9 — 异常吞噬治理（详见 `docs/PHASE9_EXCEPTION_SWALLOWING.md`）

**现状（2026-07-31 ruff 实测，`select S110,S112,BLE001,E722`）**：
- E722 裸 `except:` **96 处**
- S110 try-except-pass **124 处**
- S112 try-except-continue **17 处**
- BLE001 盲 `except Exception`（多数已有日志）**1379 处**

**治理规则（三级分类）**：

| 级 | 判定 | 处置 |
|---|---|---|
| **Level 1 必须上抛** | 数据写入、消息发送、配置加载、权限判定 | `logger.exception()` + `raise` |
| **Level 2 记日志即可** | 可选功能降级（TTS、表情包、Live2D） | `logger.warning(..., exc_info=True)` |
| **Level 3 确实可吞** | 清理路径、best-effort 通知 | 加 `# noqa: S110 — <理由>` |

**Sprint 1: 止血 — ruff baseline 模式（~1d）**
1. `pyproject.toml`：从 `extend-ignore` **移除 `E722`**；`select` 加 `"S110", "S112", "BLE001"`
2. 为当前存量生成 `[tool.ruff.lint.per-file-ignores]` 豁免表（一次性全量，之后只减不增）
3. CI 加 `invariants` job：`ruff check . --select S110,S112,BLE001,E722 --diff`（只查 diff 新增）
4. 验收：`ruff check . --select S110,S112,BLE001,E722` 有输出但全部来自豁免

**Sprint 2: memory/ + core/unified_platform_impl/（~1.5d）** — 前置：P8 记忆测试已就位
逐文件：读 → 理解每个 `except` 意图 → Level 1 改 `raise` → 跑 `uv run pytest tests/unit/memory/` 确认不回归 → 从 `per-file-ignores` 摘除该文件。
**顺序**：`memory/core.py` → `core/unified_platform_impl/message_mixin.py` → `core/unified_platform_impl/onebot_platform.py`

**Sprint 3: hub/ + webnet/（~1.5d）**
同上流程，但 `hub/decision_hub.py` 和 `webnet/` 下多为 Level 2（可选功能降级），大规模改 raise 风险高。**优先 Level 1，其余加日志**。

**Sprint 4: core/ 其余（~1.5d）**
按文件大小和引用频率排序，优先高频调用文件。**新建 `scripts/scan_swallowed_exceptions.py`**（AST 评分：写操作 +5 / 网络调用 +3 / 权限 +4 / 空 pass +2 / 裸 except +2，总分 ≥8 打印）。Level 3 只加注释不改行为。

**P9 最危险 10 处（行号已核实准确，优先处理）**：

| # | 文件:行 | 问题 | 处置 |
|---|---|---|---|
| 1 | `memory/core.py` ~2006 | 记忆衰减写盘失败被双层 `except: pass` 吞 | `logger.error` + `raise` |
| 2 | `memory/core.py` ~1892 | 归档写盘失败被吞但仍计数成功 | `logger.error` + `raise` |
| 3 | `memory/core.py` ~707, ~1649 | 裸 `except:` 导致记忆被错误过滤 | `except (TypeError, ValueError)` 精确捕获 |
| 4 | `core/web_api/miya_api.py` ~949 | 会话列表 `json.load` 失败被吞 | `logger.exception` + 返回 500 |
| 5 | `core/unified_platform_impl/message_mixin.py` ~111 | `handle_session_end` 失败被吞 | `logger.error` + `raise` |
| 6 | `core/unified_platform_impl/message_mixin.py` ~124 | `lifebook.record_interaction` 失败被吞 | `logger.warning`（Level 2） |
| 7 | `hub/decision_hub.py` ~1557 | 灵魂模型客户端创建失败被吞 | `logger.error` + `raise` |
| 8 | `core/proactive_chat.py` ~634 | 主动聊天配置加载失败被吞 | `logger.error` + `raise` |
| 9 | `core/web_api/miya_api.py` ~1071 | 会话重命名/删除假成功 | 检查返回值，失败返回 4xx |
| 10 | `core/web_api/miya_api.py` ~2680 | 已在 P6 修复，跳过 | — |

**P9 验收**：
```bash
# Sprint 1
ruff check . --select S110,S112,BLE001,E722
# 期望: 有输出但全部来自 per-file-ignores 豁免

# Sprint 2
ruff check memory/ core/unified_platform_impl/ --select S110,S112,BLE001,E722
# 期望: 无输出
uv run pytest tests/unit/memory/ -q
# 期望: 全绿

# Sprint 4
uv run python scripts/scan_swallowed_exceptions.py --min-score 8
# 期望: 空
uv run pytest tests/unit/ -q
# 期望: P8 的 27 个测试全部仍绿
```

**P9 风险与缓解**：`pass → raise` 让静默降级路径崩溃 → 必须依赖 P8 测试安全网；Level 2 只加日志不改 raise；每批独立 commit；`per-file-ignores` 只减不增。

---

## 关键命令

```bash
cd F:\Ranxin\Miya
git switch fix/v8-hardening

uv run python scripts/smoke_test.py --fast     # 快速验证 (5/5 必须通过)
uv run python scripts/import_graph.py --check  # 静态可达性 (exit 0 必须通过)
uv run pytest tests/unit/ -q                   # P8 基线 (27 passed)
uv run pytest tests/unit/memory/ -q            # 记忆测试 (P9 Sprint 2 安全网)
ruff check . --select S110,S112,BLE001,E722    # P9 异常吞噬存量
```

> ⚠️ 所有 python 命令必须用 `uv run`（`uv sync --group dev` 后可用）。裸 `python`/`venv/` 无项目依赖。

## 重要注意事项

- **config/.env 里是真实凭证** —— 绝不 `git add`，绝不 `git clean -xdf`
- **`.miya/` 是运行时数据**（database.db/memory/），已加入 .gitignore，绝不提交
- **5 个健康平台不可被改坏** —— OneBot/Telegram/Discord/QQOfficial/Lark
  - ⚠️ 平台现状：仅 OneBot/QQOfficial 有发送方法（send_group_message 等）；Telegram/Discord/Lark **无发送实现**（仅接收），`BasePlatform.send_message` 未被任何平台覆写。`tests/unit/platform/test_send_message_contract.py` 已用「能力现状快照」记录此缺口
- **恢复演练已验证** —— `D:\MiyaBackup\20260726-pre-repair\` 的记忆库与源 2,763 条一致
- **legacy 分支有正确实现** —— 微信/企微发送逻辑在 `legacy/pre-cleanup-snapshot` 分支
- **E 盘不是有效备份目标** —— 与源盘 F 同属 Disk 1，跨物理盘备份只在 D 盘 (Disk 0)

## 环境状态（2026-07-31 校准，已就绪）

- 项目实际 Python **3.11.x**；正确运行方式 `uv run`（hatch build 配置已修复）
- pytest 在 `[dependency-groups] dev`，需 `uv sync --group dev`
- `run/`、`utils/` 已是正规包（`__init__.py`），editable 用 `.pth` 链接源目录，**改源码即时生效**
- `webnet/ToolNet/tools/__init__.py` 已惰性化（不再强制加载全部可选依赖）
- `beautifulsoup4` 已在主依赖
- pytest 收集有个已知 1 error（`_pytest/capture.py` "I/O operation on closed file"，pytest 9.x 自身问题，非项目代码），不影响测试执行

## 遗留 issue（P9 或后续处理）

1. **`core/platforms_config.py` 双轨制** —— 与 `config/platforms_config.py` 是两套 API（`get_default_platforms` vs `get_enabled_platforms`）；仅被 4 个死代码文件引用（`core/dashboard_api.py` / `core/miya_core.py` / `core/miya_system.py` / `core/miya_unified_config.py`，均 0 活跃调用）。`tests/test_config_topology.py::test_only_one_platforms_config` 因此失败。**建议 P9 清理时删除 core 版 + 4 个死消费方，再把 test_config_topology 移入 tests/unit/config/**
2. **平台 `send_message` 统一契约缺失** —— 所有平台均未覆写 `BasePlatform.send_message`；Telegram/Discord/Lark 无发送实现。契约测试已记录现状快照，后续需补齐发送能力
3. **`set_global_audit_logger` 与装饰器单例脱节**（P7.3 后无调用者，仅保留兼容）
