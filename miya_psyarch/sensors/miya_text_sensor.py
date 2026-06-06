"""
弥娅中文文本感受器 — jieba 分词 + 英文保留

"今天天气真好hello world" → ["今天", "天气", "真好", "hello", "world"]
中文用 jieba 分词，英文保留 AP 原生的 TOKEN_RE 行为
"""

from __future__ import annotations

import re
from collections import OrderedDict

import jieba

from miya_psyarch.sensors.text.sensor import TextSensor, normalize_text, TOKEN_RE

_CHINESE_BLOCK = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]+")


def _segment_mixed(text: str) -> list[str]:
    """中英文混合分词：先按中/非中分块，中文用 jieba，非中文用 TOKEN_RE"""
    normalized = normalize_text(text)
    if not normalized:
        return []
    units: list[str] = []
    pos = 0
    for m in _CHINESE_BLOCK.finditer(normalized):
        # 中文块前面的非中文部分
        before = normalized[pos : m.start()]
        if before.strip():
            units.extend(TOKEN_RE.findall(before))
        # 中文块用 jieba 分词
        cn_block = m.group()
        words = [w for w in jieba.cut(cn_block) if w.strip()]
        units.extend(words)
        pos = m.end()
    # 最后的非中文尾巴
    tail = normalized[pos:]
    if tail.strip():
        units.extend(TOKEN_RE.findall(tail))
    return units


def _energy_for(token: str) -> float:
    n = len(token)
    if _CHINESE_BLOCK.fullmatch(token):
        if n >= 3:
            return 1.8
        if n == 2:
            return 1.4
        return 1.0
    if n >= 6:
        return 1.6
    if n >= 4:
        return 1.3
    return 1.1


class MiyaTextSensor(TextSensor):
    """弥娅中文感知器 — jieba 分词，不破坏英文 token"""

    def __init__(self, *, budget_limit: int) -> None:
        super().__init__(budget_limit=budget_limit)

    def ingest(self, text: str, *, tick_index: int, source_type: str = "external_text") -> dict:
        key = (str(text or ""), str(source_type or ""), int(self.budget_limit))
        cached = self._packet_cache.get(key)
        if cached is None:
            units = _segment_mixed(text)
            limited = units[: self.budget_limit]
            preview_units = limited[: self._preview_limit]
            sa_items_preview = [
                {
                    "sa_label": f"text::{unit}",
                    "display_text": unit,
                    "source_type": source_type,
                    "position": idx,
                    "real_energy": _energy_for(unit),
                }
                for idx, unit in enumerate(preview_units)
            ]
            cached = {
                "normalized_text": normalize_text(text),
                "units": tuple(units),
                "sa_item_count": len(limited),
                "sa_items_preview": tuple(tuple(item.items()) for item in sa_items_preview),
            }
            self._packet_cache[key] = cached
            if len(self._packet_cache) > self._cache_limit:
                self._packet_cache.popitem(last=False)
        else:
            self._packet_cache.move_to_end(key)

        units = list(cached.get("units", ()) or ())
        sa_items_preview = [dict(item) for item in (cached.get("sa_items_preview", ()) or ())]
        return {
            "tick_index": int(tick_index),
            "source_type": source_type,
            "input_text": str(text or ""),
            "normalized_text": str(cached.get("normalized_text", "") or ""),
            "units": units,
            "sa_item_count": int(cached.get("sa_item_count", len(units[: self.budget_limit])) or 0),
            "sa_items": sa_items_preview,
        }


def patch_text_sensor(engine) -> None:
    engine.text_sensor = MiyaTextSensor(budget_limit=engine.config.text_sensor.budget_limit)
