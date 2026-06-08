from __future__ import annotations

_MEM_F_CFG = {}
try:
    import yaml
    from pathlib import Path

    p = Path(__file__).resolve().parent.parent / "config" / "miya_config.yaml"
    with open(p, "r", encoding="utf-8") as f_cfg:
        raw = yaml.safe_load(f_cfg) or {}
    _MEM_F_CFG = raw.get("memory_fusion", {})
except Exception:
    pass

_MF_LABELS = _MEM_F_CFG.get("labels", {})
_MF_TRUNC = _MEM_F_CFG.get("truncation", {})
_MF_ENERGY = _MEM_F_CFG.get("energy", {})
_MF_LIMITS = _MEM_F_CFG.get("limits", {})
_MF_SRC = _MEM_F_CFG.get("source_types", {})
_MF_FAMILIES = _MEM_F_CFG.get("families", {})
"""
弥娅记忆深度融合 — 将 MiyaMemoryCore 完整融入 AP 认知闭环

不再只是"桥接"SQLite，而是让 Miya 的以下记忆系统成为 AP 状态池的第一公民:
- 身份锚定 (弥娅是谁 / 佳是谁) → 永久状态池项
- 认知记忆 (思考/情绪/归因) → 深层思考模式
- 向量语义搜索 → Bn/Cn 增强召回
- 记忆索引 (8616条) → 按需注入
"""


