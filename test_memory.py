import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


async def test():
    from memory import get_memory_core

    # 使用 run 目录
    core = await get_memory_core(str(Path(__file__).parent / "run" / "data" / "memory"))

    # 搜索情绪相关记忆
    results = await core.retrieve("#emotion", limit=20)
    print(f"找到 {len(results)} 条 #emotion 记忆:")
    for r in results[:20]:
        print(f"  [{r.level}] {r.content[:80]}...")

    # 搜索所有记忆
    print("\n--- 全部recent ---")
    all_results = await core.retrieve("", limit=5, level_filter="dialogue")
    print(f"对话记忆: {len(all_results)}")
    for r in all_results[:5]:
        print(f"  - {r.content[:60]}...")


if __name__ == "__main__":
    asyncio.run(test())
