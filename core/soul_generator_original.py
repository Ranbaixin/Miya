"""
灵魂发生器 (Soul Generator) - 弥娅的"灵魂"系统
让弥娅拥有类似人类的情绪、认知和行为模式

核心特性：
1. 情绪池 - 完整人类情感图谱（70+情绪类别）
2. 情境检测器 - 识别关系/时间/话题/情绪状态
3. 心理学剖析引擎 - 归因/识别/预测/反思/调节
4. 行为引擎 - 意图残留追踪（未完成意图）
5. 情绪记忆锚点 - 记住情绪事件而非细节
6. 情绪恢复曲线 - 自然衰减机制
7. 社交面具 - 真实情绪与表达分离
"""

import logging
import time
import random
import json
import sys
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("Miya.灵魂发生器")


class SoulDisplay:
    """
    灵魂发生器终端显示 - 青色科幻风格
    用于美化灵魂发生器的日志输出
    """

    # 颜色代码
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    MAGENTA = "\033[35m"
    BLUE = "\033[34m"
    WHITE = "\033[37m"
    GRAY = "\033[90m"
    LIGHT_CYAN = "\033[96m"
    PINK = "\033[95m"  # 粉色 - 用于情绪变化
    ORANGE = "\033[38;5;208m"  # 橙色 - 用于关系影响
    LIGHT_GREEN = "\033[92m"  # 亮绿色 - 用于积极效果

    # 符号
    HEART = "♥"
    SPARKLE = "✦"
    WAVE = "〰"
    ARROW = "→"
    BRAIN = "◈"
    FIRE = "🔥"
    STARS = "✨"

    @classmethod
    def _print(cls, text: str) -> None:
        """输出到 stderr"""
        sys.stderr.write(text + "\n")
        sys.stderr.flush()

    @classmethod
    def header(cls, title: str = "灵魂发生器") -> str:
        """显示标题"""
        text = (
            f"\n{cls.CYAN}{cls.BOLD}╔{'═' * 40}╗{cls.RESET}\n"
            f"{cls.CYAN}{cls.BOLD}║ {cls.BRAIN} {title} {cls.BRAIN}{' ' * (32 - len(title))}║{cls.RESET}\n"
            f"{cls.CYAN}{cls.BOLD}╚{'═' * 40}╝{cls.RESET}"
        )
        cls._print(text)
        return text

    @classmethod
    def emotion_analysis(cls, emotion: str, intensity: int, extra: str = "") -> str:
        """情绪分析结果（支持多情绪）"""
        # 根据情绪强度选择颜色
        if intensity >= 70:
            color = cls.MAGENTA  # 强烈情绪
        elif intensity >= 50:
            color = cls.CYAN  # 中等情绪
        else:
            color = cls.GRAY  # 平静

        # 检查是否是多情绪展示
        if " + " in extra or ("多情绪:" in extra and "+" in extra):
            text = f"  {cls.CYAN}{cls.HEART} 情绪分析{cls.RESET} {color}{emotion}{cls.RESET} {cls.DIM}(强度: {intensity}%){cls.RESET}"
            text += f"\n    {cls.DIM}{extra}{cls.RESET}"
        else:
            text = f"  {cls.CYAN}{cls.HEART} 情绪分析{cls.RESET} {color}{emotion}{cls.RESET} {cls.DIM}(强度: {intensity}%){cls.RESET}"
            if extra:
                text += f"\n    {cls.DIM}{extra[:60]}...{cls.RESET}"
        cls._print(text)
        return text

    @classmethod
    def inner_thought(cls, thought: str) -> str:
        """AI内心独白"""
        text = (
            f"