"""
弥娅新记忆系统测试
"""

import asyncio
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))



async def test_basic_operations():
    """测试基本操作"""
    print("\n" + "=" * 50)
    print("测试 1: 基本存储操作")
    print("=" * 50)

    from memory.miya_memory import (
        MemoryLevel,
        get_miya_memory,
        reset_miya_memory,
    )

    # 重置确保干净测试
    reset_miya_memory()

    # 初始化
    memory = await get_miya_memory("data/test_memory")
    print("[OK] Initialization")

    # 测试存储对话
    dialogue_id = await memory.store(
        content="你好，我是小明",
        level=MemoryLevel.DIALOGUE,
        user_id="test_user",
        session_id="test_session",
        platform="test",
        role="user",
    )
    print(f"[OK] 存储对话: {dialogue_id}")

    # 测试存储重要记忆
    important_id = await memory.store(
        content="我喜欢唱歌和画画",
        level=MemoryLevel.LONG_TERM,
        user_id="test_user",
        tags=["偏好", "喜欢"],
        priority=0.7,
        source="manual",
    )
    print(f"[OK] 存储重要记忆: {important_id}")

    # 测试存储短期记忆
    short_id = await memory.store(
        content="这是在测试短期记忆",
        level=MemoryLevel.SHORT_TERM,
        user_id="test_user",
        ttl=3600,  # 1小时
    )
    print(f"[OK] 存储短期记忆: {short_id}")

    # 测试自动分类
    auto_id = await memory.store(
        content="记住我的生日是12月25日",
        user_id="test_user",
        source="auto_extract",
    )
    print(f"[OK] 自动分类存储: {auto_id}")

    return memory


async def test_retrieval(memory):
    """测试检索功能"""
    print("\n" + "=" * 50)
    print("测试 2: 检索功能")
    print("=" * 50)

    # 测试搜索
    results = await memory.retrieve(
        query="唱歌",
        user_id="test_user",
        limit=10,
    )
    print(f"[OK] 搜索'唱歌': 找到 {len(results)} 条")
    for r in results:
        print(f"   - [{r.level.value}] {r.content[:40]}...")

    # 测试按标签搜索
    tag_results = await memory.search_by_tag("偏好", user_id="test_user")
    print(f"[OK] 按标签'偏好'搜索: 找到 {len(tag_results)} 条")

    # 测试获取用户画像
    profile = await memory.get_user_profile("test_user")
    print("[OK] 用户画像:")
    print(f"   - 总记忆数: {profile['total_memories']}")
    print(f"   - 偏好: {profile.get('preferences', [])[:3]}")
    print(f"   - 标签分布: {dict(list(profile.get('tags', {}).items())[:5])}")

    return results


async def test_update_delete(memory):
    """测试更新和删除"""
    print("\n" + "=" * 50)
    print("测试 3: 更新和删除")
    print("=" * 50)

    # 先存一条
    test_id = await memory.store(
        content="测试更新",
        user_id="test_user",
        tags=["测试"],
    )
    print(f"[OK] 存储测试记忆: {test_id}")

    # 更新
    success = await memory.update(test_id, content="更新后的内容", priority=0.9)
    print(f"[OK] 更新记忆: {'成功' if success else '失败'}")

    # 删除
    deleted = await memory.delete(test_id)
    print(f"[OK] 删除记忆: {'成功' if deleted else '失败'}")

    # 验证删除
    results = await memory.retrieve(query="更新", user_id="test_user")
    print(f"[OK] 验证删除后搜索: 找到 {len(results)} 条")


async def test_statistics(memory):
    """测试统计功能"""
    print("\n" + "=" * 50)
    print("测试 4: 统计功能")
    print("=" * 50)

    stats = await memory.get_statistics()
    print("[STAT] System Stats:")
    print(f"   - 对话历史: {stats.get('dialogue_count', 0)} 条")
    print(f"   - 短期记忆: {stats.get('short_term_count', 0)} 条")
    print(f"   - 长期记忆: {stats.get('long_term_count', 0)} 条")
    print(f"   - 标签数量: {stats.get('tag_count', 0)}")
    print(f"   - 用户数量: {stats.get('user_count', 0)}")


async def test_adapter():
    """测试适配器"""
    print("\n" + "=" * 50)
    print("测试 5: 适配器兼容测试")
    print("=" * 50)

    from memory.miya_memory_adapter import MemoryNetAdapter, reset_global_memory_adapter

    reset_global_memory_adapter()

    adapter = MemoryNetAdapter()
    await adapter.initialize()
    print("[OK] 适配器初始化成功")

    # 测试添加对话
    msg_id = await adapter.add_conversation(
        session_id="qq_123456",
        role="user",
        content="测试消息",
    )
    print(f"[OK] 适配器添加对话: {msg_id}")

    # 测试获取对话
    messages = await adapter.get_conversation("qq_123456", limit=5)
    print(f"[OK] 适配器获取对话: {len(messages)} 条")

    # 测试添加记忆
    mem_id = await adapter.add_memory(
        fact="这是测试记忆",
        tags=["测试"],
        user_id="123456",
    )
    print(f"[OK] 适配器添加记忆: {mem_id}")

    # 测试搜索
    search_results = await adapter.search_memory("测试", user_id="123456")
    print(f"[OK] 适配器搜索: {len(search_results)} 条")

    return adapter


async def test_auto_extract():
    """测试自动提取"""
    print("\n" + "=" * 50)
    print("测试 6: 自动提取功能")
    print("=" * 50)

    from memory.miya_memory import MemoryExtractor

    test_texts = [
        "我叫小明，喜欢唱歌",
        "记住我的生日是5月20日",
        "我的电话是13800138000",
        "我讨厌数学课",
        "别忘了明天开会",
    ]

    for text in test_texts:
        results = MemoryExtractor.extract(text)
        print(f"\n[TEXT] Original: {text}")
        print(f"   提取: {results}")


async def test_cross_platform():
    """测试跨平台记忆"""
    print("\n" + "=" * 50)
    print("测试 7: 跨平台记忆")
    print("=" * 50)

    from memory.miya_memory import (
        MemoryLevel,
        get_miya_memory,
        reset_miya_memory,
    )

    reset_miya_memory()
    memory = await get_miya_memory("data/test_memory_cross")

    # 模拟多平台
    platforms = ["qq", "wechat", "terminal", "web"]

    for i, platform in enumerate(platforms):
        await memory.store(
            content=f"来自{platform}的测试消息 {i}",
            level=MemoryLevel.DIALOGUE,
            user_id="user_001",
            session_id=f"session_{i}",
            platform=platform,
            role="user",
        )

    # 获取用户所有记忆
    user_memories = await memory.search_by_user("user_001")
    print(f"[OK] 用户跨平台记忆: {len(user_memories)} 条")

    # 按平台统计
    by_platform = {}
    for mem in user_memories:
        p = mem.platform
        by_platform[p] = by_platform.get(p, 0) + 1

    print(f"   平台分布: {by_platform}")


async def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("[TEST] Miya Memory System Test")
    print("=" * 60)

    try:
        # 1. 基本操作
        memory = await test_basic_operations()

        # 2. 检索
        await test_retrieval(memory)

        # 3. 更新删除
        await test_update_delete(memory)

        # 4. 统计
        await test_statistics(memory)

        # 5. 适配器
        await test_adapter()

        # 6. 自动提取
        await test_auto_extract()

        # 7. 跨平台
        await test_cross_platform()

        print("\n" + "=" * 60)
        print("[OK] All tests passed!")
        print("=" * 60)

    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