import asyncio
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("miya_psyarch.memory_fusion")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class MiyaMemoryFusion:
    """弥娅记忆深度融合引擎"""

    def __init__(self, engine):
        self._engine = engine
        self._identity_anchors: list[dict] = []
        self._user_anchors: list[dict] = []
        self._cognitive_entries: list[dict] = []
        self._loaded = False

    def load_all(self) -> None:
        """加载全部记忆源"""
        if self._loaded:
            return
        self._load_identity_anchors()
        self._load_user_anchors()
        self._load_cognitive_memories()
        self._loaded = True
        logger.info(
            f"MiyaMemoryFusion loaded: {len(self._identity_anchors)} identity, "
            f"{len(self._user_anchors)} user, {len(self._cognitive_entries)} cognitive"
        )

    def inject_permanent_anchors(self) -> list[dict]:
        """获取永久锚定 items（缓存版，每 tick 零开销）"""
        if self._engine._runtime is None:
            return []
        return self._build_cached_anchor_items()

    def inject_cognitive_memories(self) -> list[dict]:
        """获取认知记忆 items——让 AP 永久持有弥娅的思考模式"""
        if self._engine._runtime is None:
            return []
        items = []
        for entry in self._cognitive_entries:
            thought = entry.get("inner_thought", "")
            thinking = entry.get("thinking", "")
            attr = entry.get("attribution", "")
            refl = entry.get("reflection", "")
            emos = entry.get("emotions", {})
            top_emo = max(emos.items(), key=lambda x: x[1]) if emos else ("思考", 50)

            if thought:
                items.append(
                    {
                        "sa_label": f"cognitive::inner::{top_emo[0]}::{thought[:15]}",
                        "display_text": _MF_LABELS.get("inner_prefix", "弥娅独白: {thought}").replace(
                            "{thought}", thought[: _MF_TRUNC.get("inner_thought", 30)]
                        ),
                        "family": "cognitive_memory",
                        "source_type": "inner_thought",
                        "real_energy": 1.8,
                        "anchor_meta": {
                            "emotion": top_emo[0],
                            "intensity": top_emo[1],
                            "thought": thought,
                            "type": "inner",
                        },
                    }
                )
            if attr and len(attr) > 3:
                items.append(
                    {
                        "sa_label": f"cognitive::attr::{top_emo[0]}::{attr[:15]}",
                        "display_text": _MF_LABELS.get("attribution_prefix", "归因: {attr}").replace(
                            "{attr}", attr[: _MF_TRUNC.get("attribution", 30)]
                        ),
                        "family": "cognitive_memory",
                        "source_type": "attribution",
                        "real_energy": 1.3,
                        "anchor_meta": {"emotion": top_emo[0], "attribution": attr, "type": "attr"},
                    }
                )
            if refl and len(refl) > 5:
                items.append(
                    {
                        "sa_label": f"cognitive::refl::{refl[:20]}",
                        "display_text": _MF_LABELS.get("reflection_prefix", "反思: {refl}").replace(
                            "{refl}", refl[: _MF_TRUNC.get("reflection", 30)]
                        ),
                        "family": "cognitive_memory",
                        "source_type": "reflection",
                        "real_energy": 1.5,
                        "anchor_meta": {"reflection": refl, "type": "refl"},
                    }
                )
        return items

    async def vector_search_inject(self, query: str, limit: int = 8) -> list[str]:
        """用 MiyaMemoryCore 做向量语义搜索，注入 AP 状态池"""
        if self._engine._runtime is None:
            return []
        try:
            from memory import get_memory_core

            core = await get_memory_core()
            results = await core.retrieve(query=query, limit=limit)
            items = []
            recalled = []
            for m in results:
                content = getattr(m, "content", "")
                if not content or len(content) < 3:
                    continue
                score = getattr(m, "score", 0.5)
                role = getattr(m, "role", "memory")
                items.append(
                    {
                        "sa_label": f"memory_recall::{role}::{content[:25]}",
                        "display_text": f"[回忆] {content[:35]}",
                        "family": "memory_recall",
                        "source_type": "vector_search",
                        "real_energy": min(2.0, 0.4 + score * 2.0),
                        "anchor_meta": {
                            "role": role,
                            "score": score,
                            "content": content,
                        },
                    }
                )
                recalled.append(f"score={score:.2f} | {content[:40]}")
            if items:
                self._engine._runtime.state_pool.apply_external_items(
                    items, tick_index=self._engine._runtime.tick_index
                )
            return recalled
        except Exception as e:
            logger.debug(f"Vector search failed: {e}")
            return []

    def get_memory_context_for_llm(self) -> str:
        """获取当前状态池中的记忆项，供 LLM 使用"""
        if self._engine._runtime is None:
            return ""
        pool = self._engine._runtime.state_pool
        memories = []
        for k, v in pool._entries.items():
            family = str(v.family)
            if family in ("memory_recall", "memory_anchor", "cognitive_memory"):
                content = (
                    (v.anchor_meta or {}).get("content", str(k)[:40]) if hasattr(v, "anchor_meta") else str(k)[:40]
                )
                memories.append((v.real_energy, content))
        if not memories:
            return ""
        top = sorted(memories, key=lambda x: -x[0])[:5]
        lines = ["记忆召回:"]
        for energy, content in top:
            lines.append(f"  [{energy:.1f}] {content[:60]}")
        return "\n".join(lines)

    # ── 内部加载 ──

    def _load_identity_anchors(self) -> None:
        path = _PROJECT_ROOT / "data" / "memory_anchors_identity.json"
        if path.exists():
            try:
                self._identity_anchors = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                pass
        self._cached_anchor_items = None  # 文件变化时清除缓存

    def _load_user_anchors(self) -> None:
        path = _PROJECT_ROOT / "data" / "memory_anchors_user.json"
        if path.exists():
            try:
                self._user_anchors = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                pass
        self._cached_anchor_items = None  # 文件变化时清除缓存

    def _build_cached_anchor_items(self) -> list[dict]:
        """构建永久锚定 items（缓存，仅数据变更时重建）"""
        if self._cached_anchor_items is not None:
            return self._cached_anchor_items
        items = []
        for anchor in self._identity_anchors:
            content = (anchor.get("fact") or anchor.get("content") or "")[:50]
            if content:
                items.append(
                    {
                        "sa_label": f"anchor::identity::{content[:20]}",
                        "display_text": _MF_LABELS.get("identity_prefix", "[身份] {content}").replace(
                            "{content}", content[: _MF_TRUNC.get("identity", 30)]
                        ),
                        "family": "memory_anchor",
                        "source_type": "identity_anchor",
                        "real_energy": 2.0,
                        "anchor_meta": {"type": "identity", "full": content},
                    }
                )
        for anchor in self._user_anchors:
            content = (anchor.get("fact") or anchor.get("content") or "")[:50]
            if content:
                items.append(
                    {
                        "sa_label": f"anchor::user::{content[:20]}",
                        "display_text": _MF_LABELS.get("user_prefix", "[佳] {content}").replace(
                            "{content}", content[: _MF_TRUNC.get("user", 30)]
                        ),
                        "family": "memory_anchor",
                        "source_type": "user_anchor",
                        "real_energy": 2.0,
                        "anchor_meta": {"type": "user", "full": content},
                    }
                )
        self._cached_anchor_items = items
        return items

    def _load_cognitive_memories(self) -> None:
        path = _PROJECT_ROOT / "data" / "memory" / "cognitive_memories.json"
        if path.exists():
            try:
                self._cognitive_entries = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                pass


# 全局单例
_fusion: MiyaMemoryFusion | None = None


def get_memory_fusion(engine) -> MiyaMemoryFusion:
    global _fusion
    if _fusion is None:
        _fusion = MiyaMemoryFusion(engine)
    return _fusion
