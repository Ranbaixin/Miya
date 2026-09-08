"""记忆类人化行为验收 demo（2026-09）

构造带情绪/关联/时间跨度的测试记忆集，人工检查 build_context 输出的"人味"：
- 艾宾浩斯衰减：40 天前的记忆相关度低于昨天的新记忆
- 情绪加权：带情绪基调的记忆排前
- 联想召回：由一条记忆带出关联记忆并标注"（由…想起）"
- 模糊化措辞：按相关度分档（确定/印象里/好像）+ 模糊片段

用法：uv run python scripts/memory_humanization_demo.py
"""

import asyncio
import os
import shutil
import sys
import tempfile
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def main():
    from memory.cognitive_engine import CognitiveEngine
    from memory.core import MemoryLevel, MiyaMemoryCore
    from memory.memory_enhancer import MemoryLink

    tmp = tempfile.mkdtemp()
    try:
        core = MiyaMemoryCore(tmp, enable_backup=False)
        await core.initialize(lazy_load=True)
        engine = CognitiveEngine(memory_core=core)
        engine._enhancer = core._enhancer

        def days_ago(n: int) -> str:
            return (datetime.now() - timedelta(days=n)).isoformat()

        # ---- 构造测试记忆集 ----
        # 1. 昨天的高相关记忆（关键词命中：考试/学习）
        fresh_id = await core.store(
            "我们约好下周一起复习期末考试的重点内容",
            user_id="u1", level=MemoryLevel.LONG_TERM, tags=["学习", "考试"],
        )

        # 2. 40 天前的旧记忆（同关键词，应因衰减而措辞更不确定）
        old_id = await core.store(
            "上次考试复习时你说 prefers 咖啡而不是茶",
            user_id="u1", level=MemoryLevel.LONG_TERM, tags=["学习", "考试"],
        )

        # 3. 带情绪基调的记忆
        emo_id = await core.store(
            "考试通过那天你特别开心，我们一起庆祝了",
            user_id="u1", level=MemoryLevel.LONG_TERM, emotional_tone="极度兴奋",
            significance=0.9, tags=["考试", "庆祝"],
        )

        # 4. 关联对：fresh_id → emo_id（实体链接）+ fresh_id → gift_id（联想才可达的记忆：
        #    gift 不带"学习/考试"标签，正常检索不命中，只能由一跳链接带出）
        gift_id = await core.store(
            "考试完你收到了星黛露玩偶当礼物",
            user_id="u1", level=MemoryLevel.LONG_TERM, tags=["礼物"],
        )
        engine._enhancer._links[fresh_id] = [
            MemoryLink(source_id=fresh_id, target_id=emo_id, link_type="entity", strength=0.85),
            MemoryLink(source_id=fresh_id, target_id=gift_id, link_type="entity", strength=0.9),
        ]

        # 统一改写时间戳（store 后索引与本体同步更新）
        for mid, created in (
            (fresh_id, days_ago(1)),
            (old_id, days_ago(40)),
            (emo_id, days_ago(35)),
            (gift_id, days_ago(35)),
        ):
            mem = await core.get_by_id(mid)
            mem.created_at = created
            await core.backend.save(mem)
            core.backend._index[mid]["created_at"] = created

        print("=" * 60)
        print("检索输入：'还记得考试复习的事吗'")
        print("=" * 60)
        memories = await engine.retrieve("还记得考试复习的事吗", limit=5)
        ctx = await engine.build_context("还记得考试复习的事吗", memories=memories)
        print(ctx)
        print()

        # 模糊片段为 ≤10% 概率浮现，这里确定性展示其措辞格式
        print("=" * 60)
        print("模糊片段措辞示例（30~50 天旧记忆低概率浮现时的样子）")
        print("=" * 60)
        from memory.core import MemoryItem

        fragment = MemoryItem(
            id="frag", content="那天好像聊过毕业旅行的目的地",
            created_at=days_ago(42),
        )
        fragment.metadata["fuzzy_fragment"] = True
        frag_ctx = await engine.build_context("考试复习", memories=[fragment])
        for line in frag_ctx.splitlines():
            if "毕业旅行" in line:
                print(line)
        print()

        # ---- 检索打分对比（衰减/情绪/访问强化） ----
        print("=" * 60)
        print("打分明细（相关度）")
        print("=" * 60)
        topics = engine._extract_topics("考试复习")
        keywords = engine._extract_keywords("考试复习")
        for mid, label in ((fresh_id, "昨天-复习约定"), (old_id, "40天前-偏好"), (emo_id, "35天前-通过庆祝(情绪)")):
            mem = await core.get_by_id(mid)
            r = await engine._calculate_relevance(mem, topics, keywords, "")
            print(f"  {label:24s} → {r:.3f}")

        await core.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(main())
