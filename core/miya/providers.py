"""
AI 提供商管理器 - Providers

35+ AI 提供商统一管理
"""

import logging
from typing import Dict, Optional, Any

logger = logging.getLogger("miya.providers")


AVAILABLE_PROVIDERS = {
    # LLM
    "openai": "OpenAI",
    "claude": "Anthropic (Claude)",
    "gemini": "Google Gemini",
    "deepseek": "DeepSeek",
    "groq": "Groq",
    "xai": "xAI (Grok)",
    "moonshot": "月之暗面 (Moonshot)",
    "zhipu": "智谱 AI",
    "dashscope": "阿里云百炼",
    "openrouter": "OpenRouter",
    "ollama": "Ollama (本地)",
    "vllm": "vLLM (本地)",
    "xinference": "Xinference (本地)",
    "kimi_code": "Kimi Code",
    # STT
    "whisper": "Whisper",
    "sensevoice": "SenseVoice",
    # TTS
    "edge_tts": "Edge TTS",
    "azure_tts": "Azure TTS",
    "fishaudio": "FishAudio",
    "gpt_sovits": "GPT-SoVITS",
    # Embedding
    "openai_embedding": "OpenAI Embedding",
    "gemini_embedding": "Gemini Embedding",
    # Rerank
    "bailian_rerank": "阿里云百炼 Rerank",
    "nvidia_rerank": "NVIDIA Rerank",
}


class ProviderManager:
    """AI 提供商管理器"""

    def __init__(self) -> None:
        self._providers: Dict[str, Any] = {}
        self._default_llm: Optional[str] = None

    def create(
        self, provider_type: str, api_key: str, model: str, **config
    ) -> Optional[Any]:
        """创建提供商"""
        if provider_type not in AVAILABLE_PROVIDERS:
            logger.warning(f"[Provider] 未知类型: {provider_type}")
            return None

        try:
            from core.ai_client import AIClientFactory

            client = AIClientFactory.create_client(
                provider_type,
                api_key=api_key,
                model=model,
                **config,
            )
            self._providers[provider_type] = client
            logger.info(f"[Provider] 创建: {provider_type}")
            return client
        except Exception as e:
            logger.error(f"[Provider] 创建失败: {e}")
            return None

    def get(self, provider_type: str) -> Optional[Any]:
        """获取提供商"""
        return self._providers.get(provider_type)

    def list_all(self) -> Dict[str, str]:
        """列出所有提供商"""
        return AVAILABLE_PROVIDERS.copy()


_provider_manager: Optional[ProviderManager] = None


def get_provider_manager() -> ProviderManager:
    global _provider_manager
    if _provider_manager is None:
        _provider_manager = ProviderManager()
    return _provider_manager


__all__ = ["ProviderManager", "get_provider_manager", "AVAILABLE_PROVIDERS"]
