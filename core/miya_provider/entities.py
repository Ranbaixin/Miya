"""
Miya Provider 实体定义
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TokenUsage:
    """Token 使用统计"""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def __post_init__(self):
        if self.total_tokens == 0:
            self.total_tokens = self.prompt_tokens + self.completion_tokens


@dataclass
class LLMResponse:
    """LLM 响应"""

    completion_text: str = ""
    reasoning_content: str = ""
    tool_calls: list[dict] = field(default_factory=list)
    tool_calls_args: list[dict] = field(default_factory=list)
    usage: TokenUsage = field(default_factory=TokenUsage)
    model: str = ""
    finish_reason: str = ""
    extra: dict = field(default_factory=dict)


@dataclass
class ToolCallsResult:
    """工具调用结果"""

    tool_calls_info: dict = field(default_factory=dict)
    tool_calls_result: list[dict] = field(default_factory=list)


@dataclass
class ProviderMeta:
    """Provider 元数据"""

    id: str
    model: str
    type: str
    provider_type: str = "chat_completion"
    display_name: str = ""
    description: str = ""


@dataclass
class RerankResult:
    """重排序结果"""

    index: int
    score: float
    text: str = ""


__all__ = [
    "TokenUsage",
    "LLMResponse",
    "ToolCallsResult",
    "ProviderMeta",
    "RerankResult",
]
