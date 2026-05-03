#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Provider 抽象基类定义

参考 AstrBot 的 Provider 体系设计
"""

import abc
import asyncio
import logging
import random
from typing import Optional, Literal, Any, AsyncGenerator

from .entities import (
    LLMResponse,
    TokenUsage,
    ProviderMeta,
    ProviderStatus,
    ProviderType,
    RerankResult,
    ToolCallsResult,
    HealthCheckResult,
)

logger = logging.getLogger(__name__)

Providers = Literal[
    "Provider", "STTProvider", "TTSProvider", "EmbeddingProvider", "RerankProvider"
]


class AbstractProvider(abc.ABC):
    """Provider 抽象基类"""

    def __init__(self, provider_config: dict, provider_settings: dict = None) -> None:
        super().__init__()
        self.provider_config = provider_config
        self.provider_settings = provider_settings or {}
        self._status = ProviderStatus.LOADING
        self._health_check_result: Optional[HealthCheckResult] = None
        self._last_error: Optional[str] = None

    def get_id(self) -> str:
        """获取 Provider ID"""
        return self.provider_config.get("id", "default")

    def get_type(self) -> str:
        """获取 Provider 类型"""
        return self.provider_config.get("type", "")

    def is_enabled(self) -> bool:
        """检查是否启用"""
        return self.provider_config.get("enable", True)

    @property
    def status(self) -> ProviderStatus:
        return self._status

    @status.setter
    def status(self, value: ProviderStatus):
        self._status = value

    async def test(self, timeout: float = 45.0) -> None:
        """测试 Provider 可用性"""
        raise NotImplementedError()

    def meta(self) -> ProviderMeta:
        """获取 Provider 元数据"""
        return ProviderMeta(
            id=self.get_id(),
            model=self.provider_config.get("model", ""),
            type=self.get_type(),
            provider_type=ProviderType.CHAT_COMPLETION,
        )


class Provider(AbstractProvider):
    """对话模型 Provider 基类"""

    def __init__(
        self,
        provider_config: dict,
        provider_settings: dict = None,
    ) -> None:
        super().__init__(provider_config, provider_settings)
        self.api_keys: list[str] = self._parse_keys()
        self._current_key_index: int = 0
        self._unavailable_keys: set[str] = set()
        self._failure_count: int = 0
        self._circuit_breaker_threshold: int = 5
        self._circuit_breaker_timeout: float = 60.0

    def _parse_keys(self) -> list[str]:
        """解析 API Keys"""
        keys = self.provider_config.get("keys", [])
        if isinstance(keys, str):
            keys = [keys]
        return [k for k in keys if k] if keys else [""]

    def get_current_key(self) -> str:
        """获取当前 API Key"""
        available_keys = [
            k for k in self.api_keys if k and k not in self._unavailable_keys
        ]
        if not available_keys:
            available_keys = self.api_keys
        if not available_keys:
            return ""
        return random.choice(available_keys)

    def set_key(self, key: str) -> None:
        """设置当前 Key"""
        if key in self.api_keys:
            self._current_key_index = self.api_keys.index(key)

    def mark_key_unavailable(self, key: str) -> None:
        """标记 Key 不可用"""
        self._unavailable_keys.add(key)
        logger.warning(f"[Provider] Key 已标记为不可用: {key[:8]}***")

    def reset_keys(self) -> None:
        """重置所有 Key 状态"""
        self._unavailable_keys.clear()
        self._failure_count = 0

    @property
    def is_circuit_open(self) -> bool:
        """检查熔断器是否打开"""
        return self._failure_count >= self._circuit_breaker_threshold

    def record_failure(self) -> None:
        """记录失败"""
        self._failure_count += 1
        if self._failure_count >= self._circuit_breaker_threshold:
            logger.warning(
                f"[Provider] {self.get_id()} 熔断器打开，连续失败 {self._failure_count} 次"
            )

    def record_success(self) -> None:
        """记录成功"""
        self._failure_count = 0

    @abc.abstractmethod
    async def get_models(self) -> list[str]:
        """获取支持的模型列表"""
        raise NotImplementedError

    @abc.abstractmethod
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
        raise NotImplementedError()

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
        if False:
            yield None
        raise NotImplementedError()

    async def pop_record(self, context: list) -> None:
        """弹出 context 第一条非系统提示词对话记录"""
        poped = 0
        indexs_to_pop = []
        for idx, record in enumerate(context):
            if record.get("role") == "system":
                continue
            indexs_to_pop.append(idx)
            poped += 1
            if poped == 2:
                break
        for idx in reversed(indexs_to_pop):
            context.pop(idx)

    async def test(self, timeout: float = 45.0) -> None:
        """测试 Provider 可用性"""
        try:
            await asyncio.wait_for(
                self.text_chat(prompt="REPLY `PONG` ONLY"),
                timeout=timeout,
            )
            self._status = ProviderStatus.AVAILABLE
        except Exception as e:
            self._status = ProviderStatus.UNAVAILABLE
            self._last_error = str(e)
            raise


class STTProvider(AbstractProvider):
    """语音转文字 Provider"""

    def __init__(self, provider_config: dict, provider_settings: dict = None) -> None:
        super().__init__(provider_config, provider_settings)

    @abc.abstractmethod
    async def get_text(self, audio_url: str) -> str:
        """获取音频的文本"""
        raise NotImplementedError

    async def test(self, timeout: float = 45.0) -> None:
        """测试 STT Provider"""
        import os

        sample_audio = self.provider_settings.get("test_audio_path")
        if sample_audio and os.path.exists(sample_audio):
            await asyncio.wait_for(self.get_text(sample_audio), timeout=timeout)
        else:
            logger.debug(f"STT Provider {self.get_id()} 测试跳过（无测试音频）")


class TTSProvider(AbstractProvider):
    """文字转语音 Provider"""

    def __init__(self, provider_config: dict, provider_settings: dict = None) -> None:
        super().__init__(provider_config, provider_settings)

    def support_stream(self) -> bool:
        """是否支持流式 TTS"""
        return False

    @abc.abstractmethod
    async def get_audio(self, text: str) -> str:
        """获取文本的音频，返回音频文件路径"""
        raise NotImplementedError

    async def get_audio_stream(
        self,
        text_queue: asyncio.Queue,
        audio_queue: asyncio.Queue,
    ) -> None:
        """流式 TTS 处理"""
        accumulated_text = ""
        while True:
            text_part = await text_queue.get()
            if text_part is None:
                if accumulated_text:
                    try:
                        audio_path = await self.get_audio(accumulated_text)
                        with open(audio_path, "rb") as f:
                            audio_data = f.read()
                        await audio_queue.put((accumulated_text, audio_data))
                    except Exception:
                        pass
                await audio_queue.put(None)
                break
            accumulated_text += text_part

    async def test(self, timeout: float = 45.0) -> None:
        """测试 TTS Provider"""
        audio_path = await asyncio.wait_for(self.get_audio("hi"), timeout=timeout)
        import os

        if os.path.exists(audio_path):
            if os.path.getsize(audio_path) == 0:
                raise Exception("TTS 生成音频为空")
            try:
                os.remove(audio_path)
            except Exception:
                pass
        self._status = ProviderStatus.AVAILABLE


class EmbeddingProvider(AbstractProvider):
    """Embedding Provider"""

    def __init__(self, provider_config: dict, provider_settings: dict = None) -> None:
        super().__init__(provider_config, provider_settings)

    @abc.abstractmethod
    async def get_embedding(self, text: str) -> list[float]:
        """获取文本的向量"""
        raise NotImplementedError

    @abc.abstractmethod
    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """批量获取文本的向量"""
        raise NotImplementedError

    @abc.abstractmethod
    def get_dim(self) -> int:
        """获取向量的维度"""
        raise NotImplementedError

    async def get_embeddings_batch(
        self,
        texts: list[str],
        batch_size: int = 16,
        tasks_limit: int = 3,
        max_retries: int = 3,
        progress_callback=None,
    ) -> list[list[float]]:
        """批量获取 Embedding（带并发控制）"""
        semaphore = asyncio.Semaphore(tasks_limit)
        all_embeddings: list[list[float]] = []
        failed_batches: list[tuple[int, list[str]]] = []
        completed_count = 0
        total_count = len(texts)

        async def process_batch(batch_idx: int, batch_texts: list[str]) -> None:
            nonlocal completed_count
            async with semaphore:
                for attempt in range(max_retries):
                    try:
                        batch_embeddings = await self.get_embeddings(batch_texts)
                        all_embeddings.extend(batch_embeddings)
                        completed_count += len(batch_texts)
                        if progress_callback:
                            await progress_callback(completed_count, total_count)
                        return
                    except Exception as e:
                        if attempt == max_retries - 1:
                            failed_batches.append((batch_idx, batch_texts))
                            raise Exception(
                                f"批次 {batch_idx} 处理失败，已重试 {max_retries} 次: {e}"
                            )
                        await asyncio.sleep(2**attempt)

        tasks = []
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i : i + batch_size]
            batch_idx = i // batch_size
            tasks.append(process_batch(batch_idx, batch_texts))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        errors = [r for r in results if isinstance(r, Exception)]
        if errors:
            raise Exception(f"有 {len(errors)} 个批次处理失败")

        return all_embeddings

    async def test(self, timeout: float = 45.0) -> None:
        """测试 Embedding Provider"""
        await asyncio.wait_for(self.get_embedding("test"), timeout=timeout)
        self._status = ProviderStatus.AVAILABLE


class RerankProvider(AbstractProvider):
    """重排序 Provider"""

    def __init__(self, provider_config: dict, provider_settings: dict = None) -> None:
        super().__init__(provider_config, provider_settings)

    @abc.abstractmethod
    async def rerank(
        self,
        query: str,
        documents: list[str],
        top_n: Optional[int] = None,
    ) -> list[RerankResult]:
        """获取重排序结果"""
        raise NotImplementedError

    async def test(self, timeout: float = 45.0) -> None:
        """测试 Rerank Provider"""
        result = await asyncio.wait_for(
            self.rerank("Apple", documents=["apple", "banana"]),
            timeout=timeout,
        )
        if not result:
            raise Exception("Rerank 返回空结果")
        self._status = ProviderStatus.AVAILABLE
