# Miya v8.1 完善计划 — 新对话提示词

> 复制以下全部内容，在新 Claude Code 会话中粘贴。

---

## 项目上下文

你正在维护 **弥娅 (Miya) v8.1** —— 一个拥有独立人格、记忆与情感的 AI 虚拟化身系统。
项目位于 `F:\Ranxin\Miya`，Python 3.13，当前分支 `fix/v8-hardening`。

## 已完成（不要重复做）

以下 P-1 到 P6、P10 已在 `fix/v8-hardening` 分支完成（12 个提交，smoke 全部通过）：

- **P-1**: 三层备份（`D:\MiyaBackup\20260726-pre-repair\` 2.6GB 跨物理盘 + E 盘副本 + GitHub 8 分支 1 标签）
- **P0**: 安全网 —— `scripts/import_graph.py`（静态可达性检查）+ `scripts/smoke_test.py`（8 级冒烟）+ CI/Makefile 修复
- **P1**: 安全止血 —— `check_permission` fail-closed + `_safe_execution` 阻止 + 9 处 D 盘硬编码消除
- **P2**: 依赖修复 —— aiocqhttp/pywin32/croniter/jieba/pytest-asyncio 补齐 + 测试收集 66 items
- **P3**: 死代码清理 8 批次 —— 删除 astrbot/ 三重复制和替代架构等约 15 万行，`core/` 从 181K 降到 76K 行
- **P4**: 平台收敛 —— 下线 7 个从不回复的平台，保留 6 个健康平台
- **P5**: 终端模式修复 —— `main()` → `asyncio.run(amain())` 单事件循环重构，6 个问题一次修完
- **P6**: 假实现处置 —— 向量写入改为抛异常（不再返回 mock_xxx 伪装成功）+ 假统计修复
- **P10**: 文档对齐 —— README 修正、FIX_LOG 失效声明

## 待完成（本次会话目标）

### P7 — 资源泄漏与并发修复 (详见 `docs/PHASE7_RESOURCE_LEAKS.md`)
- 7.1: 补齐 `Miya.ashutdown()` 关闭链（WebNet/图片处理器/多模态分析器/Neo4j/向量库/Uvicorn）
- 7.2: `asyncio.create_task` 引用持有（RUF006）
- 7.3: 新增 `utils/singleton.py` → 12 个一级单例加 `@sync_singleton`

### P8 — 测试基建重建 (详见 `docs/PHASE8_TEST_INFRA.md`)
- Step 1: 建立 `tests/unit/{memory,platform,config,permission}/` 目录结构
- Step 2: 记忆读写测试 (`test_store_query.py` + `test_concurrent.py`，6 个核心操作)
- Step 3: 平台发送契约测试
- Step 4: 权限 fail-closed 测试
- Step 5: CI 验证（真的会红）

### P9 — 异常吞噬治理 (详见 `docs/PHASE9_EXCEPTION_SWALLOWING.md`)
- Sprint 1: ruff baseline 模式止血（存量豁免，新增为 0）
- Sprint 2: memory/ + core/unified_platform_impl/ 逐文件改 raise
- Sprint 3: hub/ + webnet/
- Sprint 4: core/ 其余 + 新建 `scripts/scan_swallowed_exceptions.py`

## 关键命令

```bash
cd F:\Ranxin\Miya
git switch fix/v8-hardening
python scripts/smoke_test.py --fast    # 快速验证 (5/5 必须通过)
python scripts/import_graph.py --check # 静态可达性 (exit 0 必须通过)
```

## 重要注意事项

- **config/.env 里是真实凭证** —— 绝不 `git add`，绝不 `git clean -xdf`
- **5 个健康平台不可被改坏** —— OneBot/Telegram/Discord/QQOfficial/Lark
- **恢复演练已验证** —— `D:\MiyaBackup\20260726-pre-repair\` 的记忆库与源 2,763 条一致
- **legacy 分支有正确实现** —— 微信/企微发送逻辑在 `legacy/pre-cleanup-snapshot` 分支
- **E 盘不是有效备份目标** —— 与源盘 F 同属 Disk 1 (Samsung 970 EVO Plus)，跨物理盘的备份只在 D 盘 (Disk 0)
