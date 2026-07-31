# P7 — 资源泄漏与并发修复 (2.5 天)

> 分支: fix/v8-hardening
> 前置依赖: P5 已完成 (单事件循环重构)
> 状态: 待执行
> ⚠️ 环境前置（2026-07-31 核实）：本地 `uv run` 默认构建失败（pyproject.toml 缺 `[tool.hatch.build.targets.wheel]`，hatchling 报 "Unable to determine which files to ship"），
>   且裸 `python`（MSYS2 3.12）/ `venv/`（3.11.9）/ uv `.venv`（3.11.14）均无 pytest。执行 P7 前需先修复构建配置（同 P8 Step 0），否则下方验收命令无法运行。

---

## 一、背景

P5 已将 `run/main.py` 重构为单事件循环架构 (`main()` → `asyncio.run(amain())`)，所有异步操作在同一个 loop 内完成。这为 P7 扫清了前提障碍——现在可以在 `amain()` 的 `finally` 块中统一 `await` 各子系统的关闭，而不是在同步 `shutdown()` 中用 `asyncio.create_task` 发后不管。

当前 `Miya.shutdown()` (`run/main.py` 原 807-870 行) 存在以下问题：
1. 不关闭 `httpx.AsyncClient` 实例（`multi_vision_analyzer.py:129`、`webnet/qq/image_handler.py:31`），进程退出时会有 `Unclosed client session` 警告
   > 注（2026-07-31 校准）：`image_handler.py:31` 的 AsyncClient 属实，但所属 `QQNet` 全项目无实例化点（P4 收敛后死结构），运行时不会创建；`multi_vision_analyzer.py` 的 AsyncClient 由 7.1 补齐的 `_global_analyzer.close()` 处理。
2. 不关闭 Neo4j driver、向量库连接、uvicorn server
3. 对 scheduler 的关闭用 `asyncio.create_task`（无引用持有，可能被 GC）
4. 90+ 个全局单例无锁保护，而 uvicorn 在独立线程跑

P5 已新增 `async def ashutdown()` 方法，但当前实现只覆盖了 6 个子系统（scheduler/decision_hub/mlink/memory_net/ai_client/redis），需要补齐。

---

## 二、执行步骤

### 7.1 补齐 `Miya.ashutdown()` 关闭链 (~1d)

**文件**: `run/main.py` (Miya 类的 `ashutdown` 方法)

> ⚠️ **校准说明（2026-07-31 逐项核实）**：原计划引用的部分路径/属性/方法名在 P3 死代码清理后已不存在。
> 以下为基于当前代码核实的真实关闭链（codegraph + grep 确认，非猜测）。

**现状**：`ashutdown()`（`run/main.py:807`）现有 6 项关闭（scheduler/decision_hub/mlink/memory_net/ai_client/redis），
其中 **MemoryNet 无 `close()` 方法是空操作**（`hasattr` 保护静默跳过）。

**需要补齐的关闭目标（按真实代码核实）**：

| 子系统 | 真实持有位置 | 真实关闭方式 | 说明 |
|---|---|---|---|
| 多模态分析器 | 模块级 `_global_analyzer`（`core/multi_vision_analyzer.py`，由 `get_vision_analyzer()` 惰性创建，1055 行） | `if _global_analyzer: await _global_analyzer.close()` | **Miya 类无 `self.multi_vision_analyzer` 属性**；onebot_platform 通过 `get_vision_analyzer()` 使用。`close()` 在 1045 行 |
| Neo4j driver | `self.grag_memory`（`GRAGMemoryManager.get_instance()` 单例，`core/grag_memory.py:55`） | `await self.grag_memory.close()` | `close()` 在 `core/grag_memory.py:447`，内部关 `self._neo4j_driver`（用 `asyncio.to_thread`，属性名是 `_neo4j_driver` 非 `driver`） |
| MemoryNet 内部资源 | `self.memory_net`（`webnet/memory.py` 的 `MemoryNet`，无 `close()`） | memory 层后端各自 `close()` | 真实后端关闭点：`memory/core.py:347`、`memory/sqlite_backend.py:408`、`memory/real_vector_cache.py:190`。文档原说的 `self.memory_net.vector_store` 不存在 |
| Uvicorn server | `_start_api_server`（`run/main.py:557`）：`uvicorn.run()` 在 `threading.Thread(daemon=False)`（631 行）阻塞 | **需改造**：改用 `uvicorn.Server(config)`，保存 `self._uvicorn_server` + `self._server_thread`；关闭时 `server.should_exit = True` + `thread.join(timeout=5)` | 当前 `uvicorn.run()` 无 server 实例可引用，`self.web_api._server` 不存在；且**非 daemon 线程会阻止进程退出**（主线程结束等待它），必须处理 |

