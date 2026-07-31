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

### P9 — 异常吞噬治理 ✅（2026-07-31 完成，4 个 Sprint 独立提交）

**治理结果**：memory/、core/unified_platform_impl/、hub/、webnet/、core/ 共
**280+ 文件、约 1600 处** S110/S112/BLE001/E722 违规清零，全部从 per-file-ignores
豁免表摘除。豁免表仅剩范围外目录（scripts/mcpserver/tests/plugins/utils/config/
setup/run/examples）的 57 条历史条目（之后只减不增）。

**提交**：
- `cdd785d2` Sprint 1 止血：ruff 规则激活 + 豁免表 + CI invariants gate + 2 处语法错误修复
- `9ea9a0eb` Sprint 2：memory/ + unified_platform_impl/（含计划 #1/#2/#3 改 raise）
- `ae8e146c` Sprint 3：hub/ + webnet/（保守策略，0 处新增 raise）
- `8e0ba05a` Sprint 4：core/ 其余 + `scripts/scan_swallowed_exceptions.py`

**关键修复（被吞异常隐藏的 bug）**：
- `core/web_api/miya_api.py` 缺 `from pathlib import Path` 导致 NameError 被宽 except
  吞掉 → 168 条路由从未挂载。已修复并验证
- `core/web_api/auth.py` 权限校验异常静默放行（fail-open）→ 改为 401 拒绝
- `core/web_api/miya_api.py` 会话创建/删除/重命名假成功（计划 #9）→ 检查持久化结果
- `skills/marketplace.py` 写盘失败改 logger.exception + raise（Level 1）

**验收**：`ruff check . --select S110,S112,BLE001,E722` 全绿（仅剩豁免）；
`scan_swallowed_exceptions.py --min-score 8` 输出为空；`pytest tests/unit/` 27 passed；
smoke 5/5；import_graph exit 0。

**遗留 issue（P9 或后续处理，本次未做）**：
1. `core/platforms_config.py` 双轨制 —— 与 `config/platforms_config.py` 两套 API；
   仅被 4 个死代码文件引用。建议删除 core 版 + 4 死消费方，移 test_config_topology 进 tests/unit/config/
2. 平台 `send_message` 统一契约缺失 —— 契约测试已记录现状快照
3. `set_global_audit_logger` 与装饰器单例脱节（仅保留兼容）
4. 范围外目录 57 条豁免（scripts/mcpserver/tests/plugins/utils/config/setup/run/examples）
   若后续收紧规则需逐目录治理
## 关键命令

```bash
cd F:\Ranxin\Miya
git switch fix/v8-hardening

uv run python scripts/smoke_test.py --fast     # 快速验证 (5/5 必须通过)
uv run python scripts/import_graph.py --check  # 静态可达性 (exit 0 必须通过)
uv run pytest tests/unit/ -q                   # P8 基线 (27 passed)
uv run pytest tests/unit/memory/ -q            # 记忆测试 (P9 Sprint 2 安全网)
ruff check . --select S110,S112,BLE001,E722    # P9 后应全绿（仅剩范围外豁免）
uv run python scripts/scan_swallowed_exceptions.py --min-score 8   # P9 危险站点扫描（应为空）
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

