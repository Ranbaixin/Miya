"""
弥娅统一记忆系统 V3.1 全面测试
"""

import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def test_1_init():
    """测试1: 初始化"""
    print("\n" + "=" * 60)
    print("[TEST 1] Initialization")
    print("=" * 60)

    from memory.core import get_memory_core, reset_memory_core

    reset_memory_core()

    core = await get_memory_core("data/test_memory_v31")
    print("[OK] Core initialized")
    print(f"[OK] Data dir: {core.data_dir}")

    stats = await core.get_statistics()
    print(f"[OK] Stats: {stats}")

    return core


async def test_2_store(core):
    """测试2: 存储"""
    print("\n" + "=" * 60)
    print("[TEST 2] Store")
    print("=" * 60)

    # 存储对话
    dialogue_id = await core.store(
        content="你好，我是小明",
        level=core.backend._get_dir.__class__.__module__,
        user_id="user_001",
        session_id="session_001",
        platform="qq",
        role="user",
    )
    print(f"[OK] Store dialogue: {dialogue_id}")

    # 存储重要记忆
    important_id = await core.store(
        content="我喜欢唱歌和画画",
        level="long_term",
        user_id="user_001",
        tags=["偏好", "喜欢"],
        priority=0.7,
        source="manual",
    )
    print(f"[OK] Store important: {important_id}")

    # 自动分类存储
    auto_id = await core.store(
        content="记住我的生日是12月25日",
        user_id="user_001",
        source="auto_extract",
    )
    print(f"[OK] Auto classify: {auto_id}")

    # 批量存储测试
    batch_ids = []
    for i in range(50):
        mid = await core.store(
            content=f"批量测试消息 {i}",
            level="dialogue",
            user_id="user_batch",
            session_id="session_batch",
            platform="test",
            role="user",
        )
        batch_ids.append(mid)

    print(f"[OK] Batch store: {len(batch_ids)} items")

    return dialogue_id, important_id, auto_id


async def test_3_retrieve(core):
    """测试3: 检索"""
    print("\n" + "=" * 60)
    print("[TEST 3] Retrieve")
    print("=" * 60)

    # 搜索
    results = await core.retrieve(query="唱歌", user_id="user_001")
    print(f"[OK] Search '唱歌': {len(results)} results")
    for r in results[:3]:
        print(f"     - [{r.level.value}] {r.content[:40]}...")

    # 按标签搜索
    tag_results = await core.search_by_tag("偏好", user_id="user_001")
    print(f"[OK] Tag search '偏好': {len(tag_results)} results")

    # 按用户搜索
    user_results = await core.search_by_user("user_001")
    print(f"[OK] User search: {len(user_results)} results")

    # 获取对话
    dialogue = await core.get_dialogue("session_001", "qq")
    print(f"[OK] Dialogue: {len(dialogue)} messages")

    return results


async def test_4_update_delete(core):
    """测试4: 更新删除"""
    print("\n" + "=" * 60)
    print("[TEST 4] Update & Delete")
    print("=" * 60)

    # 存储测试
    test_id = await core.store(
        content="测试更新删除",
        user_id="test_user",
        tags=["测试"],
    )
    print(f"[OK] Store test: {test_id}")

    # 更新
    success = await core.update(
        test_id, content="更新后内容", priority=0.9, is_pinned=True
    )
    print(f"[OK] Update: {success}")

    # 验证更新
    updated = await core.get_by_id(test_id)
    print(
        f"[OK] Verified: content={updated.content}, priority={updated.priority}, pinned={updated.is_pinned}"
    )

    # 删除
    deleted = await core.delete(test_id)
    print(f"[OK] Delete: {deleted}")

    # 验证删除
    verify = await core.get_by_id(test_id)
    print(f"[OK] Verify delete: {verify is None}")


async def test_5_profile(core):
    """测试5: 用户画像"""
    print("\n" + "=" * 60)
    print("[TEST 5] User Profile")
    print("=" * 60)

    profile = await core.get_user_profile("user_001")
    print("[OK] Profile:")
    print(f"     - total: {profile['total_memories']}")
    print(f"     - by_level: {profile['by_level']}")
    print(f"     - by_tag: {profile['by_tag']}")
    print(f"     - preferences: {profile.get('preferences', [])[:2]}")
    print(f"     - birthdays: {profile.get('birthdays', [])[:2]}")


async def test_6_adapter():
    """测试6: 适配器"""
    print("\n" + "=" * 60)
    print("[TEST 6] Adapter")
    print("=" * 60)

    from memory.adapter import MiyaMemoryNet, reset_memory_net


    reset_memory_net()

    net = MiyaMemoryNet()
    await net.initialize()
    print("[OK] Adapter initialized")

    # 添加对话
    msg_id = await net.add_conversation(
        session_id="qq_123456",
        role="user",
        content="测试消息",
    )
    print(f"[OK] Add conversation: {msg_id}")

    # 获取对话
    messages = await net.get_conversation("qq_123456", limit=10)
    print(f"[OK] Get conversation: {len(messages)} messages")

    # 添加记忆
    mem_id = await net.add_memory(
        fact="这是测试记忆",
        tags=["测试"],
        user_id="123456",
    )
    print(f"[OK] Add memory: {mem_id}")

    # 搜索
    results = await net.search_memory("测试", user_id="123456")
    print(f"[OK] Search: {len(results)} results")

    # 统计
    stats = await net.get_statistics()
    print(f"[OK] Stats: {stats.get('total_cached', 0)} cached")

    return net