**明确不需要关闭（原计划误列，移除）**：

| 原计划项 | 核实结论 |
|---|---|
| WebNet/NetManager（原引 `webnet/net_manager.py` 的 `shutdown()`） | NetManager 是纯注册表（register/get/stats，`webnet/net_manager.py:22`），无连接/任务/文件句柄；WebNet（`webnet/webnet.py:241`）用 `sqlite3.connect()` 每次操作即开即关。**无资源泄漏，不做** |
| QQ 图片处理器（原引 `self.web_net.image_handler` 的 `close()`） | `image_handler` 属于 `webnet/qq/core.py:76` 的 **`QQNet`** 类；`QQNet(` **全项目无实例化点**（P4 收敛后死结构，QQ 由 unified_platform 的 QQOfficialPlatform 接管）。若未来启用需调 `cleanup()`（`image_handler.py:348`，async，非 `close()`）。**当前不处理** |

**实现要点**:
```python
async def ashutdown(self) -> None:
    """异步关闭系统"""
    self.logger.info("弥娅系统正在关闭...")
    
    # 每个子系统包在 asyncio.wait_for(timeout=10) 里防止挂死
    async def _safe_close(name, close_fn):
        try:
            await asyncio.wait_for(close_fn(), timeout=10)
            self.logger.debug(f"{name} 已关闭")
        except asyncio.TimeoutError:
            self.logger.warning(f"{name} 关闭超时")
        except Exception as e:
            self.logger.debug(f"{name} 关闭失败: {e}")
    
    # 1-6. 现有子系统（scheduler/decision_hub/mlink/memory_net/ai_client/redis）...
    #       ⚠️ memory_net 当前无 close() 是空操作，需按真实链补：
    #           memory/core.py close() + memory/sqlite_backend.py close() + memory/real_vector_cache.py close()
    # 7. 多模态分析器：模块级 _global_analyzer（get_vision_analyzer() 惰性创建）
    # 8. Neo4j：await self.grag_memory.close()（core/grag_memory.py:447）
    # 9. Uvicorn：改造后 server.should_exit = True + thread.join(timeout=5)
    # 原计划误列的 WebNet（纯注册表）/ 图片处理器（QQNet 无实例化点）经核实无资源，不关闭
```

**验证**:
```bash
python -X dev -W error::ResourceWarning -c "
import asyncio, run.main
async def t(): 
    m = run.main.Miya()
    await m.ashutdown()
asyncio.run(t())
" 2>&1 | grep -i "unclosed\|ResourceWarning"
# 期望: 无输出
```

### 7.2 `asyncio.create_task` 引用持有 (~0.5d)

**工具**: `ruff check . --select RUF006` 定位 fire-and-forget 任务

**通用模式**: 类里维护 `self._tasks: set[asyncio.Task]`，创建任务后 `task.add_done_callback(self._tasks.discard)`。

**优先处理目录**: `run/`、`core/unified_platform_impl/`、`hub/`

> **实际清单（2026-07-31 `ruff check run/ core/unified_platform_impl/ --select RUF006`，共 10 处）**：
> - `core/unified_platform_impl/message_mixin.py:294,296` — `asyncio.ensure_future` ×2
> - `core/unified_platform_impl/onebot_platform.py:598,601,628,658,704,744` — `asyncio.ensure_future` ×6
> - `core/unified_platform_impl/webhook_platforms.py:62` — `asyncio.create_task` ×1
> - `run/main.py:860` — `asyncio.create_task` ×1（旧的同步 `shutdown()` 里 fire-and-forget scheduler.stop）

```python
# 在 __init__ 中:
self._tasks: set[asyncio.Task] = set()

# 创建后台任务时:
task = asyncio.create_task(some_coro())
self._tasks.add(task)
task.add_done_callback(self._tasks.discard)

# 在 ashutdown 中:
for task in list(self._tasks):
    task.cancel()
```

### 7.3 全局单例线程安全 (~1d)

**核心判断**: 不做依赖注入（90+ 单例的重构代价太大）。改为装饰器加锁。

**新增文件**: `utils/singleton.py` (~60 行)

