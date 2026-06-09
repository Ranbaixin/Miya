from __future__ import annotations

"""
弥娅 Browser Use Agent — 基于 APV2.1 认知引擎的浏览器自动化子系统

将浏览器操作注入 APV2.1 的行动规划管线：
- AP 认知决定「何时」使用浏览器
- LLM 皮层执行「做什么」
- OpenClaw Gateway 提供底层执行能力

集成路径：
  APV21Runtime.tick() → InnateCodingEngine → browser action drives
  → ActionConsequencePlanner → browser_use actions selected
  → BrowserUseExecutor → OpenClaw Gateway → 浏览器执行
  → ScreenVision → 结果感知 → AP 学习闭环
"""

from miya_psyarch.action.browser_use.adapter import BrowserUseExecutor
from miya_psyarch.action.browser_use.registry import register_browser_actions

__all__ = ["BrowserUseExecutor", "register_browser_actions"]
