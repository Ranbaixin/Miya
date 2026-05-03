"""
Miya Anthropic Provider
"""

import json
import logging
from typing import Literal

from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)


class AnthropicProvider:
    """Anthropic Claude Provider"""

    def __init__(self, provider_config: dict, provider_settings: dict) -> None:
        self.provider_config = provider_config
        self.provider_settings = provider_settings

        self.api_key = provider_config.get("key", [""])[0] or ""
        self.base_url = provider_config.get("api_base", "https://api.anthropic.com")
        self.timeout = provider_config.get("timeout", 120)
        self.model = provider_config.get("model", "claude-sonnet-4-20250514")
        self.thinking_config = provider_config.get("thinking_config", {})

        self.client = AsyncAnthropic(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
        )

        logger.info(f"[AnthropicProvider] 初始化: {self.model}")

    def meta(self):
        return {
            "id": self.provider_config.get("id", "anthropic"),
            "model": self.model,
            "type": "anthropic_chat_completion",
        }

    async def initialize(self) -> None:
        logger.info(f"[AnthropicProvider] {self.meta()['id']} 初始化完成")

    async def get_models(self) -> list[str]:
        return [self.model]

    async def text_chat(
        self,
        prompt: str | None = None,
        messages: list[dict] | None = None,
        system_prompt: str | None = None,
        tools: list[dict] | None = None,
        tool_choice: Literal["auto", "required", "none"] = "auto",
    ):
        system = system_prompt or ""
        all_messages = messages or []
        if prompt:
            all_messages.append({"role": "user", "content": prompt})

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system,
                messages=all_messages,
            )

            text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    text += block.text

            from .entities import LLMResponse, TokenUsage

            return LLMResponse(
                completion_text=text,
                model=self.model,
                usage=TokenUsage(
                    prompt_tokens=response.usage.input_tokens,
                    completion_tokens=response.usage.output_tokens,
                ),
            )
        except Exception as e:
            logger.error(f"[AnthropicProvider] API调用失败: {e}")
            from .entities import LLMResponse

            return LLMResponse(completion_text=f"API调用失败: {e}")


__all__ = ["AnthropicProvider"]
