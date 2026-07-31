"""记忆测试共享 fixture（P8 Step2）。"""
import shutil
import tempfile

import pytest

from memory.core import MiyaMemoryCore


@pytest.fixture
async def memory_core():
    """基于临时目录的 MiyaMemoryCore 实例，测试结束自动 close + 清理。"""
    tmp = tempfile.mkdtemp()
    core = MiyaMemoryCore(tmp, enable_backup=False)
    await core.initialize(lazy_load=True)
    yield core
    try:
        await core.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