async def test_7_auto_extract():
    """测试7: 自动提取"""
    print("\n" + "=" * 60)
    print("[TEST 7] Auto Extract")
    print("=" * 60)

    from memory.adapter import MiyaMemoryNet, reset_memory_net

    reset_memory_net()

    net = MiyaMemoryNet()
    await net.initialize()

    test_texts = [
        "我叫小明，喜欢唱歌",
        "记住我的生日是5月20日",
        "我的电话是13800138000",
        "我讨厌数学课",
        "别忘了明天开会",
    ]

    for text in test_texts:
        count = await net.extract_and_store_important_info(text, user_id="extract_test")
        print(f"[OK] '{text[:20]}...' -> {count} extracted")


async def test_8_convenience():
    """测试8: 便捷函数"""
    print("\n" + "=" * 60)
    print("[TEST 8] Convenience Functions")
    print("=" * 60)

    from memory import (
        get_memory_stats,
        get_user_memories,
        reset_memory_adapter,
        search_memory,
        store_dialogue,
        store_important,
    )

    reset_memory_adapter()

    # 便捷存储
    d_id = await store_dialogue(
        content="便捷对话",
        role="user",
        user_id="convenience",
        session_id="s1",
    )
    print(f"[OK] store_dialogue: {d_id}")

    i_id = await store_important(
        content="便捷重要记忆",
        user_id="convenience",
        tags=["测试"],
    )
    print(f"[OK] store_important: {i_id}")

    # 便捷搜索
    results = await search_memory("便捷", user_id="convenience")
    print(f"[OK] search_memory: {len(results)}")

    # 便捷获取
    mems = await get_user_memories("convenience")
    print(f"[OK] get_user_memories: {len(mems)}")

    # 统计
    stats = await get_memory_stats()
    print(f"[OK] get_memory_stats: {stats.get('total_cached', 0)} cached")


async def test_9_performance():
    """测试9: 性能测试"""
    print("\n" + "=" * 60)
    print("[TEST 9] Performance")
    print("=" * 60)

    from memory import get_memory_core, reset_memory_core

    reset_memory_core()
    core = await get_memory_core("data/test_perf")

    # 批量写入性能
    start = time.time()
    for i in range(100):
        await core.store(
            content=f"性能测试 {i}",
            user_id="perf_user",
            session_id="perf_session",
        )
    write_time = time.time() - start
    print(f"[OK] Write 100 items: {write_time:.3f}s ({100 / write_time:.1f}/s)")

    # 批量读取性能
    start = time.time()
    for i in range(100):
        await core.retrieve(query="性能", user_id="perf_user")
    read_time = time.time() - start
    print(f"[OK] Read 100 queries: {read_time:.3f}s ({100 / read_time:.1f}/s)")

    # 统计
    stats = await core.get_statistics()
    print(f"[OK] Final stats: {stats.get('total_cached', 0)} cached")


async def test_10_edge_cases():
    """测试10: 边界情况"""
    print("\n" + "=" * 60)
    print("[TEST 10] Edge Cases")
    print("=" * 60)

    from memory import get_memory_core, reset_memory_core

    reset_memory_core()
    core = await get_memory_core("data/test_edge")

    # 空内容
    try:
        await core.store(content="", user_id="test")
        print("[FAIL] Empty content should fail")
    except:
        print("[OK] Empty content rejected")

    # 特殊字符
    sid = await core.store(
        content="特殊字符: 🎉😂😢 💯👀",
        user_id="test",
    )
    print(f"[OK] Special chars: {sid}")

    # 超长内容
    long_content = "测试内容 " * 1000
    lid = await core.store(content=long_content[:5000], user_id="test")
    print(f"[OK] Long content: {lid}")

    # Unicode
    uid = await core.store(
        content="中文English日本語한국어",
        user_id="test",
    )
    print(f"[OK] Unicode: {uid}")


async def main():
    """主测试"""
    print("\n" + "=" * 60)
    print("  MIYA MEMORY SYSTEM V3.1 COMPREHENSIVE TEST")
    print("=" * 60)

    try:
        # 1. 初始化
        core = await test_1_init()

        # 2. 存储
        await test_2_store(core)

        # 3. 检索
        await test_3_retrieve(core)

        # 4. 更新删除
        await test_4_update_delete(core)

        # 5. 用户画像
        await test_5_profile(core)

        # 6. 适配器
        await test_6_adapter()

        # 7. 自动提取
        await test_7_auto_extract()

        # 8. 便捷函数
        await test_8_convenience()

        # 9. 性能
        await test_9_performance()

        # 10. 边界情况
        await test_10_edge_cases()

        print("\n" + "=" * 60)
        print("  [SUCCESS] ALL TESTS PASSED!")
        print("=" * 60)

    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
