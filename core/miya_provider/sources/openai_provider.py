"""
Miya OpenAI Provider
融合 AstrBot 的完善实现 + Miya 的简便接口
"""

import json
from typing import Any, Literal

from openai import AsyncAzureOpenAI, AsyncOpenAI

from ..tools import get_logger
from .provider import LLMProvider, ProviderType
from .entities import LLMResponse, TokenUsage

logger = get_logger(__name__)


class OpenAIProvider(LLMProvider):
    """OpenAI API Provider - 融合两家之长"""

    def __init__(self, provider_config: dict, provider_settings: dict) -> None:
        super().__init__(provider_config, provider_settings)

        self.api_key = self.get_keys()[0] or ""
        self.base_url = provider_config.get("api_base", None)
        self.proxy = provider_config.get("proxy", "")
        self.timeout = provider_config.get("timeout", 120)
        self.api_version = provider_config.get("api_version", None)

        model = provider_config.get("model", "gpt-4o-mini")
        self.set_model(model)
        self.reasoning_key = "reasoning_content"

        if self.api_version:
            self.client = AsyncAzureOpenAI(
                api_key=self.api_key,
                api_version=self.api_version,
                base_url=self.base_url,
                timeout=self.timeout,
            )
        else:
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout,
            )

        logger.info(f"[OpenAIProvider] 初始化: {model}")

    def _create_http_client(self):
        """创建HTTP客户端"""
        return None

    async def initialize(self) -> None:
        await super().initialize()
        logger.info(f"[OpenAIProvider] {self.meta().id} 初始化完成")

    async def get_models(self) -> list[str]:
        try:
            models = await self.client.models.list()
            return sorted([m.id for m in models.data])
        except Exception as e:
            logger.warning(f"[OpenAIProvider] 获取模型列表失败: {e}")
            return [self.model_name]

    async def text_chat(
        self,
        prompt: str | None = None,
        messages: list[dict] | None = None,
        system_prompt: str | None = None,
        tools: list[dict] | None = None,
        tool_choice: Literal["auto", "required", "none"] = "auto",
        extra: dict | None = None,
    ) -> LLMResponse:
        messages = self._build_messages(prompt, messages, system_prompt)
        return await self._do_chat(messages, tools, tool_choice, extra or {})

    async def _do_chat(
        self,
        messages: list[dict],
        tools: list[dict] | None,
        tool_choice: str,
        extra: dict,
    ) -> LLMResponse:
        request_params = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        if tools:
            request_params["tools"] = tools
            if tool_choice == "required":
                tool_choice = "auto"
            request_params["tool_choice"] = tool_choice

        request_params.update(extra)

        try:
            completion = await self.client.chat.completions.create(**request_params)
        except Exception as e:
            logger.error(f"[OpenAIProvider] API调用失败: {e}")
            return LLMResponse(completion_text=f"API调用失败: {e}")

        choice = completion.choices[0]
        message = choice.message

        response = LLMResponse(
            completion_text=message.content or "",
            model=self.model_name,
            finish_reason=choice.finish_reason or "",
        )

        reasoning = getattr(message, "reasoning_content", None)
        if reasoning:
            response.reasoning_content = reasoning

        if message.tool_calls:
            response.tool_calls = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in message.tool_calls
            ]

        if completion.usage:
            response.usage = TokenUsage(
                prompt_tokens=completion.usage.prompt_tokens,
                completion_tokens=completion.usage.completion_tokens,
                total_tokens=completion.usage.total_tokens,
            )

        return response

    async def text_chat_stream(
        self,
        prompt: str | None = None,
        messages: list[dict] | None = None,
        system_prompt: str | None = None,
        tools: list[dict] | None = None,
        tool_choice: Literal["auto", "required", "none"] = "auto",
    ):
        messages = self._build_messages(prompt, messages, system_prompt)
        request_params = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": True,
        }

        if tools:
            request_params["tools"] = tools
            request_params["tool_choice"] = tool_choice

        try:
            stream = await self.client.chat.completions.create(**request_params)
            async for chunk in stream:
                choice = chunk.choices[0]
                delta = choice.delta

                response = LLMResponse(
                    completion_text=delta.content or "",
                    model=self.model_name,
                )

                if delta.tool_calls:
                    response.tool_calls = [
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in delta.tool_calls
                    ]

                yield response
        except Exception as e:
            logger.error(f"[OpenAIProvider] 流式调用失败: {e}")
            yield LLMResponse(completion_text=f"流式调用失败: {e}")


__all__ = ["OpenAIProvider"]
