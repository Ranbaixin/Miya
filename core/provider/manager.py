#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Provider 管理器

统一管理所有类型的 Provider
"""

import asyncio
import copy
import logging
import os
import time
from typing import Optional, Callable, Dict, List, Any

from .entities import (
    ProviderType,
    ProviderStatus,
    HealthCheckResult,
)
from .provider import (
    Provider,
    STTProvider,
    TTSProvider,
    EmbeddingProvider,
    RerankProvider,
    AbstractProvider,
    Providers,
)
from .register import provider_cls_map

logger = logging.getLogger(__name__)


class ProviderManager:
    """Provider 管理器"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.providers_config: list = []
        self.provider_settings: dict = {}
        self.provider_stt_settings: dict = {}
        self.provider_tts_settings: dict = {}

        self.provider_insts: List[Provider] = []
        self.stt_provider_insts: List[STTProvider] = []
        self.tts_provider_insts: List[TTSProvider] = []
        self.embedding_provider_insts: List[EmbeddingProvider] = []
        self.rerank_provider_insts: List[RerankProvider] = []

        self.inst_map: Dict[str, Providers] = {}

        self.curr_provider_inst: Optional[Provider] = None
        self.curr_stt_provider_inst: Optional[STTProvider] = None
        self.curr_tts_provider_inst: Optional[TTSProvider] = None

        self._provider_change_callback: Optional[Callable] = None
        self._provider_change_hooks: List[Callable] = []
        self._health_check_task: Optional[asyncio.Task] = None
        self._session_provider_map: Dict[str, str] = {}

        self._initialized = True

    def set_provider_change_callback(self, cb: Callable) -> None:
        """设置 Provider 变更回调"""
        self._provider_change_callback = cb

    def register_provider_change_hook(self, hook: Callable) -> None:
        """注册 Provider 变更钩子"""
        if hook not in self._provider_change_hooks:
            self._provider_change_hooks.append(hook)

    def _notify_provider_changed(
        self, provider_id: str, provider_type: ProviderType, umo: Optional[str] = None
    ) -> None:
        """通知 Provider 变更"""
        if self._provider_change_callback:
            try:
                self._provider_change_callback(provider_id, provider_type, umo)
            except Exception as e:
                logger.warning(f"Provider 变更回调失败: {e}")
        for hook in self._provider_change_hooks:
            if hook == self._provider_change_callback:
                continue
            try:
                hook(provider_id, provider_type, umo)
            except Exception as e:
                logger.warning(f"Provider 变更钩子失败: {e}")

    async def set_provider(
        self,
        provider_id: str,
        provider_type: ProviderType,
        umo: Optional[str] = None,
    ) -> None:
        """设置 Provider"""
        if provider_id not in self.inst_map:
            raise ValueError(f"Provider {provider_id} 不存在")

        if umo:
            self._session_provider_map[f"{umo}_{provider_type.value}"] = provider_id
            self._notify_provider_changed(provider_id, provider_type, umo)
            return

        prov = self.inst_map.get(provider_id)
        if provider_type == ProviderType.TEXT_TO_SPEECH and isinstance(
            prov, TTSProvider
        ):
            self.curr_tts_provider_inst = prov
            self._notify_provider_changed(provider_id, provider_type, umo)
        elif provider_type == ProviderType.SPEECH_TO_TEXT and isinstance(
            prov, STTProvider
        ):
            self.curr_stt_provider_inst = prov
            self._notify_provider_changed(provider_id, provider_type, umo)
        elif provider_type == ProviderType.CHAT_COMPLETION and isinstance(
            prov, Provider
        ):
            self.curr_provider_inst = prov
            self._notify_provider_changed(provider_id, provider_type, umo)

    def get_provider_by_id(self, provider_id: str) -> Optional[Providers]:
        """根据 ID 获取 Provider"""
        return self.inst_map.get(provider_id)

    def get_using_provider(
        self, provider_type: ProviderType, umo: Optional[str] = None
    ) -> Optional[Providers]:
        """获取当前使用的 Provider"""
        if umo:
            session_key = f"{umo}_{provider_type.value}"
            provider_id = self._session_provider_map.get(session_key)
            if provider_id:
                return self.inst_map.get(provider_id)

        if provider_type == ProviderType.CHAT_COMPLETION:
            return self.curr_provider_inst or (
                self.provider_insts[0] if self.provider_insts else None
            )
        elif provider_type == ProviderType.SPEECH_TO_TEXT:
            return self.curr_stt_provider_inst or (
                self.stt_provider_insts[0] if self.stt_provider_insts else None
            )
        elif provider_type == ProviderType.TEXT_TO_SPEECH:
            return self.curr_tts_provider_inst or (
                self.tts_provider_insts[0] if self.tts_provider_insts else None
            )
        elif provider_type == ProviderType.EMBEDDING:
            return (
                self.embedding_provider_insts[0]
                if self.embedding_provider_insts
                else None
            )
        elif provider_type == ProviderType.RERANK:
            return self.rerank_provider_insts[0] if self.rerank_provider_insts else None

        return None

    async def initialize(self, config: dict) -> None:
        """初始化 Provider"""
        self.providers_config = config.get("providers", [])
        self.provider_settings = config.get("provider_settings", {})
        self.provider_stt_settings = config.get("provider_stt_settings", {})
        self.provider_tts_settings = config.get("provider_tts_settings", {})

        for provider_config in self.providers_config:
            try:
                await self.load_provider(provider_config)
            except Exception as e:
                logger.error(f"加载 Provider 失败: {e}")

        if self.provider_insts and not self.curr_provider_inst:
            self.curr_provider_inst = self.provider_insts[0]

    def dynamic_import_provider(self, provider_type: str) -> None:
        """动态导入 Provider 模块"""
        type_mapping = {
            "openai_chat_completion": (
                "core.provider.sources.openai_source",
                "OpenAIProvider",
            ),
            "deepseek_chat_completion": (
                "core.provider.sources.deepseek_source",
                "DeepSeekProvider",
            ),
            "anthropic_chat_completion": (
                "core.provider.sources.anthropic_source",
                "AnthropicProvider",
            ),
            "zhipu_chat_completion": (
                "core.provider.sources.zhipu_source",
                "ZhipuProvider",
            ),
            "siliconflow_chat_completion": (
                "core.provider.sources.siliconflow_source",
                "SiliconFlowProvider",
            ),
            "gemini_chat_completion": (
                "core.provider.sources.gemini_source",
                "GeminiProvider",
            ),
            "openai_tts_api": (
                "core.provider.sources.openai_tts_source",
                "OpenAITTSProvider",
            ),
            "edge_tts": ("core.provider.sources.edge_tts_source", "EdgeTTSProvider"),
            "openai_whisper_api": (
                "core.provider.sources.whisper_source",
                "WhisperSTTProvider",
            ),
            "openai_embedding": (
                "core.provider.sources.openai_embedding_source",
                "OpenAIEmbeddingProvider",
            ),
        }

        if provider_type in type_mapping:
            module_path, class_name = type_mapping[provider_type]
            try:
                from importlib import import_module

                module = import_module(module_path)
                cls = getattr(module, class_name)
                provider_cls_map[provider_type] = type(
                    provider_cls_map.get(provider_type)
                )
                if hasattr(provider_cls_map[provider_type], "cls_type"):
                    provider_cls_map[provider_type].cls_type = cls
            except ImportError as e:
                logger.warning(f"Provider {provider_type} 导入失败: {e}")

    def _resolve_env_keys(self, provider_config: dict) -> dict:
        """解析环境变量 Key"""
        keys = provider_config.get("keys", provider_config.get("key", []))
        if not isinstance(keys, list):
            keys = [keys]
        resolved_keys = []
        for key in keys:
            if isinstance(key, str) and key.startswith("$"):
                env_key = key[1:]
                if env_key.startswith("{") and env_key.endswith("}"):
                    env_key = env_key[1:-1]
                env_val = os.getenv(env_key, "")
                resolved_keys.append(env_val)
            else:
                resolved_keys.append(key)
        provider_config["keys"] = resolved_keys
        return provider_config

    async def load_provider(self, provider_config: dict) -> None:
        """加载 Provider"""
        if not provider_config.get("enable", True):
            logger.info(f"Provider {provider_config.get('id')} 已禁用，跳过")
            return

        provider_type = provider_config.get("type", "")
        provider_id = provider_config.get("id", "")

        provider_config = self._resolve_env_keys(copy.deepcopy(provider_config))

        metadata = provider_cls_map.get(provider_type)
        if not metadata or not metadata.cls_type:
            self.dynamic_import_provider(provider_type)
            metadata = provider_cls_map.get(provider_type)

        if not metadata:
            logger.warning(f"未找到 Provider 类型: {provider_type}")
            return

        try:
            cls_type = metadata.cls_type
            inst = cls_type(provider_config, self.provider_settings)

            if isinstance(inst, Provider):
                self.provider_insts.append(inst)
                if self.provider_settings.get("default_provider_id") == provider_id:
                    self.curr_provider_inst = inst
                if not self.curr_provider_inst:
                    self.curr_provider_inst = inst
            elif isinstance(inst, STTProvider):
                self.stt_provider_insts.append(inst)
                if not self.curr_stt_provider_inst:
                    self.curr_stt_provider_inst = inst
            elif isinstance(inst, TTSProvider):
                self.tts_provider_insts.append(inst)
                if not self.curr_tts_provider_inst:
                    self.curr_tts_provider_inst = inst
            elif isinstance(inst, EmbeddingProvider):
                self.embedding_provider_insts.append(inst)
            elif isinstance(inst, RerankProvider):
                self.rerank_provider_insts.append(inst)

            self.inst_map[provider_id] = inst
            logger.info(f"已加载 Provider: {provider_type}({provider_id})")

        except Exception as e:
            logger.error(f"实例化 Provider 失败: {provider_id} - {e}")

    async def health_check_all(self, interval: float = 300.0) -> None:
        """定期健康检查"""
        while True:
            try:
                for provider_id, inst in self.inst_map.items():
                    if isinstance(inst, AbstractProvider):
                        try:
                            await inst.test(timeout=10.0)
                        except Exception as e:
                            inst.status = ProviderStatus.UNAVAILABLE
                            logger.warning(f"Provider {provider_id} 健康检查失败: {e}")
            except Exception as e:
                logger.error(f"健康检查任务失败: {e}")
            await asyncio.sleep(interval)

    def start_health_check(self, interval: float = 300.0) -> None:
        """启动健康检查任务"""
        if self._health_check_task is None or self._health_check_task.done():
            self._health_check_task = asyncio.create_task(
                self.health_check_all(interval), name="provider-manager:health-check"
            )

    def stop_health_check(self) -> None:
        """停止健康检查"""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                self._health_check_task.cancel()
            except asyncio.CancelledError:
                pass

    def get_available_providers(self, provider_type: ProviderType) -> List[Providers]:
        """获取可用的 Provider 列表"""
        if provider_type == ProviderType.CHAT_COMPLETION:
            return [
                p for p in self.provider_insts if p.status == ProviderStatus.AVAILABLE
            ]
        elif provider_type == ProviderType.SPEECH_TO_TEXT:
            return [
                p
                for p in self.stt_provider_insts
                if p.status == ProviderStatus.AVAILABLE
            ]
        elif provider_type == ProviderType.TEXT_TO_SPEECH:
            return [
                p
                for p in self.tts_provider_insts
                if p.status == ProviderStatus.AVAILABLE
            ]
        return []

    async def terminate(self) -> None:
        """终止所有 Provider"""
        self.stop_health_check()
        for inst in self.inst_map.values():
            if hasattr(inst, "terminate"):
                await inst.terminate()
        self.inst_map.clear()
        logger.info("ProviderManager 已终止")


_provider_manager_instance: Optional[ProviderManager] = None


def get_provider_manager() -> ProviderManager:
    """获取 ProviderManager 单例"""
    global _provider_manager_instance
    if _provider_manager_instance is None:
        _provider_manager_instance = ProviderManager()
    return _provider_manager_instance
