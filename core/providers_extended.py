"""
MIYA Provider 完整版

支持更多模型类型: STT, TTS, Embedding, Rerank
"""

import logging
import base64
import json
import asyncio
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncIterator
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# ==================== STT Providers ====================


class STTProvider(ABC):
    """语音转文本 Provider 基类"""

    @abstractmethod
    async def speech_to_text(self, audio_path: str, **kwargs) -> str:
        """语音转文字"""
        pass

    @abstractmethod
    async def speech_to_text_url(self, audio_url: str, **kwargs) -> str:
        """URL转文字"""
        pass


class WhisperSTT(STTProvider):
    """OpenAI Whisper STT"""

    def __init__(self, config: Dict[str, Any]):
        self.api_key = config.get("api_key", "")
        self.base_url = config.get("base_url", "https://api.openai.com/v1")
        self.model = config.get("model", "whisper-1")
        self._client = None

    async def _ensure_client(self):
        if self._client is None:
            import httpx

            self._client = httpx.AsyncClient(
                headers={"Authorization": f"Bearer {self.api_key}"}
            )

    async def speech_to_text(self, audio_path: str, **kwargs) -> str:
        await self._ensure_client()

        # 读取音频文件
        with open(audio_path, "rb") as f:
            files = {"file": f}
            data = {"model": self.model}
            resp = await self._client.post(
                f"{self.base_url}/audio/transcriptions", files=files, data=data
            )

        return resp.json().get("text", "")


class SenseVoiceSTT(STTProvider):
    """SenseVoice 自托管 STT"""

    def __init__(self, config: Dict[str, Any]):
        self.base_url = config.get("base_url", "http://localhost:8080")
        self.model = config.get("model", "SenseVoice")

    async def speech_to_text(self, audio_path: str, **kwargs) -> str:
        import httpx

        with open(audio_path, "rb") as f:
            files = {"file": f}
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/v1/audio/transcriptions", files=files
                )

        return resp.json().get("text", "")


# ==================== TTS Providers ====================


class TTSProvider(ABC):
    """文本转语音 Provider 基类"""

    @abstractmethod
    async def text_to_speech(self, text: str, **kwargs) -> bytes:
        """文字转语音"""
        pass

    async def text_to_speech_url(self, text: str, **kwargs) -> str:
        """文字转语音，返回URL"""
        raise NotImplementedError


class EdgeTTS(TTSProvider):
    """Microsoft Edge TTS"""

    def __init__(self, config: Dict[str, Any]):
        self.voice = config.get("voice", "zh-CN-XiaoxiaoNeural")
        self.rate = config.get("rate", "+0%")
        self.volume = config.get("volume", "+0%")
        self.pitch = config.get("pitch", "+0Hz")

    async def text_to_speech(self, text: str, **kwargs) -> bytes:
        import edge_tts
        import asyncio

        communicate = edge_tts.Communicate(text, self.voice)

        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]

        return audio_data


class OpenAITTS(TTSProvider):
    """OpenAI TTS"""

    def __init__(self, config: Dict[str, Any]):
        self.api_key = config.get("api_key", "")
        self.model = config.get("model", "tts-1")
        self.voice = config.get("voice", "alloy")
        self.base_url = config.get("base_url", "https://api.openai.com/v1")

    async def text_to_speech(self, text: str, **kwargs) -> bytes:
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/audio/speech",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "voice": self.voice,
                    "input": text,
                },
            )

        return resp.content


class FishAudioTTS(TTSProvider):
    """FishAudio TTS"""

    def __init__(self, config: Dict[str, Any]):
        self.api_key = config.get("api_key", "")
        self.base_url = config.get("base_url", "https://api.fishaudio.com/v1")
        self.model_id = config.get("model_id", "")

    async def text_to_speech(self, text: str, **kwargs) -> bytes:
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/tts",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model_id": self.model_id,
                    "text": text,
                },
            )

        return resp.content


class VolcEngineTTS(TTSProvider):
    """火山引擎 TTS"""

    def __init__(self, config: Dict[str, Any]):
        self.app_id = config.get("app_id", "")
        self.token = config.get("token", "")
        self.cluster = config.get("cluster", "volcengine_streaming_common")

    async def text_to_speech(self, text: str, **kwargs) -> bytes:
        # 火山引擎 TTS 签名算法（简化版）
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://openspeech.bytedance.com/api/v2/tts",
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                },
                json={
                    "app": {"app_id": self.app_id},
                    "cluster": self.cluster,
                    "input": {"text": text},
                    "voice": {"voice_id": "zh-CN_XiaoxiaoNeural"},
                },
            )

        return resp.content


# ==================== Embedding Providers ====================


