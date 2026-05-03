#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Provider 实体类定义
"""

from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum


class ProviderType(str, Enum):
    """Provider 类型枚举"""

    CHAT_COMPLETION = "chat_completion"
    SPEECH_TO_TEXT = "speech_to_text"
    TEXT_TO_SPEECH = "text_to_speech"
    EMBEDDING = "embedding"
    RERANK = "rerank"


class ProviderStatus(str, Enum):
    """Provider 状态"""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    CIRCUIT_OPEN = "circuit_open"
    LOADING = "loading"


@dataclass
class TokenUsage:
    """Token 使用统计"""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0

    def __post_init__(self):
        if self.total_tokens == 0:
            self.total_tokens = self.input_tokens + self.output_tokens
        if self.prompt_tokens == 0:
            self.prompt_tokens = self.input_tokens
        if self.completion_tokens == 0:
            self.completion_tokens = self.output_tokens


@dataclass
class LLMResponse:
    """LLM 对话响应"""

    role: str = "assistant"
    completion_text: str = ""
    result_chain: Any = None
    tools_call_args: list = field(default_factory=list)
    tools_call_name: list = field(default_factory=list)
    tools_call_ids: list = field(default_factory=list)
    reasoning_content: Optional[str] = None
    raw_completion: Any = None
    usage: TokenUsage = field(default_factory=TokenUsage)

    def __str__(self):
        return f"LLMResponse(text={self.completion_text[:50]}..., tools={len(self.tools_call_name)})"


@dataclass
class ProviderMeta:
    """Provider 元数据"""

    id: str
    model: str
    type: str
    provider_type: ProviderType


@dataclass
class RerankResult:
    """重排序结果"""

    index: int
    text: str
    score: float


@dataclass
class ToolCallsResult:
    """工具调用结果"""

    tool_call_id: str
    tool_name: str
    result: Any


@dataclass
class ProviderConfig:
    """Provider 配置"""

    id: str
    type: str
    model: str
    keys: list = field(default_factory=list)
    api_base: str = ""
    proxy: str = ""
    enable: bool = True
    timeout: float = 60.0
    max_retries: int = 3
    extra: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "ProviderConfig":
        return cls(
            id=data.get("id", ""),
            type=data.get("type", ""),
            model=data.get("model", ""),
            keys=data.get("keys", data.get("key", [])),
            api_base=data.get("api_base", data.get("base_url", "")),
            proxy=data.get("proxy", ""),
            enable=data.get("enable", True),
            timeout=data.get("timeout", 60.0),
            max_retries=data.get("max_retries", 3),
            extra=data.get("extra", {}),
        )


@dataclass
class HealthCheckResult:
    """健康检查结果"""

    provider_id: str
    status: ProviderStatus
    latency_ms: float = 0
    error: Optional[str] = None
    last_check: float = 0

    @property
    def is_healthy(self) -> bool:
        return self.status == ProviderStatus.AVAILABLE