```python
import functools, threading

_SYNC_LOCK = threading.RLock()

def sync_singleton(fn):
    """同步单例工厂 —— 不改 get_xxx() 调用签名"""
    cell = {}
    @functools.wraps(fn)
    def wrapper(*a, **kw):
        if "v" in cell:
            return cell["v"]
        with _SYNC_LOCK:
            if "v" not in cell:
                cell["v"] = fn(*a, **kw)
            return cell["v"]
    wrapper.reset = lambda: cell.clear()  # 测试专用
    return wrapper


def async_singleton(fn):
    """异步单例工厂 —— 按 event loop 分桶防止跨 loop 错误"""
    cells, locks = {}, {}
    @functools.wraps(fn)
    async def wrapper(*a, **kw):
        import asyncio
        loop = asyncio.get_running_loop()
        if loop in cells:
            return cells[loop]
        lk = locks.setdefault(loop, asyncio.Lock())
        async with lk:
            if loop not in cells:
                cells[loop] = await fn(*a, **kw)
            return cells[loop]
    wrapper.reset = lambda: (cells.clear(), locks.clear())
    return wrapper
```

**一级优先（跨线程使用，12 个）** — `run/main.py:631` 起了独立线程跑 uvicorn：

> ⚠️ **校准说明（2026-07-31 核实）**：原清单 2 个函数名/路径错误，已按实际代码修正（`get_audit_logger` → `get_global_audit_logger`；`get_rate_limiter`/`rate_limiter.py` → `get_global_security_service`/`security_service.py`）。

| 单例 | 文件 | 装饰器 |
|---|---|---|
| `get_registry()` | `core/unified_platform/registry.py:227` | `@sync_singleton` |
| `get_gestalt_controller()` | `core/gestalt_controller.py` | `@sync_singleton` |
| `_config_cache` | `core/system_config.py:13` | inline lock |
| `get_model_pool()` | `core/model_pool_manager.py:468` | `@sync_singleton` |
| `get_embedding_client()` | `core/embedding_client.py` | `@sync_singleton` |
| `get_unified_memory()` | `memory/unified_memory.py:84` | `@sync_singleton` |
| `get_log_broker()` | `core/log_broker.py` | `@sync_singleton` |
| `get_event_bus()` | `core/event_system.py:326` | `@sync_singleton` |
| `get_message_queue()` | `core/message_queue.py:423` | `@sync_singleton` |
| `get_cache_manager()` | `core/cache_manager.py` | `@sync_singleton` |
| `get_global_audit_logger()` | `core/audit_logger.py:549` | `@sync_singleton` |
| `get_global_security_service()` | `core/security_service.py:413`（RateLimiter 是其内部类，259 行） | `@sync_singleton` |

每个改造 3 分钟：删 `global _x / if _x is None` 三行，加 `@sync_singleton` 装饰器。

**不要做的事**:
- 不要用 `functools.lru_cache`（unhashable 参数会炸，无 reset 语义）
- 不要用 `threading.local`（每线程一个实例 = 正好是 bug）
- 不要顺手给单例加 `reset()` 调用点

---

## 三、验收标准

```bash
# 1. 无资源泄漏警告
python -X dev -W error::ResourceWarning run/main.py < /dev/null 2>&1 | grep -ci unclosed
# 期望: 0

# 2. shutdown 日志含全部组件
python -c "..." 2>&1 | grep -c "已关闭"
# 期望: ≥ 9（现有 6 项 + 7.1 新增 3 项：多模态分析器 / Neo4j / Uvicorn；memory 层补 close 后可能更多）

# 3. ruff RUF006 在热点目录清零
ruff check run/ core/unified_platform_impl/ --select RUF006
# 期望: 无输出

# 4. smoke 5/5 仍通过
python scripts/smoke_test.py --fast

# 5. 单例测试
python -c "
import threading, utils.singleton as S
@S.sync_singleton
def f(): return object()
results = []
def worker(): results.append(id(f()))
ts = [threading.Thread(target=worker) for _ in range(32)]
[t.start() for t in ts]; [t.join() for t in ts]
assert len(set(results)) == 1, f'got {len(set(results))} instances'
print('OK: single instance across 32 threads')
"
```

---

## 四、风险与缓解

| 风险 | 缓解 |
|---|---|
| shutdown 顺序错导致关闭挂死 | 每个 `_close` 包 `asyncio.wait_for(timeout=10)` |
| `@sync_singleton` 装饰器引入死锁 | RLock 可重入 + 只在构造时锁，热路径无锁 |
| 在单例初始化中调用另一个单例 → 循环依赖 | 观察启动日志，若出现递归锁等 warning 则改为惰性初始化 |
