# P8 — 测试基建重建 (3.5 天)

> 分支: fix/v8-hardening
> 前置依赖: P5 (单loop) + P4 (平台收敛) + P3 (死代码已删)
> 状态: 待执行

---

## 一、背景

当前状态:
- pytest 收集 66 items，但实际执行 0（pytest-asyncio 已装、conftest fixture 已修）
- 13 个脚本风格测试已隔离到 `collect_ignore_glob`
- CI 中 `tests/unit/` 路径已修正、`|| echo` 吞失败已移除
- **缺少可信的回归测试基线** — 这是 P9（异常吞噬改 raise）的安全网

P8 的目标不是"写 1000 个测试"，而是**建立一条可信的回归基线**，让 P9 把 `pass` 改 `raise` 时有安全网。

---

## 二、目标测试目录结构

```
tests/
├── unit/                    # 纯逻辑, 无 I/O, <60s
│   ├── memory/              # 记忆读写 (回归风险 #1)
│   │   ├── test_store_query.py
│   │   ├── test_concurrent.py
│   │   └── test_archive_decay.py
│   ├── platform/            # 平台回复发送 (回归风险 #2)
│   │   └── test_send_message_contract.py
│   ├── config/              # 配置加载 + 拓扑冻结 (回归风险 #3)
│   │   └── test_config_topology.py  (已创建)
│   └── permission/          # 权限 fail-closed
│       └── test_check_permission.py
├── integration/             # 需要真实文件/DB
├── legacy/                  # 13 个脚本风格测试 (collect_ignore_glob)
└── conftest.py
```

---

## 三、执行步骤

### Step 1: 建立测试目录与基础配置 (~0.5d)

```bash
mkdir -p tests/unit/memory tests/unit/platform tests/unit/config tests/unit/permission
touch tests/unit/__init__.py tests/unit/memory/__init__.py tests/unit/platform/__init__.py
```

`pyproject.toml` 配置（当前已部分完成）:
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests/unit"]
addopts = ["-v", "--tb=short"]
```

### Step 2: 记忆读写测试 (~1.5d) — 最高优先级

**目标**: 覆盖 `memory/core.py` 的 store/query/update/delete/归档/衰减 6 个核心操作。

**文件**: `tests/unit/memory/test_store_query.py`

```python
"""记忆核心读写测试 —— P9 异常吞噬治理的安全网。"""
import pytest
import tempfile, os, json
from pathlib import Path

@pytest.fixture
def memory_backend():
    """基于临时 JSON 文件的 MiyaMemoryCore 实例。"""
    # 用临时目录隔离测试，避免污染真实记忆数据
    tmp = tempfile.mkdtemp()
    config = {
        "backend": "json",
        "json_path": os.path.join(tmp, "test_memory.json"),
        "index_path": os.path.join(tmp, "test_index.json"),
    }
    # 初始化 core...
    yield core
    import shutil
    shutil.rmtree(tmp)

@pytest.mark.asyncio
async def test_store_and_retrieve(memory_backend):
    """写入一条记忆 → 按 key 查询 → 内容一致"""
    ...

@pytest.mark.asyncio
async def test_update_preserves_id(memory_backend):
    """更新记忆 → ID 不变、内容变"""
    ...

@pytest.mark.asyncio
async def test_delete_removes_from_index(memory_backend):
    """删除 → 索引不再包含 → 查询返回空"""
    ...

@pytest.mark.asyncio
async def test_archive_flags(memory_backend):
    """归档 → is_archived=True → 普通查询不返回"""
    ...

@pytest.mark.asyncio
async def test_decay_updates_priority(memory_backend):
    """衰减 → priority 降低 → 低优先级记忆排在后面"""
    ...

@pytest.mark.asyncio
async def test_concurrent_writes_no_corruption(memory_backend):
    """10 并发写入 → 索引完整 → 所有 key 可读出"""
    ...
