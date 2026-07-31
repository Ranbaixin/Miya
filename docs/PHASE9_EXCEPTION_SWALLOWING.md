# P9 — 异常吞噬治理 (5.5 天)

> 分支: fix/v8-hardening
> 前置依赖: P8 已完成 (测试安全网就位)
> 状态: 待执行

---

## 一、背景

项目当前有 ~165 处异常吞噬（`except Exception: pass` / 裸 `except:` 及各种静默降级），分布在：

| 目录 | 数量 |
|---|---|
| core | 119 (60 个文件) |
| webnet | 23 (17 个文件) |
| memory | 12 (4 个文件) |
| hub | 11 (2 个文件) |

**核心洞察：工具已经在 pyproject.toml 里了，只是被关掉了。**

`pyproject.toml` 已 `select = ["E","F","W","I","N","UP","B","SIM"]`，但：
- `E722`（裸 except）被塞进 `extend-ignore`
- `S110`（try-except-pass）/ `BLE001`（盲 Exception）未 select

---

## 二、治理规则 (三级分类)

| 级 | 判定 | 处置 |
|---|---|---|
| **Level 1: 必须上抛** | 数据写入、消息发送、配置加载、权限判定 | `logger.exception()` + `raise` |
| **Level 2: 记日志即可** | 可选功能降级（TTS、表情包、Live2D） | `logger.warning(..., exc_info=True)` |
| **Level 3: 确实可吞** | 清理路径、best-effort 通知 | 加 `# noqa: S110 — <理由>` |

---

## 三、最危险的 10 处（Level 1，优先处理）

这些是 P9 的第一批目标——P8 的记忆读写测试就位后立即处理。

| # | 文件:行 | 问题 | 处置 |
|---|---|---|---|
| 1 | `memory/core.py` ~2006 | 记忆衰减写盘失败被双层 `except: pass` 吞 | `logger.error` + `raise` |
| 2 | `memory/core.py` ~1892 | 归档写盘失败被吞但仍计数成功 | `logger.error` + `raise` |
| 3 | `memory/core.py` ~707, ~1649 | 裸 `except:` 导致记忆被错误过滤 | `except (TypeError, ValueError)` 精确捕获 |
| 4 | `miya_api.py` ~949 | 会话列表 `json.load` 失败被吞 | `logger.exception` + 返回 500 |
| 5 | `message_mixin.py` ~111 | `handle_session_end` 失败被吞 | `logger.error` + `raise` |
| 6 | `message_mixin.py` ~124 | `lifebook.record_interaction` 失败被吞 | `logger.warning`（可选功能降级） |
| 7 | `hub/decision_hub.py` ~1557 | 灵魂模型客户端创建失败被吞 | `logger.error` + `raise` |
| 8 | `core/proactive_chat.py` ~634 | 主动聊天配置加载失败被吞 | `logger.error` + `raise` |
| 9 | `miya_api.py` ~1071 | 会话重命名/删除假成功 | 检查返回值，失败返回 4xx |
| 10 | `miya_api.py` ~2680 | 三个裸 `except:` 伪装"状态正常" | 已在 P6 修复 |

---

## 四、执行节奏（4 个 Sprint）

### Sprint 1: 止血 —— ruff baseline 模式 (~1d)

**目标**: 存量豁免，新增为 0。

1. 从 `pyproject.toml` 的 `extend-ignore` 中移除 `E722`
2. 添加 `"S110", "S112", "BLE001"` 到 `select`
3. 为当前存量创建 `per-file-ignores` 豁免表（用 baseline 命令生成）
4. CI 加 `invariants` job：`ruff check . --select S110,S112,BLE001,E722 --diff`（只检查 diff 中的新增）

```toml
[tool.ruff.lint.per-file-ignores]
# Sprint 2-4 逐批摘除这些豁免
"memory/core.py" = ["S110", "BLE001"]
"hub/decision_hub.py" = ["S110", "BLE001"]
"core/web_api/miya_api.py" = ["E722", "S110"]
# ... (所有当前包含异常吞噬的文件)
```

### Sprint 2: memory/ + core/unified_platform_impl/ (~1.5d)

**前提**: P8 的 `tests/unit/memory/` 测试已就位

逐文件：读 → 理解每个 `except` 的意图 → 对 Level 1 改 `raise` → 跑 `tests/unit/memory/` 确认不回归 → 从 `per-file-ignores` 摘除该文件

**顺序**: `memory/core.py` → `core/unified_platform_impl/message_mixin.py` → `core/unified_platform_impl/onebot_platform.py`

### Sprint 3: hub/ + webnet/ (~1.5d)

同上流程，但 `hub/decision_hub.py` 和 `webnet/` 下的异常很多是可选功能降级（Level 2），大规模改 raise 风险高。优先处理 Level 1，其余加日志。

### Sprint 4: core/ 其余 (~1.5d)

按文件大小和引用频率排序，优先处理高频调用文件。对于确认为 Level 3 的（清理路径、`__del__`），只加注释，不改行为。

---

## 五、辅助工具

### `scripts/scan_swallowed_exceptions.py`（P9 Sprint 1 创建）

AST 评分脚本：`try` 块内是否有写操作/网络调用/权限判定 → 高危分。

```bash
python scripts/scan_swallowed_exceptions.py --min-score 8
# 期望 (Sprint 4 末): 输出为空
```

设计:
- 写操作模式: `await.*\.(save|write|store|insert|update|delete|flush)` → +5 分
- 网络调用: `aiohttp|httpx|requests|urllib` → +3 分
- 权限/安全: `permission|auth|token|credential` → +4 分
- 空 `pass` 块: → +2 分
- 裸 `except:`: → +2 分
- 总分 ≥ 8 → 打印文件:行 + 上下文

---

## 六、验收标准

```bash
# Sprint 1
ruff check . --select S110,S112,BLE001,E722
# 期望: 有输出但全部来自 per-file-ignores 豁免

# Sprint 2
ruff check memory/ core/unified_platform_impl/ --select S110,S112,BLE001,E722
# 期望: 无输出
pytest tests/unit/memory/ -q
# 期望: 全部仍绿

# Sprint 4
python scripts/scan_swallowed_exceptions.py --min-score 8
# 期望: 空
pytest tests/unit/ -q
# 期望: P8 的 15+ 测试全部仍绿
```

---

## 七、风险与缓解

| 风险 | 缓解 |
|---|---|
| `pass` → `raise` 让原本静默降级的路径开始崩溃 | 1. 必须在 P8 之后 2. Sprint 1 先止住新增 3. 优先动有测试覆盖的模块 4. 每批独立 commit |
| 对 Level 2 改 `raise` 导致可选功能崩溃影响主流程 | Level 2 只加日志，不改 raise |
| `per-file-ignores` 表维护成本高 | 只有 Sprint 1 建表时一次性全量生成，之后只减不增 |
