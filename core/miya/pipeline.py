"""
消息流水线 - Pipeline
"""

import logging
from typing import Any, Callable, List

logger = logging.getLogger("miya.pipeline")

PIPELINE_STAGES = [
    "preprocess",  # 预处理
    "whitelist",  # 白名单检查
    "safety",  # 内容安全
    "rate_limit",  # 限流检查
    "wake",  # 唤醒词检查
    "session",  # 会话状态
    "process",  # 核心处理
    "response",  # 响应生成
    "decorate",  # 结果装饰
]


class Pipeline:
    """消息流水线"""

    def __init__(self) -> None:
        self._stages: List[Callable] = []

    async def initialize(self) -> None:
        """初始化"""
        logger.info("[Pipeline] 初始化 9 阶段流水线")

        # 预留实现
        for stage in PIPELINE_STAGES:
            logger.debug(f"  - {stage}")

    async def process(self, message: Any) -> Any:
        """处理消息"""
        return message


_pipeline: Any = None


def get_pipeline() -> Pipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = Pipeline()
    return _pipeline


__all__ = ["Pipeline", "get_pipeline", "PIPELINE_STAGES"]
