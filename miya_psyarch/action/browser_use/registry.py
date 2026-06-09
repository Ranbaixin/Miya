from __future__ import annotations

"""
Browser Use Agent — APV2.1 行动注册表扩展

将浏览器操作注入 APV2.1 的 ACTION_NODE_REGISTRY 和 ACTUATOR_REGISTRY，
让先天规则层和行动规划器能像对待 pointer/keyboard 一样对待浏览器操作。
"""

from miya_psyarch.core.action.registry import ACTION_NODE_REGISTRY, ACTUATOR_REGISTRY


BROWSER_ACTUATOR_DEFS: dict[str, dict] = {
    "actuator::browser_navigate": {
        "label": "browser navigate",
        "external": True,
        "default_per_tick": 1,
        "threshold_range": (0.82, 1.18),
        "conflict_domain": "single_browser_tab",
    },
    "actuator::browser_interact": {
        "label": "browser interact",
        "external": True,
        "default_per_tick": 1,
        "threshold_range": (0.90, 1.25),
        "conflict_domain": "single_browser_interaction",
    },
    "actuator::browser_read": {
        "label": "browser read",
        "external": True,
        "default_per_tick": 1,
        "threshold_range": (0.60, 0.95),
        "conflict_domain": "single_browser_extract",
    },
}

BROWSER_ACTION_DEFS: dict[str, dict] = {
    "action::browser_open": {
        "actuator_id": "actuator::browser_navigate",
        "params": ("url", "new_tab"),
        "base_threshold": 0.88,
        "fatigue_type": "action_external",
        "external": True,
        "description": "打开网页",
    },
    "action::browser_search": {
        "actuator_id": "actuator::browser_navigate",
        "params": ("query", "engine"),
        "base_threshold": 0.82,
        "fatigue_type": "action_external",
        "external": True,
        "description": "在搜索引擎中搜索",
    },
    "action::browser_click": {
        "actuator_id": "actuator::browser_interact",
        "params": ("selector", "text", "x", "y"),
        "base_threshold": 0.95,
        "fatigue_type": "action_external",
        "external": True,
        "description": "点击网页元素",
    },
    "action::browser_type": {
        "actuator_id": "actuator::browser_interact",
        "params": ("selector", "text"),
        "base_threshold": 0.92,
        "fatigue_type": "action_external",
        "external": True,
        "description": "在输入框中输入文字",
    },
    "action::browser_scroll": {
        "actuator_id": "actuator::browser_interact",
        "params": ("direction", "amount"),
        "base_threshold": 0.78,
        "fatigue_type": "action_external",
        "external": True,
        "description": "滚动页面",
    },
    "action::browser_read_page": {
        "actuator_id": "actuator::browser_read",
        "params": ("extract_type",),
        "base_threshold": 0.72,
        "fatigue_type": "action_external",
        "external": True,
        "description": "读取网页内容",
    },
    "action::browser_extract_data": {
        "actuator_id": "actuator::browser_read",
        "params": ("query", "format"),
        "base_threshold": 0.85,
        "fatigue_type": "action_external",
        "external": True,
        "description": "提取网页结构化数据",
    },
    "action::browser_screenshot": {
        "actuator_id": "actuator::browser_read",
        "params": ("selector",),
        "base_threshold": 0.68,
        "fatigue_type": "action_external",
        "external": True,
        "description": "截取网页截图供视觉分析",
    },
    "action::browser_wait": {
        "actuator_id": "actuator::browser_navigate",
        "params": ("condition", "timeout"),
        "base_threshold": 0.55,
        "fatigue_type": "action_internal",
        "external": False,
        "description": "等待页面加载或元素出现",
    },
    "action::browser_back": {
        "actuator_id": "actuator::browser_navigate",
        "params": (),
        "base_threshold": 0.62,
        "fatigue_type": "action_external",
        "external": True,
        "description": "返回上一页",
    },
}


def register_browser_actions() -> int:
    count = 0
    for actuator_id, meta in BROWSER_ACTUATOR_DEFS.items():
        if actuator_id not in ACTUATOR_REGISTRY:
            ACTUATOR_REGISTRY[actuator_id] = dict(meta)
            count += 1
    for action_id, meta in BROWSER_ACTION_DEFS.items():
        if action_id not in ACTION_NODE_REGISTRY:
            ACTION_NODE_REGISTRY[action_id] = dict(meta)
            count += 1
    return count


def is_browser_action(action_id: str) -> bool:
    return action_id.startswith("action::browser_")
