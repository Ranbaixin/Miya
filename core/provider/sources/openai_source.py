#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenAI Chat Provider 实现

提供 OpenAI API 的对话模型支持
"""

import json
import logging
import time
from typing import Optional, Any, AsyncGenerator, Literal

from openai import AsyncOpenAI

from ..entities import LLMResponse, TokenUsage
from ..provider import Provider
from ..register import register_provider, ProviderType

logger = logging.getLogger(__name__)


@register_provider(
    "openai_chat_completion",
    ProviderType.CHAT_COMPLETION,
    name="OpenAI",
    description="OpenAI 官方 API (GPT-4, GPT-3.5等)",
)
class OpenAIProvider(Provider):
    """OpenAI Chat Provider"""

    def __init__(self, provider_config: dict, provider_settings: dict = None) -> None:
        super().__init__(provider_config, provider_settings)
        self.api_base = provider_config.get("api_base", "https://api.openai.com/v1")
        self.model = provider_config.get("model", "gpt-4o")
        self.proxy = provider_config.get("proxy", "")
        self.timeout = provider_config.get("timeout", 60.0)
        self.max_retries = provider_config.get("max_retries", 3)

        self._client: Optional[AsyncOpenAI] = None

    @property
    def client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self.get_current_key(),
                base_url=self.api_base,
                timeout=self.timeout,
                proxy=self.proxy if self.proxy else None,
            )
        return self._client

    def _refresh_client(self) -> None:
        """刷新客户端（使用新的 API Key）"""
        self._client = None

    async def get_models(self) -> list[str]:
        """获取模型列表"""
        try:
            models = await self.client.models.list()
            return [m.id for m in models.data if "gpt" in m.id]
        except Exception as e:
            logger.error(f"获取模型列表失败: {e}")
            return [self.model]

    async def text_chat(
        self,
        prompt: Optional[str] = None,
        contexts: Optional[list] = None,
        system_prompt: Optional[str] = None,
        tools: Optional[Any] = None,
        tool_calls_result: Optional[list] = None,
        model: Optional[str] = None,
        image_urls: Optional[list] = None,
        audio_urls: Optional[list] = None,
        tool_choice: Literal["auto", "required"] = "auto",
        **kwargs,
    ) -> LLMResponse:
        """非流式对话"""
        start_time = time.time()
        messages = self._build_messages(prompt, contexts, system_prompt, image_urls)

        if tool_calls_result:
            messages.extend(tool_calls_result)

        use_model = model or self.model
        tools_dict = None
        if tools:
            tools_dict = self._convert_tools(tools)

        retry_count = 0
        last_error = None

        while retry_count < self.max_retries:
            try:
                if self.is_circuit_open:
                    raise Exception("熔断器已打开，请求被拒绝")

                response = await self.client.chat.completions.create(
                    model=use_model,
                    messages=messages,
                    tools=tools_dict,
                    tool_choice=tool_choice if tools_dict else None,
                    **kwargs,
                )

                self.record_success()
                return self._parse_response(response, time.time() - start_time)

            except Exception as e:
                last_error = e
                retry_count += 1
                self.record_failure()

                error_str = str(e).lower()
                if "429" in error_str or "rate_limit" in error_str:
                    chosen_key = self.get_current_key()
                    self.mark_key_unavailable(chosen_key)
                    self._refresh_client()

                if (
                    "content_filter" in error_str
                    or "safety" in error_str
                    or "invalid_image" in error_str
                ):
                    if image_urls and retry_count < self.max_retries:
                        logger.warning(f"图片导致错误，尝试去除图片重试: {e}")
                        messages = self._build_messages(
                            prompt, contexts, system_prompt, None
                        )
                        image_urls = None
                        continue

                if retry_count < self.max_retries:
                    wait_time = 2**retry_count
                    logger.warning(f"API 调用失败，重试 #{retry_count}: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"API 调用失败，已达最大重试次数: {e}")

        raise last_error or Exception("API 调用失败")

    async def text_chat_stream(
        self,
        prompt: Optional[str] = None,
        contexts: Optional[list] = None,
        system_prompt: Optional[str] = None,
        tools: Optional[Any] = None,
        tool_calls_result: Optional[list] = None,
        model: Optional[str] = None,
        image_urls: Optional[list] = None,
        audio_urls: Optional[list] = None,
        tool_choice: Literal["auto", "required"] = "auto",
        **kwargs,
    ) -> AsyncGenerator[LLMResponse, None]:
        """流式对话"""
        messages = self._build_messages(prompt, contexts, system_prompt, image_urls)

        if tool_calls_result:
            messages.extend(tool_calls_result)

        use_model = model or self.model
        tools_dict = self._convert_tools(tools) if tools else None

        try:
            stream = await self.client.chat.completions.create(
                model=use_model,
                messages=messages,
                tools=tools_dict,
                tool_choice=tool_choice if tools_dict else None,
                stream=True,
                **kwargs,
            )

            full_content = ""
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_content += content
                    yield LLMResponse(
                        role="assistant",
                        completion_text=content,
                        raw_completion=chunk,
                    )

            self.record_success()

        except Exception as e:
            self.record_failure()
            logger.error(f"流式调用失败: {e}")
            raise

    def _build_messages(
        self,
        prompt: Optional[str],
        contexts: Optional[list],
        system_prompt: Optional[str],
        image_urls: Optional[list],
    ) -> list[dict]:
        """构建消息列表"""
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        if contexts:
            for ctx in contexts:
                if isinstance(ctx, dict):
                    messages.append(ctx)
                elif hasattr(ctx, "model_dump"):
                    messages.append(ctx.model_dump())

        if prompt:
            content = prompt
            if image_urls:
                content = [{"type": "text", "text": prompt}]
                for img_url in image_urls:
                    content.append({"type": "image_url", "image_url": {"url": img_url}})
            messages.append({"role": "user", "content": content})

        return messages

    def _convert_tools(self, tools: Any) -> Optional[list]:
        """转换工具格式"""
        if tools is None:
            return None
        if isinstance(tools, list):
            return tools
        if hasattr(tools, "get_tools_schema"):
            return tools.get_tools_schema()
        if hasattr(tools, "tools"):
            return tools.tools
        return None

    def _parse_response(self, response: Any, latency: float) -> LLMResponse:
        """解析响应"""
        choice = response.choices[0]
        message = choice.message

        tools_call_args = []
        tools_call_name = []
        tools_call_ids = []

        if message.tool_calls:
            for tc in message.tool_calls:
                tools_call_ids.append(tc.id or "")
                tools_call_name.append(tc.function.name if tc.function else "")
                tools_call_args.append(
                    json.loads(tc.function.arguments)
                    if tc.function and tc.function.arguments
                    else {}
                )

        usage = TokenUsage(
            input_tokens=response.usage.prompt_tokens if response.usage else 0,
            output_tokens=response.usage.completion_tokens if response.usage else 0,
        )

        return LLMResponse(
            role=message.role or "assistant",
            completion_text=message.content or "",
            tools_call_args=tools_call_args,
            tools_call_name=tools_call_name,
            tools_call_ids=tools_call_ids,
            raw_completion=response,
            usage=usage,
        )

    async def test(self, timeout: float = 45.0) -> None:
        """测试 Provider 可用性"""
        import asyncio

        await asyncio.wait_for(
            self.text_chat(prompt="Reply `PONG` only"),
            timeout=timeout,
        )


import asyncio
