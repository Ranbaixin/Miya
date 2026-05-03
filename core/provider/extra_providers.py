"""
更多 Provider 客户端

添加: Moonshot, OpenRouter, LocalAI, xAI 等
"""

import logging
from typing import Optional

logger = logging.getLogger("miya.provider.extra")

# 导入工厂
from core.ai_client import AIClientFactory


class MoonshotClient:
    """月之暗面 (Moonshot) 客户端"""

    def __init__(self, api_key: str, model: str = "kimi-k2", **kwargs):
        self.api_key = api_key
        self.model = model or "kimi-k2"
        self.base_url = "https://api.moonshot.cn/v1"

    async def text_chat(self, prompt, contexts=None, **kwargs):
        import httpx

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        messages = []
        if contexts:
            messages.extend(contexts)
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json={"model": self.model, "messages": messages},
                timeout=kwargs.get("timeout", 60.0),
            )
            resp.raise_for_status()
            result = resp.json()
            return type(
                "Response", (), {"content": result["choices"][0]["message"]["content"]}
            )()


class OpenRouterClient:
    """OpenRouter 客户端 (聚合多模型)"""

    def __init__(self, api_key: str, model: str = "openai/gpt-4o", **kwargs):
        self.api_key = api_key
        self.model = model or "openai/gpt-4o"
        self.base_url = "https://openrouter.ai/api/v1"

    async def text_chat(self, prompt, contexts=None, **kwargs):
        import httpx

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://miya.chat",
            "X-Title": "Miya",
        }

        messages = []
        if contexts:
            messages.extend(contexts)
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json={"model": self.model, "messages": messages},
                timeout=kwargs.get("timeout", 60.0),
            )
            resp.raise_for_status()
            result = resp.json()
            return type(
                "Response", (), {"content": result["choices"][0]["message"]["content"]}
            )()


class LocalAIClient:
    """LocalAI 客户端 (本地部署)"""

    def __init__(self, api_key: str = "", model: str = "llama-3", **kwargs):
        self.api_key = ""
        self.model = model or "llama-3"
        self.base_url = kwargs.get("base_url", "http://localhost:8080")

    async def text_chat(self, prompt, contexts=None, **kwargs):
        import httpx

        messages = []
        if contexts:
            messages.extend(contexts)
        messages.append({"role": "user", "content": prompt})

        # 支持 v1/chat 和 v1/completions 两种 API
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    json={"model": self.model, "messages": messages},
                    timeout=kwargs.get("timeout", 120.0),
                )
            except Exception:
                # 备用 API
                resp = await client.post(
                    f"{self.base_url}/v1/completions",
                    json={"model": self.model, "prompt": prompt},
                    timeout=kwargs.get("timeout", 120.0),
                )

            resp.raise_for_status()
            result = resp.json()

            if "choices" in result:
                return type(
                    "Response",
                    (),
                    {"content": result["choices"][0]["message"]["content"]},
                )()
            else:
                return type(
                    "Response",
                    (),
                    {"content": result.get("text", "") or result.get("content", "")},
                )()


class xAIClient:
    """xAI (Grok) 客户端"""

    def __init__(self, api_key: str, model: str = "grok-2", **kwargs):
        self.api_key = api_key
        self.model = model or "grok-2"
        self.base_url = "https://api.x.ai/v1"

    async def text_chat(self, prompt, contexts=None, **kwargs):
        import httpx

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        messages = []
        if contexts:
            messages.extend(contexts)
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json={"model": self.model, "messages": messages},
                timeout=kwargs.get("timeout", 60.0),
            )
            resp.raise_for_status()
            result = resp.json()
            return type(
                "Response", (), {"content": result["choices"][0]["message"]["content"]}
            )()


class XinferenceClient:
    """Xinference 本地模型客户端"""

    def __init__(self, api_key: str = "", model: str = "llama3", **kwargs):
        self.api_key = ""
        self.model = model
        self.base_url = kwargs.get("base_url", "http://localhost:9997")

    async def text_chat(self, prompt, contexts=None, **kwargs):
        import httpx

        messages = []
        if contexts:
            messages.extend(contexts)
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/v1/chat/completions",
                json={"model": self.model, "messages": messages},
                timeout=kwargs.get("timeout", 180.0),
            )
            resp.raise_for_status()
            result = resp.json()
            return type(
                "Response", (), {"content": result["choices"][0]["message"]["content"]}
            )()


def register_extra_providers():
    """注册额外的 Provider"""
    AIClientFactory.register("moonshot", MoonshotClient)
    AIClientFactory.register("openrouter", OpenRouterClient)
    AIClientFactory.register("localai", LocalAIClient)
    AIClientFactory.register("xinference", XinferenceClient)
    AIClientFactory.register("xai", xAIClient)

    # 别名
    AIClientFactory.register("kimi", MoonshotClient)
    AIClientFactory.register("grok", xAIClient)

    logger.info(
        "[Provider] 已注册额外 Provider: moonshot, openrouter, localai, xinference, xai, kimi, grok"
    )


__all__ = [
    "MoonshotClient",
    "OpenRouterClient",
    "LocalAIClient",
    "xAIClient",
    "XinferenceClient",
    "register_extra_providers",
]
