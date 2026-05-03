"""
OpenAI 提供商

支持 GPT-4, GPT-4o, GPT-4o-mini 等模型
"""

import asyncio
import logging
from typing import Any

import httpx

from miya.core.provider import (
    ChatProvider,
    LLMResponse,
    register_provider,
)

logger = logging.getLogger("miya.provider.openai")

DEFAULT_BASE_URL = "https://api.openai.com/v1"


@register_provider("openai")
class OpenAIProvider(ChatProvider):
    def __init__(self, config: dict, settings: dict) -> None:
        super().__init__(config, settings)
        self.base_url = config.get("base_url", DEFAULT_BASE_URL)
        self._keys = config.get("key", [])
        if isinstance(self._keys, str):
            self._keys = [self._keys]
        self._current_key_index = 0
        self._organization = config.get("organization")

    def get_keys(self) -> list[str]:
        return self._keys or []

    def get_current_key(self) -> str:
        keys = self.get_keys()
        if not keys:
            return ""
        return keys[self._current_key_index % len(keys)]

    def set_key(self, key: str) -> None:
        if key in self._keys:
            self._current_key_index = self._keys.index(key)
        else:
            self._keys.append(key)
            self._current_key_index = len(self._keys) - 1

    async def get_models(self) -> list[str]:
        """获取可用模型"""
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{self.base_url}/models",
                    headers={"Authorization": f"Bearer {self.get_current_key()}"},
                    timeout=30.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return [m["id"] for m in data.get("data", [])]
            except Exception as e:
                logger.error(f"[OpenAI] 获取模型失败: {e}")
        return []

    async def text_chat(
        self,
        prompt: str | None = None,
        contexts: list[dict] | None = None,
        system_prompt: str | None = None,
        tools: Any = None,
        **kwargs,
    ) -> LLMResponse:
        """文本对话"""
        headers = {
            "Authorization": f"Bearer {self.get_current_key()}",
            "Content-Type": "application/json",
        }
        if self._organization:
            headers["OpenAI-Organization"] = self._organization

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if contexts:
            messages.extend(contexts)
        if prompt:
            messages.append({"role": "user", "content": prompt})

        data = {
            "model": self.model_name or "gpt-4o",
            "messages": messages,
        }

        if tools:
            data["tools"] = tools
            data["tool_choice"] = kwargs.get("tool_choice", "auto")

        if kwargs.get("temperature"):
            data["temperature"] = kwargs["temperature"]
        if kwargs.get("max_tokens"):
            data["max_tokens"] = kwargs["max_tokens"]
        if kwargs.get("stream"):
            data["stream"] = True

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=kwargs.get("timeout", 120.0),
                )
                resp.raise_for_status()
                result = resp.json()

                msg = result["choices"][0]["message"]
                return LLMResponse(
                    content=msg.get("content", ""),
                    tool_calls=msg.get("tool_calls"),
                    usage=result.get("usage"),
                    model=result.get("model"),
                    finish_reason=result["choices"][0].get("finish_reason"),
                )
            except Exception as e:
                logger.error(f"[OpenAI] 对话失败: {e}")
                return LLMResponse(content=f"Error: {e}")

    async def text_chat_stream(
        self, prompt, contexts=None, system_prompt=None, tools=None, **kwargs
    ):
        """流式对话"""
        # 简化实现
        response = await self.text_chat(
            prompt, contexts, system_prompt, tools, **kwargs
        )
        yield response
        yield response


__all__ = ["OpenAIProvider"]
