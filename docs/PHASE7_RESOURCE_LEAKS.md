# P7 — 资源泄漏与并发修复 (2.5 天)

> 分支: fix/v8-hardening
> 前置依赖: P5 已完成 (单事件循环重构)
> 状态: 待执行

---

## 一、背景

P5 已将 `run/main.py` 重构为单事件循环架构 (`main()` → `asyncio.run(amain())`)，所有异步操作在同一个 loop 内完成。这为 P7 扫清了前提障碍——现在可以在 `amain()` 的 `finally` 块中统一 `await` 各子系统的关闭，而不是在同步 `shutdown()` 中用 `asyncio.create_task` 发后不管。

当前 `Miya.shutdown()` (`run/main.py` 原 807-870 行) 存在以下问题：
1. 不关闭 `httpx.AsyncClient` 实例（`multi_vision_analyzer.py:129`、`webnet/qq/image_handler.py:31`），进程退出时会有 `Unclosed client session` 警告
2. 不关闭 Neo4j driver、向量库连接、uvicorn server
3. 对 scheduler 的关闭用 `asyncio.create_task`（无引用持有，可能被 GC）
4. 90+ 个全局单例无锁保护，而 uvicorn 在独立线程跑

P5 已新增 `async def ashutdown()` 方法，但当前实现只覆盖了 6 个子系统（scheduler/decision_hub/mlink/memory_net/ai_client/redis），需要补齐。

---

## 二、执行步骤

### 7.1 补齐 `Miya.ashutdown()` 关闭链 (~1d)

**文件**: `run/main.py` (Miya 类的 `ashutdown` 方法)

需要新增关闭以下子系统：

| 子系统 | 实例属性 | close/shutdown 方法位置 |
|---|---|---|
| WebNet（蛛网管理器） | `self.net_manager` | `webnet/net_manager.py` 的 `shutdown()` |
| QQ 图片处理器 | `self.web_net.image_handler` | `webnet/qq/image_handler.py:351` 的 `close()` |
| 多模态分析器 | `self.multi_vision_analyzer` | `core/multi_vision_analyzer.py:1045` 的 `close()` |
| Neo4j driver | `self.grag_memory` | `core/grag_memory.py` 的 driver.close() |
| 向量库 | `self.memory_net.vector_store` | 取决于后端实现 |
| Uvicorn server | `self.web_api._server` | `server.should_exit = True` |

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
    
    # 1-6. 现有子系统... 
    # 7. WebNet
    # 8. 图片处理器
    # 9. 多模态分析器
    # 10. Neo4j
    # 11. 向量库
    # 12. Uvicorn
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

**一级优先（跨线程使用，12 个）** — `run/main.py:632` 起了独立线程跑 uvicorn：

| 单例 | 文件 | 装饰器 |
|---|---|---|
| `get_registry()` | `core/unified_platform/registry.py` | `@sync_singleton` |
| `get_gestalt_controller()` | `core/gestalt_controller.py` | `@sync_singleton` |
| `_config_cache` | `core/system_config.py` | inline lock |
| `get_model_pool()` | `core/model_pool_manager.py` | `@sync_singleton` |
| `get_embedding_client()` | `core/embedding_client.py` | `@sync_singleton` |
| memory 访问器 | `memory/unified_memory.py` | `@sync_singleton` |
| `get_log_broker()` | `core/log_broker.py` | `@sync_singleton` |
| `get_event_bus()` | `core/event_system.py` | `@sync_singleton` |
| `get_message_queue()` | `core/message_queue.py` | `@sync_singleton` |
| `get_cache_manager()` | `core/cache_manager.py` | `@sync_singleton` |
| `get_audit_logger()` | `core/audit_logger.py` | `@sync_singleton` |
| `get_rate_limiter()` | `core/rate_limiter.py` | `@sync_singleton` |

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
# 期望: ≥ 12

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
