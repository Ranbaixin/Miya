"""记忆健康测试（2026-08 第三轮修复验收）。

覆盖：
- 会话 key 新旧兼容（_session_ids_for 回退）
- 群聊主动发言记忆不落 user_id=0（归群桶）
- get_statistics 磁盘口径（冷启动 by_level 非 0）
"""

import shutil
import tempfile

import pytest

from memory.core import MiyaMemoryCore


# ==================== 会话 key 兼容 ====================

def test_session_ids_for_new_and_old_keys():
    from hub.decision_hub import DecisionHub

    # 群聊：新 key 含群+用户，旧 key 为 platform_user
    keys = DecisionHub._session_ids_for("aiocqhttp", "123", "829150461")
    assert keys[0] == "aiocqhttp_g829150461_u123"
    assert keys[1] == "aiocqhttp_123"

    # 私聊：新 key 带 private_ 前缀，旧 key 为 platform_user
    keys2 = DecisionHub._session_ids_for("aiocqhttp", "123", 0)
    assert keys2[0] == "aiocqhttp_private_123"
    assert keys2[1] == "aiocqhttp_123"

    # proactive 群聊（无 user_id）：仅群桶 key
    keys3 = DecisionHub._session_ids_for("aiocqhttp", "", "829150461")
    assert keys3 == ["aiocqhttp_g829150461"]


# ==================== 群聊主动发言归群桶 ====================

async def test_store_unified_memory_group_no_zero_user(monkeypatch):
    """P1 修复：群聊主动发言（无 user_id）不再产生 user_id='0' 的记忆。"""
    import hub.memory_manager as mm

    calls = {}

    async def fake_store_dialogue(**kw):
        calls.update(kw)

    async def fake_analyze(**kw):
        return None

    monkeypatch.setattr(mm, "store_dialogue", fake_store_dialogue)
    mgr = mm.MemoryManager(memory_net=None, memory_engine=None)
    monkeypatch.setattr(mgr, "_analyze_and_upgrade_assistant_memory", fake_analyze)

    await mgr.store_unified_memory(
        {
            "platform": "aiocqhttp",
            "user_id": "",
            "group_id": "829150461",
            "message_type": "group",
            "response": "大家好呀",
        },
        role="assistant",
    )
    assert calls.get("user_id") == ""  # 不再是 "0"
    assert calls.get("session_id") == "aiocqhttp_g829150461"


async def test_store_unified_memory_private_keeps_user(monkeypatch):
    """私聊主动发言仍按用户存储。"""
    import hub.memory_manager as mm

    calls = {}

    async def fake_store_dialogue(**kw):
        calls.update(kw)

    async def fake_analyze(**kw):
        return None

    monkeypatch.setattr(mm, "store_dialogue", fake_store_dialogue)
    mgr = mm.MemoryManager(memory_net=None, memory_engine=None)
    monkeypatch.setattr(mgr, "_analyze_and_upgrade_assistant_memory", fake_analyze)

    await mgr.store_unified_memory(
        {
            "platform": "aiocqhttp",
            "user_id": "123456789",
            "group_id": "0",
            "message_type": "private",
            "response": "在吗",
        },
        role="assistant",
    )
    assert calls.get("user_id") == "123456789"
    assert calls.get("session_id") == "aiocqhttp_private_123456789"


# ==================== 统计磁盘口径 ====================

async def test_statistics_disk_based_cold_start():
    """get_statistics 冷启动时 by_level/by_user 从磁盘索引读取（非 0）。"""
    tmp = tempfile.mkdtemp()
    try:
        c1 = MiyaMemoryCore(tmp, enable_backup=False)
        await c1.initialize(lazy_load=True)
        await c1.store("记忆A", user_id="u1", level="long_term")
        await c1.store("记忆B", user_id="u1", level="short_term")
        await c1.close()

        # 冷启动：新实例（空缓存）统计应反映磁盘数据
        c2 = MiyaMemoryCore(tmp, enable_backup=False)
        await c2.initialize(lazy_load=True)
        stats = await c2.get_statistics()
        assert stats["total_indexed"] >= 2
        assert stats["by_level"]["long_term"] >= 1
        assert stats["by_level"]["short_term"] >= 1
        assert stats["by_user"] >= 1
        await c2.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
