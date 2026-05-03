#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Provider 注册装饰器

使用装饰器自动注册 Provider 类型
"""

import logging
from dataclasses import dataclass
from typing import Optional, Type

from .entities import ProviderType

logger = logging.getLogger(__name__)

provider_cls_map: dict[str, "ProviderMetaData"] = {}


@dataclass
class ProviderMetaData:
    """Provider 元数据"""

    type: str
    provider_type: ProviderType
    cls_type: Optional[Type] = None
    id: str = ""
    name: str = ""
    description: str = ""


def register_provider(
    provider_type: str,
    provider_type_enum: ProviderType,
    name: str = "",
    description: str = "",
) -> callable:
    """注册 Provider 的装饰器

    Args:
        provider_type: Provider 类型标识 (如 "openai_chat_completion")
        provider_type_enum: Provider 类型枚举
        name: Provider 名称
        description: Provider 描述

    Usage:
        @register_provider("openai_chat_completion", ProviderType.CHAT_COMPLETION, name="OpenAI")
        class OpenAIProvider(Provider):
            ...
    """

    def decorator(cls: Type) -> Type:
        metadata = ProviderMetaData(
            type=provider_type,
            provider_type=provider_type_enum,
            cls_type=cls,
            name=name or cls.__name__,
            description=description,
        )
        provider_cls_map[provider_type] = metadata
        logger.debug(
            f"[ProviderRegistry] 注册 Provider: {provider_type} -> {cls.__name__}"
        )
        return cls

    return decorator


def get_provider_metadata(provider_type: str) -> Optional[ProviderMetaData]:
    """获取 Provider 元数据"""
    return provider_cls_map.get(provider_type)


def list_provider_types(provider_type_enum: Optional[ProviderType] = None) -> list[str]:
    """列出所有注册的 Provider 类型"""
    if provider_type_enum is None:
        return list(provider_cls_map.keys())
    return [
        pt
        for pt, meta in provider_cls_map.items()
        if meta.provider_type == provider_type_enum
    ]


def unregister_provider(provider_type: str) -> bool:
    """取消注册 Provider"""
    if provider_type in provider_cls_map:
        del provider_cls_map[provider_type]
        return True
    return False


CHAT_COMPLETION_TYPES = [
    "openai_chat_completion",
    "deepseek_chat_completion",
    "anthropic_chat_completion",
    "zhipu_chat_completion",
    "siliconflow_chat_completion",
    "gemini_chat_completion",
    "groq_chat_completion",
    "openrouter_chat_completion",
    "kimi_chat_completion",
    "qwen_chat_completion",
    "local_chat_completion",
]

STT_TYPES = [
    "openai_whisper_api",
    "sensevoice_selfhost",
    "xinference_stt",
]

TTS_TYPES = [
    "openai_tts_api",
    "edge_tts",
    "minimax_tts_api",
    "fishaudio_tts_api",
    "azure_tts",
]

EMBEDDING_TYPES = [
    "openai_embedding",
    "gemini_embedding",
    "xinference_embedding",
]

RERANK_TYPES = [
    "vllm_rerank",
    "xinference_rerank",
    "bailian_rerank",
]