class EmbeddingProvider(ABC):
    """嵌入 Provider 基类"""

    @abstractmethod
    async def get_embedding(self, text: str, **kwargs) -> List[float]:
        """获取单个文本嵌入"""
        pass

    async def get_embeddings(self, texts: List[str], **kwargs) -> List[List[float]]:
        """批量获取嵌入"""
        return await asyncio.gather(*[self.get_embedding(t) for t in texts])


class OpenAIEmbedding(EmbeddingProvider):
    """OpenAI Embedding"""

    def __init__(self, config: Dict[str, Any]):
        self.api_key = config.get("api_key", "")
        self.model = config.get("model", "text-embedding-3-small")
        self.base_url = config.get("base_url", "https://api.openai.com/v1")

    async def get_embedding(self, text: str, **kwargs) -> List[float]:
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "input": text,
                },
            )

        data = resp.json()
        return data["data"][0]["embedding"]


class GeminiEmbedding(EmbeddingProvider):
    """Google Gemini Embedding"""

    def __init__(self, config: Dict[str, Any]):
        self.api_key = config.get("api_key", "")
        self.model = config.get("model", "text-embedding-004")

    async def get_embedding(self, text: str, **kwargs) -> List[float]:
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta2/models/{self.model}:embedText",
                params={"key": self.api_key},
                json={"content": {"role": "user", "parts": [{"text": text}]}},
            )

        return resp.json()["embedding"]["values"]


# ==================== Rerank Providers ====================


class RerankProvider(ABC):
    """重排序 Provider 基类"""

    @abstractmethod
    async def rerank(
        self, query: str, documents: List[str], top_k: int = 10, **kwargs
    ) -> List[Dict]:
        """重排序文档"""
        pass


class XINferenceRerank(RerankProvider):
    """XINference Rerank"""

    def __init__(self, config: Dict[str, Any]):
        self.base_url = config.get("base_url", "http://localhost:9997")
        self.model = config.get("model", "bge-reranker-v2-m3")

    async def rerank(
        self, query: str, documents: List[str], top_k: int = 10, **kwargs
    ) -> List[Dict]:
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/rerank",
                json={
                    "model": self.model,
                    "query": query,
                    "docs": documents,
                    "top_k": top_k,
                },
            )

        results = resp.json().get("results", [])
        return [
            {"index": r["index"], "score": r["score"]}
            for r in sorted(results, key=lambda x: x["score"], reverse=True)
        ]


# ==================== Provider 注册表 ====================


class ProviderRegistry:
    """Provider 注册表"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._providers: Dict[str, Any] = {}
        self._register_default_providers()
        self._initialized = True

    def _register_default_providers(self):
        """注册默认 Provider"""
        # LLM
        from core.providers_miya import (
            OpenAIProvider,
            DeepSeekProvider,
            AnthropicProvider,
            SiliconFlowProvider,
        )

        # 注册
        self._providers = {
            # LLM
            "openai": OpenAIProvider,
            "deepseek": DeepSeekProvider,
            "anthropic": AnthropicProvider,
            "siliconflow": SiliconFlowProvider,
            # STT
            "whisper": WhisperSTT,
            "sensevoice": SenseVoiceSTT,
            # TTS
            "edge_tts": EdgeTTS,
            "openai_tts": OpenAITTS,
            "fishaudio": FishAudioTTS,
            "volcengine_tts": VolcEngineTTS,
            # Embedding
            "openai_embedding": OpenAIEmbedding,
            "gemini_embedding": GeminiEmbedding,
            # Rerank
            "xinference_rerank": XINferenceRerank,
        }

        logger.info(f"[ProviderRegistry] 已注册 {len(self._providers)} 个 Provider")

    def get(self, name: str) -> Optional[Any]:
        """获取 Provider 类"""
        return self._providers.get(name)

    def list_providers(self) -> List[str]:
        """列出所有 Provider"""
        return list(self._providers.keys())

    def register(self, name: str, provider_cls: type):
        """注册新 Provider"""
        self._providers[name] = provider_cls
        logger.info(f"[ProviderRegistry] 注册 {name}")


def get_provider_registry() -> ProviderRegistry:
    return ProviderRegistry()


# 便捷函数
def create_provider(provider_type: str, config: Dict[str, Any]) -> Any:
    """创建 Provider 实例"""
    registry = get_provider_registry()
    provider_cls = registry.get(provider_type)
    if provider_cls:
        return provider_cls(config)
    return None


__all__ = [
    "STTProvider",
    "TTSProvider",
    "EmbeddingProvider",
    "RerankProvider",
    "ProviderRegistry",
    "get_provider_registry",
    "create_provider",
    # STT
    "WhisperSTT",
    "SenseVoiceSTT",
    # TTS
    "EdgeTTS",
    "OpenAITTS",
    "FishAudioTTS",
    "VolcEngineTTS",
    # Embedding
    "OpenAIEmbedding",
    "GeminiEmbedding",
    # Rerank
    "XINferenceRerank",
]
