"""
Miya Provider 抽象基类
融合 AstrBot + Miya 两家之长
"""

import abc
import asyncio
import os
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal, Optional, Union

import logging

logger = logging.getLogger(__name__)


class ProviderType(Enum):
    """Provider 类型枚举"""

    CHAT_COMPLETION = "chat_completion"
    SPEECH_TO_TEXT = "speech_to_text"
    TEXT_TO_SPEECH = "text_to_speech"
    EMBEDDING = "embedding"
    RERANK = "rerank"


@dataclass
class ProviderMeta:
    """Provider 元数据"""

    id: str
    model: str
    type: str
    provider_type: ProviderType = ProviderType.CHAT_COMPLETION
    display_name: str = ""
    description: str = ""


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


class AbstractProvider(abc.ABC):
    """Provider 抽象基类"""

    def __init__(self, provider_config: dict, provider_settings: dict) -> None:
        self.provider_config = provider_config
        self.provider_settings = provider_settings
        self.model_name = ""
        self._initialized = False

    def set_model(self, model_name: str) -> None:
        self.model_name = model_name

    def get_model(self) -> str:
        return self.model_name

    def meta(self) -> ProviderMeta:
        return ProviderMeta(
            id=self.provider_config.get("id", "default"),
            model=self.get_model(),
            type=self.provider_config.get("type", "unknown"),
            provider_type=ProviderType.CHAT_COMPLETION,
            display_name=self.provider_config.get("display_name", ""),
            description=self.provider_config.get("description", ""),
        )

    async def initialize(self) -> None:
        """初始化 Provider"""
        self._initialized = True
        logger.info(f"[Provider] {self.meta().id} 初始化完成")

    async def test(self, timeout: float = 30.0) -> bool:
        """测试 Provider 可用性"""
        try:
            await asyncio.wait_for(self.text_chat(prompt="ping"), timeout=timeout)
            logger.info(f"[Provider] {self.meta().id} 测试通过")
            return True
        except Exception as e:
            logger.warning(f"[Provider] {self.meta().id} 测试失败: {e}")
            return False

    def get_current_key(self) -> str:
        """获取当前 API Key"""
        keys = self.get_keys()
        return keys[0] if keys else ""

    def get_keys(self) -> list[str]:
        keys = self.provider_config.get("key", [])
        if isinstance(keys, str):
            keys = [keys]
        return keys or [""]