```

**文件**: `tests/unit/memory/test_concurrent.py`

```python
"""记忆并发写入测试 —— 验证 load() 加锁 (P3 batch 3 修复) 不退化。"""
@pytest.mark.asyncio
async def test_concurrent_read_write():
    """同时读写 → 不丢数据, 不损坏索引"""
    ...

@pytest.mark.asyncio
async def test_expire_lock():
    """后台衰减 + 手动写入并发 → 不冲突"""
    ...
```

### Step 3: 平台回复发送契约测试 (~0.5d)

**文件**: `tests/unit/platform/test_send_message_contract.py`

```python
"""平台发送契约: 每个健康平台必须有 send_message 实现且不返回默认 False。"""
import pytest
from core.unified_platform.base import BasePlatform
from core.unified_platform_impl import (
    OneBotPlatform, TelegramPlatform, DiscordPlatform,
    QQOfficialPlatform, LarkPlatform
)

HEALTHY_PLATFORMS = [OneBotPlatform, TelegramPlatform, DiscordPlatform,
                      QQOfficialPlatform, LarkPlatform]

@pytest.mark.parametrize("cls", HEALTHY_PLATFORMS)
def test_send_message_is_overridden(cls):
    """send_message 必须被覆写，不能是基类的默认 False。"""
    assert cls.send_message is not BasePlatform.send_message, \
        f"{cls.__name__}.send_message 未覆写"

@pytest.mark.asyncio
async def test_route_to_decision_hub_returns_str_or_none():
    """route_to_decision_hub 返回值类型合规。"""
    from core.unified_platform_impl.message_mixin import MessageMixin
    # 用 mock subclass 测试...
```

### Step 4: 权限 fail-closed 测试 (~0.5d)

**文件**: `tests/unit/permission/test_check_permission.py`

```python
"""权限检查 fail-closed 回归测试 (P1 修复)。"""
import json, pytest
from webnet.ToolNet.tools.auth.check_permission import CheckPermissionTool

@pytest.mark.asyncio
async def test_check_permission_denies_unknown_user():
    result = json.loads(await CheckPermissionTool().execute(
        {"user_id": "qq_nonexistent", "permission": "tool.web_search"}, {}
    ))
    assert result["allowed"] == False

@pytest.mark.asyncio
async def test_check_permission_returns_structured_error():
    result = json.loads(await CheckPermissionTool().execute(
        {"user_id": "qq_123", "permission": "agent.execute"}, {}
    ))
    assert "error" in result
    assert result["error"] == "permission_check_unavailable"
```

### Step 5: CI 验证 (~0.5d)

```bash
# 1. 单元测试能跑
pytest tests/unit/ -q                     # ≥15 passed, 0 failed, <60s

# 2. Makefile 可用
make test                                  # exit 0

# 3. CI 真的会红 (故意引入一个 bug)
echo "assert False" >> tests/unit/memory/test_store_query.py
git push
# → GitHub Actions unit-tests job 必须变红

# 4. 恢复
git checkout -- tests/unit/memory/test_store_query.py
```

---

## 四、验收标准

```bash
# 1. 测试可执行
pytest tests/unit/ -q
# 期望: ≥15 passed, 0 failed, <60s

# 2. Makefile
make test
# 期望: exit 0

# 3. CI 不再永远绿
grep -c "|| true\||| echo" .github/workflows/ci.yml
# 期望: 0

# 4. 覆盖率基线存档
pytest tests/unit/ --cov=memory --cov=core/unified_platform_impl --cov-report=term
# 存到 .baseline-coverage.txt
```

---

## 五、本阶段不做的

| 不做 | 理由 |
|---|---|
| 迁移 13 个脚本风格测试 | 用 `collect_ignore_glob` 隔离，改哪补哪 |
| 写 100+ 测试覆盖所有模块 | 不是目标——先建立"可信基线" |
| 修新测试暴露的既有 bug | 记 issue 不当场修，否则本阶段会无限延长 |
