"""
AstrBot Provider 适配器

将 AstrBot 的模型源适配到弥娅的 Provider 接口。
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional

logger = logging.getLogger(__name__)


class AstrBotProviderAdapter(ABC):
    """
    AstrBot Provider 适配器基类

    将 AstrBot 的 Provider 接口适配到弥娅的 Provider 接口。
    """

    def __init__(self, astrbot_provider, config: Dict[str, Any]):
        self._astrbot_provider = astrbot_provider
        self._config = config
        self._initialized = False

    @property
    def provider_id(self) -> str:
        """获取 Provider ID"""
        return self._config.get("id", "unknown")

    @property
    def provider_name(self) -> str:
        """获取 Provider 名称"""
        return self._config.get("name", self.provider_id)

    @property
    def model_name(self) -> str:
        """获取模型名称"""
        return self._config.get("model", "unknown")

    async def initialize(self) -> bool:
        """初始化 Provider"""
        try:
            if hasattr(self._astrbot_provider, "initialize"):
                await self._astrbot_provider.initialize()
            self._initialized = True
            return True
        except Exception as e:
            logger.error(f"[{self.provider_id}] 初始化失败: {e}")
            return False

    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: Optional[List[Dict]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """发送聊天请求"""
        pass

    @abstractmethod
    async def chat_stream(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: Optional[List[Dict]] = None,
        **kwargs,
    ) -> AsyncIterator[Dict[str, Any]]:
        """流式聊天"""
        pass


class OpenAICompatibleAdapter(AstrBotProviderAdapter):
    """
    OpenAI 兼容 Provider 适配器

    适配所有 OpenAI 兼容的 Provider（OpenAI、DeepSeek、SiliconFlow 等）。
    """

    async def chat(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: Optional[List[Dict]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """发送聊天请求"""
        try:
            # 调用 AstrBot Provider 的 chat 方法
            if hasattr(self._astrbot_provider, "chat"):
                response = await self._astrbot_provider.chat(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    tools=tools,
                    **kwargs,
                )

                # 转换响应格式
                if hasattr(response, "content"):
                    return {
                        "content": response.content,
                        "tool_calls": getattr(response, "tool_calls", None),
                        "usage": getattr(response, "usage", None),
                        "model": getattr(response, "model", self.model_name),
                    }
                elif isinstance(response, dict):
                    return response
                else:
                    return {"content": str(response)}

            raise NotImplementedError("Provider does not support chat method")

        except Exception as e:
            logger.error(f"[{self.provider_id}] Chat failed: {e}")
            raise

    async def chat_stream(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: Optional[List[Dict]] = None,
        **kwargs,
    ) -> AsyncIterator[Dict[str, Any]]:
        """流式聊天"""
        try:
            # 调用 AstrBot Provider 的 chat_stream 方法
            if hasattr(self._astrbot_provider, "chat_stream"):
                async for chunk in self._astrbot_provider.chat_stream(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    tools=tools,
                    **kwargs,
                ):
                    if hasattr(chunk, "content"):
                        yield {
                            "content": chunk.content,
                            "tool_calls": getattr(chunk, "tool_calls", None),
                            "finish_reason": getattr(chunk, "finish_reason", None),
                        }
                    elif isinstance(chunk, dict):
                        yield chunk
                    else:
                        yield {"content": str(chunk)}
            else:
                # 如果没有 stream 方法，使用普通 chat 并模拟流式
                response = await self.chat(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    tools=tools,
                    **kwargs,
                )
                yield response

        except Exception as e:
            logger.error(f"[{self.provider_id}] Chat stream failed: {e}")
            raise


class AnthropicAdapter(AstrBotProviderAdapter):
    """
    Anthropic Provider 适配器

    适配 Anthropic Claude 模型。
    """

    async def chat(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: Optional[List[Dict]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """发送聊天请求"""
        try:
            # 调用 AstrBot Provider 的 chat 方法
            if hasattr(self._astrbot_provider, "chat"):
                response = await self._astrbot_provider.chat(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    tools=tools,
                    **kwargs,
                )

                # 转换响应格式
                if hasattr(response, "content"):
                    return {
                        "content": response.content,
                        "tool_calls": getattr(response, "tool_calls", None),
                        "usage": getattr(response, "usage", None),
                        "model": getattr(response, "model", self.model_name),
                    }
                elif isinstance(response, dict):
                    return response
                else:
                    return {"content": str(response)}

            raise NotImplementedError("Provider does not support chat method")

        except Exception as e:
            logger.error(f"[{self.provider_id}] Chat failed: {e}")
            raise

    async def chat_stream(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: Optional[List[Dict]] = None,
        **kwargs,
    ) -> AsyncIterator[Dict[str, Any]]:
        """流式聊天"""
        try:
            # 调用 AstrBot Provider 的 chat_stream 方法
            if hasattr(self._astrbot_provider, "chat_stream"):
                async for chunk in self._astrbot_provider.chat_stream(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    tools=tools,
                    **kwargs,
                ):
                    if hasattr(chunk, "content"):
                        yield {
                            "content": chunk.content,
                            "tool_calls": getattr(chunk, "tool_calls", None),
                            "finish_reason": getattr(chunk, "finish_reason", None),
                        }
                    elif isinstance(chunk, dict):
                        yield chunk
                    else:
                        yield {"content": str(chunk)}
            else:
                # 如果没有 stream 方法，使用普通 chat 并模拟流式
                response = await self.chat(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    tools=tools,
                    **kwargs,
                )
                yield response

        except Exception as e:
            logger.error(f"[{self.provider_id}] Chat stream failed: {e}")
            raise


class ProviderAdapterFactory:
    """
    Provider 适配器工厂

    根据 AstrBot Provider 类型创建对应的适配器。
    """

    # 适配器映射表
    ADAPTER_MAP = {
        # OpenAI 兼容的 Provider
        "openai": OpenAICompatibleAdapter,
        "deepseek": OpenAICompatibleAdapter,
        "siliconflow": OpenAICompatibleAdapter,
        "groq": OpenAICompatibleAdapter,
        "xai": OpenAICompatibleAdapter,
        "openrouter": OpenAICompatibleAdapter,
        "minimax": OpenAICompatibleAdapter,
        "zhipu": OpenAICompatibleAdapter,
        "kimi": OpenAICompatibleAdapter,
        "longcat": OpenAICompatibleAdapter,
        # Anthropic
        "anthropic": AnthropicAdapter,
        # 默认使用 OpenAI 兼容适配器
        "default": OpenAICompatibleAdapter,
    }

    @classmethod
    def create_adapter(
        cls,
        astrbot_provider,
        config: Dict[str, Any],
    ) -> AstrBotProviderAdapter:
        """
        创建适配器

        Args:
            astrbot_provider: AstrBot Provider 实例
            config: Provider 配置

        Returns:
            适配器实例
        """
        provider_type = config.get("type", "default").lower()
        adapter_class = cls.ADAPTER_MAP.get(provider_type, cls.ADAPTER_MAP["default"])

        return adapter_class(astrbot_provider, config)

    @classmethod
    def register_adapter(cls, provider_type: str, adapter_class: type):
        """
        注册适配器

        Args:
            provider_type: Provider 类型
            adapter_class: 适配器类
        """
        cls.ADAPTER_MAP[provider_type.lower()] = adapter_class


# 导出
__all__ = [
    "AstrBotProviderAdapter",
    "OpenAICompatibleAdapter",
    "AnthropicAdapter",
    "ProviderAdapterFactory",
]
