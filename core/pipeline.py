"""
弥娅多阶段消息处理管道

借鉴 AstrBot 的多阶段管道理念，提供结构化的消息处理流程。
"""

import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class PipelineStageType(str, Enum):
    """管道阶段类型"""

    PREPROCESS = "preprocess"
    SAFETY_CHECK = "safety_check"
    RATE_LIMIT = "rate_limit"
    WHITELIST = "whitelist"
    WAKING = "waking"
    SESSION_STATUS = "session_status"
    PROCESS = "process"
    RESULT_DECORATE = "result_decorate"
    RESPOND = "respond"


@dataclass
class PipelineContext:
    """管道上下文"""

    message: Any = None
    user_id: Optional[str] = None
    user_name: str = ""
    group_id: Optional[str] = None
    platform: str = "qq"
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 处理结果
    response: Optional[str] = None
    should_respond: bool = True
    skip_remaining: bool = False

    # 错误信息
    error: Optional[str] = None


class PipelineStage(ABC):
    """管道阶段基类"""

    def __init__(self, name: str, stage_type: PipelineStageType):
        self.name = name
        self.stage_type = stage_type
        self.enabled = True

    @abstractmethod
    async def process(self, context: PipelineContext) -> PipelineContext:
        """处理上下文"""
        pass

    async def should_skip(self, context: PipelineContext) -> bool:
        """检查是否跳过此阶段"""
        return context.skip_remaining


class PreprocessStage(PipelineStage):
    """预处理阶段"""

    def __init__(self):
        super().__init__("preprocess", PipelineStageType.PREPROCESS)

    async def process(self, context: PipelineContext) -> PipelineContext:
        """预处理消息"""
        # 提取消息内容
        if hasattr(context.message, "content"):
            context.metadata["content"] = context.message.content

        # 提取用户信息
        if hasattr(context.message, "user_id"):
            context.user_id = context.message.user_id

        if hasattr(context.message, "user_name"):
            context.user_name = context.message.user_name

        if hasattr(context.message, "group_id"):
            context.group_id = context.message.group_id

        if hasattr(context.message, "platform"):
            context.platform = context.message.platform

        logger.debug(f"[Pipeline] 预处理完成: user={context.user_id}")
        return context


class SafetyCheckStage(PipelineStage):
    """安全检查阶段"""

    def __init__(self):
        super().__init__("safety_check", PipelineStageType.SAFETY_CHECK)
        self.blocked_keywords: List[str] = []

    async def process(self, context: PipelineContext) -> PipelineContext:
        """检查消息安全性"""
        content = context.metadata.get("content", "")

        # 检查是否包含敏感词
        for keyword in self.blocked_keywords:
            if keyword in content:
                context.should_respond = False
                context.skip_remaining = True
                context.error = f"消息包含敏感词: {keyword}"
                logger.warning(f"[Pipeline] 安全检查失败: {keyword}")
                return context

        logger.debug("[Pipeline] 安全检查通过")
        return context


class RateLimitStage(PipelineStage):
    """限速阶段"""

    def __init__(self, max_requests: int = 10, time_window: int = 60):
        super().__init__("rate_limit", PipelineStageType.RATE_LIMIT)
        self.max_requests = max_requests
        self.time_window = time_window
        self._requests: Dict[str, List[float]] = {}

    async def process(self, context: PipelineContext) -> PipelineContext:
        """检查请求频率"""
        import time

        user_id = context.user_id or "unknown"
        current_time = time.time()

        # 清理过期记录
        if user_id in self._requests:
            self._requests[user_id] = [
                t
                for t in self._requests[user_id]
                if current_time - t < self.time_window
            ]
        else:
            self._requests[user_id] = []

        # 检查请求频率
        if len(self._requests[user_id]) >= self.max_requests:
            context.should_respond = False
            context.skip_remaining = True
            context.error = "请求过于频繁，请稍后再试"
            logger.warning(f"[Pipeline] 限速: user={user_id}")
            return context

        # 记录请求
        self._requests[user_id].append(current_time)

        logger.debug(f"[Pipeline] 限速检查通过: user={user_id}")
        return context


class WhitelistStage(PipelineStage):
    """白名单阶段"""

    def __init__(self):
        super().__init__("whitelist", PipelineStageType.WHITELIST)
        self._whitelist: set = set()
        self._use_whitelist: bool = False

    def set_whitelist(self, whitelist: List[str]):
        """设置白名单"""
        self._whitelist = set(whitelist)
        self._use_whitelist = len(whitelist) > 0

    async def process(self, context: PipelineContext) -> PipelineContext:
        """检查白名单"""
        if not self._use_whitelist:
            return context

        user_id = context.user_id or ""

        if user_id not in self._whitelist:
            context.should_respond = False
            context.skip_remaining = True
            context.error = "用户不在白名单中"
            logger.warning(f"[Pipeline] 白名单拒绝: user={user_id}")
            return context

        logger.debug(f"[Pipeline] 白名单检查通过: user={user_id}")
        return context


class WakingCheckStage(PipelineStage):
    """唤醒检查阶段"""

    def __init__(self):
        super().__init__("waking_check", PipelineStageType.WAKING)
        self._waking_keywords: List[str] = ["弥娅", "miya", "小弥"]

    def set_waking_keywords(self, keywords: List[str]):
        """设置唤醒关键词"""
        self._waking_keywords = keywords

    async def process(self, context: PipelineContext) -> PipelineContext:
        """检查是否需要唤醒"""
        content = context.metadata.get("content", "")

        # 检查是否包含唤醒词
        needs_waking = any(keyword in content for keyword in self._waking_keywords)

        if needs_waking:
            context.metadata["needs_waking"] = True
            logger.debug(f"[Pipeline] 检测到唤醒词")
        else:
            context.metadata["needs_waking"] = False

        return context


