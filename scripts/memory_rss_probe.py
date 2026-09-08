"""内存占用探针（2026-09 内存优化验收）

测量：
1. 空载：解释器 + 运行时导入链（记忆系统/图谱/web_api 工具/表情包）的 RSS
2. 负载：临时目录中 store + retrieve + build_context 处理 20 条消息后的 RSS

用法：python scripts/memory_rss_probe.py [--label 标签]
"""

import argparse
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def rss_mb() -> float:
    import psutil

    return psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", default="after")
    args = parser.parse_args()

    print(f"[{args.label}] 解释器基线 RSS: {rss_mb():.1f} MB")

    # 1. 运行时导入链（daemon 启动会拉起的记忆/图谱/工具/表情模块）
    import memory.core
    import memory.cognitive_engine
    import memory.memory_enhancer
    import memory.working_memory
    import hub.memory_engine
    import core.grag_memory
    import core.knowledge_graph
    import core.web_api.tools
    import utils.emoji_manager

    # graph_store 为 2026-09 新增，基线（改动前）代码没有 —— 容忍缺失
    try:
        import memory.graph_store  # noqa: F401
    except ImportError:
        print(f"[{args.label}] （基线无 graph_store 模块，跳过）")

    idle_rss = rss_mb()
    print(f"[{args.label}] 导入链后（空载）RSS: {idle_rss:.1f} MB")

    # 检查重依赖是否被意外拉入
    heavy = [m for m in ("pandas", "matplotlib", "neo4j", "loguru") if m in sys.modules]
    print(f"[{args.label}] 意外加载的重依赖: {heavy if heavy else '无'}")

    # 2. 模拟 20 条消息（store → retrieve → build_context）
    import asyncio

    async def simulate():
        tmp = tempfile.mkdtemp()
        try:
            core = memory.core.MiyaMemoryCore(tmp, enable_backup=False)
            await core.initialize(lazy_load=True)
            engine = memory.cognitive_engine.CognitiveEngine(memory_core=core)
            engine._enhancer = core._enhancer

            for i in range(20):
                await core.store(
                    f"第{i}条消息：我们一起讨论了学习和考试的安排",
                    user_id="u1",
                    level=memory.core.MemoryLevel.LONG_TERM,
                )
            for _ in range(5):
                memories = await engine.retrieve("考试安排", limit=5)
                await engine.build_context("考试安排", memories=memories)
            loaded = rss_mb()
            print(f"[{args.label}] 20 条消息处理后 RSS: {loaded:.1f} MB")
            await core.close()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    asyncio.run(simulate())


if __name__ == "__main__":
    main()
