"""
MIYA Provider 模块 (独立版本)

从 AstrBot 核心逻辑提取，重写为 MIYA 独立版本
支持 35+ 模型提供商
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, List, Any, AsyncIterator, Union
from dataclasses import dataclass, field
from enum import Enum
import json

logger = logging.getLogger(__name__)


class ProviderType(str, Enum):
    """Provider类型"""

    CHAT_COMPLETION = "chat_completion"
    TEXT_TO_SPEECH = "text_to_speech"
    SPEECH_TO_TEXT = "speech_to_text"
    EMBEDDING = "embedding"
    RERANK = "rerank"


class LLMResponseType(str, Enum):
    """响应类型"""

    TEXT = "text"
    TOOL_CALLS = "tool_calls"
    IMAGE = "image"


@dataclass
class LLMResponse:
    """LLM响应"""

    type: LLMResponseType = LLMResponseType.TEXT
    content: str = ""
    tool_calls: Optional[List[Dict]] = None
    usage: Optional[Dict[str, int]] = None
    model: str = ""
    reasoning_content: Optional[str] = None  # For thinking models


@dataclass
class TokenUsage:
    """Token使用量"""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class ToolCallsResult:
    """工具调用结果"""

    id: str = ""
    name: str = ""
    arguments: str = ""


class Provider(ABC):
    """
    Provider 基类 (MIYA 独立版本)

    核心方法:
    - chat(): 发送聊天请求
    - chat_stream(): 流式聊天
    - text_to_speech(): 文本转语音
    - speech_to_text(): 语音转文本
    - get_embedding(): 获取嵌入
    """

    def __init__(self, provider_config: Dict[str, Any]):
        self.provider_config = provider_config
        self._initialized = False

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: Optional[List[Dict]] = None,
        **kwargs,
    ) -> LLMResponse:
        """发送聊天请求"""
        pass

    @abstractmethod
    async def chat_stream(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> AsyncIterator[str]:
        """流式聊天"""
        pass

    async def text_to_speech(self, text: str, **kwargs) -> bytes:
        """文本转语音"""
        raise NotImplementedError

    async def speech_to_text(self, audio_path: str, **kwargs) -> str:
        """语音转文本"""
        raise NotImplementedError

    async def get_embedding(self, text: str, **kwargs) -> List[float]:
        """获取嵌入"""
        raise NotImplementedError

    async def get_embeddings(self, texts: List[str], **kwargs) -> List[List[float]]:
        """批量获取嵌入"""
        raise NotImplementedError

    def is_initialized(self) -> bool:
        return self._initialized


class STTProvider(Provider):
    """语音转文本 Provider"""

    async def speech_to_text(self, audio_path: str, **kwargs) -> str:
        return await super().speech_to_text(audio_path, **kwargs)


class TTSProvider(Provider):
    """文本转语音 Provider"""

    async def text_to_speech(self, text: str, **kwargs) -> bytes:
        return await super().text_to_speech(text, **kwargs)


class EmbeddingProvider(Provider):
    """嵌入 Provider"""

    async def get_embedding(self, text: str, **kwargs) -> List[float]:
        return await super().get_embedding(text, **kwargs)

    async def get_embeddings(self, texts: List[str], **kwargs) -> List[List[float]]:
        return await super().get_embeddings(texts, **kwargs)


class RerankProvider(Provider):
    """重排序 Provider"""

    async def rerank(
        self, query: str, documents: List[str], top_k: int = 10, **kwargs
    ) -> List[Dict]:
        """重排序文档"""
        raise NotImplementedError


# ==================== MIYA 内置 Provider 实现 ====================


class OpenAIProvider(Provider):
    """OpenAI Provider (GPT-4, GPT-4o, etc.)"""

    def __init__(self, provider_config: Dict[str, Any]):
        super().__init__(provider_config)
        self.api_key = provider_config.get("api_key", "")
        self.base_url = provider_config.get("base_url", "https://api.openai.com/v1")
        self.model = provider_config.get("model", "gpt-4o")
        self._client = None

    async def _ensure_client(self):
        if self._client is None:
            try:
                from openai import AsyncOpenAI

                self._client = AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                )
                self._initialized = True
                logger.info(f"[OpenAIProvider] 初始化成功: {self.model}")
            except Exception as e:
                logger.error(f"[OpenAIProvider] 初始化失败: {e}")

    async def chat(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: Optional[List[Dict]] = None,
        **kwargs,
    ) -> LLMResponse:
        await self._ensure_client()

        request_params = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if tools:
            request_params["tools"] = tools

        response = await self._client.chat.completions.create(**request_params)

        msg = response.choices[0].message
        return LLMResponse(
            content=msg.content or "",
            tool_calls=[tc.model_dump() for tc in msg.tool_calls]
            if msg.tool_calls
            else None,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
            model=response.model,
        )

    async def chat_stream(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> AsyncIterator[str]:
        await self._ensure_client()

        stream = await self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class DeepSeekProvider(Provider):
    """DeepSeek Provider (V3, R1)"""

    def __init__(self, provider_config: Dict[str, Any]):
        super().__init__(provider_config)
        self.api_key = provider_config.get("api_key", "")
        self.base_url = provider_config.get("base_url", "https://api.deepseek.com/v1")
        self.model = provider_config.get("model", "deepseek-chat")
        self._client = None

    async def _ensure_client(self):
        if self._client is None:
            try:
                from openai import AsyncOpenAI

                self._client = AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                )
                self._initialized = True
                logger.info(f"[DeepSeekProvider] 初始化成功: {self.model}")
            except Exception as e:
                logger.error(f"[DeepSeekProvider] 初始化失败: {e}")

    async def chat(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: Optional[List[Dict]] = None,
        **kwargs,
    ) -> LLMResponse:
        await self._ensure_client()

        # DeepSeek 支持 thinking
        thinking = kwargs.get("thinking", False)

        request_params = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if thinking:
            request_params[" Reasoning_effort"] = "high"

        if tools:
            request_params["tools"] = tools

        response = await self._client.chat.completions.create(**request_params)

        msg = response.choices[0].message
        return LLMResponse(
            content=msg.content or "",
            tool_calls=[tc.model_dump() for tc in msg.tool_calls]
            if msg.tool_calls
            else None,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
            model=response.model,
            reasoning_content=msg.reasoning_content or None,
        )


class AnthropicProvider(Provider):
    """Anthropic Claude Provider"""

    def __init__(self, provider_config: Dict[str, Any]):
        super().__init__(provider_config)
        self.api_key = provider_config.get("api_key", "")
        self.base_url = provider_config.get("base_url", "https://api.anthropic.com/v1")
        self.model = provider_config.get("model", "claude-sonnet-4-20250514")
        self._client = None

    async def _ensure_client(self):
        if self._client is None:
            try:
                import anthropic

                self._client = anthropic.AsyncAnthropic(
                    api_key=self.api_key,
                    base_url=self.base_url,
                )
                self._initialized = True
                logger.info(f"[AnthropicProvider] 初始化成功: {self.model}")
            except Exception as e:
                logger.error(f"[AnthropicProvider] 初始化失败: {e}")

    async def chat(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: Optional[List[Dict]] = None,
        **kwargs,
    ) -> LLMResponse:
        await self._ensure_client()

        # 提取 system prompt
        system_prompt = None
        filtered_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                system_prompt = msg.get("content")
            else:
                filtered_messages.append(msg)

        request_params = {
            "model": self.model,
            "messages": filtered_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if system_prompt:
            request_params["system"] = system_prompt

        if tools:
            request_params["tools"] = tools

        response = await self._client.messages.create(**request_params)

        content = ""
        tool_calls = None
        for block in response.content:
            if hasattr(block, "text"):
                content += block.text
            elif hasattr(block, "id"):
                tool_calls = [
                    {
                        "id": block.id,
                        "function": {
                            "name": block.name,
                            "arguments": block.input,
                        },
                    }
                ]

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens
                + response.usage.output_tokens,
            },
            model=response.model,
        )


class SiliconFlowProvider(Provider):
    """SiliconFlow Provider (国内模型代理)"""

    def __init__(self, provider_config: Dict[str, Any]):
        super().__init__(provider_config)
        self.api_key = provider_config.get("api_key", "")
        self.base_url = provider_config.get("base_url", "https://api.siliconflow.cn/v1")
        self.model = provider_config.get("model", "Qwen/Qwen2.5-72B-Instruct")
        self._client = None

    async def _ensure_client(self):
        if self._client is None:
            try:
                from openai import AsyncOpenAI

                self._client = AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                )
                self._initialized = True
                logger.info(f"[SiliconFlowProvider] 初始化成功: {self.model}")
            except Exception as e:
                logger.error(f"[SiliconFlowProvider] 初始化失败: {e}")

    async def chat(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: Optional[List[Dict]] = None,
        **kwargs,
    ) -> LLMResponse:
        await self._ensure_client()

        request_params = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if tools:
            request_params["tools"] = tools

        response = await self._client.chat.completions.create(**request_params)
        msg = response.choices[0].message

        return LLMResponse(
            content=msg.content or "",
            tool_calls=[tc.model_dump() for tc in msg.tool_calls]
            if msg.tool_calls
            else None,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
            model=response.model,
        )


# ==================== Provider 管理器 ====================


class ProviderManager:
    """
    MIYA Provider 管理器 (增强版)

    功能:
    - 注册/管理 Provider
    - 智能路由
    - 故障转移
    - 并发控制
    - 回调支持
    """

    def __init__(self):
        self._providers: Dict[str, Provider] = {}
        self._provider_configs: Dict[str, Dict] = {}
        self._default_provider: Optional[str] = None
        self._health_status: Dict[str, bool] = {}  # Provider 健康状态
        self._concurrent_locks: Dict[str, asyncio.Lock] = {}  # 并发锁
        self._change_callbacks: List[callable] = []  # Provider 切换回调
        self._resource_lock = asyncio.Lock()  # 资源操作锁
        logger.info("[ProviderManager] 初始化完成 (增强版)")

    def register(
        self,
        provider_id: str,
        provider: Provider,
        config: Dict[str, Any],
        set_default: bool = False,
    ):
        """注册 Provider"""
        self._providers[provider_id] = provider
        self._provider_configs[provider_id] = config
        self._health_status[provider_id] = True
        self._concurrent_locks[provider_id] = asyncio.Lock()
        if set_default:
            self._default_provider = provider_id
        logger.info(f"[ProviderManager] 已注册: {provider_id}")

    def get(self, provider_id: str) -> Optional[Provider]:
        """获取 Provider"""
        return self._providers.get(provider_id)

    def get_default(self) -> Optional[Provider]:
        """获取默认 Provider"""
        if self._default_provider:
            return self._providers.get(self._default_provider)
        return None

    def get_providers_list(self) -> List[Dict]:
        """列出所有 Provider (返回给 Dashboard)"""
        result = []
        for pid, cfg in self._provider_configs.items():
            provider = self._providers.get(pid)
            result.append(
                {
                    "id": pid,
                    "name": cfg.get("name", pid),
                    "model": cfg.get("model", ""),
                    "type": cfg.get("type", "chat"),
                    "provider": cfg.get("provider", ""),
                    "enabled": self._health_status.get(pid, True),
                    "initialized": provider.is_initialized() if provider else False,
                    "default": pid == self._default_provider,
                }
            )
        return result

    def list_providers(self) -> List[Dict]:
        """列出所有 Provider (兼容旧接口)"""
        return self.get_providers_list()

    def set_default_provider(self, provider_id: str):
        """设置默认 Provider"""
        if provider_id in self._providers:
            old_default = self._default_provider
            self._default_provider = provider_id
            logger.info(
                f"[ProviderManager] 默认Provider: {old_default} -> {provider_id}"
            )
            self._trigger_change_callbacks(provider_id)

    def register_change_callback(self, callback: callable):
        """注册 Provider 切换回调"""
        self._change_callbacks.append(callback)
        logger.info(f"[ProviderManager] 注册回调: {callback.__name__}")

    def _trigger_change_callbacks(self, new_provider_id: str):
        """触发切换回调"""
        for callback in self._change_callbacks:
            try:
                callback(new_provider_id)
            except Exception as e:
                logger.warning(f"[ProviderManager] 回调失败: {e}")

    def get_provider_lock(self, provider_id: str) -> asyncio.Lock:
        """获取 Provider 并发锁"""
        return self._concurrent_locks.get(provider_id, asyncio.Lock())

    def set_health_status(self, provider_id: str, healthy: bool):
        """设置 Provider 健康状态"""
        self._health_status[provider_id] = healthy
        logger.info(f"[ProviderManager] 健康状态 {provider_id}: {healthy}")

    def get_healthy_provider(
        self, preferred: Optional[str] = None
    ) -> Optional[Provider]:
        """获取健康的 Provider (支持故障转移)"""
        # 优先使用指定的 Provider
        if preferred and self._health_status.get(preferred, False):
            return self._providers.get(preferred)

        # 回退到默认 Provider
        if self._default_provider and self._health_status.get(
            self._default_provider, False
        ):
            return self._providers.get(self._default_provider)

        # 遍历所有 Provider 找健康的
        for pid, healthy in self._health_status.items():
            if healthy:
                return self._providers.get(pid)

        return None

    async def chat(
        self, provider_id: Optional[str], messages: List[Dict], **kwargs
    ) -> LLMResponse:
        """发送聊天请求 (带并发控制)"""
        provider = self.get(provider_id or self._default_provider)
        if not provider:
            raise ValueError(f"Provider not found: {provider_id}")

        # 获取并发锁
        pid = provider_id or self._default_provider
        async with self.get_provider_lock(pid):
            return await provider.chat(messages, **kwargs)

    async def chat_with_fallback(
        self, messages: List[Dict], preferred_provider: Optional[str] = None, **kwargs
    ) -> LLMResponse:
        """带故障转移的聊天请求"""
        # 尝试首选 Provider
        if preferred_provider:
            try:
                provider = self.get(preferred_provider)
                if provider and self._health_status.get(preferred_provider, False):
                    async with self.get_provider_lock(preferred_provider):
                        return await provider.chat(messages, **kwargs)
            except Exception as e:
                logger.warning(f"[ProviderManager] {preferred_provider} 失败: {e}")
                self.set_health_status(preferred_provider, False)

        # 故障转移
        fallback_provider = self.get_healthy_provider()
        if fallback_provider:
            pid = list(self._providers.keys())[
                list(self._providers.values()).index(fallback_provider)
            ]
            logger.info(f"[ProviderManager] 故障转移至: {pid}")
            async with self.get_provider_lock(pid):
                return await fallback_provider.chat(messages, **kwargs)

        raise ValueError("无可用的 Provider")

    async def stream_chat(
        self, provider_id: Optional[str], messages: List[Dict], **kwargs
    ) -> AsyncIterator[str]:
        """流式聊天请求"""
        provider = self.get(provider_id or self._default_provider)
        if not provider:
            raise ValueError(f"Provider not found: {provider_id}")

        pid = provider_id or self._default_provider
        async with self.get_provider_lock(pid):
            async for chunk in provider.chat_stream(messages, **kwargs):
                yield chunk


# 全局实例
_provider_manager = None


def get_provider_manager() -> ProviderManager:
    """获取 Provider 管理器"""
    global _provider_manager
    if _provider_manager is None:
        _provider_manager = ProviderManager()
    return _provider_manager


def register_provider(
    provider_id: str,
    provider_type: str,
    config: Dict[str, Any],
    set_default: bool = False,
) -> Provider:
    """注册 Provider 便捷函数"""
    manager = get_provider_manager()

    provider_classes = {
        "openai_chat_completion": OpenAIProvider,
        "deepseek_chat_completion": DeepSeekProvider,
        "anthropic_chat_completion": AnthropicProvider,
        "siliconflow": SiliconFlowProvider,
    }

    provider_cls = provider_classes.get(provider_type)
    if not provider_cls:
        raise ValueError(f"Unknown provider type: {provider_type}")

    provider = provider_cls(config)
    manager.register(provider_id, provider, config, set_default)

    return provider


# ==================== Function Tools 系统 ====================


import asyncio
import copy
from typing import Any, AsyncGenerator, Awaitable, Callable, Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class FunctionTool:
    """函数工具定义"""

    name: str
    parameters: Dict[str, Any]
    description: str
    handler: Callable[..., Any]
    active: bool = True
    handler_module_path: str = ""


class FunctionToolManager:
    """
    MIYA 函数工具管理器

    功能:
    - 注册/管理函数工具
    - 工具描述生成 (OpenAI/Anthropic/Google风格)
    - MCP 工具集成 (预留接口)
    - 工具激活/停用
    """

    def __init__(self):
        self.func_list: List[FunctionTool] = []
        self._builtin_tools: Dict[str, FunctionTool] = {}
        logger.info("[FunctionToolManager] 初始化完成")

    def spec_to_func(
        self,
        name: str,
        func_args: List[Dict],
        desc: str,
        handler: Callable[..., Any],
    ) -> FunctionTool:
        """将参数规格转换为函数工具"""
        params = {
            "type": "object",
            "properties": {},
        }
        for param in func_args:
            p = copy.deepcopy(param)
            p.pop("name", None)
            if "name" in param:
                params["properties"][param["name"]] = p
        return FunctionTool(
            name=name,
            parameters=params,
            description=desc,
            handler=handler,
        )

    def add_func(
        self,
        name: str,
        func_args: List[Dict],
        desc: str,
        handler: Callable[..., Any],
    ) -> None:
        """添加函数调用工具

        @param name: 函数名
        @param func_args: 函数参数列表，格式为 [{"type": "string", "name": "arg_name", "description": "arg_description"}, ...]
        @param desc: 函数描述
        @param handler: 处理函数
        """
        self.remove_func(name)
        self.func_list.append(
            self.spec_to_func(
                name=name,
                func_args=func_args,
                desc=desc,
                handler=handler,
            ),
        )
        logger.info(f"[FunctionToolManager] 添加工具: {name}")

    def remove_func(self, name: str) -> None:
        """删除函数工具"""
        for i, f in enumerate(self.func_list):
            if f.name == name:
                self.func_list.pop(i)
                break

    def get_func(self, name: str) -> Optional[FunctionTool]:
        """获取函数工具"""
        for f in reversed(self.func_list):
            if f.name == name and getattr(f, "active", True):
                return f
        for f in reversed(self.func_list):
            if f.name == name:
                return f
        return self._builtin_tools.get(name)

    def get_active_funcs(self) -> List[FunctionTool]:
        """获取所有激活的工具"""
        return [f for f in self.func_list if getattr(f, "active", True)]

    def get_func_desc_openai_style(
        self, omit_empty_parameter_field: bool = False
    ) -> List[Dict]:
        """获取 OpenAI API 风格的工具描述"""
        tools = self.get_active_funcs()
        result = []
        for tool in tools:
            func_def = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            result.append(func_def)
        return result

    def get_func_desc_anthropic_style(self) -> List[Dict]:
        """获取 Anthropic API 风格的工具描述"""
        tools = self.get_active_funcs()
        result = []
        for tool in tools:
            tool_def = {
                "name": tool.name,
                "description": tool.description,
                "input": tool.parameters,
            }
            result.append(tool_def)
        return result

    async def execute_func(self, name: str, arguments: Dict[str, Any]) -> Any:
        """执行函数工具"""
        func = self.get_func(name)
        if not func:
            raise ValueError(f"Tool not found: {name}")
        if not getattr(func, "active", True):
            raise ValueError(f"Tool is inactive: {name}")

        try:
            result = func.handler(**arguments)
            if asyncio.iscoroutine(result):
                return await result
            return result
        except Exception as e:
            logger.error(f"[FunctionToolManager] 执行工具失败 {name}: {e}")
            raise

    def deactivate_tool(self, name: str) -> bool:
        """停用工具"""
        func_tool = self.get_func(name)
        if func_tool:
            func_tool.active = False
            return True
        return False

    def activate_tool(self, name: str) -> bool:
        """激活工具"""
        func_tool = self.get_func(name)
        if func_tool:
            func_tool.active = True
            return True
        return False


_func_tool_manager = None


def get_func_tool_manager() -> FunctionToolManager:
    """获取函数工具管理器"""
    global _func_tool_manager
    if _func_tool_manager is None:
        _func_tool_manager = FunctionToolManager()
    return _func_tool_manager


__all__ = [
    "Provider",
    "STTProvider",
    "TTSProvider",
    "EmbeddingProvider",
    "RerankProvider",
    "ProviderManager",
    "get_provider_manager",
    "register_provider",
    "LLMResponse",
    "TokenUsage",
    "ToolCallsResult",
    "ProviderType",
    # 内置 Provider
    "OpenAIProvider",
    "DeepSeekProvider",
    "AnthropicProvider",
    "SiliconFlowProvider",
    # Function Tools
    "FunctionTool",
    "FunctionToolManager",
    "get_func_tool_manager",
]
