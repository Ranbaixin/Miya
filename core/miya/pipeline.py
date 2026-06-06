"""
消息流水线 v9.0 — AP 认知驱动

弥娅 v9.0 重构：用 APV2.1 认知环替代 9 级线性管道

架构：Sensors → Attention → Memory Recall → Cognition → Rules → Channels → Actions

(保留旧 PIPELINE_STAGES 常量兼容)
"""

from __future__ import annotations

import logging
from enum import Enum, auto
from typing import Any

logger = logging.getLogger("miya.pipeline")

# 旧管道常量（向后兼容）
PIPELINE_STAGES = [
    "preprocess",
    "whitelist",
    "safety",
    "rate_limit",
    "wake",
    "session",
    "process",
    "response",
    "decorate",
]


class APStage(Enum):
    """APV2.1 认知环阶段"""

    INGEST = auto()  # Sensors 感知摄入
    FAST_RECALL = auto()  # 快速记忆回溯
    ATTENTION = auto()  # 注意力调度
    COGNITION = auto()  # 认知感知 (通道驱动)
    RULES = auto()  # 天生规则 & 情绪调制
    DECISION = auto()  # 决策 & 行动预选
    GENERATION = auto()  # 行动规划 & 执行 (LLM/工具)
    MEMORY_WRITE = auto()  # 记忆写入 & 索引
    TICK_END = auto()  # 周期收尾 & 学习事件

    @classmethod
    def pipeline_order(cls) -> list[APStage]:
        return [
            cls.INGEST,
            cls.FAST_RECALL,
            cls.ATTENTION,
            cls.COGNITION,
            cls.RULES,
            cls.DECISION,
            cls.GENERATION,
            cls.MEMORY_WRITE,
            cls.TICK_END,
        ]


class Pipeline:
    """消息流水线 — APV2.1 认知驱动"""

    def __init__(self, use_ap: bool = True):
        self.use_ap = use_ap
        self._psyarch_bridge: Any = None
        self._stages: list[Any] = []
        self._initialized = False

    async def initialize(self) -> None:
        if self.use_ap:
            await self._init_ap_bridge()
        self._initialized = True
        logger.info(f"[Pipeline] AP 认知驱动: {'启用' if self.use_ap else '旧模式'}")

    async def _init_ap_bridge(self) -> None:
        """初始化 APV2.1 认知引擎桥接"""
        try:
            from core.miya_psyarch_bridge import get_psyarch_bridge

            self._psyarch_bridge = get_psyarch_bridge()
            logger.info("[Pipeline] APV2.1 桥接层就绪")
        except Exception as e:
            logger.warning(f"[Pipeline] AP 桥接失败, 降级: {e}")
            self.use_ap = False

    async def process(self, message: Any) -> Any:
        """处理消息 — AP 认知环入口"""
        if not self._initialized:
            await self.initialize()

        if self.use_ap and self._psyarch_bridge:
            return await self._process_ap(message)
        return self._process_simple(message)

    async def _process_ap(self, message: Any) -> dict[str, Any]:
        """通过 AP 认知环处理"""
        content = self._extract_content(message)

        try:
            result = self._psyarch_bridge.process_message(content)
            reply, soul_state = result if isinstance(result, tuple) else (result, {})

            return {
                "response": reply,
                "soul_state": soul_state,
                "stage": "ap_complete",
            }
        except Exception as e:
            logger.warning(f"[Pipeline] AP 处理失败: {e}")
            return {"response": None, "soul_state": {}, "stage": "ap_error"}

    async def _process_simple(self, message: Any) -> Any:
        """简单传递（无 AP）"""
        return message

    def _extract_content(self, message: Any) -> str:
        if isinstance(message, str):
            return message
        if isinstance(message, dict):
            content = message.get("content", message.get("input", ""))
            if isinstance(content, list):
                return str(content)
            return str(content)
        if hasattr(message, "content"):
            c = message.content
            if isinstance(c, dict):
                return str(c.get("content", c.get("input", str(c))))
            return str(c)
        return str(message)

    def get_psyarch_bridge(self) -> Any:
        return self._psyarch_bridge

    def is_ap_ready(self) -> bool:
        return self.use_ap and self._psyarch_bridge is not None


_pipeline: Pipeline | None = None


def get_pipeline() -> Pipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = Pipeline(use_ap=True)
    return _pipeline


__all__ = [
    "Pipeline",
    "get_pipeline",
    "PIPELINE_STAGES",
    "APStage",
]