class LLMProvider(AbstractProvider):
    """LLM Provider - 融合 AstrBot 和 Miya 的最佳特性"""

    def __init__(self, provider_config: dict, provider_settings: dict) -> None:
        super().__init__(provider_config, provider_settings)
        self.timeout = provider_config.get("timeout", 120)
        self.max_tokens = provider_config.get("max_tokens", 4096)
        self.temperature = provider_config.get("temperature", 0.7)
        self.reasoning_key = "reasoning_content"

    @abc.abstractmethod
    async def text_chat(
        self,
        prompt: str | None = None,
        messages: list[dict] | None = None,
        system_prompt: str | None = None,
        tools: list[dict] | None = None,
        tool_choice: Literal["auto", "required", "none"] = "auto",
        extra: dict | None = None,
    ) -> LLMResponse:
        """文本对话"""
        raise NotImplementedError

    @abc.abstractmethod
    async def text_chat_stream(
        self,
        prompt: str | None = None,
        messages: list[dict] | None = None,
        system_prompt: str | None = None,
        tools: list[dict] | None = None,
        tool_choice: Literal["auto", "required", "none"] = "auto",
    ) -> AsyncGenerator[LLMResponse, None]:
        """流式文本对话"""
        if False:
            yield LLMResponse()
        raise NotImplementedError()

    @abc.abstractmethod
    async def get_models(self) -> list[str]:
        """获取可用模型列表"""
        raise NotImplementedError

    def _build_messages(
        self,
        prompt: str | None = None,
        messages: list[dict] | None = None,
        system_prompt: str | None = None,
    ) -> list[dict]:
        """构建消息列表 - Miya 的最佳实践"""
        result = []
        if system_prompt:
            result.append({"role": "system", "content": system_prompt})
        if messages:
            result.extend(messages)
        if prompt:
            result.append({"role": "user", "content": prompt})
        return result

    async def chat(
        self,
        prompt: str | None = None,
        messages: list[dict] | None = None,
        system_prompt: str | None = None,
        tools: list[dict] | None = None,
        tool_choice: Literal["auto", "required", "none"] = "auto",
    ) -> str:
        """简便聊天接口 - 返回纯文本"""
        response = await self.text_chat(
            prompt=prompt,
            messages=messages,
            system_prompt=system_prompt,
            tools=tools,
            tool_choice=tool_choice,
        )
        return response.completion_text

    async def chat_with_functions(
        self,
        prompt: str,
        system_prompt: str,
        tools: list[dict],
        max_iterations: int = 10,
    ) -> tuple[str, list[dict]]:
        """带工具调用的聊天 - Miya 的核心能力"""
        messages = [{"role": "system", "content": system_prompt}]
        current_messages = messages.copy()
        current_messages.append({"role": "user", "content": prompt})

        iteration = 0
        while iteration < max_iterations:
            response = await self.text_chat(
                messages=current_messages,
                tools=tools,
                tool_choice="auto",
            )

            if not response.tool_calls:
                return response.completion_text, []

            tool_results = []
            for tool_call in response.tool_calls:
                tool_name = tool_call.get("function", {}).get("name", "")
                tool_args = tool_call.get("function", {}).get("arguments", {})

                current_messages.append(
                    {
                        "role": "assistant",
                        "content": response.completion_text,
                        "tool_calls": [tool_call],
                    }
                )

                result = {
                    "content": f"Tool {tool_name} executed",
                    "tool_call_id": tool_call.get("id"),
                }
                tool_results.append(result)

                current_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.get("id"),
                        "content": result["content"],
                    }
                )

            iteration += 1

        return response.completion_text, tool_results


class TTSProvider(AbstractProvider):
    """TTS Provider"""

    def __init__(self, provider_config: dict, provider_settings: dict) -> None:
        super().__init__(provider_config, provider_settings)
        self.voice = provider_config.get("voice", "alloy")
        self.speed = provider_config.get("speed", 1.0)

    def support_stream(self) -> bool:
        return False

    @abc.abstractmethod
    async def get_audio(self, text: str) -> str:
        """获取音频文件路径"""
        raise NotImplementedError

    async def get_audio_stream(
        self,
        text_queue: asyncio.Queue[str | None],
        audio_queue: "asyncio.Queue[bytes | tuple[str, bytes] | None]",
    ) -> None:
        """流式 TTS"""
        accumulated_text = ""
        while True:
            text_part = await text_queue.get()
            if text_part is None:
                if accumulated_text:
                    audio_path = await self.get_audio(accumulated_text)
                    with open(audio_path, "rb") as f:
                        audio_data = f.read()
                    await audio_queue.put((accumulated_text, audio_data))
                await audio_queue.put(None)
                break
            accumulated_text += text_part


class STTProvider(AbstractProvider):
    """STT Provider"""

    @abc.abstractmethod
    async def get_text(self, audio_url: str) -> str:
        """语音转文本"""
        raise NotImplementedError

    async def test(self, timeout: float = 30.0) -> bool:
        sample_audio = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "samples",
            "stt_test.wav",
        )
        if os.path.exists(sample_audio):
            await self.get_text(sample_audio)
        return True


class EmbeddingProvider(AbstractProvider):
    """Embedding Provider"""

    @abc.abstractmethod
    async def get_embedding(self, text: str) -> list[float]:
        """获取文本向量"""
        raise NotImplementedError

    @abc.abstractmethod
    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """批量获取向量"""
        raise NotImplementedError

    @abc.abstractmethod
    def get_dim(self) -> int:
        """向量维度"""
        raise NotImplementedError


class RerankProvider(AbstractProvider):
    """Rerank Provider"""

    @abc.abstractmethod
    async def rerank(
        self,
        query: str,
        documents: list[str],
        top_n: int | None = None,
    ) -> list[dict]:
        """重排序"""
        raise NotImplementedError