class SessionStatusStage(PipelineStage):
    """会话状态阶段"""

    def __init__(self):
        super().__init__("session_status", PipelineStageType.SESSION_STATUS)

    async def process(self, context: PipelineContext) -> PipelineContext:
        """检查会话状态"""
        # 这里可以添加会话状态检查逻辑
        # 例如：检查会话是否过期、是否有活跃会话等

        logger.debug(f"[Pipeline] 会话状态检查完成")
        return context


class ProcessStage(PipelineStage):
    """处理阶段"""

    def __init__(self, handler: Callable):
        super().__init__("process", PipelineStageType.PROCESS)
        self._handler = handler

    async def process(self, context: PipelineContext) -> PipelineContext:
        """处理消息"""
        try:
            response = await self._handler(context)
            context.response = response
            logger.debug(f"[Pipeline] 处理完成")
        except Exception as e:
            context.error = str(e)
            logger.error(f"[Pipeline] 处理失败: {e}")

        return context


class ResultDecorateStage(PipelineStage):
    """结果装饰阶段"""

    def __init__(self):
        super().__init__("result_decorate", PipelineStageType.RESULT_DECORATE)

    async def process(self, context: PipelineContext) -> PipelineContext:
        """装饰处理结果"""
        if context.response:
            # 这里可以添加结果装饰逻辑
            # 例如：添加表情、格式化等
            pass

        logger.debug(f"[Pipeline] 结果装饰完成")
        return context


class RespondStage(PipelineStage):
    """响应阶段"""

    def __init__(self, responder: Callable):
        super().__init__("respond", PipelineStageType.RESPOND)
        self._responder = responder

    async def process(self, context: PipelineContext) -> PipelineContext:
        """发送响应"""
        if context.should_respond and context.response:
            try:
                await self._responder(context)
                logger.debug(f"[Pipeline] 响应发送完成")
            except Exception as e:
                logger.error(f"[Pipeline] 响应发送失败: {e}")

        return context


class Pipeline:
    """消息处理管道"""

    def __init__(self, name: str = "default"):
        self.name = name
        self._stages: List[PipelineStage] = []
        self._initialized = False

    def add_stage(self, stage: PipelineStage):
        """添加阶段"""
        self._stages.append(stage)
        # 按类型排序
        self._stages.sort(key=lambda s: list(PipelineStageType).index(s.stage_type))
        logger.debug(f"[Pipeline] 添加阶段: {stage.name}")

    async def process(self, context: PipelineContext) -> PipelineContext:
        """处理消息"""
        logger.info(f"[Pipeline] 开始处理: {self.name}")

        for stage in self._stages:
            if not stage.enabled:
                continue

            # 检查是否跳过
            if await stage.should_skip(context):
                logger.debug(f"[Pipeline] 跳过阶段: {stage.name}")
                continue

            # 处理
            try:
                context = await stage.process(context)
                logger.debug(f"[Pipeline] 阶段完成: {stage.name}")
            except Exception as e:
                logger.error(f"[Pipeline] 阶段失败 {stage.name}: {e}")
                context.error = str(e)
                break

        logger.info(f"[Pipeline] 处理完成: {self.name}")
        return context


class PipelineManager:
    """管道管理器"""

    def __init__(self):
        self._pipelines: Dict[str, Pipeline] = {}

    def create_pipeline(self, name: str) -> Pipeline:
        """创建管道"""
        pipeline = Pipeline(name)
        self._pipelines[name] = pipeline
        return pipeline

    def get_pipeline(self, name: str) -> Optional[Pipeline]:
        """获取管道"""
        return self._pipelines.get(name)

    def list_pipelines(self) -> List[str]:
        """列出所有管道"""
        return list(self._pipelines.keys())


# 全局实例
_pipeline_manager: Optional[PipelineManager] = None


def get_pipeline_manager() -> PipelineManager:
    """获取全局管道管理器"""
    global _pipeline_manager
    if _pipeline_manager is None:
        _pipeline_manager = PipelineManager()
    return _pipeline_manager


def create_default_pipeline(handler: Callable, responder: Callable) -> Pipeline:
    """创建默认管道"""
    manager = get_pipeline_manager()
    pipeline = manager.create_pipeline("default")

    # 添加默认阶段
    pipeline.add_stage(PreprocessStage())
    pipeline.add_stage(SafetyCheckStage())
    pipeline.add_stage(RateLimitStage())
    pipeline.add_stage(WakingCheckStage())
    pipeline.add_stage(SessionStatusStage())
    pipeline.add_stage(ProcessStage(handler))
    pipeline.add_stage(ResultDecorateStage())
    pipeline.add_stage(RespondStage(responder))

    return pipeline


# 导出
__all__ = [
    "PipelineStageType",
    "PipelineContext",
    "PipelineStage",
    "PreprocessStage",
    "SafetyCheckStage",
    "RateLimitStage",
    "WhitelistStage",
    "WakingCheckStage",
    "SessionStatusStage",
    "ProcessStage",
    "ResultDecorateStage",
    "RespondStage",
    "Pipeline",
    "PipelineManager",
    "get_pipeline_manager",
    "create_default_pipeline",
]
