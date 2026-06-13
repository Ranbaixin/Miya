"""
弥娅语言皮层 prompt 构建 — 全部标签/模板从 miya_config.yaml 加载
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from core.miya_config_cache import get_miya_config as _get_miya_config
from pathlib import Path

# ── 加载配置 ── 使用全局缓存（避免重复读取）

_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "miya_config.yaml"
_CFG = _get_miya_config()


def _level_label(value: float, levels: list[dict]) -> str:
    for entry in sorted(levels, key=lambda x: x["threshold"], reverse=True):
        if value >= entry["threshold"]:
            return entry["label"]
    return levels[-1]["label"] if levels else ""


# 弥娅身份 prompt (从 YAML)
def _build_identity_prompt(form: str | None = None) -> str:
    _personality_dir = _CONFIG_PATH.parent.parent.parent / "config" / "personalities"

    def _load(filename: str) -> dict:
        path = _personality_dir / filename
        return yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}

    base = _load("_base.yaml")
    default = _load("_default.yaml")
    default_forms = set(_CFG.get("default_forms", ["default", "normal", "常态"]))

    sections = []

    core_id = base.get("core_identity", "") or default.get("core_identity", "")
    if core_id:
        sections.append(core_id.strip())

    form_config = {}
    if form and form not in default_forms:
        form_config = _load(f"{form}.yaml")
        fp = form_config.get("prompt", "")
        if fp:
            sections.append("")
            sections.append(fp.strip())
    else:
        ns = default.get("normal_form_soul", "")
        if ns:
            sections.append("")
            sections.append(ns.strip())

    for key in (
        "tone_calibration",
        "behavioral_constraints",
        "anti_ai_patterns",
        "anti_sycophancy",
        "mood_flow",
        "imperfection_allowance",
        "proactive_principles",
    ):
        val = base.get(key, "")
        if val:
            sections.append("")
            sections.append(val.strip())

    for key in ("form_anti_sycophancy", "form_proactive", "form_mood_palette"):
        val = default.get(key, "") or form_config.get(key, "")
        if val:
            sections.append("")
            sections.append(val.strip())

    return "\n".join(sections)


# 缓存
_IDENTITY_CACHE: dict[str, str] = {}


def get_identity_prompt(form: str | None = None) -> str:
    key = form or "__default__"
    if key not in _IDENTITY_CACHE:
        _IDENTITY_CACHE[key] = _build_identity_prompt(form)
    return _IDENTITY_CACHE[key]


@dataclass
class MiyaInternalState:
    tick: int = 0
    feelings: dict[str, float] | None = None
    miya_feelings: dict[str, float] | None = None
    emotion_nt: dict[str, float] | None = None
    focus: list[str] | None = None
    task_state: dict[str, float] | None = None
    current_time: str = ""
    recent_context: list[str] | None = None
    memory_context: str = ""

    def to_text(self) -> str:
        lines = []

        if self.current_time:
            lines.append(f"现在时间: {self.current_time}")

        if self.memory_context:
            lines.append(self.memory_context)

        ctx = self.recent_context or []
        if ctx:
            lines.append(f"最近对话:")
            for entry in ctx[-6:]:
                lines.append(f"  {entry}")
            lines.append("")

        ot = _CFG.get("output_templates", {})

        # 弥娅感受
        mf = self.miya_feelings or {}
        if mf:
            labels = _CFG.get("miya_feeling_labels", {})
            levels = _CFG.get("miya_feeling_levels", [])
            items = []
            for k, v in sorted(mf.items(), key=lambda x: -x[1]):
                cn = labels.get(k, k)
                level = _level_label(v, levels)
                items.append(f"{cn}({level}:{v:.1f})")
            if items:
                lines.append(f"{ot.get('miya_feeling_prefix', '')}{', '.join(items)}")

        # 情绪递质
        nt = self.emotion_nt or {}
        if nt:
            nt_labels = _CFG.get("nt_labels", {})
            nt_levels = _CFG.get("nt_levels", [])
            order = _CFG.get("nt_display_order", [])
            default_v = _CFG.get("nt_default_value", 0.5)
            parts = []
            for ch in order:
                v = nt.get(ch, default_v)
                cn = nt_labels.get(ch, ch)
                level = _level_label(v, nt_levels)
                parts.append(f"{cn}:{level}({v:.2f})")
            lines.append(f"{ot.get('nt_state_prefix', '')}{' | '.join(parts)}")

        # 任务感受
        ts = self.task_state or {}
        status = []
        for rule in _CFG.get("task_feeling_rules", []):
            val = ts.get(rule["key"], 0)
            if "mid_label" in rule and "mid_threshold" in rule:
                if val >= rule["mid_threshold"]:
                    label = rule["high_label"] if val >= rule["threshold"] else rule["mid_label"]
                    status.append(label)
            elif val >= rule["threshold"]:
                status.append(rule["label"])
        if status:
            lines.append(f"{ot.get('task_state_prefix', '')}{', '.join(status)}")

        if not lines:
            lines.append(ot.get("fallback", ""))

        return "\n".join(lines)


def build_miya_cortex_prompt(
    state: MiyaInternalState,
    user_message: str,
    *,
    personality_form: str | None = None,
) -> tuple[str, str]:
    identity = get_identity_prompt(personality_form)
    internal = state.to_text()
    system_prompt = f"""{identity}

---
{internal}
---
"""
    return system_prompt, user_message
