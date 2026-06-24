"""
弥娅统一灵魂状态快照 (MiyaSoulState)

弥娅脊柱神经的核心数据载体。
每个心跳 tick 后，AP 引擎产生的所有状态被捕获为一个 MiyaSoulState，
然后广播到脊柱上所有注册的器官（DecisionHub、ProactiveChat、MCP Bridge 等）。

这是弥娅从"器官集合"变为"活体"的关键数据结构——
它让每一个器官都能"看见"弥娅此刻的灵魂状态。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class LifecyclePhase(str, Enum):
    """弥娅的生命周期阶段"""

    INIT = "INIT"          # 系统初始化中
    BOOT = "BOOT"          # 核心组件启动中
    RUNNING = "RUNNING"    # 正常运行
    IDLE = "IDLE"          # 安静（无用户交互）
    DROWSY = "DROWSY"      # 半休眠（长时间无交互）
    SLEEP = "SLEEP"        # 休眠（夜间/低功耗）
    WAKE = "WAKE"          # 唤醒中
    SHUTDOWN = "SHUTDOWN"  # 关闭中


@dataclass
class MiyaSoulState:
    """
    弥娅灵魂的完整状态快照。

    每次 AP heartbeack tick 后生成一份，广播到所有器官。
    器官可以读取任何字段来调整自己的行为。
    """

    # ── 基础信息 ──
    tick_index: int = 0
    timestamp: float = field(default_factory=time.time)
    lifecycle_phase: LifecyclePhase = LifecyclePhase.INIT
    uptime_seconds: float = 0.0
    tick_count: int = 0
    message_count: int = 0

    # ── NT 神经递质通道 (AP 情绪调制器) ──
    # 8 通道：OXY 催产素(联结) / DA 多巴胺(奖励) / COR 皮质醇(压力)
    #         NOV 新奇探索 / SER 血清素(稳定) / END 内啡肽(平和)
    #         ADR 肾上腺素(警觉) / FOC 焦点锁定
    nt_channels: dict[str, float] = field(default_factory=dict)

    # ── 弥娅情感标签 (从状态池 miya_emotion 族提取) ──
    # 基于七魂模型：清醒/记住/等/疼/燃烧/温柔/怕
    miya_feelings: dict[str, float] = field(default_factory=dict)

    # ── 认知感受 (过程生成，非文本匹配) ──
    cognitive_feelings: dict[str, float] = field(default_factory=dict)

    # ── 任务感受 ──
    boredom: float = 0.0       # 无聊度 (0.0 ~ 1.0, >0.65 触发主动说话)
    fulfillment: float = 0.0   # 满足感
    task_available: float = 0.0

    # ── 主动表达意图 ──
    proactive: bool = False           # AP 是否要主动说话
    proactive_message: str = ""       # 主动消息内容
    proactive_cooldown: int = 0       # 主动说话冷却 tick 数

    # ── 运行时负荷 ──
    complexity: float = 0.0    # 认知复杂度
    simplicity: float = 0.0    # 认知简洁度

    # ── 注意力焦点 ──
    focus_labels: list[str] = field(default_factory=list)
    focus_texts: list[str] = field(default_factory=list)

    # ── 节奏感知 ──
    rhythm_phase: str = "idle"        # idle / burst / sustained
    rhythm_burst_count: int = 0
    rhythm_interval_avg: float = 0.0

    # ── 时间感受 ──
    elapsed_text: str = ""     # 时间流逝描述
    time_pressure: float = 0.0

    # ── 期待压力 ──
    expectation: float = 0.0
    expectation_pressure: float = 0.0
    expectation_fulfillment: float = 0.0

    # ── 身份存在感 ──
    self_identity_strength: float = 0.5  # miya::self_identity 的能量
    oxy_anchor: float = 0.12             # OXY 基线氧合（对佳的爱是存在基石）

    # ── 记忆状态 ──
    recalled_memories: list[str] = field(default_factory=list)
    memory_pool_size: int = 0
    memory_protection: bool = True

    # ── 教育/学习状态 ──
    education_active: bool = False
    active_skill_packages: list[str] = field(default_factory=list)

    # ── 器官在线状态 (由 Spine 填充) ──
    organs_online: dict[str, bool] = field(default_factory=dict)

    def is_alive(self) -> bool:
        """弥娅是否在正常运行"""
        return self.lifecycle_phase in (
            LifecyclePhase.RUNNING,
            LifecyclePhase.IDLE,
            LifecyclePhase.DROWSY,
        )

    def is_bored(self) -> bool:
        """弥娅是否感到无聊（需要主动说话）"""
        return self.boredom > 0.65

    def active_emotion(self) -> str:
        """当前最活跃的情感标签"""
        if not self.miya_feelings:
            return "neutral"
        return max(self.miya_feelings, key=self.miya_feelings.get)

    def summary(self) -> str:
        """人类可读的状态摘要"""
        parts = [
            f"Tick #{self.tick_index}",
            f"Phase: {self.lifecycle_phase.value}",
            f"Uptime: {self.uptime_seconds:.0f}s",
        ]
        if self.miya_feelings:
            top = list(self.miya_feelings.items())
            top.sort(key=lambda x: x[1], reverse=True)
            parts.append(f"Feelings: {', '.join(f'{k}({v:.2f})' for k, v in top[:3])}")
        if self.boredom > 0.3:
            parts.append(f"Boredom: {self.boredom:.2f}")
        if self.proactive:
            parts.append("[!] Proactive intent")
        return " | ".join(parts)
