"""
Provider Bridge - Provider 桥接器

将 core/provider (新架构) 与 core/ai_client (旧系统) 连接
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("miya.provider.bridge")


# Provider 映射表
_provider_map = {
    "openai": "OpenAIClient",
    "deepseek": "DeepSeekClient",
    "anthropic": "AnthropicClient",
    "zhipu": "ZhipuAIClient",
    # 新增
    "claude": "AnthropicClient",  # Claude = Anthropic
    "gemini": "GeminiClient",
    "groq": "GroqClient",
    "ollama": "OllamaClient",
    "siliconflow": "SiliconFlowClient",
}


def get_client_class(provider_type: str) -> Optional[str]:
    """获取客户端类名"""
    return _provider_map.get(provider_type.lower())


def register_provider_mapping(miya_type: str, client_class: str) -> None:
    """注册 Provider 映射"""
    _provider_map[miya_type] = client_class
    logger.info(f"[ProviderBridge] 注册映射: {miya_type} -> {client_class}")


def create_client(
    provider_type: str,
    api_key: str,
    model: str,
    **kwargs,
) -> Optional[Any]:
    """创建 AI 客户端"""
    from core.ai_client import AIClientFactory

    client_class = get_client_class(provider_type)
    if not client_class:
        logger.warning(f"[ProviderBridge] 未知 Provider: {provider_type}")
        return None

    try:
        client = AIClientFactory.create_client(
            client_class,
            api_key=api_key,
            model=model,
            **kwargs,
        )
        logger.info(f"[ProviderBridge] 创建客户端: {provider_type} ({model})")
        return client
    except Exception as e:
        logger.error(f"[ProviderBridge] 创建失败 {provider_type}: {e}")
        return None


async def chat(
    client: Any,
    prompt: str,
    contexts: list | None = None,
    **kwargs,
) -> str:
    """对话"""
    try:
        if hasattr(client, "chat"):
            return await client.chat(prompt, contexts, **kwargs)
        elif hasattr(client, "text_chat"):
            result = await client.text_chat(prompt, contexts, **kwargs)
            return result.content if hasattr(result, "content") else str(result)
    except Exception as e:
        logger.error(f"[ProviderBridge] 对话失败: {e}")
        return f"Error: {e}"


# 新增 Provider 客户端
def add_provider_clients():
    """添加新 Provider 客户端到工厂"""
    from core.ai_client import AIClientFactory

    # Gemini Client
    class GeminiClient:
        """Google Gemini 客户端"""

        def __init__(self, api_key: str, model: str, **kwargs):
            self.api_key = api_key
            self.model = model or "gemini-2.0-flash"
            self.base_url = kwargs.get(
                "base_url", "https://generativelanguage.googleapis.com/v1"
            )

        async def text_chat(self, prompt, contexts=None, **kwargs):
            import httpx

            headers = {"Content-Type": "application/json"}

            messages = []
            if contexts:
                messages.extend(contexts)
            messages.append({"role": "user", "parts": [{"text": prompt}]})

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/models/{self.model}:generateContent",
                    headers=headers,
                    json={"contents": messages},
                    timeout=kwargs.get("timeout", 60.0),
                )
                resp.raise_for_status()
                result = resp.json()
                return type(
                    "Response",
                    (),
                    {"content": result["candidates"][0]["content"]["parts"][0]["text"]},
                )()

    # Groq Client
    class GroqClient:
        """Groq 客户端"""

        def __init__(self, api_key: str, model: str, **kwargs):
            self.api_key = api_key
            self.model = model or "llama-3.1-70b-versatile"
            self.base_url = "https://api.groq.com/openai/v1"

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
                    "Response",
                    (),
                    {"content": result["choices"][0]["message"]["content"]},
                )()

    # Ollama Client
    class OllamaClient:
        """Ollama 本地客户端"""

        def __init__(self, api_key: str, model: str, **kwargs):
            self.api_key = ""
            self.model = model or "llama3.1"
            self.base_url = kwargs.get("base_url", "http://localhost:11434")

        async def text_chat(self, prompt, contexts=None, **kwargs):
            import httpx

            messages = []
            if contexts:
                messages.extend(contexts)
            messages.append({"role": "user", "content": prompt})

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/api/chat",
                    json={"model": self.model, "messages": messages},
                    timeout=kwargs.get("timeout", 120.0),
                )
                resp.raise_for_status()
                result = resp.json()
                return type("Response", (), {"content": result["message"]["content"]})()

    # SiliconFlow Client
    class SiliconFlowClient:
        """SiliconFlow 客户端"""

        def __init__(self, api_key: str, model: str, **kwargs):
            self.api_key = api_key
            self.model = model or "Qwen/Qwen2.5-7B-Instruct"
            self.base_url = "https://api.siliconflow.cn/v1"

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
                    "Response",
                    (),
                    {"content": result["choices"][0]["message"]["content"]},
                )()

    # 注册到工厂
    AIClientFactory.register("gemini", GeminiClient)
    AIClientFactory.register("groq", GroqClient)
    AIClientFactory.register("ollama", OllamaClient)
    AIClientFactory.register("siliconflow", SiliconFlowClient)

    logger.info("[ProviderBridge] 已添加新 Provider 客户端")


__all__ = [
    "ProviderBridge",
    "get_client_class",
    "register_provider_mapping",
    "create_client",
    "chat",
    "add_provider_clients",
]
